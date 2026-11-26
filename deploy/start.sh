#!/bin/sh
set -e

export PORT="${PORT:-8080}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/tmp/chroma_db}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-/tmp/uip_command.db}"
export DEV_ARCHIVE_LOCAL_DIR="${DEV_ARCHIVE_LOCAL_DIR:-/tmp/dev_vault}"
export DEV_ARCHIVE_LOCAL_ENABLED="${DEV_ARCHIVE_LOCAL_ENABLED:-false}"

mkdir -p "$CHROMA_PERSIST_DIR" "$DEV_ARCHIVE_LOCAL_DIR" /tmp /tmp/nginx_body /tmp/nginx_proxy /tmp/nginx_fastcgi /tmp/nginx_uwsgi /tmp/nginx_scgi

# Jana konfigurasi Nginx dengan port dinamik Cloud Run ($PORT)
envsubst '${PORT}' < /app/deploy/nginx.conf.template > /tmp/nginx.conf

# 1. Hidupkan Backend FastAPI pada 127.0.0.1:8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 &
BACKEND_PID=$!

# 2. Hidupkan Frontend Next.js Standalone pada 127.0.0.1:3000
PORT=3000 HOSTNAME=127.0.0.1 node /app/frontend/server.js &
FRONTEND_PID=$!

# Pastikan proses ditutup bersih jika container dihentikan
cleanup() {
    kill "$BACKEND_PID" "$FRONTEND_PID" "${NGINX_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Tunggu Backend FastAPI (/healthz) & Frontend Next.js siap mendengar (elak 502 cold-start)
python - <<'PY'
import socket, time, urllib.request

deadline = time.time() + 60
while time.time() < deadline:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=2) as resp:
            if resp.status == 200:
                break
    except Exception:
        time.sleep(0.3)

while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", 3000), timeout=1):
            break
    except OSError:
        time.sleep(0.25)
PY

# 3. Jalankan Nginx dan pantau kesemua proses utama (keluar jika mana-mana mati)
nginx -c /tmp/nginx.conf -g "daemon off;" &
NGINX_PID=$!

while true; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "RALAT: Proses Backend FastAPI terhenti." >&2
        exit 1
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "RALAT: Proses Frontend Next.js terhenti." >&2
        exit 1
    fi
    if ! kill -0 "$NGINX_PID" 2>/dev/null; then
        echo "RALAT: Proses Nginx terhenti." >&2
        exit 1
    fi
    sleep 5
done
