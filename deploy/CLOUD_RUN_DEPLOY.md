# Panduan Deploy **i-UIP Nerus** ke Google Cloud Run

Aplikasi ini kini disiapkan sebagai **1 servis Cloud Run gabungan** (`Nginx` pada port `8080` → `/api/*` ke FastAPI `uvicorn:8000` dan `/*` ke Next.js standalone `3000`). Tiada isu CORS dan hanya **1 URL HTTPS** sahaja diperlukan.

---

## Prasyarat Sebelum Deploy

1. **Pangkalan Data Kekal (`DATABASE_URL` PostgreSQL):**
   - Cloud Run bersifat *stateless*. Jika `DATABASE_URL` tidak ditetapkan, data akan disimpan sementara di `/tmp/uip_command.db` dan akan hilang apabila container dimulakan semula.
   - Sediakan pangkalan data PostgreSQL (cth. **Neon.tech / Supabase Free Tier** atau **Google Cloud SQL PostgreSQL**) dan salin connection string `postgresql://user:pass@host:5432/dbname?sslmode=require`.
2. **Private Bucket Pembangun (`dev-vault` — Eksklusif `zero4eleven@gmail.com`):**
   - Semua akaun didaftar, soalan Tanya Pakar, dan dokumen/imej dianalisa disimpan ke dalam jadual `dev_archive_records` (PostgreSQL/SQLite) + Private Object Storage Bucket (`dev-vault`).
   - Walaupun env S3 belum ditetapkan, `DATABASE_URL` PostgreSQL tetap menyimpan teks analisis dan lampiran fail sehingga **5 MB** secara kekal (dan boleh disegerakkan bila-bila masa melalui butang **Sync S3** di Tab **Arkib & Bucket Dev**).
   - Untuk menyimpan lampiran bersaiz besar sehingga **20 MB** terus ke Neon Object Storage bucket persendirian `dev-vault`, tambah env vars berikut pada Cloud Run Variables:
     - `DEV_ARCHIVE_BUCKET=dev-vault`
     - `AWS_ENDPOINT_URL_S3=https://<branch-id>.storage.<region>.aws.neon.tech`
     - `AWS_ACCESS_KEY_ID=<S3_TOKEN_ID_NEON>`
     - `AWS_SECRET_ACCESS_KEY=<S3_SECRET_NEON>`
     - `AWS_REGION=ap-southeast-1`
3. **Google Cloud CLI (`gcloud`)** telah log masuk ke projek anda (`gen-lang-client-0742709224`).

---

## Langkah Deploy (1 Arahan)

Jalankan arahan berikut di folder akar projek (`projek uip/`):

```bash
gcloud config set project gen-lang-client-0742709224

gcloud run deploy iuip-nerus \
  --source . \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 180 \
  --set-env-vars "GEMINI_API_KEY=KUNCI_GEMINI_ANDA,GOOGLE_CLIENT_ID=290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com,DATABASE_URL=POSTGRESQL_URL_ANDA"
```

---

## Selepas Deploy Selesai

1. Salin URL HTTPS yang diberikan oleh Cloud Run (contoh: `https://iuip-nerus-xxxxxxxx-as.a.run.app`).
2. Buka **Google Cloud Console** → **APIs & Services** → **Credentials** → sunting OAuth 2.0 Client ID anda (`290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com`).
3. Masukkan URL Cloud Run anda ke dalam **Authorized JavaScript origins** (di sebelah `http://localhost:3000`).
4. Uji kesihatan pelayan di `https://<URL-ANDA>/api/health` (sepatutnya memulangkan `{"status":"ok","db":"postgres"}`).
