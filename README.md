# UIP-Command (Fasa 1 MVP)

Aplikasi hibrid desktop/web berbilang model untuk **Unit Perundangan dan Pendakwaan (UIP)**, Kementerian Kesihatan Malaysia bagi penguatkuasaan kesihatan awam.

## 1. Persediaan Persekitaran (`.env`)
Salin `.env.example` menjadi `.env` dan isi kunci API anda jika ingin menggunakan mod awan Gemini:
```powershell
Copy-Item .env.example .env
```
- Jika `GEMINI_API_KEY` belum diisi, sistem tetap berfungsi penuh dalam **mod simulasi berkalibrasi tempatan**.
- Jika **Ollama (`gemma3:12b`)** di `http://localhost:11434` tidak dihidupkan, enjin privasi secara automatik menggunakan **Regex Pintar Malaysia** untuk menyamarkan data sulit (OSA/PDPA).

## 2. Menjalankan Backend (FastAPI)
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

## 3. Menjalankan Frontend (Next.js Split-View)
```powershell
cd frontend
npm run dev
```
Buka pelayar pada `http://localhost:3000`.

## 4. Pangkalan Data Akta Verbatim (`data/akta/`)
Letakkan fail `.txt` atau `.pdf` akta penuh (Akta 852, Akta Makanan 1983, Akta 154, Akta 342, Akta 593, Akta 56) di dalam folder `data/akta/`. Sistem akan mengindeksnya secara automatik semasa pelancaran atau melalui `POST /api/rag/ingest`.

## 5. Latihan Model Tempatan (`training/`)
```powershell
.\.venv\Scripts\python.exe training\prepare_dataset.py --input-dir .\arkib_ip --output .\training\uip_dataset.jsonl
python training\finetune_unsloth.py --dataset .\training\uip_dataset.jsonl
```
