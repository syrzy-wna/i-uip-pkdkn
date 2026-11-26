#!/usr/bin/env python3
"""Repeatable builder for the i-UIP Nerus KKM 2024 Active SOP Corpus (33 Active SOPs + Structured JSON v2).

Reads the 34 verified Google Drive PDFs referenced by `manifest.json` (default:
`/home/antigravity/.gemini/jetski/scratch/teamwork_tmp/gdrive_sops/manifest.json`) and generates:
  1. `data/sop_kkm_2024/sops_aktif/{file_stem}.md` (33 clean PyMuPDF active SOPs; 0 PPKHT 2004)
  2. `data/sop_kkm_2024/sops_structured/{file_stem}.json` (33 structured v2 JSON files)
  3. `data/sop_kkm_2024/sop_index_active_router.json` (33 active SOP router entries; 0 PPKHT 2004)
  4. `data/sop_kkm_2024/sop_index_master.json` (33 active + 5 quarantined deprecated = 38 entries)
  5. `data/sop_kkm_2024/sop_bundle_aktif_context_cache.txt` (33 active SOPs bundle; 0 PPKHT 2004)
  6. `data/sop_kkm_2024/pekeliling_rujukan.json` (Pekeliling KPK Bil 18/2024 incomplete-scan notice)

HARD LEGAL INVARIANTS ENFORCED:
  - 5 repealed PPKHT 2004 SOPs are NEVER indexed into sops_aktif/, sops_structured/, active router, or bundle.
  - Statute > SOP [NOTA PINDAAN] hierarchy enforced for Akta 852, Akta A1702, Akta A1742 & P.U.(A) 139/2025.
  - Akta 852 obstruction explicitly cites Seksyen 186 Kanun Keseksaan [Akta 574] via PDRM.
  - Seksyen 32B Akta 281 remains 100% VALID & ACTIVE for food safety (UIP-UMUM-04-24).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf as fitz  # PyMuPDF

REPO_ROOT = Path(__file__).resolve().parents[1]
SOP_DATA_DIR = REPO_ROOT / "data" / "sop_kkm_2024"
DEFAULT_MANIFEST = Path(
    "/home/antigravity/.gemini/jetski/scratch/teamwork_tmp/gdrive_sops/manifest.json"
)

# Canonical mapping from GDrive manifest index (1..34) to SOP metadata
GDRIVE_CATALOG: Dict[int, Dict[str, Any]] = {
    1: {
        "file_stem": "UIP-AKPMDKA-08-24",
        "sop_id": "UIP-AKPMDKA-08-24",
        "alias_kod": ["AKPMDKA-08-24", "AKPMDKS-08-24", "08 AKPMDKS 08-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 56", "Akta 593", "Akta 388", "Akta 92"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Penghantaran Barang Kes Ke Makmal Di Bawah Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Seksyen 28 Akta 852", "Seksyen 35-36 Akta 852", "P.U.(A) 263/2024 (Makmal Diluluskan)", "Seksyen 399 KTJ", "Rantaian Jagaan Eksibit (Borang 1-3)"],
        "kata_kunci": ["hantar barang kes", "hantar sampel makmal", "makmal akta 852", "p.u.(a) 263/2024", "analisis nikotin", "rokok elektronik makmal", "vape makmal", "borang 1", "borang 2", "borang 3", "uip-akpmdka-08-24"],
        "nota_audit_kualiti": ["Nama fail sumber Google Drive menggunakan ejaan 'AKPMDKS'; kod rasmi dalam dokumen ialah UIP-AKPMDKA-08-24."],
    },
    2: {
        "file_stem": "UIP-AKPMDKA-07-24",
        "sop_id": "UIP-AKPMDKA-07-24",
        "alias_kod": ["AKPMDKA-07-24", "AKPMDKS-07-24", "07 AKPMDKS 07-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 56", "Akta 593", "Akta 388"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Pemulangan Sementara Barang Disita Di Bawah Seksyen 37 Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Seksyen 37 Akta 852 (Pemulangan Sementara)", "Seksyen 35-36 Akta 852", "Bon / Jaminan Pemulangan Sementara", "Kebenaran Bertulis Ketua Pengarah / Pegawai Diberi Kuasa"],
        "kata_kunci": ["pemulangan sementara", "pelepasan sementara", "seksyen 37 akta 852", "tuntut barang sitaan vape", "pulang barang sita", "bon jaminan sitaan", "uip-akpmdka-07-24"],
        "nota_audit_kualiti": ["Nama fail sumber menyebut 'Pelepasan Sementara'; tajuk rasmi dalam dokumen ialah Pemulangan Sementara Di Bawah Seksyen 37 Akta 852. Nombor muka surat Isi Kandungan PDF berbeza +2 dan tajuk Carta Alir bertindih nombor '8.' telah dinormalkan."],
    },
    3: {
        "file_stem": "UIP-AKPMDKA-06-24",
        "sop_id": "UIP-AKPMDKA-06-24",
        "alias_kod": ["AKPMDKA-06-24", "AKPMDKS-06-24", "06 AKPMDKS 06-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 56", "Akta 593", "Akta 388", "Akta 574"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Penyitaan Produk Merokok & Barang Kes Di Bawah Seksyen 35, 36 dan 37 Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Seksyen 35 Akta 852 (Kuasa Menyita)", "Seksyen 36 Akta 852 (Senarai Benda Disita)", "Seksyen 37 Akta 852 (Pelepasan / Pelucuthakan 30 hari)", "Borang Senarai Sitaan S.36"],
        "kata_kunci": ["sita vape", "penyitaan akta 852", "seksyen 35 akta 852", "seksyen 36 akta 852", "senarai benda disita", "lak barang kes vape", "sita produk merokok", "30 hari sitaan", "uip-akpmdka-06-24"],
        "nota_audit_kualiti": ["Nama fail sumber Google Drive menggunakan ejaan 'AKPMDKS'; kod rasmi ialah UIP-AKPMDKA-06-24."],
    },
    4: {
        "file_stem": "UIP-AKPMDKA-05-24",
        "sop_id": "UIP-AKPMDKA-05-24",
        "alias_kod": ["AKPMDKA-05-24", "AKPMDKS-05-24", "UIP-AKMPDKA-05-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 56", "Akta 593", "Akta 92", "Akta 388", "Akta 574"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Penguatkuasaan Bagi Kesalahan Tidak Boleh Dikompaun Di Bawah Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Kesalahan Tidak Boleh Kompaun Akta 852 (S.3, S.7, S.9, S.10, S.11, S.13(1), S.14, S.15)", "Buka Kertas Siasatan Terus (Tanpa Kompaun)", "Seksyen 41 Akta 852 (Izin Mendakwa TPR)", "Notis Hadir Penyiasatan & Rakaman S.112 KTJ"],
        "kata_kunci": ["kesalahan tidak boleh dikompaun", "tidak boleh kompaun akta 852", "jual vape kepada obd", "seksyen 13(1) akta 852", "pamer vape", "seksyen 10(1) akta 852", "iklan vape", "seksyen 7(1) akta 852", "jual online vape", "tidak berdaftar seksyen 3", "uip-akpmdka-05-24"],
        "nota_audit_kualiti": ["Tiga ralat cetak dalaman PDF asal dinormalkan: kepala halaman 3 'UIP-AKMPDKA-05-24', frasa berulang pada kepala halaman, dan duplikasi label 'Lampiran B' dalam Isi Kandungan (item kedua ialah Lampiran C: Notis Hadir Penyiasatan)."],
    },
    5: {
        "file_stem": "UIP-AKPMDKA-04-24",
        "sop_id": "UIP-AKPMDKA-04-24",
        "alias_kod": ["AKPMDKA-04-24", "AKPMDKS-04-24", "04 AKPMDKS 04-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 56", "Akta 593", "Akta 388"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Tatacara Pengambilan Sampel Produk Merokok Di Bawah Subseksyen 28(2) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Subseksyen 28(2) Akta 852 (Kuasa Ambil Sampel)", "Seksyen 29 Akta 852 (Pembayaran & Pembahagian Sampel)", "Borang A & Borang 1-3 Persampelan", "P.U.(A) 263/2024 (Makmal Analisis)"],
        "kata_kunci": ["persampelan akta 852", "ambil sampel vape", "sampel cecair vape", "sampel rokok", "seksyen 28(2) akta 852", "ujian makmal vape", "borang a sampel", "uip-akpmdka-04-24"],
        "nota_audit_kualiti": ["Nama fail sumber menggunakan 'AKPMDKS'; kod rasmi ialah UIP-AKPMDKA-04-24."],
    },
    6: {
        "file_stem": "UIP-AKPMDKA-03-24",
        "sop_id": "UIP-AKPMDKA-03-24",
        "alias_kod": ["AKPMDKA-03-24", "AKPMDKS-03-24", "03 AKPMDKS 03-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 593", "Akta 56", "Akta 344", "Akta 574"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Menggeledah Tanpa Waran Di Bawah Seksyen 33 Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Seksyen 33 Akta 852 (Menggeledah Tanpa Waran)", "Sebab Munasabah Keterangan Akan Dialihkan/Dimusnahkan", "Seksyen 35 & 36 Akta 852 (Sitaan & Senarai)", "Contoh Draf Laporan Polis (Lampiran C)"],
        "kata_kunci": ["geledah tanpa waran akta 852", "geledah vape tanpa waran", "seksyen 33 akta 852", "serbu kedai vape tanpa waran", "uip-akpmdka-03-24"],
        "nota_audit_kualiti": ["Ralat cetak PDF asal dinormalkan: Isi Kandungan menyenaraikan dua 'Lampiran B' sedangkan halaman 12 ialah LAMPIRAN C (Contoh Draf Laporan Polis), serta ejaan 'menggeladah'."],
    },
    7: {
        "file_stem": "UIP-AKPMDKA-02-24",
        "sop_id": "UIP-AKPMDKA-02-24",
        "alias_kod": ["AKPMDKA-02-24", "AKPMDKS-02-24", "02 AKPMDKS 02-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "Akta 593", "Akta 56", "Akta 344", "Akta 574"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Menggeledah Dengan Waran Di Bawah Seksyen 32 Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
        "seksyen_kunci": ["Seksyen 32 Akta 852 (Permohonan & Pelaksanaan Waran Geledah Majistret)", "Seksyen 35 & 36 Akta 852 (Sitaan & Senarai)", "Afidavit & Maklumat Bersumpah Kepada Majistret", "Lampiran A-F Waran Geledah Akta 852"],
        "kata_kunci": ["geledah dengan waran akta 852", "waran geledah vape", "waran geledah akta 852", "seksyen 32 akta 852", "mohon waran majistret vape", "uip-akpmdka-02-24"],
        "nota_audit_kualiti": ["Rujukan silang rosak dalam PDF asal ('UIP-UMUM-05-16 (Pindaan 2024)' yang tidak wujud) telah dipetakan kepada kod aktif UIP-UMUM-05-07 (PINDAAN 2024). Jadual Proses Kerja tanpa garisan sempadan diekstrak melalui pengelompokan koordinat-X."],
    },
    8: {
        "file_stem": "UIP-AKPMDKA-01-24",
        "sop_id": "UIP-AKPMDKA-01-24",
        "alias_kod": ["AKPMDKA-01-24", "01 AKPMDKA 01-24"],
        "kategori": "AKTA_852",
        "akta_utama": "Akta 852",
        "akta_berkaitan": ["Akta 852", "P.U.(A) 257/2024", "P.U.(A) 258/2024", "P.U.(A) 259/2024", "P.U.(A) 264/2024", "Akta 56", "Akta 593", "Akta 92"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "01 Okt 2024",
        "tarikh_iso": "2024-10-01",
        "tajuk": "Prosedur Pelaksanaan Notis Memerintahkan Kehadiran Ke Mahkamah Di Bawah Seksyen 47 dan Tawaran Mengkompaun Kesalahan Di Bawah Seksyen 48 Akta 852",
        "seksyen_kunci": ["Seksyen 47 Akta 852 (Notis Kehadiran Mahkamah — P.U.(A) 264/2024)", "Seksyen 48 Akta 852 (Tawaran Kompaun — P.U.(A) 259/2024)", "Kesalahan Boleh Kompaun: S.13(3), S.16(2), S.17(1), S.18(1)", "Seksyen 41 Akta 852 (Izin Mendakwa TPR)", "Tempoh Bayaran & Tarikh Hadir Mahkamah (>60 hari)"],
        "kata_kunci": ["notis seksyen 47", "notis s.47", "kompaun akta 852", "tawaran kompaun akta 852", "seksyen 48 akta 852", "merokok kawasan larangan", "seksyen 16(2)", "seksyen 17(1)", "seksyen 18(1)", "seksyen 13(3)", "pengurangan kompaun akta 852", "buku notis akta 852", "uip-akpmdka-01-24"],
        "nota_audit_kualiti": ["Ralat cetak PDF asal dinormalkan: duplikasi nombor '22' dalam Isi Kandungan ('22 Pematuhan' & '22 Tarikh Kuatkuasa') dan ejaan 'seksyen 90(A)' -> 'Seksyen 90A'. Menggantikan sepenuhnya UIP-PPKHT-01-16 yang dimansuhkan."],
    },
    # #9 is Pekeliling KPK Bil 18/2024 (handled separately as pekeliling_rujukan.json)
    10: {"file_stem": "UIP-APPPB-01-21"},
    11: {"file_stem": "UIP-APPPB-06-20"},
    12: {"file_stem": "UIP-APPPB-02-16"},
    13: {"file_stem": "UIP-APPPB-01-16"},
    14: {"file_stem": "UIP-APPPB-03-07"},
    15: {"file_stem": "UIP-APPPB-02-07"},
    16: {"file_stem": "UIP-APPPB-01-07"},
    17: {"file_stem": "UIP-APSPP-01-24"},
    18: {"file_stem": "UIP-APSPP-02-16"},
    19: {"file_stem": "UIP-APSPP-01-16"},
    20: {"file_stem": "UIP-APSPP-02-07"},
    21: {"file_stem": "UIP-APSPP-01-07"},
    22: {
        "file_stem": "UIP-UMUM-06-24",
        "sop_id": "UIP-UMUM-06-24",
        "alias_kod": ["UIP-UMUM-06-2024", "UIP-UMUM–06-24"],
        "kategori": "UMUM",
        "akta_utama": "SOP Umum / KTJ",
        "akta_berkaitan": ["Akta 852", "Akta 281", "Akta 154", "Akta 342", "Akta 593", "Akta 56", "Akta 574"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "Disember 2024",
        "tarikh_iso": "2024-12-01",
        "tajuk": "Prosedur Pengurusan Aktiviti Risikan Undang-Undang Kesihatan Awam",
        "seksyen_kunci": ["Pengumpulan & Penilaian Maklumat Risikan (SULIT)", "Borang Laporan Risikan (Lampiran A — SULIT)", "Senarai Semak Aktiviti Risikan (Lampiran B)", "Keselamatan Anggota & Kerahsiaan Sumber Maklumat"],
        "kata_kunci": ["risikan", "aktiviti risikan", "intipan", "maklumat risikan", "borang laporan risikan", "sulit", "penyamaran", "premis sasaran", "uip-umum-06-24", "uip-umum-06-2024"],
        "nota_audit_kualiti": ["Nama fail sumber menggunakan kod 'UIP-UMUM-06-2024' dan kulit muka menggunakan tanda en-dash; kod rasmi dalam badan SOP ialah UIP-UMUM-06-24. Sudah merujuk Akta 852 tanpa rujukan PPKHT 2004."],
    },
    23: {
        "file_stem": "UIP-UMUM-05-24",
        "sop_id": "UIP-UMUM-05-24",
        "alias_kod": ["UMUM-05-24", "29 SOP UMUM-05-24"],
        "kategori": "UMUM",
        "akta_utama": "SOP Umum / KTJ",
        "akta_berkaitan": ["Akta 852", "Akta 281", "Akta 154", "Akta 342", "Akta 593", "Akta 56"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "22 Apr 2024",
        "tarikh_iso": "2024-04-22",
        "tajuk": "Prosedur Pengurusan Barang Kes / Eksibit Di Bawah Perundangan Kesihatan Awam",
        "seksyen_kunci": ["Rantaian Jagaan Eksibit (Chain of Custody)", "Stor Barang Kes & Pegawai Penjaga Stor Eksibit", "Pendaftaran, Pelabelan, Lak (Seal) & Pelupusan S.407/407A KTJ", "Lampiran A-C Daftar & Serah Terima Eksibit"],
        "kata_kunci": ["pengurusan eksibit", "barang kes", "stor eksibit", "bilik barang kes", "chain of custody", "rantaian jagaan", "daftar barang kes", "lupus barang kes", "pelupusan eksibit", "uip-umum-05-24"],
        "nota_audit_kualiti": ["Langkah 6 PDF asal masih menyebut 'PPKHT 2004 dan Akta 852' — diberi [NOTA PINDAAN] bahawa PPKHT 2004 telah dimansuhkan mulai 1 Okt 2024. Ralat cetak 'Keluaran: 00' dan 'Definasi' dalam PDF asal dinormalkan."],
    },
    24: {
        "file_stem": "UIP-UMUM-04-24",
        "sop_id": "UIP-UMUM-04-24",
        "alias_kod": ["UMUM-04-24", "28 SOP UMUM-04-24"],
        "kategori": "AKTA_281",
        "akta_utama": "Akta 281",
        "akta_berkaitan": ["Akta 281", "PPKM 2009", "PPM 1985", "Akta 593", "Akta 56", "Akta 388"],
        "keluaran": "01",
        "pindaan": "00",
        "tarikh_kuatkuasa": "22 Apr 2024",
        "tarikh_iso": "2024-04-22",
        "tajuk": "Prosedur Pengeluaran Kompaun Di Bawah Akta Makanan 1983 [Akta 281]",
        "seksyen_kunci": ["Seksyen 32B Akta Makanan 1983 (Notis Memerintahkan Kehadiran Ke Mahkamah — AKTIF bagi keselamatan makanan)", "Seksyen 33 Akta Makanan 1983 (Kuasa Mengkompaun)", "Peraturan-Peraturan Makanan (Pengkompaunan Kesalahan) 2017", "Jadual Kadar Kompaun Kategori Premis I-IV (PPM 1985 & PPKM 2009)", "14 Lampiran (A-N)"],
        "kata_kunci": ["kompaun akta makanan", "kompaun akta 281", "notis 32b makanan", "notis seksyen 32b", "kompaun ppkm 2009", "kompaun ppm 1985", "jadual kompaun makanan", "kategori premis makanan", "pengurangan kompaun makanan", "uip-umum-04-24"],
        "nota_audit_kualiti": ["Isi Kandungan PDF asal berbeza +1 muka surat bagi kesemua 14 Lampiran dan mengandungi ralat cetak '2007' (sepatutnya Peraturan-Peraturan Makanan (Pengkompaunan Kesalahan) 2017). 15 halaman lampiran (m/s 16-27, 31-33: Lampiran D, E, F, G, K, L termasuk jadual kadar kompaun melintang 90° SOP-PKKM-PD-09 & PD-04) adalah imej imbasan dan ditandakan status 'imej_imbasan_perlu_ocr'."],
    },
    25: {"file_stem": "UIP-UMUM-03-24"},
    26: {"file_stem": "UIP-UMUM-02-24"},
    27: {"file_stem": "UIP-UMUM-01-24"},
    28: {"file_stem": "UIP-UMUM-01-22"},
    29: {"file_stem": "UIP-UMUM-01-16"},
    30: {"file_stem": "UIP-UMUM-05-07"},
    31: {"file_stem": "UIP-UMUM-04-07"},
    32: {"file_stem": "UIP-UMUM-03-07"},
    33: {"file_stem": "UIP-UMUM-02-07"},
    34: {"file_stem": "UIP-UMUM-01-07"},
}

PPKHT_AFFECTED_STEMS = {
    "UIP-UMUM-01-07",
    "UIP-UMUM-02-07",
    "UIP-UMUM-03-07",
    "UIP-UMUM-04-07",
    "UIP-UMUM-05-07",
    "UIP-UMUM-01-16",
    "UIP-UMUM-01-22",
    "UIP-UMUM-05-24",
}

APPPB_STEMS = {
    "UIP-APPPB-01-07",
    "UIP-APPPB-02-07",
    "UIP-APPPB-03-07",
    "UIP-APPPB-01-16",
    "UIP-APPPB-02-16",
    "UIP-APPPB-06-20",
    "UIP-APPPB-01-21",
}

AKTA_281_FOOD_STEMS = {"UIP-UMUM-02-24", "UIP-UMUM-03-24", "UIP-UMUM-04-24"}

# Known role codes in KKM SOPs
ROLE_CODES = [
    "KPK", "TKPK", "PKN", "TPKN", "TPK", "KSIP", "KUIPN", "KUIPD", "PKD", "PKP",
    "KPPKP", "PPKPK", "PPKP", "PKAK", "PKA", "PDK", "PSPP", "PKE", "PR", "PA",
    "PP", "IO", "RO", "PO", "TPR", "UIPD", "UIPN", "PDRM", "PPD", "MO", "FMS",
    "JKN", "KKM", "IP", "PKS", "PT", "OKS", "OKN", "OKK",
]
ROLE_CODE_RE = re.compile(r"\b(" + "|".join(ROLE_CODES) + r")\b")

KNOWN_ROLE_TITLES: Dict[str, str] = {
    "KPK": "Ketua Pengarah Kesihatan",
    "PKN": "Pengarah Kesihatan Negeri",
    "TPKN": "Timbalan Pengarah Kesihatan Negeri (Kesihatan Awam)",
    "KSIP": "Ketua Sektor Inspektorat dan Perundangan",
    "KUIPN": "Ketua Unit Inspektorat dan Perundangan Negeri",
    "KUIPD": "Ketua Unit Inspektorat dan Perundangan Daerah",
    "PKD": "Pegawai Kesihatan Daerah",
    "PKP": "Pegawai Kesihatan Persekitaran",
    "PKE": "Pegawai Kesihatan Epidemiologi",
    "KPPKP": "Ketua Penolong Pegawai Kesihatan Persekitaran",
    "PPKPK": "Penolong Pegawai Kesihatan Persekitaran Kanan",
    "PPKP": "Penolong Pegawai Kesihatan Persekitaran",
    "PKAK": "Pembantu Kesihatan Awam Kanan",
    "PKA": "Pembantu Kesihatan Awam",
    "PDK": "Pegawai Diberi Kuasa",
    "PSPP": "Pemeriksa Serangga Pembawa Penyakit",
    "IO": "Pegawai Penyiasat (Investigating Officer)",
    "RO": "Pegawai Serbuan / Pegawai Pengesan (Raiding Officer)",
    "PO": "Pegawai Pendakwa (Prosecuting Officer)",
    "TPR": "Timbalan Pendakwa Raya",
    "UIPD": "Unit Inspektorat dan Perundangan Daerah",
    "UIPN": "Unit Inspektorat dan Perundangan Negeri",
    "PDRM": "Polis Diraja Malaysia",
}


def clean_pdf_text(text: str) -> str:
    """Clean extraction whitespace and known PDF glitches without altering legal meaning."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\u00a0", " ").replace("\uf0b7", "- ").replace("\u2022", "- ")
    # Fix broken hyphenated line breaks and accidental double spaces
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def strip_running_headers_and_footers(page_text: str) -> str:
    lines = page_text.splitlines()
    out: List[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            out.append("")
            continue
        if re.match(r"^NO\.?\s*RUJUKAN\s*(?:PROSEDUR|DOKUMEN)?\s*:?\s*UIP-", s, re.I):
            continue
        if re.match(r"^MUKA\s*SURAT\s*:?\s*\d+", s, re.I):
            continue
        if re.match(r"^\d{1,3}$", s) and len(out) < 3:
            continue
        out.append(ln)
    return "\n".join(out).strip()


def extract_pdf_pages(pdf_path: Path, strip_trailing_blank: bool = False) -> List[Tuple[int, str, int]]:
    """Return list of (1-based page_no, text, image_count) via PyMuPDF."""
    pages: List[Tuple[int, str, int]] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            txt = clean_pdf_text(page.get_text("text") or "")
            imgs = len(page.get_images(full=True))
            pages.append((i, txt, imgs))
    if strip_trailing_blank and pages:
        last_no, last_txt, last_imgs = pages[-1]
        cleaned_last = strip_running_headers_and_footers(last_txt)
        if last_imgs == 0 and len(re.sub(r"[\W\d_]+", "", cleaned_last)) < 10:
            pages = pages[:-1]
    return pages


def _extract_page_rows_by_xcoord(page: Any, pno: int) -> Tuple[List[Tuple[str, str, str, int]], bool]:
    """Extract Proses Kerja rows using exact word bounding-box x/y coordinates.

    Handles both borderless tables and single-merged-cell multi-step tables where
    PyMuPDF `find_tables()` collapses all steps into 1 giant cell.
    Returns (rows, hit_end_section).
    """
    width = float(page.rect.width or 595.0)
    words = page.get_text("words") or []
    if not words:
        return [], False

    # Detect dynamic column boundaries from table header words ("Anggota" / "Tindakan" / "Rujukan")
    col1_max = width * 0.24
    col2_max = width * 0.75
    header_y: Optional[float] = None
    for w in words:
        wt = str(w[4]).strip().lower()
        if wt == "tindakan" and 60 < w[0] < width * 0.45:
            col1_max = max(width * 0.16, float(w[0]) - 10.0)
            header_y = float(w[3])
        elif wt == "rujukan" and w[0] > width * 0.62:
            col2_max = min(width * 0.86, float(w[0]) - 10.0)

    # Group words into visual horizontal lines (~6.5pt tolerance)
    lines_by_y: List[Tuple[float, List[Tuple[float, str]]]] = []
    for w in sorted(words, key=lambda item: (round(item[1] / 5.0), item[0])):
        x0, y0, _, _, wtxt = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
        if y0 < 52 or y0 > (page.rect.height - 42):
            continue
        if header_y is not None and y0 <= header_y + 2.0:
            continue
        if not lines_by_y or abs(lines_by_y[-1][0] - y0) > 6.5:
            lines_by_y.append((y0, [(x0, wtxt)]))
        else:
            lines_by_y[-1][1].append((x0, wtxt))

    out_rows: List[Tuple[str, str, str, int]] = []
    cur_c1: List[str] = []
    cur_c2: List[str] = []
    cur_c3: List[str] = []
    hit_end = False

    def _flush() -> None:
        nonlocal cur_c1, cur_c2, cur_c3
        s1 = " ".join(cur_c1).strip()
        s2 = " ".join(cur_c2).strip()
        s3 = " ".join(cur_c3).strip()
        if s2 and not ("anggota" in s1.lower() and "tindakan" in s2.lower()):
            out_rows.append((s1, s2, s3, pno))
        cur_c1, cur_c2, cur_c3 = [], [], []

    step_start_re = re.compile(r"^(?:\d+(?:\.\d+)*\.?\)?)\s+\S")
    phase_start_re = re.compile(
        r"^(?:DI\s+(?:PEJABAT|LAPANGAN|MAHKAMAH|MAKMAL)|(?:SEBELUM|SEMASA|SELEPAS)\s+[A-Z]+|"
        r"\d+\.0\s+[A-Z]|PERSEDIAAN\s+AWAL|TINDAKAN\s+SUSULAN)\b",
        re.I,
    )

    for _, line_words in lines_by_y:
        line_words.sort(key=lambda t: t[0])
        full_line = " ".join(t[1] for t in line_words).strip()
        full_low = full_line.lower()
        if re.match(r"^(?:no\.?\s*rujukan|muka\s*surat|prosedur\s+)", full_low):
            continue
        if re.match(r"^\d*\.?\s*(?:c?arta\s+alir|pematuhan\s+prosedur|tarikh\s+kuat\s*kuasa|senarai\s+rujukan)\b", full_low):
            _flush()
            hit_end = True
            break
        if ("angg" in full_low and "terlibat" in full_low) or ("tindakan" in full_low and "rujukan" in full_low):
            continue

        c1_w = [t[1] for t in line_words if t[0] < col1_max]
        c2_w = [t[1] for t in line_words if col1_max <= t[0] < col2_max]
        c3_w = [t[1] for t in line_words if t[0] >= col2_max]
        line_c2 = " ".join(c2_w).strip()
        line_c1 = " ".join(c1_w).strip()

        # Sometimes step number slightly straddles col1_max (e.g. x just left of Tindakan header)
        if not line_c2 and step_start_re.match(line_c1):
            line_c2 = line_c1
            c2_w = c1_w
            c1_w = []
            line_c1 = ""

        is_phase_line = bool(phase_start_re.match(line_c2)) and len(line_c2) <= 85 and not c3_w
        if is_phase_line:
            _flush()
            out_rows.append(("", line_c2, "", pno))
            continue

        starts_new = bool(step_start_re.match(line_c2))
        if starts_new and (cur_c2 or cur_c1):
            _flush()
        cur_c1.extend(c1_w)
        cur_c2.extend(c2_w)
        cur_c3.extend(c3_w)

    _flush()
    return out_rows, hit_end


def _split_merged_cell_row(col1: str, col2: str, col3: str, pno: int) -> List[Tuple[str, str, str, int]]:
    """Split a merged table cell containing multiple numbered steps into individual rows."""
    step_markers = list(re.finditer(r"(?:^|\n)\s*(\d+(?:\.\d+)*\.?)\s+(?=\S)", col2))
    if len(step_markers) <= 1:
        return [(col1, col2, col3, pno)]

    chunks: List[str] = []
    prefix = col2[:step_markers[0].start()].strip()
    if prefix:
        chunks.append(prefix)
    for idx, m in enumerate(step_markers):
        start = m.start()
        end = step_markers[idx + 1].start() if idx + 1 < len(step_markers) else len(col2)
        chunk = col2[start:end].strip()
        if chunk:
            chunks.append(chunk)

    role_blocks = [b.strip() for b in re.split(r"\n\s*\n+", col1.strip()) if b.strip()] if col1.strip() else []
    ref_blocks = [b.strip() for b in re.split(r"\n\s*\n+", col3.strip()) if b.strip()] if col3.strip() else []

    split_rows: List[Tuple[str, str, str, int]] = []
    step_idx = 0
    for ch in chunks:
        if not re.match(r"^\d+(?:\.\d+)*\.?\s+", ch):
            split_rows.append(("", ch, "", pno))
            continue
        r1 = role_blocks[step_idx] if step_idx < len(role_blocks) else (role_blocks[-1] if role_blocks else col1.strip())
        r3 = ref_blocks[step_idx] if step_idx < len(ref_blocks) else (col3.strip() if step_idx == 0 else "")
        split_rows.append((r1, ch, r3, pno))
        step_idx += 1
    return split_rows


def extract_proses_kerja_rows(pdf_path: Path, file_stem: str) -> List[Tuple[str, str, str, int]]:
    """Extract 3-column Proses Kerja rows (anggota, tindakan, rujukan, page_no).

    Skips cover/TOC pages reliably, detects merged multi-step table cells, and falls back
    to exact word x/y-coordinate column alignment whenever bordered table extraction merges
    or misses rows.
    """
    rows: List[Tuple[str, str, str, int]] = []
    force_xcoord = file_stem in {
        "UIP-AKPMDKA-02-24", "UIP-UMUM-01-22", "UIP-APSPP-02-07",
        "UIP-APSPP-02-16", "UIP-UMUM-01-16", "UIP-UMUM-05-24", "UIP-UMUM-06-24",
        "UIP-APPPB-01-16",
    }

    with fitz.open(pdf_path) as doc:
        in_proses = False
        for pno, page in enumerate(doc, start=1):
            raw_txt = page.get_text("text") or ""
            low = raw_txt.lower()

            # Reliably skip cover & Table of Contents pages (can extend to pno 3!)
            is_toc_page = (
                "isi kandungan" in low
                or "kandungan" in low[:300]
                or ("senarai lampiran" in low and "tindakan" not in low)
                or (pno <= 2 and "kementerian kesihatan malaysia" in low and "tindakan" not in low)
            )
            if is_toc_page:
                continue

            has_proses_hdr = bool(re.search(r"(?:^|\n)\s*(?:\d+\.?\s*)?proses\s+kerja\b", low))
            has_table_hdr = bool(
                re.search(r"(?:^|\n)\s*angg+ota\s*\n?\s*(?:yang\s+)?terlibat\b", low)
                and re.search(r"(?:^|\n)\s*tindakan\s*(?:\n|$)", low)
            )
            has_carta_hdr = bool(re.search(r"(?:^|\n)\s*(?:\d+\.?\s*)?c?arta\s+alir\b", low))

            if has_proses_hdr or (not in_proses and has_table_hdr and pno >= 3):
                in_proses = True
            if in_proses and has_carta_hdr and not has_proses_hdr and not has_table_hdr:
                break
            if not in_proses:
                continue

            page_rows: List[Tuple[str, str, str, int]] = []
            if not force_xcoord:
                try:
                    tabs = page.find_tables()
                    for tab in tabs.tables:
                        data = tab.extract() or []
                        for r in data:
                            cells = [clean_pdf_text(str(c or "")) for c in r]
                            if not any(cells):
                                continue
                            joined_low = " ".join(cells).lower()
                            if "angg" in joined_low and "tindakan" in joined_low:
                                continue
                            if len(cells) >= 3:
                                col1, col2, col3 = cells[0], cells[1], " ".join(c for c in cells[2:] if c)
                            elif len(cells) == 2:
                                col1, col2, col3 = "", cells[0], cells[1]
                            else:
                                col1, col2, col3 = "", cells[0], ""
                            if col2 or col1:
                                page_rows.extend(_split_merged_cell_row(col1, col2, col3, pno))
                except Exception:
                    page_rows = []

            # If borderless or find_tables returned suspiciously few rows, use exact x/y alignment
            if force_xcoord or len(page_rows) == 0:
                xy_rows, hit_end = _extract_page_rows_by_xcoord(page, pno)
                if xy_rows:
                    page_rows = xy_rows
                if hit_end:
                    rows.extend(page_rows)
                    break

            rows.extend(page_rows)

            if has_carta_hdr and not has_proses_hdr:
                break

    return rows


def extract_section_block(full_text: str, start_pat: str, end_pats: List[str], max_chars: int = 3500) -> str:
    # Search after TOC (skip first pages containing Isi Kandungan / Senarai Lampiran)
    search_start = 0
    for toc_kw in (r"SENARAI\s+LAMPIRAN", r"I\s*S\s*I\s+K\s*A\s*N\s*D\s*U\s*N\s*G\s*A\s*N|ISI\s+KANDUNGAN"):
        toc_m = re.search(toc_kw, full_text[:5500], re.I)
        if toc_m:
            pm = re.search(r"### \[Muka Surat PDF:", full_text[toc_m.end():])
            if pm:
                search_start = max(search_start, toc_m.end() + pm.start())

    sub = full_text[search_start:]
    m = re.search(start_pat, sub, re.I | re.M)
    if not m:
        m = re.search(start_pat, full_text, re.I | re.M)
        if not m:
            return ""
        sub = full_text[m.end():]
    else:
        sub = sub[m.end():]

    end_idx = len(sub)
    for ep in end_pats:
        em = re.search(ep, sub, re.I | re.M)
        if em and em.start() < end_idx:
            end_idx = em.start()
    return clean_pdf_text(sub[:min(end_idx, max_chars)])


def parse_tujuan(full_text: str, tajuk: str) -> str:
    blk = extract_section_block(
        full_text,
        r"(?:^|\n)\s*(?:\d+\.?\s*)?TUJUAN(?:\s+PROSEDUR)?\b[^\n]*\n",
        [
            r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:PANDUAN\s+AM|PUNCA\s+KUASA|UNDANG-UNDANG\s+BERKAITAN|SKOP|LATAR\s+BELAKANG|DEFINI[CS]I|ANGG+OTA\s+(?:YANG\s+)?TERLIBAT)\b",
        ],
        max_chars=1200,
    )
    blk = re.sub(r"### \[Muka Surat PDF:[^\]]+\]", "", blk)
    blk = strip_running_headers_and_footers(blk)
    blk = re.sub(r"\s+", " ", blk).strip()
    if len(blk) >= 25:
        return blk[:650]
    return f"Menggariskan tatacara pelaksanaan rasmi bagi {tajuk} oleh pegawai penguat kuasa KKM."


def parse_anggota(full_text: str) -> List[Dict[str, str]]:
    blk = extract_section_block(
        full_text,
        r"(?:^|\n)\s*(?:\d+\.?\s*)?ANGG+OTA\s+(?:YANG\s+)?TERLIBAT\b[^\n]*\n",
        [r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:SINGKATAN|PROSES\s+KERJA|PANDUAN\s+AM|DEFINI[CS]I|RUJUKAN)\b"],
        max_chars=1800,
    )
    found: List[Dict[str, str]] = []
    seen: set[str] = set()
    for ln in blk.splitlines():
        s = re.sub(r"^[\-\•\d\.\)\s]+", "", ln.strip())
        if len(s) < 3 or s.startswith("###"):
            continue
        m = re.search(r"\(([A-Z]{2,6})\)", s)
        if m:
            kod = m.group(1)
            jaw = re.sub(r"\s*\([A-Z]{2,6}\)\s*", "", s).strip(" -–:")
        else:
            code_m = ROLE_CODE_RE.search(s)
            kod = code_m.group(1) if code_m else s[:12].upper()
            jaw = KNOWN_ROLE_TITLES.get(kod, s)
        if kod not in seen:
            seen.add(kod)
            found.append({"kod": kod, "jawatan": jaw or KNOWN_ROLE_TITLES.get(kod, kod)})
    if not found:
        for kod in ROLE_CODE_RE.findall(full_text):
            if kod in KNOWN_ROLE_TITLES and kod not in seen:
                seen.add(kod)
                found.append({"kod": kod, "jawatan": KNOWN_ROLE_TITLES[kod]})
                if len(found) >= 8:
                    break
    return found[:12]


def parse_singkatan(full_text: str) -> List[Dict[str, str]]:
    blk = extract_section_block(
        full_text,
        r"(?:^|\n)\s*(?:\d+\.?\s*)?SINGKATAN(?:\s+YANG\s+DI\s*GUNAKAN)?\b[^\n]*\n",
        [r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:PROSES\s+KERJA|PANDUAN\s+AM|KAWALAN|TATACARA|C?ARTA\s+ALIR)\b"],
        max_chars=3600,
    )
    blk = re.sub(r"### \[Muka Surat PDF:[^\]]+\]", "", blk)
    blk = strip_running_headers_and_footers(blk)
    items: List[Dict[str, str]] = []
    seen: set[str] = set()

    # Strategy 1: Numbered KKM format `6.1 \n KPPKP \n : \n Ketua ...`
    numbered_chunks = re.split(r"(?=(?:^|\n)\s*\d+\.\d+\.?\s+)", blk)
    for ch in numbered_chunks:
        flat = re.sub(r"\s+", " ", ch).strip()
        m = re.match(r"^\d+\.\d+\.?\s+([^:]{1,40}?)\s*[:\-–=]\s*(.+)$", flat)
        if m:
            kod = m.group(1).strip()
            mak = m.group(2).strip().rstrip(".")
            if kod and kod not in seen and len(mak) >= 3:
                seen.add(kod)
                items.append({"kod": kod, "maksud": mak})

    # Strategy 2: Unnumbered `CODE : Meaning` or two-line pairs
    if not items:
        lines = [ln.strip() for ln in blk.splitlines() if ln.strip() and not ln.strip().startswith("###")]
        i = 0
        while i < len(lines):
            ln = lines[i]
            m = re.match(r"^([A-Z0-9/\(\)&]{2,15})\s*[:\-–=]\s*(.+)$", ln)
            if m:
                kod, mak = m.group(1).strip(), m.group(2).strip()
                if kod not in seen and len(mak) >= 3:
                    seen.add(kod)
                    items.append({"kod": kod, "maksud": mak})
                i += 1
                continue
            if re.match(r"^[A-Z0-9/]{2,10}$", ln) and i + 1 < len(lines) and len(lines[i + 1]) >= 4:
                kod, mak = ln, lines[i + 1].lstrip(":-– ").strip()
                if kod not in seen:
                    seen.add(kod)
                    items.append({"kod": kod, "maksud": mak})
                i += 2
                continue
            i += 1
    return items[:30]


def parse_undang_undang(full_text: str, akta_berkaitan: List[str], file_stem: str) -> List[Dict[str, Any]]:
    blk = extract_section_block(
        full_text,
        r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:UNDANG-UNDANG\s+BERKAITAN|PUNCA\s+KUASA)\b[^\n]*\n",
        [r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:ANGG+OTA|SINGKATAN|PROSES\s+KERJA|PANDUAN\s+AM)\b"],
        max_chars=2200,
    )
    items: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for ln in blk.splitlines():
        s = re.sub(r"^[\-\•\d\.\)\s]+", "", ln.strip())
        if len(s) < 6 or s.startswith("###") or "no. rujukan" in s.lower():
            continue
        if not re.search(r"\b(?:akta|peraturan|kanun|perintah|p\.u\.|ihr|ordinan)\b", s, re.I):
            continue
        key = s.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        is_ppkht = bool(re.search(r"ppkht|kawalan\s+hasil\s+tembakau\s+2004", s, re.I))
        is_pu327 = bool(re.search(r"327/1993", s, re.I))
        act_m = re.search(r"Akta\s+(\d+)", s, re.I)
        akta_kod = f"Akta {act_m.group(1)}" if act_m else None
        status = "DIMANSUHKAN" if (is_ppkht or is_pu327) else "AKTIF"
        nota = None
        if is_ppkht:
            nota = "[NOTA PINDAAN] Dimansuhkan mulai 1 Okt 2024 dan digantikan oleh Akta 852."
        elif is_pu327:
            nota = "[NOTA PINDAAN] Digantikan oleh Akta A1742 & P.U.(A) 139/2025 (berkuat kuasa 1 Mei 2025)."
        items.append({"akta": s[:220], "akta_kod": akta_kod, "status": status, "nota": nota})

    if not items:
        for a in akta_berkaitan:
            items.append({"akta": a, "akta_kod": a, "status": "AKTIF", "nota": None})

    # Ensure Akta 852 / Akta A1742 companion statutes appear when relevant
    if file_stem in APPPB_STEMS and not any("A1742" in it["akta"] for it in items):
        items.append({
            "akta": "Akta Pencegahan dan Pengawalan Penyakit Berjangkit (Pindaan) 2025 [Akta A1742] & P.U.(A) 139/2025",
            "akta_kod": "Akta 342",
            "status": "AKTIF",
            "nota": "[NOTA PINDAAN] Berkuat kuasa 1 Mei 2025 — mengatasi kadar penalti & kompaun lama cetakan SOP 15 Feb 2024.",
        })
    return items[:15]


def extract_sla_timelines(full_text: str, file_stem: str) -> List[Dict[str, Optional[str]]]:
    """Extract verified operational SLA / statutory timelines."""
    curated: Dict[str, List[Dict[str, Optional[str]]]] = {
        "UIP-AKPMDKA-01-24": [
            {"label": "Tempoh Tawaran Bayaran Kompaun", "tempoh": "14 hari / 30 hari", "rujukan": "Seksyen 48 Akta 852 & P.U.(A) 259/2024"},
            {"label": "Tarikh Hadir Mahkamah (Notis S.47)", "tempoh": "Selepas 60 hari dari tarikh notis", "rujukan": "Seksyen 47 Akta 852"},
        ],
        "UIP-AKPMDKA-06-24": [
            {"label": "Tempoh Semakan / Pelucuthakan Barang Disita", "tempoh": "30 hari", "rujukan": "Seksyen 37 Akta 852"},
        ],
        "UIP-AKPMDKA-07-24": [
            {"label": "Pemulangan Sementara Barang Disita", "tempoh": "Tertakluk syarat & bon S.37", "rujukan": "Seksyen 37 Akta 852"},
        ],
        "UIP-APSPP-01-24": [
            {"label": "Tempoh Penutupan Tapak Binaan", "tempoh": "14 hari (maksimum)", "rujukan": "Seksyen 8(3)(aa) Akta 154"},
            {"label": "Rayuan Buka Semula Premis", "tempoh": "Sekurang-kurangnya 3 hari selepas tutup", "rujukan": "Lampiran D UIP-APSPP-01-24"},
        ],
        "UIP-APSPP-01-07": [
            {"label": "Serahan Sampul Kecil ke UIPD", "tempoh": "Dalam tempoh 3 hari", "rujukan": "Proses Kerja UIP-APSPP-01-07"},
            {"label": "Pemeriksaan Selepas 10 Malam", "tempoh": "Perlu Notis S.5(3) Akta 154", "rujukan": "Seksyen 5(3) Akta 154"},
        ],
        "UIP-APSPP-01-16": [
            {"label": "Notis Sebelum Pecah Masuk Premis Berkunci", "tempoh": "24 jam / <=7 hari (semak konsistensi)", "rujukan": "Seksyen 5(5) Akta 154"},
        ],
        "UIP-APPPB-01-07": [
            {"label": "Tempoh Penutupan Premis Basmi Kuman", "tempoh": "Tidak kurang 3 hari (maks 14 hari)", "rujukan": "Perenggan 18(1)(d) Akta 342"},
        ],
        "UIP-APPPB-02-07": [
            {"label": "Tempoh Pelaksanaan Arahan Basmi Kuman", "tempoh": "3 hingga 14 hari", "rujukan": "Perenggan 18(1)(c) Akta 342"},
        ],
        "UIP-APPPB-01-16": [
            {"label": "Perintah Lisan Kepada Bertulis", "tempoh": "Dalam tempoh 24 jam", "rujukan": "Subseksyen 15(1) Akta 342"},
        ],
        "UIP-APPPB-01-21": [
            {"label": "Tempoh Bayaran Kompaun Akta 342", "tempoh": "14 hari dari tarikh tawaran", "rujukan": "Seksyen 25 Akta 342 & P.U.(A) 139/2025"},
        ],
        "UIP-UMUM-04-24": [
            {"label": "Tempoh Bayaran Kompaun Akta Makanan 1983", "tempoh": "14 hari dari tarikh serahan notis S.32B", "rujukan": "Seksyen 32B & 33 Akta 281"},
        ],
        "UIP-UMUM-05-07": [
            {"label": "Pra-Perbicaraan (S.172A KTJ)", "tempoh": "30 hari", "rujukan": "Seksyen 172A KTJ"},
            {"label": "Serahan Sapina Saksi", "tempoh": "10 hari sebelum bicara", "rujukan": "UIP-UMUM-05-07"},
            {"label": "Laporan Keputusan ke UIPN / Rayuan TPR", "tempoh": "3 hari ke UIPN / 14 hari ke TPR", "rujukan": "UIP-UMUM-05-07"},
        ],
    }
    if file_stem in curated:
        return curated[file_stem]

    # Auto-detect timelines from text
    found: List[Dict[str, Optional[str]]] = []
    seen: set[str] = set()
    for m in re.finditer(r"(\d+\s*(?:hingga\s*\d+\s*)?(?:jam|hari|minggu|bulan))", full_text, re.I):
        tp = re.sub(r"\s+", " ", m.group(1)).strip()
        if tp.lower() in seen:
            continue
        ctx = full_text[max(0, m.start() - 60):min(len(full_text), m.end() + 70)]
        ctx = re.sub(r"\s+", " ", ctx).strip()
        if any(skip in ctx.lower() for skip in ("isi kandungan", "muka surat", "kuatkuasa", "februari", "oktober", "april")):
            continue
        seen.add(tp.lower())
        found.append({"label": ctx[:85], "tempoh": tp, "rujukan": file_stem})
        if len(found) >= 4:
            break
    return found


def build_nota_pindaan(file_stem: str, existing_master_notes: List[str]) -> List[Dict[str, Any]]:
    """Build mandatory Statute > SOP [NOTA PINDAAN] alerts."""
    notes: List[Dict[str, Any]] = []

    if file_stem == "UIP-APPPB-01-21":
        notes.append({
            "tahap": "KRITIKAL",
            "tajuk": "[NOTA PINDAAN] Kadar Kompaun & Penalti Akta 342 Dipinda (Akta A1742 & P.U.(A) 139/2025)",
            "butiran": (
                "Teks cetakan SOP 15 Feb 2024 masih menyebut P.U.(A) 327/1993 dan kadar lama RM1,000.00. "
                "Mulai 1 Mei 2025, Akta A1742 & P.U.(A) 139/2025 menetapkan had kompaun S.25 sehingga RM5,000 (individu) / "
                "RM50,000 (pertubuhan perbadanan) bagi kesalahan Jadual Pertama (S.10(2), S.11(5), S.21A(3), S.22(b)/(c)/(d)) "
                "dengan keizinan bertulis Pendakwa Raya, dan penalti am S.24 sehingga RM10,000/2 tahun (individu) atau RM100,000 (korporat)."
            ),
            "gantian_statut": "Akta A1742 & P.U.(A) 139/2025 (1 Mei 2025)",
        })
    elif file_stem in APPPB_STEMS:
        notes.append({
            "tahap": "AMARAN",
            "tajuk": "[NOTA PINDAAN] Pindaan Penalti & Kuasa Akta 342 (Akta A1742 — 1 Mei 2025)",
            "butiran": (
                "SOP ini berkuat kuasa 15 Feb 2024 sebelum Akta Pencegahan dan Pengawalan Penyakit Berjangkit (Pindaan) 2025 [Akta A1742] "
                "dan P.U.(A) 139/2025 (1 Mei 2025). Utamakan had penalti baharu Seksyen 24(a) (individu maks RM10,000 / penjara 2 tahun) "
                "dan Seksyen 24(b) (pertubuhan perbadanan maks RM100,000) serta liabiliti korporat S.22A."
            ),
            "gantian_statut": "Akta A1742 & P.U.(A) 139/2025 (1 Mei 2025)",
        })

    if file_stem in PPKHT_AFFECTED_STEMS:
        extra = ""
        if file_stem == "UIP-UMUM-01-16":
            extra = " Rujukan 'UIP-PPKHT-01-16' pada Lampiran A item 5 adalah mansuh dan digantikan oleh UIP-AKPMDKA-01-24."
        elif file_stem == "UIP-UMUM-02-07":
            extra = " Lampiran C (Senarai Semak K/S PPKHT 2004 / Notis 32B) adalah MANSUH — guna UIP-AKPMDKA-01-24 / UIP-AKPMDKA-05-24 bersama Notis S.47 & Izin Dakwa S.41 Akta 852."
        elif file_stem == "UIP-UMUM-05-24":
            extra = " Langkah 6 yang menyebut 'PPKHT 2004 dan Akta 852' hendaklah dibaca sebagai Akta 852 sahaja bersama UIP-AKPMDKA-06-24 & 08-24."
        notes.append({
            "tahap": "KRITIKAL" if file_stem in {"UIP-UMUM-02-07", "UIP-UMUM-01-16", "UIP-UMUM-05-24"} else "AMARAN",
            "tajuk": "[NOTA PINDAAN] PPKHT 2004 Dimansuhkan — Digantikan Oleh Akta 852 (1 Okt 2024)",
            "butiran": (
                "Sebarang rujukan PPKHT 2004 dan Notis Seksyen 32B Akta Makanan 1983 bagi kesalahan produk merokok/vape dalam SOP ini "
                "telah DIMANSUHKAN mulai 1 Oktober 2024 dan digantikan sepenuhnya oleh Akta 852 (UIP-AKPMDKA-01-24 hingga 08-24)."
                + extra
            ),
            "gantian_statut": "Akta 852 & UIP-AKPMDKA-01-24..08-24 (1 Okt 2024)",
        })

    if file_stem in AKTA_281_FOOD_STEMS:
        if file_stem == "UIP-UMUM-04-24":
            notes.append({
                "tahap": "INFO",
                "tajuk": "[NOTA PINDAAN] Skop Akta A1702: Notis S.32B KEKAL SAH Bagi Keselamatan Makanan Sahaja",
                "butiran": (
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 (PPM 1985 & PPKM 2009) KEKAL 100% SAH DAN BERKUAT KUASA bagi kesalahan makanan. "
                    "Akta A1702 (1 Okt 2024) hanya memindahkan produk merokok/tembakau/vape ke Akta 852 (guna UIP-AKPMDKA-01-24 & Notis S.47/S.48)."
                ),
                "gantian_statut": "Akta Makanan (Pindaan) 2024 [Akta A1702]",
            })
        else:
            target_852 = "UIP-AKPMDKA-02-24 (S.32)" if file_stem == "UIP-UMUM-03-24" else "UIP-AKPMDKA-03-24 (S.33)"
            notes.append({
                "tahap": "INFO",
                "tajuk": "[NOTA PINDAAN] Skop Akta A1702: Geledah Akta Makanan 1983 (Makanan Sahaja)",
                "butiran": (
                    f"Berikutan Akta A1702 (1 Okt 2024), prosedur ini terpakai khusus bagi penguatkuasaan keselamatan makanan di bawah Akta 281. "
                    f"Bagi kes penggeledahan produk merokok/vape di bawah Akta 852, rujuk {target_852}."
                ),
                "gantian_statut": f"Akta A1702 & {target_852}",
            })

    if file_stem == "UIP-UMUM-01-24":
        notes.append({
            "tahap": "AMARAN",
            "tajuk": "[NOTA PINDAAN] Halangan Tugas Semasa Penguatkuasaan Akta 852 -> Seksyen 186 Kanun Keseksaan",
            "butiran": (
                "Disahkan terhadap teks rasmi AKTA_852.pdf bahawa Akta 852 TIDAK mempunyai seksyen halangan tugas tersendiri. "
                "Sekiranya PPKP dihalang, diugut atau dikasari semasa operasi Akta 852, buat Laporan Polis (S.107 KTJ) "
                "untuk siasatan PDRM di bawah Seksyen 186 / 353 / 506 Kanun Keseksaan [Akta 574]."
            ),
            "gantian_statut": "Seksyen 186 Kanun Keseksaan [Akta 574] & S.107 KTJ",
        })

    if file_stem == "UIP-UMUM-01-22":
        notes.append({
            "tahap": "INFO",
            "tajuk": "Pembetulan Konflik Kod Cetakan (UIP-UMUM-01-23 -> UIP-UMUM-01-22)",
            "butiran": "Jadual Kandungan buku SOP mencetak kod 'UIP-UMUM-01-23', namun kod rasmi dalam badan prosedur ialah UIP-UMUM-01-22 (PINDAAN 2024).",
            "gantian_statut": None,
        })
    if file_stem == "UIP-APPPB-06-20":
        notes.append({
            "tahap": "INFO",
            "tajuk": "Pembetulan Konflik Kod Cetakan (UIP-APPPB-01-20 -> UIP-APPPB-06-20)",
            "butiran": "Jadual Kandungan buku SOP mencetak kod 'UIP-APPPB-01-20', namun kod rasmi dalam badan prosedur ialah UIP-APPPB-06-20 (PINDAAN 2024).",
            "gantian_statut": None,
        })
    if file_stem == "UIP-APPPB-01-16":
        notes.append({
            "tahap": "INFO",
            "tajuk": "Pembetulan Ralat Cetak Seksyen (Subseksyen 5(1) -> Subseksyen 15(1) Akta 342)",
            "butiran": "Jadual Kandungan mencetak 'Subseksyen 5(1)' secara salah cetak; peruntukan sah bagi Perintah Pemerhatian/Pengawasan ialah Subseksyen 15(1) Akta 342.",
            "gantian_statut": "Subseksyen 15(1) Akta 342",
        })

    return notes


def build_fasa_kerja_and_flowchart(
    rows: List[Tuple[str, str, str, int]],
    file_stem: str,
    known_stems: set[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    """Convert raw Proses Kerja rows into structured phases, steps, flowchart DAG, and field checklist."""
    phases: List[Dict[str, Any]] = []
    current_phase: Dict[str, Any] = {
        "fasa_id": "F1",
        "tajuk_fasa": "1. Pelaksanaan Proses Kerja",
        "langkah": [],
    }
    phase_counter = 1
    step_counter = 0

    for col1, col2, col3, pno in rows:
        t_clean = re.sub(r"\s+", " ", col2).strip()
        if not t_clean or len(t_clean) < 3:
            continue
        # Fix broken cross-ref UIP-UMUM-05-16 -> UIP-UMUM-05-07
        col3_fixed = re.sub(r"UIP-UMUM-05-16", "UIP-UMUM-05-07", col3, flags=re.I)
        t_fixed = re.sub(r"UIP-UMUM-05-16", "UIP-UMUM-05-07", t_clean, flags=re.I)

        # Detect phase header row (no roles, short uppercase or numbered section header like "1. SEBELUM PEMERIKSAAN" or "1.0 Perancangan")
        is_phase_header = (
            not col1.strip()
            and not col3.strip()
            and len(t_fixed) <= 90
            and (
                t_fixed.isupper()
                or bool(re.match(r"^(?:[A-Z]\.|FASA\s+\d+|\d+\.0\s+\S|\d+\.\s+[A-Z][A-Z\s/\-]{4,})$", t_fixed))
                or any(
                    t_fixed.lower().startswith(p)
                    for p in ("sebelum ", "semasa ", "selepas ", "persediaan", "di pejabat", "di lapangan", "di mahkamah", "tindakan susulan", "pendakwaan")
                )
            )
        )
        if is_phase_header:
            if current_phase["langkah"]:
                phases.append(current_phase)
                phase_counter += 1
            current_phase = {
                "fasa_id": f"F{phase_counter}",
                "tajuk_fasa": t_fixed.title() if t_fixed.isupper() else t_fixed,
                "langkah": [],
            }
            continue

        # Continuation row without step number and without roles -> append to previous step
        num_m = re.match(r"^(\d+(?:\.\d+)*)\.?\)?\s+(.+)$", t_fixed)
        if not num_m and not col1.strip() and current_phase["langkah"]:
            prev = current_phase["langkah"][-1]
            prev["tindakan"].append(t_fixed)
            if col3_fixed.strip():
                for ref_ln in [x.strip() for x in col3_fixed.splitlines() if x.strip()]:
                    if ref_ln not in prev["rujukan"]:
                        prev["rujukan"].append(ref_ln)
            continue

        step_counter += 1
        if num_m:
            step_no = num_m.group(1)
            step_body = num_m.group(2).strip()
        else:
            step_no = str(step_counter)
            step_body = t_fixed

        # Extract roles
        roles = list(dict.fromkeys(ROLE_CODE_RE.findall(col1.upper())))
        if not roles and col1.strip():
            roles = [r.strip() for r in re.split(r"[/,\n]+", col1.strip()) if r.strip()][:4]

        # Extract references, lampiran, cross-SOPs
        ref_blob = f"{col3_fixed} {step_body}"
        rujukan_list = [x.strip() for x in re.split(r"\n|;", col3_fixed) if x.strip()]
        lampiran_refs = list(
            dict.fromkeys(
                f"{m.group(1).capitalize()} {m.group(2).upper()}"
                for m in re.finditer(r"\b(Lampiran|Borang)\s+([A-Z0-9]{1,3})\b", ref_blob, re.I)
            )
        )
        sop_refs = list(
            dict.fromkeys(
                m.group(1).upper()
                for m in re.finditer(r"\b(UIP-[A-Z]+-\d{2}-\d{2})\b", ref_blob, re.I)
                if "PPKHT" not in m.group(1).upper()
                and m.group(1).upper() != file_stem.upper()
                and (not known_stems or m.group(1).upper() in known_stems)
            )
        )
        # Map deprecated UIP-APSPP-03-07 -> UIP-UMUM-01-24
        if re.search(r"UIP-APSPP-03-07", ref_blob, re.I) and "UIP-UMUM-01-24" not in sop_refs:
            sop_refs.append("UIP-UMUM-01-24")

        # Extract SLA mention in step
        sla_m = re.search(r"(\d+\s*(?:hingga\s*\d+\s*)?(?:jam|hari|minggu|bulan))", step_body, re.I)
        sla_val = re.sub(r"\s+", " ", sla_m.group(1)).strip() if sla_m else None

        # Detect conditional decision branch
        keputusan = None
        if re.search(r"\b(?:sekiranya|jika|apabila|enggan|gagal\s+bayar|tidak\s+mematuhi|tidak\s+lengkap|dihalang)\b", step_body, re.I):
            keputusan = {
                "soalan": f"Semakan syarat langkah {step_no}: {step_body[:95]}{'...' if len(step_body) > 95 else ''}",
                "cabang_ya": "Laksanakan tindakan khas / rujuk SOP berkaitan seperti dinyatakan dalam langkah ini.",
                "cabang_tidak": "Teruskan ke langkah aliran kerja berikutnya.",
            }

        # Inline amendment warning if step touches PPKHT 2004 / old S.32B tobacco / RM1,000 Akta 342
        amaran_pindaan = None
        if re.search(r"ppkht\s*2004|uip-ppkht", ref_blob, re.I):
            amaran_pindaan = "[NOTA PINDAAN] PPKHT 2004 dimansuhkan (1 Okt 2024) — rujuk Akta 852 & UIP-AKPMDKA-01-24..08-24."
        elif file_stem == "UIP-APPPB-01-21" and re.search(r"1,000|327/1993", ref_blob, re.I):
            amaran_pindaan = "[NOTA PINDAAN] Had kompaun Akta 342 dipinda oleh Akta A1742 & P.U.(A) 139/2025 (maks RM5,000 individu / RM50,000 korporat)."

        # Short concise title for step
        first_sentence = re.split(r"(?<=[.;])\s+", step_body)[0]
        tajuk_step = first_sentence[:110].rstrip(".,;:")

        # Split bullet sub-actions cleanly
        tindakan_items = [s.strip() for s in re.split(r"\s+(?=(?:[a-z]\)|i+\)|-\s+))", step_body) if s.strip()]
        if not tindakan_items:
            tindakan_items = [step_body]

        current_phase["langkah"].append({
            "no": step_no,
            "tajuk": tajuk_step,
            "anggota": roles,
            "tindakan": tindakan_items,
            "rujukan": rujukan_list[:6],
            "rujukan_lampiran": lampiran_refs[:6],
            "rujukan_sop": sop_refs[:4],
            "sla": sla_val,
            "keputusan": keputusan,
            "amaran_pindaan": amaran_pindaan,
            "muka_surat_pdf": pno,
        })

    if current_phase["langkah"]:
        phases.append(current_phase)

    # Ensure at least 1 phase even if PDF had unusual layout
    if not phases:
        phases = [{
            "fasa_id": "F1",
            "tajuk_fasa": "1. Ringkasan Tatacara Pelaksanaan",
            "langkah": [{
                "no": "1",
                "tajuk": "Rujuk prosedur penuh SOP pada tab Teks Penuh Asal",
                "anggota": ["PPKP"],
                "tindakan": ["Sila rujuk teks penuh SOP yang disahkan bagi perincian langkah kerja."],
                "rujukan": [file_stem],
                "rujukan_lampiran": [],
                "rujukan_sop": [],
                "sla": None,
                "keputusan": None,
                "amaran_pindaan": None,
                "muka_surat_pdf": 1,
            }],
        }]

    # Build clean visual flowchart DAG from structured steps (guaranteed valid ordered DAG!)
    nodes: List[Dict[str, Any]] = [
        {"id": "N_START", "type": "start", "label": "Mula Operasi / Prosedur", "role": None, "step_ref": None, "sop_ref": None}
    ]
    edges: List[Dict[str, Any]] = []
    prev_id = "N_START"
    flat_steps = [st for ph in phases for st in ph["langkah"]]
    # Cap flowchart at 14 concise readable nodes so it is scannable on mobile & desktop
    selected_steps = flat_steps[:14]
    for idx, st in enumerate(selected_steps, start=1):
        nid = f"N{idx}"
        is_dec = st["keputusan"] is not None
        role_str = "/".join(st["anggota"][:2]) if st["anggota"] else None
        sop_ref = st["rujukan_sop"][0] if st["rujukan_sop"] else None
        nodes.append({
            "id": nid,
            "type": "decision" if is_dec else "process",
            "label": f"{st['no']}. {st['tajuk'][:88]}",
            "role": role_str,
            "step_ref": st["no"],
            "sop_ref": sop_ref,
        })
        edge_label = "Teruskan" if (idx > 1 and nodes[-2]["type"] == "decision") else None
        edges.append({"from": prev_id, "to": nid, "label": edge_label})
        prev_id = nid
    nodes.append({"id": "N_END", "type": "end", "label": "Selesai & Rekod Fail UIP", "role": None, "step_ref": None, "sop_ref": None})
    edges.append({"from": prev_id, "to": "N_END", "label": None})
    carta_alir = {"nodes": nodes, "edges": edges}

    # Build interactive field checklist from steps + lampiran
    checklist: List[Dict[str, Any]] = []
    chk_idx = 0
    for ph in phases:
        for st in ph["langkah"]:
            if len(checklist) >= 12:
                break
            chk_idx += 1
            ref_str = ", ".join(st["rujukan_lampiran"][:2] or st["rujukan"][:1]) or None
            checklist.append({
                "id": f"CHK-{chk_idx:02d}",
                "kumpulan": ph["tajuk_fasa"],
                "item": f"[{st['no']}] {st['tajuk']}",
                "wajib": True,
                "rujukan": ref_str,
            })

    return phases, carta_alir, checklist


def parse_lampiran(
    full_text: str,
    file_stem: str,
    existing_master_lampiran: Optional[Dict[str, Any]],
    pages: List[Tuple[int, str, int]],
) -> List[Dict[str, Any]]:
    """Build verified Lampiran/Borang cards with status & OCR-scan indicators."""
    items: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()

    def _classify_jenis(tajuk: str) -> str:
        low = tajuk.lower()
        if "senarai semak" in low:
            return "senarai_semak"
        if "jadual" in low or "kadar kompaun" in low:
            return "jadual_kompaun"
        if "daftar" in low or "buku" in low:
            return "buku_daftar"
        if "surat" in low or "contoh" in low or "draf" in low or "afidavit" in low:
            return "surat_contoh"
        if "cara mengisi" in low or "panduan" in low:
            return "panduan"
        if "borang" in low or "notis" in low or "perintah" in low or "perakuan" in low or "sijil" in low:
            return "borang"
        return "lain"

    # 1. Start from verified master index lampiran for the 22 existing SOPs
    if isinstance(existing_master_lampiran, dict):
        for kod, val in existing_master_lampiran.items():
            kod_clean = str(kod).strip()
            tajuk = str(val.get("tajuk") if isinstance(val, dict) else val).strip()
            if not kod_clean or kod_clean.upper() in seen_codes:
                continue
            seen_codes.add(kod_clean.upper())
            is_dep = bool(re.search(r"DEPRECATED|PPKHT\s*2004", tajuk, re.I))
            items.append({
                "kod": kod_clean,
                "tajuk": tajuk,
                "jenis": _classify_jenis(tajuk),
                "muka_surat_pdf": str(val.get("muka_surat_pdf") or "") if isinstance(val, dict) else None,
                "status": "DEPRECATED_PPKHT_2004" if is_dep else "AKTIF",
                "status_ekstrak": "teks_penuh",
                "nota": "[NOTA PINDAAN] Dimansuhkan — guna Akta 852 / UIP-AKPMDKA-01-24." if is_dep else None,
            })

    # 2. Extract Lampiran / Borang headings from PDF pages (especially for the 11 new SOPs)
    if not items:
        for pno, ptxt, imgs in pages:
            low_p = ptxt.lower()
            if pno <= 2 and "isi kandungan" in low_p:
                continue
            m = re.search(r"(?:^|\n)\s*(LAMPIRAN\s+[A-Z0-9]{1,3}|BORANG\s+[A-Z0-9]{1,3})\s*[:\-–]?\s*([^\n]{0,120})", ptxt, re.I)
            if m:
                kod = re.sub(r"\s+", " ", m.group(1)).strip().title()
                tajuk = m.group(2).strip(" :-–")
                if len(tajuk) < 4:
                    # Grab next non-empty line
                    after = ptxt[m.end():].splitlines()
                    for al in after:
                        als = al.strip()
                        if len(als) >= 4 and not re.match(r"^no\.?\s*rujukan", als, re.I):
                            tajuk = als[:140]
                            break
                if kod.upper() in seen_codes:
                    continue
                seen_codes.add(kod.upper())
                is_raster_only = (len(strip_running_headers_and_footers(ptxt)) < 85 and imgs > 0)
                items.append({
                    "kod": kod,
                    "tajuk": tajuk or f"Dokumen Rasmi {kod}",
                    "jenis": _classify_jenis(tajuk),
                    "muka_surat_pdf": str(pno),
                    "status": "AKTIF",
                    "status_ekstrak": "imej_imbasan_perlu_ocr" if is_raster_only else "teks_penuh",
                    "nota": "Halaman imbasan imej asal PDF (jadual/borang imbasan — rujuk salinan PDF rasmi KKM)." if is_raster_only else None,
                })

    # Special verified metadata for UIP-UMUM-04-24 (14 Lampiran A-N including 15 raster pages D,E,F,G,K,L)
    if file_stem == "UIP-UMUM-04-24":
        curated_04_24 = [
            ("Lampiran A", "Notis Memerintahkan Kehadiran Di Mahkamah (Seksyen 32B Akta Makanan 1983)", "13", "teks_penuh", None),
            ("Lampiran B", "Tawaran Mengkompaun Kesalahan (Seksyen 33 Akta Makanan 1983)", "14", "teks_penuh", None),
            ("Lampiran C", "Resit Rasmi Bayaran Kompaun & Perakuan Penerimaan", "15", "teks_penuh", None),
            ("Lampiran D", "Borang Permohonan Pengurangan Kompaun (Imbasan)", "16-17", "imej_imbasan_perlu_ocr", "Halaman imbasan asal PDF."),
            ("Lampiran E", "Surat Keputusan Pengurangan Kompaun (Imbasan)", "18-19", "imej_imbasan_perlu_ocr", "Halaman imbasan asal PDF."),
            ("Lampiran F", "Jadual Kadar Kompaun Peraturan-Peraturan Makanan 1985 mengikut Kategori Premis I–IV (SOP-PKKM-PD-09)", "20-25", "imej_imbasan_perlu_ocr", "Jadual melintang 90° imbasan asal PDF — rujuk Peraturan-Peraturan Makanan (Pengkompaunan Kesalahan) 2017."),
            ("Lampiran G", "Jadual Kadar Kompaun PPKM 2009 mengikut Kategori Premis I–IV (SOP-PKKM-PD-04)", "26-27", "imej_imbasan_perlu_ocr", "Jadual melintang 90° imbasan asal PDF — rujuk Jadual Keempat PPKM 2009."),
            ("Lampiran H", "Buku Daftar Pengeluaran Notis Seksyen 32B & Kompaun", "28", "teks_penuh", None),
            ("Lampiran I", "Buku Daftar Kawalan Buku Notis Seksyen 32B", "29", "teks_penuh", None),
            ("Lampiran J", "Laporan Bulanan Kutipan Kompaun Akta Makanan 1983", "30", "teks_penuh", None),
            ("Lampiran K", "Surat Peringatan / Tuntutan Bayaran Kompaun (Imbasan)", "31-32", "imej_imbasan_perlu_ocr", "Halaman imbasan asal PDF."),
            ("Lampiran L", "Borang Pembatalan Notis Seksyen 32B (Imbasan)", "33", "imej_imbasan_perlu_ocr", "Halaman imbasan asal PDF."),
            ("Lampiran M", "Senarai Semak Pengeluaran Notis & Kompaun Akta Makanan 1983", "34", "teks_penuh", None),
            ("Lampiran N", "Carta / Ringkasan Punca Kuasa Pengkompaunan Akta Makanan 1983", "35", "teks_penuh", None),
        ]
        items = [
            {
                "kod": k,
                "tajuk": t,
                "jenis": _classify_jenis(t),
                "muka_surat_pdf": mp,
                "status": "AKTIF",
                "status_ekstrak": st,
                "nota": nt,
            }
            for k, t, mp, st, nt in curated_04_24
        ]

    return items


def build_corpus(manifest_path: Path) -> None:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest tidak dijumpai di {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    old_active_index = json.loads((SOP_DATA_DIR / "sop_index_active_router.json").read_text(encoding="utf-8"))
    old_master_raw = json.loads((SOP_DATA_DIR / "sop_index_master.json").read_text(encoding="utf-8"))
    old_master_meta = dict(old_master_raw.get("meta") or {}) if isinstance(old_master_raw, dict) else {}
    old_master_index = list(old_master_raw.get("sops") or []) if isinstance(old_master_raw, dict) else list(old_master_raw)

    old_active_by_stem: Dict[str, dict] = {str(r["file_stem"]).upper(): r for r in old_active_index}
    old_master_by_stem: Dict[str, dict] = {
        str(r.get("file_stem") or "").upper(): r
        for r in old_master_index
        if isinstance(r, dict) and str(r.get("file_stem") or "").strip()
    }
    archived_deprecated_entries = [
        r for r in old_master_index
        if isinstance(r, dict) and ("PPKHT" in str(r.get("sop_id") or "").upper() or r.get("status") == "DEPRECATED_BY_AKTA_852")
    ]

    sops_aktif_dir = SOP_DATA_DIR / "sops_aktif"
    sops_struct_dir = SOP_DATA_DIR / "sops_structured"
    sops_aktif_dir.mkdir(parents=True, exist_ok=True)
    sops_struct_dir.mkdir(parents=True, exist_ok=True)

    # First pass: collect all 33 canonical active stems
    known_stems: set[str] = {
        str(cfg["file_stem"]).upper() for cfg in GDRIVE_CATALOG.values()
    }
    assert len(known_stems) == 33, f"Expected 33 active SOP stems, got {len(known_stems)}"
    assert all("PPKHT" not in s for s in known_stems), "HARD PROHIBITION: PPKHT stem detected!"

    new_active_router: List[dict] = []
    new_master_active: List[dict] = []
    bundle_parts: List[str] = []
    structured_by_stem: Dict[str, dict] = {}
    summary_title_by_stem: Dict[str, Tuple[str, str]] = {}

    for entry in sorted(manifest, key=lambda x: int(x["index"])):
        idx = int(entry["index"])
        if idx == 9:
            # Pekeliling KPK Bil 18/2024 handled separately
            continue

        cfg = GDRIVE_CATALOG[idx]
        file_stem = str(cfg["file_stem"])
        stem_up = file_stem.upper()
        pdf_path = Path(entry["local_pdf_path"])
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF hilang bagi indeks #{idx}: {pdf_path}")

        old_act = old_active_by_stem.get(stem_up, {})
        old_mst = old_master_by_stem.get(stem_up, {})

        sop_id = str(cfg.get("sop_id") or old_act.get("sop_id") or file_stem)
        tajuk = str(cfg.get("tajuk") or old_act.get("tajuk") or file_stem)
        kategori = str(cfg.get("kategori") or old_act.get("kategori") or "UMUM")
        akta_berkaitan = list(cfg.get("akta_berkaitan") or old_act.get("akta_berkaitan") or ["Akta Kesihatan Awam KKM"])
        seksyen_kunci = list(cfg.get("seksyen_kunci") or old_act.get("seksyen_kunci") or [])
        kata_kunci = list(cfg.get("kata_kunci") or old_act.get("kata_kunci") or [])
        toc_id_alias = old_act.get("toc_id_alias")
        alias_kod = list(cfg.get("alias_kod") or ([] if not toc_id_alias else [str(toc_id_alias)]))
        keluaran = str(cfg.get("keluaran") or "01")
        pindaan = str(cfg.get("pindaan") or ("01" if "PINDAAN 2024" in sop_id.upper() else "00"))
        tarikh_kuatkuasa = str(cfg.get("tarikh_kuatkuasa") or "15 Feb 2024")
        tarikh_iso = str(cfg.get("tarikh_iso") or "2024-02-15")

        pages = extract_pdf_pages(pdf_path, strip_trailing_blank=(file_stem == "UIP-UMUM-03-24"))
        page_range = f"1-{len(pages)}"
        if old_mst.get("muka_surat_pdf"):
            page_range = str(old_mst["muka_surat_pdf"])

        # Build clean Markdown body with [Muka Surat PDF: X] markers + inline [NOTA PINDAAN]
        md_page_blocks: List[str] = []
        for pno, ptxt, imgs in pages:
            body_p = ptxt
            if file_stem == "UIP-UMUM-01-16":
                body_p = re.sub(
                    r"(UIP-PPKHT-01-16[^\n]*)",
                    r"\1 [NOTA PINDAAN: MANSUH — DIGANTIKAN OLEH UIP-AKPMDKA-01-24 / AKTA 852]",
                    body_p,
                    flags=re.I,
                )
            elif file_stem == "UIP-UMUM-02-07":
                body_p = re.sub(
                    r"(PPKHT\s*2004)",
                    r"\1 [NOTA PINDAAN: MANSUH — DIGANTIKAN OLEH AKTA 852 & UIP-AKPMDKA-01-24/05-24]",
                    body_p,
                    flags=re.I,
                )
            elif file_stem == "UIP-UMUM-05-24":
                body_p = re.sub(
                    r"(PPKHT\s*2004\s+dan\s+Akta\s+852)",
                    r"\1 [NOTA PINDAAN: PPKHT 2004 MANSUH — GUNA AKTA 852 & UIP-AKPMDKA-06-24/08-24]",
                    body_p,
                    flags=re.I,
                )
            elif file_stem == "UIP-AKPMDKA-02-24":
                body_p = re.sub(
                    r"UIP-UMUM-05-16",
                    "UIP-UMUM-05-07 [NOTA AUDIT: diperbetulkan daripada ralat cetak PDF UIP-UMUM-05-16]",
                    body_p,
                    flags=re.I,
                )
            if len(strip_running_headers_and_footers(body_p)) < 85 and imgs > 0:
                body_p = f"{body_p}\n\n_[Halaman imbasan imej asal PDF — sila rujuk salinan PDF rasmi KKM bagi borang/jadual pada halaman ini.]_".strip()
            md_page_blocks.append(f"### [Muka Surat PDF: {pno}]\n\n{body_p}")

        full_body_md = "\n\n---\n\n".join(md_page_blocks)

        # Structured extraction
        tujuan = parse_tujuan(full_body_md, tajuk)
        anggota = parse_anggota(full_body_md)
        singkatan = parse_singkatan(full_body_md)
        undang_undang = parse_undang_undang(full_body_md, akta_berkaitan, file_stem)
        tempoh_sla = extract_sla_timelines(full_body_md, file_stem)
        nota_pindaan = build_nota_pindaan(file_stem, list(old_mst.get("nota_audit") or []))
        proses_rows = extract_proses_kerja_rows(pdf_path, file_stem)
        fasa_kerja, carta_alir, senarai_semak = build_fasa_kerja_and_flowchart(proses_rows, file_stem, known_stems)
        lampiran_list = parse_lampiran(full_body_md, file_stem, old_mst.get("lampiran"), pages)

        # Pematuhan
        pematuhan_blk = extract_section_block(
            full_body_md,
            r"(?:^|\n)\s*(?:\d+\.?\s*)?PEMATUHAN\s+PROSEDUR\b[^\n]*\n",
            [r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:TARIKH\s+KUAT\s*KUASA|SENARAI\s+RUJUKAN|SENARAI\s+LAMPIRAN)\b"],
            max_chars=1200,
        )
        pematuhan = [
            re.sub(r"^[\-\•\d\.\)\s]+", "", ln.strip())
            for ln in pematuhan_blk.splitlines()
            if len(ln.strip()) >= 12 and not ln.strip().startswith("###")
        ][:8]
        if not pematuhan:
            pematuhan = [
                "Peraturan-Peraturan Pegawai Awam (Kelakuan dan Tatatertib) 1993",
                "Pemakaian Kad Perakuan Kuasa KKM dan pematuhan rantaian keterangan mahkamah.",
            ]

        # Panduan Am
        panduan_blk = extract_section_block(
            full_body_md,
            r"(?:^|\n)\s*(?:\d+\.?\s*)?PANDUAN\s+AM\b[^\n]*\n",
            [r"(?:^|\n)\s*(?:\d+\.?\s*)?(?:UNDANG-UNDANG|ANGG+OTA|SINGKATAN|PROSES\s+KERJA)\b"],
            max_chars=1800,
        )
        panduan_am = [
            re.sub(r"^[\-\•\d\.\)\s]+", "", ln.strip())
            for ln in panduan_blk.splitlines()
            if len(ln.strip()) >= 14 and not ln.strip().startswith("###")
        ][:10]

        # Cross-SOP references
        raw_cross = list(old_act.get("rujukan_silang") or [])
        for ph in fasa_kerja:
            for st in ph["langkah"]:
                for sr in st["rujukan_sop"]:
                    if sr not in raw_cross:
                        raw_cross.append(sr)
        for m_cr in re.finditer(r"\b(UIP-[A-Z]+-\d{2}-\d{2})\b", full_body_md, re.I):
            c_up = m_cr.group(1).upper()
            if "PPKHT" not in c_up and c_up != stem_up and c_up in known_stems:
                if not any(c_up in rc.upper() for rc in raw_cross):
                    raw_cross.append(c_up)

        rujukan_silang_clean: List[str] = []
        for rc in raw_cross:
            if "PPKHT" in str(rc).upper():
                continue
            head = str(rc).split(" ")[0].strip().upper()
            if head == "UIP-UMUM-05-16":
                head = "UIP-UMUM-05-07"
            if head == "UIP-APSPP-03-07":
                head = "UIP-UMUM-01-24"
            if head in known_stems and head != stem_up and head not in rujukan_silang_clean:
                rujukan_silang_clean.append(head)

        akta_utama = str(
            cfg.get("akta_utama")
            or (
                "Akta 852"
                if kategori == "AKTA_852"
                else "Akta 154"
                if "APSPP" in kategori
                else "Akta 342"
                if "APPPB" in kategori
                else "Akta 281"
                if file_stem in AKTA_281_FOOD_STEMS
                else "SOP Umum / KTJ"
            )
        )

        nota_audit_kualiti = list(cfg.get("nota_audit_kualiti") or [])
        if old_mst.get("nota_audit"):
            for na in old_mst["nota_audit"]:
                na_s = str(na).strip()
                # Fix factual error in sop_index_master.json:498 for UIP-UMUM-01-24
                if file_stem == "UIP-UMUM-01-24" and "peruntukan halangan tugas khusus dalam Akta 852" in na_s:
                    na_s = (
                        "Akta 852 TIDAK mempunyai seksyen halangan tugas tersendiri — halangan tugas semasa "
                        "penguatkuasaan Akta 852 wajib dirujuk kepada PDRM di bawah Seksyen 186 Kanun Keseksaan [Akta 574]."
                    )
                if na_s and na_s not in nota_audit_kualiti:
                    nota_audit_kualiti.append(na_s)

        ringkasan_eksekutif = (
            f"{tujuan[:260]}"
            if tujuan
            else f"Prosedur operasi standard rasmi KKM ({sop_id}) bagi {tajuk}."
        )

        struct_doc = {
            "schema_version": "2.0",
            "sop_id": sop_id,
            "file_stem": file_stem,
            "alias_kod": alias_kod,
            "tajuk": tajuk,
            "kategori": kategori,
            "akta_utama": akta_utama,
            "akta_berkaitan": akta_berkaitan,
            "keluaran": keluaran,
            "pindaan": pindaan,
            "tarikh_kuatkuasa": tarikh_kuatkuasa,
            "ringkasan_eksekutif": ringkasan_eksekutif,
            "tujuan": tujuan,
            "panduan_am": panduan_am,
            "punca_kuasa": seksyen_kunci[:6] or [f"{akta_utama} — Rujuk peruntukan statutori berkaitan"],
            "undang_undang_berkaitan": undang_undang,
            "anggota_terlibat": anggota,
            "singkatan": singkatan,
            "nota_pindaan": nota_pindaan,
            "tempoh_sla": tempoh_sla,
            "fasa_kerja": fasa_kerja,
            "carta_alir": carta_alir,
            "senarai_semak": senarai_semak,
            "lampiran": lampiran_list,
            "pematuhan": pematuhan,
            "rujukan_silang_resolved": [],  # Filled in second pass
            "nota_audit_kualiti": nota_audit_kualiti,
            "_raw_cross_stems": rujukan_silang_clean,
        }
        structured_by_stem[stem_up] = struct_doc
        summary_title_by_stem[stem_up] = (sop_id, tajuk)

        # Build clean active Markdown file (`sops_aktif/{file_stem}.md`)
        fm_lines = [
            "---",
            f'sop_id: "{sop_id}"',
            f'tajuk: "{tajuk.replace(chr(34), chr(39))}"',
            f'kategori: "{kategori}"',
            'status: "AKTIF"',
            f'tarikh_kuatkuasa: "{tarikh_iso}"',
            f'muka_surat_pdf: "{page_range}"',
            f"akta_berkaitan: {json.dumps(akta_berkaitan, ensure_ascii=False)}",
            f"seksyen_kunci: {json.dumps(seksyen_kunci, ensure_ascii=False)}",
            f"rujukan_silang: {json.dumps(rujukan_silang_clean, ensure_ascii=False)}",
        ]
        if toc_id_alias:
            fm_lines.append(f'toc_id_alias: "{toc_id_alias}"')
        fm_lines.append("---")

        md_sections = ["\n".join(fm_lines), f"# {sop_id} — {tajuk}"]
        if nota_pindaan:
            np_lines = ["## Nota Pindaan & Hierarki Statut > SOP"]
            for np_item in nota_pindaan:
                np_lines.append(f"- **[{np_item['tahap']}] {np_item['tajuk']}:** {np_item['butiran']}")
            md_sections.append("\n".join(np_lines))
        if nota_audit_kualiti:
            na_lines = ["## Nota Audit Sistem i-UIP Nerus"]
            for na in nota_audit_kualiti:
                na_lines.append(f"- {na}")
            md_sections.append("\n".join(na_lines))
        if lampiran_list:
            lp_lines = ["## Indeks Lampiran Disahkan"]
            for lp in lampiran_list:
                tag = " [MANSUH — PPKHT 2004]" if lp["status"] == "DEPRECATED_PPKHT_2004" else ""
                lp_lines.append(f"- **{lp['kod']}:** {lp['tajuk']}{tag}")
            md_sections.append("\n".join(lp_lines))
        md_sections.append(f"## Kandungan Penuh SOP\n\n{full_body_md}")

        final_md = "\n\n".join(md_sections) + "\n"
        (sops_aktif_dir / f"{file_stem}.md").write_text(final_md, encoding="utf-8")

        bundle_parts.append(
            f'<SOP id="{sop_id}" file_stem="{file_stem}" kategori="{kategori}" tarikh_kuatkuasa="{tarikh_kuatkuasa}">\n'
            f"{final_md}\n</SOP>"
        )

        # Router index entry (strictly active, 0 PPKHT)
        router_rec = {
            "sop_id": sop_id,
            "file_stem": file_stem,
            "fail_md": f"data/sops_aktif/{file_stem}.md",
            "fail_json": f"data/sops_structured/{file_stem}.json",
            "toc_id_alias": toc_id_alias,
            "kategori": kategori,
            "akta_utama": akta_utama,
            "keluaran": keluaran,
            "pindaan": pindaan,
            "tarikh_kuatkuasa": tarikh_kuatkuasa,
            "tajuk": tajuk,
            "akta_berkaitan": akta_berkaitan,
            "seksyen_kunci": seksyen_kunci,
            "kata_kunci": kata_kunci,
            "rujukan_silang": rujukan_silang_clean,
            "lampiran_ringkas": [f"{lp['kod']}: {lp['tajuk']}" for lp in lampiran_list[:8]],
            "muka_surat_pdf": page_range,
        }
        new_active_router.append(router_rec)

        master_rec = {
            **router_rec,
            "status": "AKTIF",
            "nota_audit": nota_audit_kualiti,
            "lampiran": {lp["kod"]: lp["tajuk"] for lp in lampiran_list},
            "sumber_gdrive_id": entry["file_id"],
            "sumber_sha256": entry["sha256"],
        }
        new_master_active.append(master_rec)

    # Second pass: resolve cross-SOP references cleanly and write structured v2 JSONs
    for stem_up, sdoc in structured_by_stem.items():
        cross_stems = sdoc.pop("_raw_cross_stems", [])
        resolved: List[Dict[str, str]] = []
        for cs in cross_stems:
            if cs in summary_title_by_stem:
                c_sid, c_tajuk = summary_title_by_stem[cs]
                resolved.append({"sop_id": c_sid, "file_stem": cs, "tajuk": c_tajuk})
        sdoc["rujukan_silang_resolved"] = resolved
        (sops_struct_dir / f"{sdoc['file_stem']}.json").write_text(
            json.dumps(sdoc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Sort active router neatly: Akta 852 -> UMUM -> APSPP -> APPPB
    cat_order = {"AKTA_852": 0, "AKTA_281": 1, "UMUM": 2, "APSPP_1975": 3, "APPPB_1988": 4}
    new_active_router.sort(key=lambda r: (cat_order.get(r["kategori"], 9), r["file_stem"]))
    new_master_active.sort(key=lambda r: (cat_order.get(r["kategori"], 9), r["file_stem"]))

    # Write indexes & bundle
    (SOP_DATA_DIR / "sop_index_active_router.json").write_text(
        json.dumps(new_active_router, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    old_master_meta.update({
        "total_sops": len(new_master_active) + len(archived_deprecated_entries),
        "active_sops": len(new_master_active),
        "deprecated_sops": len(archived_deprecated_entries),
        "version": "SOP-KKM-2024-v2-33-AKTIF",
    })
    (SOP_DATA_DIR / "sop_index_master.json").write_text(
        json.dumps({"meta": old_master_meta, "sops": new_master_active + archived_deprecated_entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (SOP_DATA_DIR / "sop_bundle_aktif_context_cache.txt").write_text(
        "=== KOLEKSI 33 SOP PENGUATKUASAAN KKM AKTIF (PINDAAN 2024 + AKTA 852 + UMUM 2024) ===\n"
        "AMARAN KERAS: 5 SOP PPKHT 2004 DIMANSUHKAN DAN DIKUARANTIN — SIFAR SOP PPKHT DALAM BUNDLE INI.\n\n"
        + "\n\n".join(bundle_parts)
        + "\n",
        encoding="utf-8",
    )

    # Write Pekeliling KPK Bil 18/2024 (#09) supplementary reference with explicit incomplete-scan disclaimer
    pekeliling_entry = [
        {
            "kod": "Pekeliling KPK Bil 18/2024",
            "no_rujukan": "KKM.100-1/3/10 (40)",
            "tarikh": "18 Okt 2024",
            "tajuk": "Garis Panduan Penguatkuasaan dan Pengkompaunan Di Bawah Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
            "status_imbasan": "IMBASAN_TIDAK_LENGKAP_HALAMAN_GANJIL_SAHAJA",
            "amaran_ketidaklengkapan": (
                "Fail PDF sumber (#09) hanya mengandungi halaman ganjil (imbasan dupleks tidak lengkap — 17 halaman imej, "
                "halaman genap termasuk §7.1–7.2.1 jadual kadar kompaun/pengurangan pertama tiada). "
                "JANGAN jadikan fail imbasan tidak lengkap ini sebagai jadual kadar muktamad; sentiasa rujuk "
                "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Pengkompaunan Kesalahan) 2024 [P.U.(A) 259/2024] "
                "dan data/akta/AKTA_852_PERATURAN_KOMPAUN_2024.pdf."
            ),
            "fakta_disahkan": [
                "Menguatkuasakan 8 SOP rasmi Akta 852 (UIP-AKPMDKA-01-24 hingga UIP-AKPMDKA-08-24) bermula 1 Oktober 2024.",
                "Menegaskan 4 kesalahan boleh kompaun di bawah Akta 852: Seksyen 13(3), Seksyen 16(2), Seksyen 17(1) dan Seksyen 18(1).",
                "Kesalahan selain daripada 4 seksyen tersebut (cth. S.3, S.7, S.9, S.10, S.13(1)) TIDAK BOLEH DIKOMPAUN dan wajib Buka IP Terus (UIP-AKPMDKA-05-24).",
            ],
            "rujukan_statut_muktamad": "data/akta/AKTA_852_PERATURAN_KOMPAUN_2024.pdf",
            "sumber_gdrive_id": "1QHlSnPq6TM2kI1qixRr2WFuNk6Sq6bOr",
        }
    ]
    (SOP_DATA_DIR / "pekeliling_rujukan.json").write_text(
        json.dumps(pekeliling_entry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"SUCCESS: Built {len(new_active_router)} active SOPs (sops_aktif + sops_structured + router + master + bundle) + 1 pekeliling warning.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build 33 active KKM 2024 SOPs & structured v2 JSONs.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    build_corpus(args.manifest)
