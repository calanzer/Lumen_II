# Deployment Guide — ABA Authorization Agent

## Architecture

```
Browser (BCBA)
    │  HTTPS
    ▼
Nginx (TLS termination)
    │
    ▼
Streamlit App (Python 3.11)
    ├── SQLite (data/aba_auth.db)
    └── Anthropic API (Claude Sonnet)
```

Single Python process, local SQLite file, outbound HTTPS to Anthropic. No database server, no message queue, no container orchestration needed.

**Estimated cost:** ~$25-50/month (VPS + Anthropic API usage)

---

## Prerequisites

1. **Anthropic API key** with a signed BAA for HIPAA-compliant PHI processing. Contact [Anthropic sales](https://www.anthropic.com/contact-sales) to request a BAA for their HIPAA-ready API service. See [Anthropic BAA documentation](https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers).

2. **A VPS** with a HIPAA-eligible provider:
   - **AWS Lightsail** — $5-10/month, BAA via AWS
   - **Azure VM** (B1s) — ~$8/month, BAA via Microsoft

3. **A domain name** pointed at your VPS IP address.

---

## Step 1: Server Setup

SSH into your VPS and install dependencies:

```bash
sudo apt update && sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx sqlite3
```

## Step 2: Deploy the App

```bash
# Clone and install
git clone <your-repo-url> /opt/aba-auth-agent
cd /opt/aba-auth-agent/aba-auth-agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set your Anthropic API key
cp .env.example .env
nano .env  # Add: ANTHROPIC_API_KEY=sk-ant-...

# Delete the default auth config so it regenerates with your own password on first launch
rm -f .streamlit/auth_config.yaml
```

## Step 3: Create a systemd Service

```bash
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

Verify it's running: `curl http://127.0.0.1:8501/_stcore/health`

## Step 4: Nginx + TLS

```bash
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
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Get a TLS certificate (auto-renews)
sudo certbot --nginx -d yourdomain.com
```

The app is now live at `https://yourdomain.com`.

## Step 5: Database Backups

```bash
sudo tee /etc/cron.daily/backup-aba-db > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR=/opt/aba-auth-agent/backups
mkdir -p "$BACKUP_DIR"
sqlite3 /opt/aba-auth-agent/aba-auth-agent/data/aba_auth.db ".backup '$BACKUP_DIR/aba_auth_$(date +%Y%m%d).db'"
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
EOF

sudo chmod +x /etc/cron.daily/backup-aba-db
```

## Step 6: Set Login Credentials

On first launch, the app generates `.streamlit/auth_config.yaml` with a default user (`bcba_reviewer` / `changeme`). Change this immediately:

```bash
cd /opt/aba-auth-agent/aba-auth-agent
source .venv/bin/activate
python3 -c "
import bcrypt, yaml
password = input('New password: ')
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
config_path = '.streamlit/auth_config.yaml'
with open(config_path) as f:
    config = yaml.safe_load(f)
config['credentials']['usernames']['bcba_reviewer']['password'] = hashed
with open(config_path, 'w') as f:
    yaml.dump(config, f)
print('Password updated.')
"
sudo systemctl restart aba-auth-agent
```

To add additional BCBA users, edit `.streamlit/auth_config.yaml` directly.

---

## Updating

```bash
cd /opt/aba-auth-agent
git pull origin main
sudo systemctl restart aba-auth-agent
```

---

## Post-Deployment Checklist

- [ ] Change default login credentials
- [ ] Verify HTTPS works (not HTTP)
- [ ] Test the full workflow (upload, review, generate, export)
- [ ] Confirm Claude API calls succeed (run a test extraction)
- [ ] Verify daily backups are running (`ls /opt/aba-auth-agent/backups/`)
- [ ] Set up uptime monitoring (UptimeRobot free tier, ping `https://yourdomain.com/_stcore/health`)
- [ ] Confirm Anthropic BAA is signed
- [ ] Enable disk encryption on the VPS (AWS Lightsail: enabled by default)

---

## Scaling Later

This setup handles 1-5 BCBAs comfortably. If you grow beyond that:

- **More users:** Migrate SQLite to PostgreSQL (managed RDS or Cloud SQL, ~$15/month). The `data/store.py` queries are standard SQL and port directly.
- **Container deployment:** The included Dockerfile works with AWS ECS Fargate, Google Cloud Run, or Azure Container Apps. Mount a persistent volume for the SQLite file or use a managed database.
- **Multiple clinics:** Add the `user_id` column to scope data per authenticated user (the schema already has this field planned).
