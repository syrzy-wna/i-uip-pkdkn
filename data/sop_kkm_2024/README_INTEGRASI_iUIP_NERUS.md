# Pakej Otak SOP KKM Pindaan 2024 — Aplikasi i-UIP Nerus

Pakej ini menukar fail asal `PROSEDUR OPERASI PIAWAI (SOP) KKM PINDAAN 2024.pdf` (407 muka surat) kepada pangkalan pengetahuan berstruktur, bersih, dan diaudit sedia untuk dipasang terus ke dalam *backend* **i-UIP Nerus** (Cloud Run / Google AI Studio / Firebase).

## Ringkasan Audit Data yang Telah Disiapkan

1. **Pengasingan Akta 852 vs PPKHT 2004 (5 SOP Dimansuhkan):**
   - Semua 5 SOP Bahagian D (`UIP-PPKHT-02-07` hingga `UIP-PPKHT-04-23`) telah dikeluarkan daripada indeks aktif dan disimpan dalam `data/sops_arkib_deprecated/` supaya AI tidak sesekali memetik PPKHT 2004 atau Notis S.32B bagi kes merokok/vape semasa.
   - Amaran audit telah disuntik terus ke dalam `UIP-UMUM-02-07` (Lampiran C) bagi mengelakkan kekeliruan.
2. **Pembetulan Konflik Kod & Rujukan Dalaman PDF Asal:**
   - **Kamera Badan (BWC):** Kod rasmi `UIP-UMUM-01-22 (PINDAAN 2024)` dipetakan bersama alias silap cetak kandungan (`UIP-UMUM-01-23`). Label Lampiran 2 dibetulkan kepada *Perakuan Seksyen 90A(2)*.
   - **Tutup Premis S.18(1)(f) Akta 342:** Kod rasmi `UIP-APPPB-06-20 (PINDAAN 2024)` dipetakan bersama alias silap cetak kandungan (`UIP-APPPB-01-20`).
   - **Menghalang Tugas:** Rujukan lama `UIP-APSPP-03-07` di dalam `UIP-APSPP-01-07` dilabelkan dengan kod baharu `UIP-UMUM-01-24`.
   - **Lampiran Tercicir / Silap Cetak:** Lampiran E (PPM 1985) & F (Akta 342) dalam `UIP-UMUM-02-07`, Lampiran B–D dalam `UIP-UMUM-04-07`, Lampiran A–F dalam `UIP-UMUM-03-07`, serta pembetulan ralat cetak `Subseksyen 5(1)` -> `Subseksyen 15(1)` dalam `UIP-APPPB-01-16` telah lengkap diindekskan.

## Struktur Folder

- `data/sop_index_active_router.json` — Indeks ringan 22 SOP aktif (~4.7k token) untuk Peringkat 1 (Router).
- `data/sop_index_master.json` — Indeks lengkap semua 27 SOP (22 aktif + 5 arkib) beserta nota audit.
- `data/sops_aktif/` — 22 fail Markdown bersih (`1 SOP = 1 Fail`) lengkap dengan penanda `[Muka Surat PDF: X]`.
- `data/sops_arkib_deprecated/` — 5 fail PPKHT 2004 diasingkan (tidak masuk enjin aktif).
- `data/sop_bundle_aktif_context_cache.txt` — Gabungan penuh 22 SOP aktif (~90k token) sedia untuk **Gemini Context Caching**.
- `backend/python/` — Modul Python (`uip_brain.py`, `system_prompts.py`) menggunakan `google-genai`.
- `backend/typescript/` — Modul TypeScript (`uipBrain.ts`, `systemPrompts.ts`) menggunakan `@google/genai`.
- `tests/` — 20 soalan perangkap (`golden_test_set.json`) + skrip ujian automatik (`run_eval.py`).

## Cara Pasang ke i-UIP Nerus (3 Langkah)

### Pilihan A — Backend Python (FastAPI / Cloud Run)
1. Salin folder `data/` dan fail dalam `backend/python/` ke repositori Cloud Run anda.
2. Pasang kebergantungan:
   ```bash
   pip install -r backend/python/requirements.txt
   ```
3. Panggil dari endpoint `/api/tanya-pakar` atau `/api/audit-ks`:
   ```python
   from uip_brain import IUIPNerusBrain

   brain = IUIPNerusBrain(package_root="/app")
   hasil = brain.tanya_pakar_uip(
       soalan=req.soalan,
       konteks_statut_tambahan=petikan_akta_852_atau_281_anda,
       guna_cache=False,  # Tukar ke True jika mahu guna Gemini Context Caching
   )
   ```

### Pilihan B — Backend TypeScript / Node (Google AI Studio / Cloud Run)
1. Salin folder `data/` dan fail dalam `backend/typescript/` ke projek anda.
2. Pasang SDK: `npm install @google/genai`.
3. Import `IUIPNerusBrain` daripada `uipBrain.ts` dan panggil `brain.tanyaPakarUip({ soalan, konteksStatutTambahan })`.

### Langkah Wajib Sebelum Deploy: Jalankan Ujian Perangkap
```bash
export GEMINI_API_KEY="kunci_api_anda"
python tests/run_eval.py --mode router
python tests/run_eval.py --mode full
```
Pastikan skor mencapai **20/20 LULUS** sebelum menghantar kemas kini ke `iuippkdkn.cloud.run`.
