#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/backend"

if [ ! -d .venv ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
    .venv/bin/pip install -e . 2>/dev/null || .venv/bin/pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] python-dotenv
fi

if [ -f .env ]; then
    set -a; source .env; set +a
fi

exec .venv/bin/uvicorn monthtrack.app:app --host 0.0.0.0 --port 8000 --reload
