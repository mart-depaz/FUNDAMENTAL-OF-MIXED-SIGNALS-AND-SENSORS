Oracle Always Free VPS deployment notes

Steps (summary):

1. Create an Oracle Cloud account and provision an "Always Free" Compute instance (Ubuntu 22.04 recommended).
   - Choose a public VM with at least 1GB RAM (the free tier provides this)
   - Configure SSH keys when creating the instance

2. Point a DNS A record for your domain to the public IP (recommended) so you can obtain a TLS cert.
   - If you don't have a domain, use the public IP (camera will not work on HTTP; get a domain or use Cloudflare DNS + proxy to provide HTTPS)

3. SSH into the instance and run the `deploy.sh` script provided in `deploy/oracle/deploy.sh`:

```bash
# on your local machine
scp -r deploy/oracle ubuntu@YOUR_INSTANCE_IP:~/
ssh ubuntu@YOUR_INSTANCE_IP
sudo bash ~/deploy.sh yourdomain.com
```

4. After deploy completes, verify:

- Nginx is running and serving your site
- Gunicorn is running via systemd
- Static files are served from `/home/ubuntu/attendance/staticfiles`
- If you provided a domain, certbot will have installed HTTPS automatically

Notes about camera access and HTTPS:
- Browser camera requires secure context (HTTPS) except on `localhost`.
- If you use the server IP without HTTPS the camera will be blocked by the browser.
- Use a domain and configure Let's Encrypt (certbot) as shown in the `deploy.sh` script.

Files added in this repo to help deployment:
- `deploy/oracle/gunicorn.service` - systemd template for gunicorn
- `deploy/oracle/nginx.conf` - nginx config template (set `server_name` to your domain)
- `deploy/oracle/deploy.sh` - deployment script to set up virtualenv, pip, collectstatic, migrate, systemd, nginx and certbot

Security recommendations:
- Do not run as root; the script uses `ubuntu` user and `www-data` group in templates.
- Store secrets in environment variables or a secrets manager; the script uses temp env exports for simplicity.
- For production, use a managed database or configure PostgreSQL with backups.

If you want, I can:
- Provide a ready-to-run `cloud-init` script to bootstrap the instance on creation
- Help you generate DNS records and set up a domain
- Walk you through running the `deploy.sh` step-by-step
