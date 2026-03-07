# Deployment Guide — ABA Authorization Agent

## Architecture

```
Browser (BCBA)
    │  HTTPS
    ▼
Nginx (TLS) → Streamlit App → Anthropic API
                   │
                SQLite DB
```

Single process, local SQLite, outbound HTTPS to Anthropic. ~$25-50/month total.

Push to GitHub → auto-deploys via GitHub Actions. After initial setup, you never SSH into the server again.

---

## Prerequisites

1. **Anthropic API key** with a signed BAA. Contact [Anthropic sales](https://www.anthropic.com/contact-sales). See [BAA docs](https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers).
2. **AWS Lightsail instance** ($5-10/month, BAA included). Create a $10 Ubuntu 22.04 instance in the [Lightsail console](https://lightsail.aws.amazon.com/).
3. **A domain name** with DNS pointed at your Lightsail static IP.
4. **GitHub repo** (private) containing this codebase.

---

## One-Time Server Setup (~15 minutes)

SSH into your Lightsail instance and run this entire block:

```bash
# Install dependencies
sudo apt update && sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx sqlite3

# Clone your repo
git clone https://github.com/<you>/<repo>.git /opt/aba-auth-agent
cd /opt/aba-auth-agent/aba-auth-agent

# Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set API key
cp .env.example .env
nano .env  # Set ANTHROPIC_API_KEY=sk-ant-...

# Remove default auth config (app will regenerate on first launch)
rm -f .streamlit/auth_config.yaml

# Create systemd service
sudo tee /etc/systemd/system/aba-auth-agent.service > /dev/null <<'UNIT'
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
UNIT

sudo systemctl enable --now aba-auth-agent

# Nginx reverse proxy
sudo tee /etc/nginx/sites-available/aba-auth-agent > /dev/null <<'NGINX'
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
NGINX

sudo ln -sf /etc/nginx/sites-available/aba-auth-agent /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# TLS certificate (auto-renews)
sudo certbot --nginx -d yourdomain.com

# Daily database backups
sudo tee /etc/cron.daily/backup-aba-db > /dev/null <<'CRON'
#!/bin/bash
BACKUP_DIR=/opt/aba-auth-agent/backups
mkdir -p "$BACKUP_DIR"
sqlite3 /opt/aba-auth-agent/aba-auth-agent/data/aba_auth.db ".backup '$BACKUP_DIR/aba_auth_$(date +%Y%m%d).db'"
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
CRON
sudo chmod +x /etc/cron.daily/backup-aba-db
```

App is live at `https://yourdomain.com`. Change the default password on first login.

---

## GitHub Actions Auto-Deploy

Add this file to your repo so pushes to `main` deploy automatically. You never need to SSH again after initial setup.

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]
    paths:
      - 'aba-auth-agent/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ubuntu
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/aba-auth-agent
            git pull origin main
            cd aba-auth-agent
            source .venv/bin/activate
            pip install -q -r requirements.txt
            sudo systemctl restart aba-auth-agent
```

### Set up the GitHub secrets

In your GitHub repo, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Your Lightsail static IP (e.g., `54.123.45.67`) |
| `SERVER_SSH_KEY` | The private key for your Lightsail instance (paste the full PEM contents) |

That's it. Push code → GitHub deploys it → app restarts.

---

## Post-Deploy Checklist

- [ ] Change default login credentials (`bcba_reviewer` / `changeme`)
- [ ] Verify HTTPS works
- [ ] Test the full workflow (upload → review → generate → export)
- [ ] Push a small change to verify GitHub Actions deploy works
- [ ] Confirm Anthropic BAA is signed
- [ ] Check backups are running (`ls /opt/aba-auth-agent/backups/`)

---

## Scaling Later

This handles 1-5 BCBAs. If you outgrow it:

- **More users:** Migrate SQLite → PostgreSQL (AWS RDS, ~$15/month). The queries in `data/store.py` are standard SQL and port directly.
- **Multiple clinics:** Scope data per user with the `user_id` column (already planned in the schema).
