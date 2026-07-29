# Deploy

Single-user app (password + JWT), data stored as `.md` files.

---

## Option 1 — Direct server (simplest)

```bash
# in the project root
./run.sh
```

The server starts at `http://0.0.0.0:8000`. **No HTTPS** — use on a local network only, or behind a proxy.

---

## Option 2 — Systemd + reverse proxy (recommended)

### 2.1 Systemd service

`/etc/systemd/system/monthtrack.service`:

```ini
[Unit]
Description=monthTrack
After=network.target

[Service]
Type=simple
User=thiago
WorkingDirectory=/home/thiago/shared_HOME/vscode/monthTrack/backend
EnvironmentFile=/home/thiago/shared_HOME/vscode/monthTrack/backend/.env
ExecStart=/home/thiago/shared_HOME/vscode/monthTrack/backend/.venv/bin/uvicorn monthtrack.app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now monthtrack
```

### 2.2 Nginx (HTTPS with Let's Encrypt)

```nginx
server {
    listen 443 ssl;
    server_name monthtrack.exemplo.com;

    ssl_certificate     /etc/letsencrypt/live/monthtrack.exemplo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monthtrack.exemplo.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name monthtrack.exemplo.com;
    return 301 https://$server_name$request_uri;
}
```

### 2.3 Caddy (alternative, automatic HTTPS)

```caddy
monthtrack.exemplo.com {
    reverse_proxy 127.0.0.1:8000
}
```

---

## Option 3 — Docker (optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install .
CMD ["uvicorn", "monthtrack.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Mount the data directory as a volume:

```bash
docker build -t monthtrack .
docker run -d -p 8000:8000 \
  -e APP_PASSWORD=my_password \
  -e DATA_DIR=/data \
  -v /local/path/data:/data \
  monthtrack
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_PASSWORD` | no* | random | Access password |
| `DATA_DIR` | no | `data` | Directory for `.md` files |
| `APP_SECRET` | no | random | Key for signing JWT |

\* If not set, a random password is printed to the console on startup.

---

## Maintenance

- **Backup**: copy the entire `DATA_DIR` directory (plain `.md` text files)
- **Update**: `git pull` and restart the service
- **Logs**: `journalctl -u monthtrack -f`
