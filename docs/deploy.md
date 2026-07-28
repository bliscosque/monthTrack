# Deploy

App single-user (senha + JWT), dados em arquivos `.md`.

---

## Opção 1 — Servidor direto (mais simples)

```bash
# na raiz do projeto
./run.sh
```

O servidor sobe em `http://0.0.0.0:8000`. **Sem HTTPS** — use apenas em rede local ou atrás de um proxy.

---

## Opção 2 — Systemd + reverse proxy (recomendado)

### 2.1 Service systemd

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

### 2.2 Nginx (HTTPS com Let's Encrypt)

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

### 2.3 Caddy (alternativa, HTTPS automático)

```caddy
monthtrack.exemplo.com {
    reverse_proxy 127.0.0.1:8000
}
```

---

## Opção 3 — Docker (opcional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install .
CMD ["uvicorn", "monthtrack.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Monte o diretório de dados como volume:

```bash
docker build -t monthtrack .
docker run -d -p 8000:8000 \
  -e APP_PASSWORD=minha_senha \
  -e DATA_DIR=/data \
  -v /caminho/local/data:/data \
  monthtrack
```

---

## Variáveis de ambiente

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `APP_PASSWORD` | não* | gerada aleatória | Senha de acesso |
| `DATA_DIR` | não | `data` | Diretório dos arquivos `.md` |
| `APP_SECRET` | não | aleatório | Chave para assinar JWT |

\* Se não definida, uma senha aleatória é exibida no console na inicialização.

---

## Manutenção

- **Backup**: copie o diretório `DATA_DIR` inteiro (são arquivos `.md` de texto)
- **Atualizar**: `git pull` e reiniciar o service
- **Logs**: `journalctl -u monthtrack -f`
