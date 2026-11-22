#!/bin/sh
set -e

export PORT="${PORT:-8080}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/tmp/chroma_db}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-/tmp/uip_command.db}"
export DEV_ARCHIVE_LOCAL_DIR="${DEV_ARCHIVE_LOCAL_DIR:-/tmp/dev_vault}"

mkdir -p "$CHROMA_PERSIST_DIR" "$DEV_ARCHIVE_LOCAL_DIR" /tmp

# Jana konfigurasi Nginx dengan port dinamik Cloud Run ($PORT)
envsubst '${PORT}' < /app/deploy/nginx.conf.template > /tmp/nginx.conf

# 1. Hidupkan Backend FastAPI pada 127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 &
BACKEND_PID=$!

# 2. Hidupkan Frontend Next.js Standalone pada 127.0.0.1:3000
PORT=3000 HOSTNAME=127.0.0.1 node /app/frontend/server.js &
FRONTEND_PID=$!

# Pastikan proses ditutup bersih jika container dihentikan
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM

# Tunggu Backend FastAPI & Frontend Next.js siap mendengar (elak 502 cold-start)
python - <<'PY'
import socket, time

for host, port in (("127.0.0.1", 8000), ("127.0.0.1", 3000)):
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except OSError:
            time.sleep(0.25)
PY

# 3. Jalankan Nginx di foreground untuk menerima trafik Cloud Run
exec nginx -c /tmp/nginx.conf -g "daemon off;"
