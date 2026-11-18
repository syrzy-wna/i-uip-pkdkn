#!/bin/sh
set -e

export PORT="${PORT:-8080}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/tmp/chroma_db}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-/tmp/uip_command.db}"

mkdir -p "$CHROMA_PERSIST_DIR" /tmp

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

# 3. Jalankan Nginx di foreground untuk menerima trafik Cloud Run
exec nginx -c /tmp/nginx.conf -g "daemon off;"
