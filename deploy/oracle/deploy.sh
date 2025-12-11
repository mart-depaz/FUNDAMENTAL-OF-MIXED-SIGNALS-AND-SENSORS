#!/bin/bash
set -euo pipefail

# Usage: ./deploy.sh your_domain_or_ip
DOMAIN=${1:-}
PROJECT_DIR=/home/ubuntu/attendance
VENV_DIR="$PROJECT_DIR/.venv"
REPO_URL="https://github.com/mart-depaz/FUNDAMENTAL-OF-MIXED-SIGNALS-AND-SENSORS.git"

# Create user and directories (run as root)
# adduser --disabled-password --gecos "" ubuntu
mkdir -p $PROJECT_DIR
chown ubuntu:www-data $PROJECT_DIR

# Clone/update repo
if [ -d "$PROJECT_DIR/.git" ]; then
  cd $PROJECT_DIR && git pull origin main
else
  git clone $REPO_URL $PROJECT_DIR
fi

cd $PROJECT_DIR

# Create virtualenv
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Environment variables: create a .env or systemd environment
# Export minimal env vars (alternatively use systemd EnvironmentFile)
export PRODUCTION=true
export ORACLE=true
export SECRET_KEY="$(cat /dev/urandom | tr -dc 'A-Za-z0-9' | head -c32)"
export ALLOWED_HOSTS=${DOMAIN}

# Collect static and migrate
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Create run directory for gunicorn socket
sudo mkdir -p /run
sudo chown ubuntu:www-data /run

# Copy systemd service (adjust paths)
sudo cp deploy/oracle/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn

# Nginx
sudo apt-get update
sudo apt-get install -y nginx
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp deploy/oracle/nginx.conf /etc/nginx/sites-available/attendance
sudo ln -sf /etc/nginx/sites-available/attendance /etc/nginx/sites-enabled/attendance
sudo nginx -t
sudo systemctl restart nginx

# SSL with certbot (optional if you have a domain)
if [ -n "$DOMAIN" ]; then
  sudo apt-get install -y certbot python3-certbot-nginx
  sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m your-email@example.com
fi

echo "Deployment completed. Visit: http://$DOMAIN (or your server IP)"
