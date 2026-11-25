# =====================================================================
# i-UIP Nerus (Unit Inspektorat & Perundangan PKD Kuala Nerus)
# Multi-stage Dockerfile sedia untuk Google Cloud Run (1-Servis Gabungan)
# =====================================================================

# Peringkat 1: Bina Next.js Standalone
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN mkdir -p /app/frontend/public
# Kosongkan NEXT_PUBLIC_API_URL supaya frontend guna laluan same-origin (/api/...)
ENV NEXT_PUBLIC_API_URL=""
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Peringkat 2: Persekitaran Produksi Python FastAPI + Node.js + Nginx
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_ENV=production \
    PORT=8080

# Pasang Nginx, envsubst (gettext-base), libstdc++6 (untuk PyMuPDF) dan Node.js 20 untuk Next.js standalone
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    libstdc++6 \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y gnupg curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Pasang kebergantungan Python (termasuk pymupdf untuk penghurai PDF Warta AGC & python-multipart untuk muat naik Admin)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/backend/requirements.txt \
    && python -c "import pymupdf as fitz; doc = fitz.open(); doc.close(); print('PyMuPDF PDF parser OK:', fitz.__version__)"

# Salin kod backend, data akta, pustaka perundangan 2-lapisan, 22 SOP aktif KKM 2024 (TANPA sops_arkib_deprecated), skrip CLI & skrip deploy
COPY backend/ /app/backend/
COPY data/akta/ /app/data/akta/
COPY data/legal_library/ /app/data/legal_library/
COPY data/sop_kkm_2024/sop_index_active_router.json /app/data/sop_kkm_2024/sop_index_active_router.json
COPY data/sop_kkm_2024/sop_bundle_aktif_context_cache.txt /app/data/sop_kkm_2024/sop_bundle_aktif_context_cache.txt
COPY data/sop_kkm_2024/sops_aktif/ /app/data/sop_kkm_2024/sops_aktif/
COPY scripts/ /app/scripts/
COPY deploy/ /app/deploy/

# Salin hasil binaan Next.js standalone
COPY --from=frontend-builder /app/frontend/.next/standalone /app/frontend/
COPY --from=frontend-builder /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /app/frontend/public /app/frontend/public

# Pastikan skrip start.sh berformat LF (bukan CRLF Windows) dan boleh dilaksanakan
RUN sed -i 's/\r$//' /app/deploy/start.sh && chmod +x /app/deploy/start.sh

EXPOSE 8080

CMD ["/app/deploy/start.sh"]
