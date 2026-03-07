# Deployment Guide — ABA Authorization Agent

This document covers how to deploy the ABA Authorization Agent for production use at a clinic. It addresses HIPAA compliance, infrastructure choices, and step-by-step instructions for each recommended provider.

---

## Architecture Overview

```
Browser (BCBA)
    │
    ▼
Streamlit App (Python 3.11+)
    │
    ├── SQLite database (local file: data/aba_auth.db)
    ├── Word templates (templates/*.docx)
    └── Anthropic API (Claude Sonnet for extraction + generation)
```

The app is a single Python process serving a Streamlit web UI. It stores all data in a local SQLite file and makes outbound HTTPS calls to the Anthropic API. There is no separate database server, no Redis, no message queue. This simplicity is intentional — it minimizes the attack surface and operational burden for a small clinic deployment.

---

## HIPAA Compliance Requirements

This app processes Protected Health Information (PHI). Any production deployment must satisfy these requirements:

### 1. Business Associate Agreement (BAA)

You need a signed BAA with every vendor that touches PHI:

| Vendor | Handles PHI? | BAA Available? | Notes |
|--------|-------------|----------------|-------|
| **Anthropic (direct API)** | Yes — progress report text sent to Claude API | **Yes** — contact Anthropic sales | Requires sales engagement, zero data retention, and HIPAA-ready service qualification. See [Anthropic BAA docs](https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers). |
| **AWS Bedrock** | Yes — Claude via Bedrock | Yes — automatic for HIPAA-eligible services | Enable HIPAA-eligible services in your AWS account |
| **Google Cloud Vertex AI** | Yes — Claude via Vertex | Yes — via GCP BAA | Sign via Cloud Console |
| **Azure** | Yes — Claude via Azure | Yes — via Microsoft BAA | Sign via Azure Trust Center |
| **AWS / GCP / Azure (hosting)** | Yes — if hosting the app | Yes | BAA covers both Claude access and infrastructure |
| **Streamlit Community Cloud** | Yes | **No** | Not suitable for production with PHI |
| **Railway / Render / Fly.io** | Yes | **No** | Not suitable for production with PHI |

**Three paths to a HIPAA-compliant Claude API:**

1. **Anthropic direct API with BAA** — Contact [Anthropic sales](https://www.anthropic.com/contact-sales) to request a BAA for their HIPAA-ready API service. This requires zero data retention and a qualification process. Simplest option if approved — no code changes needed, the app already uses `anthropic.Anthropic()`.

2. **AWS Bedrock** — Claude is available as a Bedrock foundation model, covered under your AWS BAA. Requires a one-line code change.

3. **Google Cloud Vertex AI** or **Azure** — Same story, Claude available through these providers under their respective BAAs.

For a small clinic, option 1 (direct Anthropic BAA) is the fastest path if you can get approved. For organizations already on AWS/GCP/Azure, option 2 or 3 avoids a separate vendor relationship.

### 2. Claude API Configuration

The app currently uses `anthropic.Anthropic()` (direct API). If you get a BAA directly from Anthropic, no code change is needed. If you route through a cloud provider, change the client constructor:

**AWS Bedrock:**
```python
# In pipeline/extractor.py and pipeline/generator.py
import anthropic

client = anthropic.AnthropicBedrock(
    aws_region="us-east-1",
)
```

**Google Vertex AI:**
```python
import anthropic

client = anthropic.AnthropicVertex(
    region="us-east5",
    project_id="your-gcp-project-id",
)
```

All three options are drop-in compatible — same `client.messages.create()` interface, same model names. The only change is the client constructor.

### 3. Encryption

- **In transit:** Streamlit serves over HTTP by default. You must terminate TLS in front of it (see reverse proxy setup below).
- **At rest:** The SQLite database file contains PHI. The host volume must use encrypted storage (AWS EBS encryption, GCP persistent disk encryption, or Azure disk encryption — all enabled by default on these providers).

### 4. Access Controls

- The app has built-in authentication via `streamlit-authenticator`.
- **Change the default password** before any deployment. Edit `.streamlit/auth_config.yaml` or delete it and let the app regenerate on first launch with a new password.
- For multi-user clinics, add additional users to the auth config.
- Consider placing the app behind a VPN or IP allowlist for additional access control.

### 5. Audit Logging

Not currently implemented. For a full HIPAA deployment, add logging of:
- Login/logout events
- Which client records were accessed
- Data exports (who exported what, when)

This can be added as a middleware layer or by extending `data/store.py`.

---

## Recommended Deployment: AWS (ECS Fargate)

This is the recommended approach for most clinics. It provides HIPAA compliance, automatic scaling, and no server management.

### Prerequisites

- AWS account with HIPAA-eligible services enabled
- AWS CLI configured
- Docker installed locally
- Anthropic access enabled in AWS Bedrock (request model access for Claude Sonnet in the AWS console)

### Step 1: Create a Dockerfile

Create `Dockerfile` in the `aba-auth-agent/` directory:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite (will be mounted as EFS volume)
RUN mkdir -p /app/data

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false"]
```

### Step 2: Build and push to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name aba-auth-agent --region us-east-1

# Build and push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker build -t aba-auth-agent .
docker tag aba-auth-agent:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/aba-auth-agent:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/aba-auth-agent:latest
```

### Step 3: Create EFS file system (persistent SQLite storage)

The SQLite database must survive container restarts. ECS Fargate containers are ephemeral, so mount an EFS volume.

```bash
# Create EFS file system (encrypted at rest by default)
aws efs create-file-system \
    --performance-mode generalPurpose \
    --encrypted \
    --tags Key=Name,Value=aba-auth-agent-data \
    --region us-east-1
```

Note the `FileSystemId` for the ECS task definition.

### Step 4: ECS task definition

Create `task-definition.json`:

```json
{
  "family": "aba-auth-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/aba-auth-agent-task-role",
  "containerDefinitions": [
    {
      "name": "aba-auth-agent",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/aba-auth-agent:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "mountPoints": [
        {
          "sourceVolume": "aba-data",
          "containerPath": "/app/data"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/aba-auth-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "aba-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "<efs-file-system-id>",
        "transitEncryption": "ENABLED"
      }
    }
  ]
}
```

The task role needs `bedrock:InvokeModel` permission for Claude Sonnet. Create an IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-*"
    }
  ]
}
```

### Step 5: ALB + TLS termination

Create an Application Load Balancer with an HTTPS listener and an ACM certificate:

```bash
# Create ALB (in the same VPC as ECS)
aws elbv2 create-load-balancer \
    --name aba-auth-agent-alb \
    --subnets <subnet-1> <subnet-2> \
    --security-groups <sg-id> \
    --scheme internet-facing

# Create target group for port 8501
aws elbv2 create-target-group \
    --name aba-agent-tg \
    --protocol HTTP \
    --port 8501 \
    --vpc-id <vpc-id> \
    --target-type ip \
    --health-check-path /_stcore/health

# Create HTTPS listener (requires ACM certificate)
aws elbv2 create-listener \
    --load-balancer-arn <alb-arn> \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=<acm-cert-arn> \
    --default-actions Type=forward,TargetGroupArn=<tg-arn>
```

### Step 6: Create the ECS service

```bash
aws ecs create-service \
    --cluster default \
    --service-name aba-auth-agent \
    --task-definition aba-auth-agent \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[<subnet-1>,<subnet-2>],securityGroups=[<sg-id>],assignPublicIp=DISABLED}" \
    --load-balancers targetGroupArn=<tg-arn>,containerName=aba-auth-agent,containerPort=8501
```

**Important:** Set `desired-count` to `1`. Streamlit + SQLite is a single-writer architecture. Running multiple replicas will cause database locking issues. If you need horizontal scaling, migrate to PostgreSQL first.

### Cost Estimate (AWS)

| Component | Monthly Cost |
|-----------|-------------|
| ECS Fargate (1 vCPU, 2GB, always-on) | ~$35 |
| ALB | ~$18 |
| EFS (1GB) | ~$0.30 |
| ECR (image storage) | ~$1 |
| CloudWatch Logs | ~$2 |
| **Infrastructure total** | **~$56/month** |
| Anthropic API via Bedrock (est. 30 clients/month) | ~$15-40/month |
| **Total** | **~$70-100/month** |

---

## Alternative: Google Cloud Run

Simpler than ECS but same HIPAA story — requires GCP BAA and Vertex AI for Claude API calls.

### Step 1: Build and push

```bash
# Build and push to Artifact Registry
gcloud builds submit --tag us-east1-docker.pkg.dev/<project>/aba-auth-agent/app:latest
```

### Step 2: Deploy

```bash
gcloud run deploy aba-auth-agent \
    --image us-east1-docker.pkg.dev/<project>/aba-auth-agent/app:latest \
    --region us-east1 \
    --port 8501 \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 1 \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=<project-id>"
```

**SQLite caveat:** Cloud Run containers have an ephemeral filesystem. You must mount a Cloud Storage FUSE bucket or a Filestore NFS volume for persistent SQLite storage. Alternatively, migrate to Cloud SQL (PostgreSQL).

### Cost Estimate (GCP)

| Component | Monthly Cost |
|-----------|-------------|
| Cloud Run (1 vCPU, 2GB, always-on) | ~$40 |
| Filestore (1TB minimum, NFS) | ~$200 |
| **Or** Cloud SQL (PostgreSQL, db-f1-micro) | ~$10 |
| Vertex AI Claude Sonnet calls | ~$15-40/month |
| **Total (with Cloud SQL)** | **~$65-90/month** |

> **Note:** Filestore's 1TB minimum makes it expensive for a tiny SQLite file. If deploying on GCP, migrating to Cloud SQL PostgreSQL is the more practical path.

---

## Alternative: Single VPS (Budget Option)

For a single clinic with 1-3 BCBAs, a simple VPS is the most cost-effective option. This requires more manual setup but costs $6-20/month.

**Suitable providers with HIPAA BAAs:**
- **AWS Lightsail** ($5-10/month, BAA via AWS)
- **Azure VM** (B1s, ~$8/month, BAA via Microsoft)

**Not suitable (no BAA):**
- DigitalOcean, Linode, Vultr, Hetzner

### Setup on AWS Lightsail

```bash
# SSH into the instance
ssh ubuntu@<lightsail-ip>

# Install Python 3.11
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx

# Clone the repo
git clone <your-repo-url> /opt/aba-auth-agent
cd /opt/aba-auth-agent/aba-auth-agent

# Create venv and install
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — use your Anthropic API key (with signed BAA)
# or configure Bedrock credentials instead

# Create systemd service
sudo tee /etc/systemd/system/aba-auth-agent.service > /dev/null <<'EOF'
[Unit]
Description=ABA Authorization Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/aba-auth-agent/aba-auth-agent
Environment="PATH=/opt/aba-auth-agent/aba-auth-agent/.venv/bin:/usr/bin"
ExecStart=/opt/aba-auth-agent/aba-auth-agent/.venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --browser.gatherUsageStats=false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable aba-auth-agent
sudo systemctl start aba-auth-agent
```

### Nginx reverse proxy with TLS

```bash
# Configure nginx
sudo tee /etc/nginx/sites-available/aba-auth-agent > /dev/null <<'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/aba-auth-agent /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get TLS certificate
sudo certbot --nginx -d yourdomain.com
```

### Backups (critical for SQLite)

```bash
# Daily backup cron job
sudo tee /etc/cron.daily/backup-aba-db > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR=/opt/aba-auth-agent/backups
mkdir -p "$BACKUP_DIR"
sqlite3 /opt/aba-auth-agent/aba-auth-agent/data/aba_auth.db ".backup '$BACKUP_DIR/aba_auth_$(date +%Y%m%d).db'"
# Keep last 30 days
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
EOF

sudo chmod +x /etc/cron.daily/backup-aba-db
```

### Cost Estimate (VPS)

| Component | Monthly Cost |
|-----------|-------------|
| AWS Lightsail (1 vCPU, 1GB) | $5 |
| Domain name | ~$1 |
| Anthropic API (direct, 30 clients/month) | ~$15-40 |
| **Total** | **~$20-45/month** |

---

## Deployment Decision Matrix

| Factor | AWS ECS | GCP Cloud Run | VPS |
|--------|---------|---------------|-----|
| HIPAA compliance | Full (Bedrock BAA) | Full (Vertex BAA) | Full (with Anthropic direct BAA) |
| Setup complexity | High | Medium | Low |
| Monthly cost | ~$70-100 | ~$65-90 | ~$20-45 |
| Maintenance burden | Low (managed) | Low (managed) | Medium (you patch the OS) |
| Auto-restart on crash | Yes | Yes | Yes (systemd) |
| TLS | ALB handles it | Automatic | Certbot (manual renewal) |
| Backups | EFS snapshots | Automatic | Manual cron |
| Multi-BCBA scaling | Needs PostgreSQL migration | Needs PostgreSQL migration | Works fine for 1-3 users |
| Best for | Clinics with existing AWS | Clinics with existing GCP | Single clinic, budget-conscious |

### Recommendation

- **Single clinic, 1-3 BCBAs, budget matters:** VPS on AWS Lightsail. $20/month, 30 minutes to set up.
- **Multi-clinic or compliance-first:** AWS ECS Fargate with Bedrock. Full HIPAA stack, ~$80/month.
- **Already on GCP:** Cloud Run with Vertex AI and Cloud SQL.

---

## Post-Deployment Checklist

- [ ] Change default login credentials (`bcba_reviewer` / `changeme`)
- [ ] Verify TLS is active (HTTPS, not HTTP)
- [ ] Set up automated database backups
- [ ] Test the full workflow end-to-end (upload → review → generate → export)
- [ ] Confirm Claude API calls work (check with a test extraction)
- [ ] Set up uptime monitoring (e.g., UptimeRobot free tier — ping `https://yourdomain.com/_stcore/health`)
- [ ] Document the deployment for the clinic's IT contact
- [ ] If using real PHI: confirm BAA is signed with all vendors
- [ ] If using real PHI: enable disk encryption on the host
- [ ] If using real PHI: restrict network access (VPN or IP allowlist)

---

## Updating the App

### VPS

```bash
cd /opt/aba-auth-agent
git pull origin main
sudo systemctl restart aba-auth-agent
```

### ECS Fargate

```bash
# Rebuild and push new image
docker build -t aba-auth-agent .
docker tag aba-auth-agent:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/aba-auth-agent:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/aba-auth-agent:latest

# Force new deployment
aws ecs update-service --cluster default --service aba-auth-agent --force-new-deployment
```

### Cloud Run

```bash
gcloud builds submit --tag us-east1-docker.pkg.dev/<project>/aba-auth-agent/app:latest
gcloud run deploy aba-auth-agent --image us-east1-docker.pkg.dev/<project>/aba-auth-agent/app:latest
```
