"""Modul Tanya Pakar UIP (Penasihat Kes, Seksyen Pertuduhan & SOP Lapangan KKM).

Membantu PPKP / IO / Pegawai Pendakwa menjawab soalan sebenar di lapangan:
- Kesalahan ini nak caj seksyen apa (Kesalahan & Hukuman tepat)?
- Boleh kompaun dahulu, perintah tutup premis, atau wajib buka IP terus?
- Apa prosedur lapangan langkah demi langkah & apa dokumen/eksibit wajib?
- Apa perangkap kesilapan biasa yang sering kena kuiri TPR?
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.model_router import UIPModelRouter

logger = logging.getLogger("uip.advisor")

UIP_SCENARIO_LIBRARY: List[Dict[str, Any]] = [
    {
        "id": "ak852_pamer_vape",
        "akta_utama": "Akta 852",
        "tajuk": "Kedai Serbaneka Pamer Rokok / Vape Secara Terbuka di Kaunter",
        "keywords": [
            "pamer rokok", "pamer vape", "pameran rokok", "pameran vape", "pamer terbuka", "pamer secara terbuka",
            "vape di kaunter", "rokok di kaunter", "kabinet rokok", "serbaneka", "kedai runcit",
            "pamer", "pameran", "pod", "rokok elektronik", "260/2024",
        ],
        "negative_keywords": ["hisap rokok", "merokok tepi jalan", "iklan papan"],
        "keputusan_tindakan": "SITA BARANG PAMERAN (S.35/S.36) & BUKA IP TERUS (S.10(1) TIDAK BOLEH KOMPAUN di bawah P.U.(A) 259/2024)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Pameran terbuka vape atau rokok di kaunter jualan melanggar Seksyen 10(1) Akta 852 dibaca bersama Peraturan 6 P.U. (A) 260/2024. "
            "Kesalahan Seksyen 10(1) tidak tersenarai sebagai kesalahan boleh kompaun di bawah Jadual Pertama P.U. (A) 259/2024; "
            "barang pameran wajib disita di bawah Seksyen 35 & 36 Akta 852 dan dibuka Kertas Siasatan (IP) untuk pendakwaan mahkamah."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Pameran produk merokok / vape secara terbuka di tempat jualan",
                "seksyen_kesalahan": "Seksyen 10(1) Akta 852 dibaca bersama Peraturan 6 P.U. (A) 260/2024 (jika syarikat baca bersama S.49)",
                "seksyen_hukuman": "Seksyen 10(2)(a) [Bukan Pertubuhan Perbadanan] atau Seksyen 10(2)(b) [Pertubuhan Perbadanan] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara maks 1 tahun | Syarikat: Denda RM20,000 – RM100,000 / penjara 2 tahun",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN (Seksyen 10(1) tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Sita (S.35/S.36) & Buka IP Terus.",
            }
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa Rasmi KKM (Seksyen 24(2) Akta 852) kepada pemilik atau penjaga premis.",
            "Ambil gambar sudut jauh dan dekat menunjukkan pod/rokok dipamer secara terbuka sebelum disentuh.",
            "Jalankan pemeriksaan (Seksyen 26/30) dan sita semua unit yang dipamerkan secara salah di bawah Seksyen 35 Akta 852.",
            "Isi Borang Senarai Benda Disita di bawah Seksyen 36 Akta 852 di tempat kejadian, dapatkan tandatangan terima pemilik dan serahkan satu salinan.",
            "Lak barang kes dengan nombor siri lak KKM, lukis Pelan Lakar premis dan rekod masuk ke Stor Barang Kes PKD.",
        ],
        "eksibit_wajib": [
            "Produk vape/rokok yang disita & dilak (P1–Pn)",
            "Borang Senarai Benda Disita Seksyen 36 Akta 852 bertandatangan terima",
            "Gambar foto berwarna bertarikh + Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Cetakan Carian Rasmi SSM (e-Info/MyData) + Sijil S.90A & Lesen PBT",
            "Pelan Lakar kedudukan rak/kaunter pameran bertandatangan IO",
        ],
        "perangkap_kesilapan": [
            "JANGAN tulis 'Borang Sitaan Seksyen 38' — Seksyen 38 ialah kos memegang barang; senarai sitaan ialah Seksyen 36 Akta 852!",
            "Jangan hanya tuduh pekerja kaunter warga asing tanpa menyemak pemilik syarikat/pengarah dalam SSM (Seksyen 49 Akta 852).",
            "Jangan lupa Sijil Seksyen 90A(2) untuk gambar digital & cetakan SSM.",
        ],
        "templat_ringkas": (
            "Kesalahan: Mempamerkan secara terbuka produk merokok / rokok elektronik (vape) di kaunter bayaran yang boleh dilihat pelanggan "
            "yang melanggar Seksyen 10(1) Akta 852 dibaca bersama Peraturan 6 P.U. (A) 260/2024. "
            "Penyitaan dibuat di bawah Seksyen 35 dan Borang Senarai Benda Disita Seksyen 36 Akta 852 telah diserahkan."
        ),
    },
    {
        "id": "ak852_obd_merokok_tepi_jalan",
        "akta_utama": "Akta 852",
        "tajuk": "Pelajar / Bawah 18 Tahun (OBD) Merokok atau Hisap Vape (Sekolah / Tandas / Tempat Awam)",
        "keywords": [
            "budak sekolah", "pelajar sekolah", "pelajar merokok", "pelajar hisap", "pelajar sedang hisap",
            "pelajar menghisap", "tangkap pelajar", "tandas sekolah", "kawasan sekolah", "tepi jalan",
            "hisap rokok", "hisap vape", "menghisap rokok", "menghisap vape", "hisap vape dalam",
            "seragam sekolah", "pondok bas", "seksyen 17", "17(1)",
            "obd merokok", "remaja merokok", "bawah umur hisap",
        ],
        "negative_keywords": ["jual kepada", "menjual rokok", "kedai jual", "tanda larangan"],
        "incompatible_with": ["ak852_larangan_merokok"],
        "keputusan_tindakan": "Keluarkan Notis S.47 & tawarkan kompaun S.48(2) di bawah Seksyen 17(1) Akta 852 (patuhi perlindungan Akta 611 & maklumkan ibu bapa/penjaga); siasat kedai penjual di bawah S.13(1).",
        "ringkasan_keputusan": "Keluarkan Notis S.47 & tawarkan kompaun S.48(2) (dengan keizinan bertulis Pendakwa Raya) bagi kesalahan Seksyen 17(1) Akta 852 serta maklumkan ibu bapa/penjaga (Akta 611), dan siasat kedai penjual di bawah Seksyen 13(1).",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Pelajar atau individu bawah 18 tahun (OBD) yang ditangkap sedang menghisap vape atau rokok (termasuk di tandas sekolah, kawasan sekolah atau tempat awam) "
            "melakukan kesalahan di bawah Seksyen 17(1) Akta 852. Kesalahan ini boleh dikompaun di bawah Seksyen 48(2) [Borang 1 & Borang 2 P.U. (A) 259/2024] berserta Notis Hadir Mahkamah S.47 "
            "dengan pemakluman wajib kepada ibu bapa/penjaga serta pematuhan perlindungan kanak-kanak di bawah Akta Kanak-Kanak 2001 [Akta 611]. "
            "Buka IP terhadap OBD hanya jika gagal jelas kompaun dalam 30 hari, tetapi wajib siasat kedai/penjual di bawah Seksyen 13(1) Akta 852."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Bawah 18 Tahun (OBD) merokok, mengunyah atau menggunakan produk tembakau / vape",
                "seksyen_kesalahan": "Seksyen 17(1) Akta 852",
                "seksyen_hukuman": "Seksyen 17(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM500 atau Perintah Khidmat Masyarakat (Akta 852)",
                "boleh_kompaun": "Boleh kompaun RM50 di bawah Seksyen 48(2) [P.U. (A) 259/2024] dengan keizinan bertulis Pendakwa Raya (tempoh 30 hari; maklumkan ibu bapa/penjaga).",
            },
            {
                "perihal": "Penjual / Pekedai (Jika dikenal pasti menjual rokok/vape kepada pelajar tersebut)",
                "seksyen_kesalahan": "Seksyen 13(1) Akta 852",
                "seksyen_hukuman": "Seksyen 13(2)(a) [Individu] / Seksyen 13(2)(b) [Syarikat] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara 1 tahun | Syarikat: RM20,000 – RM100,000",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN — Terus Buka IP terhadap penjual jika transaksi jualan kepada OBD dibuktikan.",
            },
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa Rasmi KKM (Seksyen 24(2) & Seksyen 25 Akta 852) kepada pihak pentadbiran sekolah / guru saksi dan pelajar secara berhemah.",
            "Sahkan identiti serta umur pelajar (bawah 18 tahun pada tarikh kejadian) melalui MyKad atau Kad Pelajar, dan rekodkan butiran penuh ibu bapa/penjaga.",
            "Rakam bukti kejadian dengan segera: ambil keterangan awal guru/saksi yang menangkap pelajar sedang menghisap vape (rakaman S.112 KTJ jika ke mahkamah), gambar lokasi/peranti vape (+ Sijil S.90A(2)), dan rantaian serahan peranti daripada guru kepada PPKP.",
            "Keluarkan Notis Hadir Mahkamah Seksyen 47 dan tawaran kompaun Seksyen 48(2) [Borang 1 & 2 P.U.(A) 259/2024] (tempoh 30 hari), maklumkan kepada ibu bapa/penjaga, dan patuhi perlindungan identiti/privasi kanak-kanak di bawah Akta Kanak-Kanak 2001 [Akta 611] (Seksyen 15 & Seksyen 83).",
            "Dapatkan maklumat kedai/pembekal vape daripada pelajar secara berhemah untuk tindakan pemeriksaan dan siasatan susulan terhadap penjual di bawah Seksyen 13(1) Akta 852.",
        ],
        "eksibit_wajib": [
            "Salinan MyKad / Kad Pelajar / Pengesahan JPN (membuktikan umur di bawah 18 tahun pada tarikh kejadian)",
            "Keterangan saksi mata guru/pengawas yang melihat pelajar sedang menghisap vape (S.112 KTJ jika buka IP) + laporan disiplin sekolah",
            "Salinan pendua Tawaran Kompaun / Notis Seksyen 47 bertandatangan terima / saksi + rekod pemakluman ibu bapa/penjaga",
            "Peranti vape / pod yang dirampas beserta rekod rantaian serahan daripada guru kepada PPKP (Borang S.36 jika disita)",
            "Gambar foto peranti vape & lokasi kejadian (tandas/kawasan sekolah) + Sijil Seksyen 90A(2) Akta Keterangan 1950",
        ],
        "perangkap_kesilapan": [
            "PEMILIKAN SEMATA-MATA BUKAN KESALAHAN S.17(1): Kesalahan S.17(1) hanya sah jika ada bukti jelas pelajar sedang menghisap, mengunyah atau menggunakan — bukan sekadar jumpa dalam beg!",
            "PERLINDUNGAN KANAK-KANAK (AKTA 611): JANGAN siarkan gambar/nama pelajar di media sosial atau soal siasat secara kasar tanpa kehadiran guru/penjaga — patuhi Seksyen 15 (sekatan penyiaran identiti) & Seksyen 83 Akta Kanak-Kanak 2001 [Akta 611].",
            "RANTAIAN SERAHAN BARANG KES: Jika guru yang merampas vape terlebih dahulu di tandas sekolah, rekodkan tarikh/masa dan tandatangan serahan daripada guru kepada PPKP supaya rantaian barang kes tidak terputus.",
            "Pastikan salinan bukti tarikh lahir (MyKad/JPN) dilampirkan untuk membuktikan status bawah 18 tahun (OBD).",
        ],
        "templat_ringkas": (
            "Kesalahan: Orang Belum Dewasa (< 18 tahun) didapati sedang menghisap produk pengganti tembakau / rokok elektronik (vape) "
            "yang melanggar Seksyen 17(1) Akta 852 dan boleh dihukum di bawah Seksyen 17(2) Akta 852. "
            "Notis Seksyen 47, pemakluman kepada ibu bapa/penjaga dan pematuhan tatacara Akta Kanak-Kanak 2001 [Akta 611] telah dilaksanakan."
        ),
    },
    {
        "id": "ak852_jual_obd",
        "akta_utama": "Akta 852",
        "tajuk": "Pekedai Menjual Rokok / Vape kepada Orang Belum Dewasa (OBD < 18 Tahun)",
        "keywords": [
            "jual rokok", "jual vape", "menjual rokok", "menjual vape", "penjual rokok", "pekedai jual",
            "kaunter jual", "resit belian", "18 tahun", "jual kepada obd", "membeli rokok",
            "seksyen 13 akta 852", "bawah umur",
        ],
        "negative_keywords": ["makanan tercemar", "keracunan", "najis tikus", "pamer secara terbuka"],
        "keputusan_tindakan": "PENJUAL: BUKA IP TERUS (S.13(1) Tidak Boleh Kompaun) | OBD MEMBELI/MEROKOK: KOMPAUN S.48(2) / KHIDMAT MASYARAKAT",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Menjual produk merokok kepada kanak-kanak/remaja di bawah 18 tahun tidak tersenarai untuk kompaun di bawah Jadual Pertama P.U. (A) 259/2024 "
            "dengan penalti berat sehingga RM100,000 bagi syarikat. Penjual wajib dibuka IP dan disita bukti transaksi, "
            "manakala OBD yang membeli (S.13(3)) atau merokok (S.17(1)) boleh ditawarkan kompaun S.48(2) dengan pemakluman penjaga."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Penjual: Menjual produk merokok / rokok elektronik kepada Orang Belum Dewasa (< 18 tahun)",
                "seksyen_kesalahan": "Seksyen 13(1) Akta 852 (dibaca bersama Seksyen 49 jika syarikat)",
                "seksyen_hukuman": "Seksyen 13(2)(a) [Individu] / Seksyen 13(2)(b) [Syarikat] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara maks 1 tahun | Syarikat: Denda RM20,000 – RM100,000",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN — Wajib Buka IP terus untuk pendakwaan.",
            },
            {
                "perihal": "OBD: Membeli / Merokok / Menggunakan produk merokok di bawah umur 18 tahun",
                "seksyen_kesalahan": "Seksyen 13(3) [Membeli] atau Seksyen 17(1) [Merokok/Mengunyah/Menggunakan] Akta 852",
                "seksyen_hukuman": "Seksyen 13(4) / Seksyen 17(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM500 atau Perintah Khidmat Masyarakat",
                "boleh_kompaun": "Boleh dikompaun di bawah Seksyen 48(2) P.U. (A) 259/2024 (keizinan bertulis Pendakwa Raya & maklumkan ibu bapa/penjaga).",
            },
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa KKM sebaik sahaja transaksi jualan kepada OBD atau perbuatan OBD menghisap vape/rokok disaksikan.",
            "Semak MyKad atau Sijil Lahir OBD untuk sahkan umur di bawah 18 tahun pada tarikh kejadian.",
            "Sita produk yang dibeli/dihisap berserta resit bayaran menggunakan Borang Senarai Benda Disita Seksyen 36 Akta 852.",
            "Rakam percakapan Seksyen 112 KTJ OBD (dengan kehadiran ibu bapa/penjaga jika perlu) sebagai saksi utama jualan oleh pekedai.",
        ],
        "eksibit_wajib": [
            "Salinan MyKad / Pengesahan JPN OBD (membuktikan umur di bawah 18 tahun pada tarikh kejadian)",
            "Produk rokok/vape yang dibeli & resit pembelian berlak KKM + Borang S.36",
            "Rakaman percakapan S.112 OBD dan PPKP saksi kejadian",
            "Gambar premis / kaunter jualan + Sijil Seksyen 90A(2)",
        ],
        "perangkap_kesilapan": [
            "Gagal melampirkan bukti sah tarikh lahir (salinan MyKad/JPN OBD) di mahkamah.",
            "Mengambil keterangan OBD tanpa kehadiran penjaga atau tanpa nota amaran S.112(2)&(3) KTJ.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menjual produk merokok kepada seorang Orang Belum Dewasa berumur di bawah 18 tahun "
            "yang melanggar Seksyen 13(1) Akta 852 dan boleh dihukum di bawah Seksyen 13(2)(a)/(b) Akta 852. "
            "Barang kes telah disita di bawah Seksyen 35/36 Akta 852 dan salinan MyKad OBD dilampirkan."
        ),
    },
    {
        "id": "ak852_larangan_merokok",
        "akta_utama": "Akta 852",
        "tajuk": "Merokok / Vape di Tempat Larangan (Restoran) & Pemilik Sedia Bekas Abu Rokok",
        "keywords": [
            "kawasan larangan merokok", "tempat makan", "rokok dalam restoran",
            "merokok di restoran", "hisap rokok di restoran", "hisap vape di restoran",
            "seksyen 16", "257/2024",
        ],
        "negative_keywords": ["tepi jalan", "budak sekolah", "najis tikus", "suntikan tifoid", "tiada tanda", "tanda larangan", "papan tanda", "kod qr", "258/2024"],
        "incompatible_with": ["ak852_obd_merokok_tepi_jalan"],
        "keputusan_tindakan": "KOMPAUN DAHULU (Tawaran Kompaun S.48(2) & Notis S.47 — 30 Hari); BUKA IP HANYA JIKA GAGAL BAYAR",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Kesalahan individu merokok di restoran (S.16(2)) serta pemilik premis gagal mempamer tanda larangan QR atau "
            "menyediakan bekas abu rokok (S.18(1)) adalah kesalahan boleh kompaun lazim. PPKP hendaklah mengeluarkan Tawaran Kompaun S.48(2) "
            "(Borang 1 & 2 P.U.(A) 259/2024) berserta Notis Hadir Mahkamah S.47 dengan tempoh bayaran 30 hari; hanya buka IP jika kompaun tidak dijelaskan selepas tamat 30 hari."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Individu merokok / hisap vape di kawasan tempat makan / larangan",
                "seksyen_kesalahan": "Seksyen 16(2) Akta 852 dibaca bersama P.U. (A) 257/2024",
                "seksyen_hukuman": "Seksyen 16(3) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM5,000",
                "boleh_kompaun": "Boleh dikompaun RM250.00 di bawah Seksyen 48(2) [P.U. (A) 259/2024] — tempoh bayaran 30 hari.",
            },
            {
                "perihal": "Pemilik premis gagal pamer tanda amaran Kod QR atau sediakan bekas abu rokok",
                "seksyen_kesalahan": "Seksyen 18(1)(a) [Tiada tanda/P.U.(A) 258/2024] atau Seksyen 18(1)(b) [Bekas abu rokok] Akta 852",
                "seksyen_hukuman": "Seksyen 18(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM5,000",
                "boleh_kompaun": "Boleh dikompaun di bawah Seksyen 48(2) [P.U. (A) 259/2024] — tempoh bayaran 30 hari.",
            },
        ],
        "sop_lapangan": [
            "Ambil gambar perokok sedang memegang/menghembus asap atau wap vape di dalam premis (termasuk jarak 3 meter dari meja makan luar).",
            "Ambil gambar keadaan dinding premis (jika tiada tanda larangan Kod QR) atau gambar bekas abu rokok di atas meja.",
            "Tunjukkan Kad Kuasa, periksa MyKad dan serahkan Tawaran Kompaun / Notis Seksyen 47 (tandatangan terima; jika enggan tandatangan, catat 'Enggan Tandatangan' berserta saksi PPKP).",
            "Jika kompaun tidak dibayar selepas 30 hari (rujuk pengesahan Unit Hasil PKD), barulah buka Fail IP dan sediakan Borang 114.",
        ],
        "eksibit_wajib": [
            "Salinan pendua Tawaran Kompaun / Notis Seksyen 47 bertandatangan terima / catatan saksi enggan tandatangan",
            "Gambar foto bukti (puntung rokok/vape/papan tanda/bekas abu rokok) + Sijil Seksyen 90A(2)",
            "Sijil / Pengesahan Unit Hasil PKD bahawa kompaun tidak dibayar selepas tamat 30 hari (jika dibawa ke mahkamah)",
        ],
        "perangkap_kesilapan": [
            "JANGAN tulis 'melanggar Seksyen 16(1)' — Seksyen 16(1) ialah kuasa Menteri mengisytiharkan tempat larangan; kesalahan perokok ialah Seksyen 16(2)!",
            "Jangan hantar kes ke mahkamah sebelum tempoh kompaun 30 hari Akta 852 tamat sepenuhnya.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menghisap rokok / rokok elektronik di tempat makan yang diisytiharkan sebagai kawasan larangan merokok di bawah P.U. (A) 257/2024 "
            "yang melanggar Seksyen 16(2) Akta 852 dan boleh dihukum di bawah Seksyen 16(3) Akta 852. "
            "Notis Seksyen 47 dan tawaran kompaun Seksyen 48(2) [30 hari] telah diserahkan."
        ),
    },
    {
        "id": "ak852_tanda_larangan_premis",
        "akta_utama": "Akta 852",
        "tajuk": "Pemilik / Penghuni Premis (Restoran / Kafeteria / Kedai) Gagal Pamer Tanda Amaran Larangan Merokok Kod QR atau Sedia Bekas Abu Rokok",
        "keywords": [
            "tiada tanda larangan", "tanda larangan merokok", "tanda amaran", "papan tanda",
            "kod qr", "258/2024", "seksyen 18", "ashtray", "bekas abu",
            "cafetaria", "kafeteria", "peniaga cafe", "tidak pasang tanda", "tak pasang tanda",
        ],
        "negative_keywords": ["pelajar hisap", "budak sekolah", "najis tikus", "suntikan tifoid"],
        "status_kesalahan": "ADA_KESALAHAN",
        "ringkasan_keputusan": (
            "ADA KESALAHAN & BOLEH KOMPAUN di bawah Seksyen 18(1)(a) Akta 852 dibaca bersama Peraturan 2(1) & 2(2) P.U. (A) 258/2024 "
            "— keluarkan Notis S.47 & tawarkan kompaun S.48(2) (RM250–RM2,500, tempoh 30 hari). Alasan tanda sudah dipasang di pintu pagar utama universiti/kompleks TIDAK membebaskan penghuni tempat makan."
        ),
        "keputusan_tindakan": "BOLEH KOMPAUN — KELUARKAN NOTIS S.47 & TAWARAN KOMPAUN S.48(2) AKTA 852 (RM250–RM2,500; 30 HARI) DI BAWAH SEKSYEN 18(1)(a)",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Di bawah Seksyen 18(1)(a) Akta 852 dibaca bersama Peraturan 2(1) & 2(2) P.U. (A) 258/2024, 'Tuan punya atau penghuni' mana-mana kawasan atau tempat "
            "larangan merokok wajib pada setiap masa mempamerkan tanda amaran larangan merokok berspesifikasi Jadual Pertama (min 40 sm x 50 sm di dalam bangunan dengan Kod QR 10 sm x 10 sm, "
            "atau 60 sm x 90 sm di laluan masuk) di bahagian yang mudah dilihat. "
            "Kafeteria / kafe ialah suatu 'tempat makan' tersendiri (Bil. 4 Jadual Pertama & Perenggan 2 P.U. (A) 257/2024), berasingan daripada kategori kawasan institusi pendidikan tinggi (Bil. 12). "
            "Oleh itu, pengusaha/penyewa kafeteria ialah 'penghuni' yang memikul kewajipan statutori tersendiri dan alasan bahawa pihak universiti/kompleks sudah memasang papan tanda di pintu pagar utama TIDAK sah untuk mengecualikan kompaun."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Tuan punya atau penghuni tempat makan / premis larangan merokok gagal mempamerkan tanda amaran larangan merokok mengikut spesifikasi Kod QR",
                "seksyen_kesalahan": "Seksyen 18(1)(a) Akta 852 dibaca bersama Peraturan 2(1) & 2(2), Jadual Pertama & Kedua P.U. (A) 258/2024 serta Bil. 4 Jadual Pertama P.U. (A) 257/2024",
                "seksyen_hukuman": "Seksyen 18(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM5,000",
                "boleh_kompaun": "Boleh dikompaun RM250.00 – RM2,500.00 di bawah Seksyen 48(2) & Jadual Pertama(d) P.U. (A) 259/2024 (tempoh bayaran 30 hari).",
            },
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa KKM (Seksyen 24(2) Akta 852) kepada pengusaha / peniaga / pengurus premis makan secara berhemah.",
            "Sahkan status OKT sebagai 'tuan punya atau penghuni' premis makan tersebut (semak perjanjian sewaan/tender kafeteria, lesen PBT atau Carian SSM) dan sahkan premis memang beroperasi menghidang/menjual makanan (takrif 'tempat makan' Perenggan 2 & Bil. 4 P.U. (A) 257/2024).",
            "Periksa seluruh bahagian dinding mudah dilihat di dalam bangunan dan laluan masuk kafeteria; ambil gambar foto menyeluruh sudut jauh & dekat membuktikan tiada tanda amaran larangan merokok Kod QR (min 40 sm x 50 sm di dalam bangunan, Bil. 1 Jadual Pertama P.U. (A) 258/2024) beserta Sijil Seksyen 90A(2).",
            "Jelaskan kepada peniaga bahawa kewajipan di bawah Seksyen 18(1)(a) & Peraturan 2(1) P.U. (A) 258/2024 terletak terus ke atas 'penghuni' tempat makan tersebut, dan papan tanda universiti/kompleks di pintu masuk utama tidak melepaskan kewajipan di dalam kafeteria.",
            "Serahkan Tawaran Kompaun Borang 2 P.U. (A) 259/2024 (Seksyen 48(2), tempoh bayaran 30 hari) berserta Notis Hadir Mahkamah Seksyen 47; hanya buka Fail IP jika kompaun gagal dibayar selepas tamat 30 hari.",
        ],
        "eksibit_wajib": [
            "Gambar foto sudut jauh & dekat bahagian dalam dan laluan masuk kafeteria/premis membuktikan ketiadaan tanda amaran larangan merokok Kod QR + Sijil Seksyen 90A(2)",
            "Bukti status 'penghuni / tuan punya' premis (salinan perjanjian sewaan/tender kafeteria universiti, Carian SSM atau lesen PBT)",
            "Salinan pendua Tawaran Kompaun Borang 2 P.U. (A) 259/2024 & Notis Seksyen 47 bertandatangan terima / catatan saksi PPKP",
            "Sijil Unit Hasil PKD bahawa kompaun tidak dijelaskan selepas tamat 30 hari (jika kes dibawa ke mahkamah)",
        ],
        "perangkap_kesilapan": [
            "JANGAN salah petik Seksyen 16(2) Akta 852 (kesalahan individu merokok) bagi kes ketiadaan papan tanda — kesalahan tuan punya/penghuni premis ialah Seksyen 18(1)(a) Akta 852!",
            "JANGAN petik 'Peraturan 3 P.U. (A) 258/2024' (tidak wujud — P.U. (A) 258/2024 hanya mempunyai Peraturan 1, Peraturan 2, Jadual Pertama & Jadual Kedua) dan jangan anggap kes ini tidak boleh kompaun.",
            "Pastikan OKT dinamakan betul sebagai 'penghuni' (peniaga/pengendali kafeteria yang sah melalui surat tawaran/sewaan) dan bukan pekerja biasa tanpa kuasa pengurusan.",
        ],
        "templat_ringkas": (
            "Kesalahan: Tuan punya atau penghuni tempat makan (kafeteria) gagal pada setiap masa mempamerkan tanda amaran larangan merokok mengikut spesifikasi "
            "Jadual Pertama & Kedua Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Tanda Amaran Larangan Merokok) 2024 [P.U. (A) 258/2024], "
            "melanggar Seksyen 18(1)(a) Akta 852 dan boleh dihukum di bawah Seksyen 18(2) Akta 852. Notis S.47 & Tawaran Kompaun S.48(2) [30 hari] telah diserahkan."
        ),
    },
    {
        "id": "ak852_larangan_merokok_bangunan_mall_parkir",
        "akta_utama": "Akta 852",
        "tajuk": "Merokok / Vape Di Dalam Kompleks Membeli-Belah, Parkir Bertingkat Mall atau Bangunan Larangan (Termasuk Dalam Kereta)",
        "keywords": [
            "parking bertingkat", "parkir bertingkat", "tempat letak kereta bertingkat",
            "merokok dalam kereta", "hisap rokok dalam kereta", "hisap vape dalam kereta",
            "mall", "kompleks membeli-belah", "pusat beli-belah", "pusat membeli-belah",
            "parking mall", "parkir mall", "letak kereta", "dalam bangunan",
            "kenderaan awam", "bas sekolah", "stesen minyak", "tandas awam", "lif",
            "kedai berhawa dingin", "bangunan dobi", "bangunan tempat kerja",
        ],
        "negative_keywords": ["pelajar", "murid", "budak sekolah", "najis tikus", "suntikan tifoid"],
        "incompatible_with": ["ak852_obd_merokok_tepi_jalan"],
        "status_kesalahan": "ADA_KESALAHAN",
        "ringkasan_keputusan": (
            "ADA KESALAHAN di bawah Seksyen 16(2) Akta 852 jika parkir bertingkat tersebut sebahagian daripada struktur bangunan / "
            "bumbung kekal kompleks membeli-belah (Bil. 15 & Perenggan 1(b), Jadual Pertama P.U. (A) 257/2024) — keluarkan Notis S.47 & tawarkan kompaun S.48(2) (RM250, 30 hari)."
        ),
        "keputusan_tindakan": "KELUARKAN NOTIS S.47 & TAWARKAN KOMPAUN S.48(2) (RM250 — 30 HARI) JIKA DALAM STRUKTUR BANGUNAN / BUMBUNG KEKAL MALL",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Di bawah Seksyen 16(2) Akta 852 dibaca bersama Perenggan 3 dan Jadual Pertama (Bil. 15 — Kompleks membeli-belah & Perenggan 1(b) takrif 'bangunan') "
            "Perintah P.U. (A) 257/2024, keseluruhan kawasan di dalam struktur bangunan kompleks membeli-belah — termasuk tempat letak kereta bertingkat berbumbung, "
            "bumbung kekal bersambung dan lingkungan jarak 3 meter dari garisan bangunan — adalah KAWASAN LARANGAN MEROKOK. "
            "Walaupun individu merokok di dalam kereta persendirian, kesalahan tetap terpakai kerana kenderaan itu berada di dalam bangunan larangan merokok "
            "(pengecualian 'tempat letak kereta awam terbuka' hanya disebut bagi R&R [Bil. 24] dan Taman Awam [Bil. 25], bukannya bangunan kompleks membeli-belah). "
            "Sebaliknya, jika kereta berada di tempat letak kereta awam terbuka (open-air) di luar jarak 3 meter dari garisan bangunan mall dan bukan kenderaan awam/bas sekolah, ia TIDAK menjadi kesalahan."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Individu merokok / menggunakan produk pengganti tembakau (vape) di dalam bangunan kompleks membeli-belah (termasuk ruang parkir bertingkat berbumbung)",
                "seksyen_kesalahan": "Seksyen 16(2) Akta 852 dibaca bersama Perenggan 3 & Jadual Pertama (Perenggan 1(b) & Bil. 15) P.U. (A) 257/2024",
                "seksyen_hukuman": "Seksyen 16(3) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM5,000",
                "boleh_kompaun": "Boleh dikompaun RM250.00 di bawah Seksyen 48(2) Akta 852 [P.U. (A) 259/2024] — tempoh bayaran 30 hari.",
            },
        ],
        "sop_lapangan": [
            "Sahkan lokasi kejadian secara fizikal: pastikan tempat letak kereta bertingkat itu benar-benar berada di dalam struktur bangunan / di bawah bumbung kekal bersambungan kompleks membeli-belah (atau dalam jarak 3 meter dari garisan bangunan mall), BUKAN parkir terbuka (open-air) luar bangunan.",
            "Saksikan sendiri perbuatan suspek sedang merokok atau menghembus asap/wap rokok/vape dengan jelas (contohnya melalui tingkap kereta terbuka). Ambil gambar kedudukan kereta, asap/rokok, papan tanda aras parkir dan sambungan ke bangunan mall.",
            "Tunjukkan Kad Kuasa KKM (Seksyen 24(2) Akta 852) dengan berhemah dari luar kenderaan — JANGAN sekali-kali membuka pintu kereta persendirian atau merampas barang secara paksa tanpa punca kuasa.",
            "Semak pengenalan diri (MyKad) suspek, jelaskan kesalahan di bawah Seksyen 16(2) Akta 852 & Bil. 15 Jadual Pertama P.U. (A) 257/2024, dan serahkan Tawaran Kompaun S.48(2) (Borang 2 P.U. (A) 259/2024) serta Notis Hadir Mahkamah S.47 (tempoh bayaran 30 hari).",
            "Jika suspek enggan menandatangani notis, catatkan 'Enggan Tandatangan' berserta tandatangan saksi PPKP. Hanya buka Fail IP jika kompaun gagal dibayar selepas tamat tempoh 30 hari.",
        ],
        "eksibit_wajib": [
            "Gambar foto sudut jauh & dekat menunjukkan kereta berada di dalam struktur parkir bertingkat / berbumbung kompleks membeli-belah (beserta papan tanda aras/nama mall) + Sijil Seksyen 90A(2)",
            "Gambar foto atau catatan pemerhatian langsung PPKP saksi bahawa suspek benar-benar sedang merokok/memegang rokok bernyala atau vape",
            "Salinan pendua Tawaran Kompaun Borang 2 P.U. (A) 259/2024 & Notis Seksyen 47 bertandatangan terima / catatan saksi",
            "Sijil pengesahan Unit Hasil PKD bahawa kompaun tidak dijelaskan selepas tamat 30 hari (hanya jika dibawa ke mahkamah)",
        ],
        "perangkap_kesilapan": [
            "BEZA PARKIR BERTINGKAT VS PARKIR TERBUKA: Jangan keluarkan kompaun jika kereta berada di tempat letak kereta awam terbuka (open-air) yang terletak lebih 3 meter dari garisan bangunan kompleks membeli-belah.",
            "HAD KUASA PEMERIKSAAN KERETA PERSENDIRIAN: Jangan membuka pintu kenderaan persendirian secara paksa atau bertindak jika tingkap gelap/tertutup rapat tanpa pengesahan visual jelas perbuatan merokok.",
            "JANGAN salah petik Seksyen 16(1) (kuasa Menteri mengisytihar) atau Seksyen 3(1) (produk tidak berdaftar) — seksyen kesalahan individu merokok ialah Seksyen 16(2) Akta 852.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menghisap rokok / rokok elektronik di dalam ruang tempat letak kereta bertingkat bangunan kompleks membeli-belah "
            "yang diisytiharkan sebagai kawasan larangan merokok di bawah Bil. 15 & Perenggan 1(b), Jadual Pertama P.U. (A) 257/2024, "
            "melanggar Seksyen 16(2) Akta 852 dan boleh dihukum di bawah Seksyen 16(3) Akta 852. "
            "Notis Seksyen 47 dan tawaran kompaun Seksyen 48(2) [RM250, 30 hari] telah diserahkan."
        ),
    },
    {
        "id": "ak852_iklan_vape",
        "akta_utama": "Akta 852",
        "tajuk": "Iklan, Poster, Gegantung atau Promosi Produk Vape / Rokok (Fizikal atau Skrin Digital)",
        "keywords": [
            "iklan rokok", "iklan vape", "papan iklan", "poster iklan", "bunting", "promosi vape",
            "tajaan", "skrin digital", "media sosial", "seksyen 7 akta 852", "seksyen 9 akta 852",
        ],
        "keputusan_tindakan": "SITA POSTER/IKLAN (S.35/S.36) & BUKA IP TERUS (S.7(1) TIDAK BOLEH KOMPAUN di bawah P.U.(A) 259/2024)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Kes iklan dan promosi vape melanggar Seksyen 7(1) / Seksyen 9(1) Akta 852. "
            "Seksyen 7(1) tidak disenaraikan sebagai kesalahan boleh kompaun di bawah Jadual Pertama P.U. (A) 259/2024; "
            "bahan iklan fizikal wajib disita di bawah S.35/36, atau tangkapan skrin digital dicetak dengan Sijil Seksyen 90A(2) & anggapan Seksyen 114A Akta 56 untuk membuka IP."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menyiarkan / mempamerkan iklan produk merokok atau rokok elektronik",
                "seksyen_kesalahan": "Seksyen 7(1) Akta 852 [atau Seksyen 9(1) jika promosi harga/diskaun; dibaca bersama S.49 jika syarikat]",
                "seksyen_hukuman": "Seksyen 7(2)(a) [Individu] / Seksyen 7(2)(b) [Pertubuhan Perbadanan] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara 1 tahun | Syarikat: Denda RM20,000 – RM100,000",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN di bawah Jadual Pertama P.U. (A) 259/2024 bagi S.7(1) — wajib buka IP untuk pendakwaan.",
            }
        ],
        "sop_lapangan": [
            "Ambil gambar keseluruhan kedai serta gambar jelas poster/gegantung/skrin LED iklan vape sebelum menyentuh bahan.",
            "Sita poster atau papan iklan fizikal di bawah Seksyen 35 dan keluarkan Borang Senarai Sitaan Seksyen 36 Akta 852.",
            "Jika iklan di skrin LED/media sosial rasmi kedai, ambil gambar skrin serta cetak paparan tersebut bersama Sijil Seksyen 90A(2) & rujukan Seksyen 114A Akta Keterangan 1950.",
        ],
        "eksibit_wajib": [
            "Bahan iklan/poster fizikal yang disita & dilak KKM + Borang S.36",
            "Gambar foto bukti & cetakan paparan iklan digital + Sijil Seksyen 90A(2)",
            "Carian Rasmi SSM + Sijil S.90A bagi membuktikan entiti yang menyiarkan iklan",
        ],
        "perangkap_kesilapan": [
            "PERTINDIHAN PERTUDUHAN (S.163 KTJ): Jangan campur Seksyen 7(1) [Iklan] dan Seksyen 10(1) [Pameran produk] dalam satu Borang 114 yang sama — wajib asingkan kepada 2 Borang 114 berbeza!",
        ],
        "templat_ringkas": (
            "Kesalahan: Menyiarkan atau menyebabkan disiarkan iklan promosi rokok elektronik (vape) di premis perniagaan "
            "yang melanggar Seksyen 7(1) Akta 852 dan boleh dihukum di bawah Seksyen 7(2)(a)/(b) Akta 852."
        ),
    },
    {
        "id": "ak281_premis_kotor",
        "akta_utama": "Akta 281",
        "tajuk": "Restoran / Premis Makanan Kotor (Markah < 70%, Najis Tikus, Lipas, LILATI)",
        "keywords": [
            "premis kotor", "dapur kotor", "najis tikus", "lipas", "lalat", "lilati", "perangkap minyak",
            "tutup premis makanan", "seksyen 11 akta 281", "peraturan 11", "peraturan 34", "70%",
            "kotor", "tikus",
        ],
        "negative_keywords": ["taska", "tadika", "hfmd", "kolam renang"],
        "keputusan_tindakan": "DUA TINDAKAN SERENTAK: Perintah Tutup S.11 Akta 281 + Notis Kompaun S.32B (Buka IP jika ingkar/tak bayar)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Premis makanan yang berada dalam keadaan tidak suci (< 70% atau penemuan tikus/lipas hidup di kawasan penyediaan) "
            "wajib dikeluarkan Perintah Penutupan Premis Seksyen 11 Akta Makanan 1983 serta-merta (maksimum 14 hari), "
            "DAN dikenakan Notis Seksyen 32B / Kompaun S.33 bagi pelanggaran Peraturan 11(1) atau 34(1) PPKM 2009. "
            "Jika pemilik ingkar tutup atau tidak membayar kompaun, terus Buka IP untuk dakwa di mahkamah."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menjalankan premis makanan dalam keadaan tidak bersih / tidak menyelenggara premis bebas perosak",
                "seksyen_kesalahan": "Peraturan 11(1) PPKM 2009 [atau Peraturan 34(1) PPKM 2009]",
                "seksyen_hukuman": "Peraturan 11(2) PPKM 2009 [atau Peraturan 34(2) PPKM 2009]",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun",
                "boleh_kompaun": "Boleh dikompaun melalui Notis S.32B & S.33 Akta Makanan 1983 (14 hari). Buka IP jika gagal bayar.",
            },
            {
                "perihal": "HANYA JIKA PEMILIK INGKAR PERINTAH TUTUP SEK. 11 (Masih buka niaga selepas notis tutup)",
                "seksyen_kesalahan": "Seksyen 11(2) Akta Makanan 1983",
                "seksyen_hukuman": "Seksyen 11(2) Akta Makanan 1983",
                "hukuman_maksimum": "Penjara tidak melebihi 5 tahun atau denda atau kedua-duanya",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN — Wajib Buka IP Terus jika ingkar perintah tutup S.11!",
            },
        ],
        "sop_lapangan": [
            "Lakukan penilaian mengikut Borang Pemeriksaan Premis Makanan (KMM) bersama PPKP saksi.",
            "Ambil gambar jelas penemuan najis tikus, lipas hidup, lantai berlumut atau perangkap minyak tersumbat sebelum pekerja membersihkannya.",
            "Serahkan Perintah Penutupan Premis Seksyen 11 kepada pemilik/penjaga (dapatkan tandatangan terima), tampal Notis Tutup di pintu hadapan & ambil gambar.",
            "Keluarkan Notis Seksyen 32B Akta 281 bagi kesalahan Peraturan 11(1)/34 PPKM 2009 secara berasingan.",
        ],
        "eksibit_wajib": [
            "Borang Pemeriksaan Premis Makanan (KMM) bertandatangan pemeriksa",
            "Salinan Perintah Penutupan Seksyen 11 bertandatangan terima + gambar tampalan notis",
            "Gambar foto bukti kekotoran/perosak + Sijil Seksyen 90A(2)",
            "Pelan Lakar kawasan dapur & stor premis bertandatangan IO",
            "Salinan Notis Seksyen 32B & pengesahan Unit Hasil (jika buka IP kerana gagal bayar)",
        ],
        "perangkap_kesilapan": [
            "JANGAN hantar najis tikus ke makmal MKAK untuk diuji (najis tikus dibuktikan dengan gambar foto + keterangan pegawai, bukan laporan makmal!).",
            "JANGAN tulis pertuduhan mahkamah 'Seksyen 11' jika pemilik patuh menutup premis — kesalahan kekotoran didakwa di bawah Peraturan 11(1) / 34(1) PPKM 2009.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menjalankan premis makanan dalam keadaan tidak bersih dengan penemuan najis tikus dan lipas hidup di kawasan penyediaan makanan "
            "yang melanggar Peraturan 11(1) [dibaca bersama Peraturan 11(2)] dan Peraturan 34(1) PPKM 2009 [P.U. (A) 95/2009]. "
            "Perintah Penutupan Premis Tidak Suci di bawah Seksyen 11 Akta Makanan 1983 dan Notis Seksyen 32B telah diserahkan."
        ),
    },
    {
        "id": "ak281_pengendali_tifoid",
        "akta_utama": "Akta 281",
        "tajuk": "Pengendali Makanan Tiada Suntikan Anti-Tifoid, Tiada Sijil Latihan (LPM) atau Tidak Pakai Apron",
        "keywords": [
            "suntikan tifoid", "tiada tifoid", "tifoid", "typhoid", "suntikan", "sijil lpm", "slpm", "latihan pengendali",
            "apron", "penutup kepala", "kasut bertutup", "kuku panjang", "cincin", "peraturan 30", "peraturan 31", "peraturan 32", "peraturan 33",
        ],
        "keputusan_tindakan": "KOMPAUN DAHULU (Notis Seksyen 32B Akta 281); BUKA IP JIKA GAGAL BAYAR KOMPAUN",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Kesalahan di bawah Peraturan 30, 31, 32 dan 33 PPKM 2009 tersenarai sebagai kesalahan boleh dikompaun di bawah Seksyen 33 "
            "melalui Notis Seksyen 32B Akta Makanan 1983. Keluarkan kompaun dahulu dan hanya buka IP jika pesalah gagal membayar selepas tamat tempoh."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Tiada Sijil Latihan Pengendali Makanan (SLPM)",
                "seksyen_kesalahan": "Peraturan 30(1) PPKM 2009 [atau Peraturan 11(1)(b) jika menuduh tuan punya premis]",
                "seksyen_hukuman": "Peraturan 30(3) PPKM 2009 [atau Peraturan 11(2) bagi tuan punya]",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun",
                "boleh_kompaun": "Boleh kompaun melalui Notis Seksyen 32B Akta Makanan 1983.",
            },
            {
                "perihal": "Tiada Suntikan Vaksin Anti-Tifoid / Pemeriksaan Perubatan Sah",
                "seksyen_kesalahan": "Peraturan 31(1) PPKM 2009 [JANGAN keliru dengan Peraturan 30!]",
                "seksyen_hukuman": "Peraturan 31(3) PPKM 2009",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun",
                "boleh_kompaun": "Boleh kompaun melalui Notis Seksyen 32B Akta Makanan 1983.",
            },
            {
                "perihal": "Tidak memakai pakaian bersih / apron cerah / penutup kepala / kasut bertutup",
                "seksyen_kesalahan": "Peraturan 32(1) PPKM 2009 [Kebersihan diri / kuku / cincin: Peraturan 33(1)]",
                "seksyen_hukuman": "Peraturan 32(3) PPKM 2009 [Peraturan 33(2) bagi P.33]",
                "hukuman_maksimum": "Peraturan 32(3): Denda tidak melebihi RM1,000 sahaja | Peraturan 33(2): Denda maks RM10,000 atau penjara 2 tahun",
                "boleh_kompaun": "Boleh kompaun melalui Notis Seksyen 32B Akta Makanan 1983.",
            },
        ],
        "sop_lapangan": [
            "Ambil gambar menunjukkan pekerja sedang aktif mengendalikan makanan (memasak/membungkus/menghidang) — membuktikan status 'pengendali makanan'.",
            "Semak Kad Pengenalan / Pasport pekerja, Kad Suntikan Anti-Tifoid, dan Sijil LPM.",
            "Keluarkan Notis Seksyen 32B secara berasingan bagi setiap peraturan yang dilanggar.",
        ],
        "eksibit_wajib": [
            "Gambar pekerja sedang aktif mengendalikan makanan + Sijil Seksyen 90A(2)",
            "Salinan Notis Seksyen 32B bertandatangan terima / saksi enggan tandatangan",
            "Salinan MyKad / Pasport pekerja & rekod semakan sijil LPM/Tifoid",
        ],
        "perangkap_kesilapan": [
            "PERANGKAP NOMBOR PERATURAN: Peraturan 30 = Latihan LPM | Peraturan 31 = Suntikan Anti-Tifoid | Peraturan 32 = Pakaian | Peraturan 33 = Kuku/Cincin!",
            "Pastikan gambar menunjukkan pekerja menyentuh atau mengendalikan makanan (bukan sekadar duduk berehat atau mencuci kereta).",
        ],
        "templat_ringkas": (
            "Kesalahan: Bekerja sebagai pengendali makanan di premis makanan tanpa mendapatkan suntikan vaksin anti-tifoid yang sah di bawah Peraturan 31(1) "
            "yang boleh dihukum di bawah Peraturan 31(3) PPKM 2009 [serta tanpa Sijil Latihan Pengendali Makanan di bawah Peraturan 30(1)]. "
            "Notis Seksyen 32B Akta Makanan 1983 telah diserahkan."
        ),
    },
    {
        "id": "ak281_makanan_tercemar",
        "akta_utama": "Akta 281",
        "tajuk": "Makanan Tercemar Benda Asing (Lipas/Paku/Logam), Bahan Beracun atau Punca Keracunan Makanan",
        "keywords": [
            "keracunan makanan", "keracunan", "benda asing", "paku dalam makanan", "serpihan kaca", "bangkai",
            "bahan beracun", "bahan kimia", "persampelan makanan", "sampel makanan", "juruanalisis",
            "mkak", "seksyen 13 akta 281", "seksyen 13b", "seksyen 19",
        ],
        "negative_keywords": ["jual rokok", "obd", "tamat tempoh", "expired"],
        "keputusan_tindakan": "WAJIB BUKA IP TERUS TANPA KOMPAUN (Kes Tidak Boleh Dikompaun — Izin Dakwa TPR S.32A)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Kesalahan melibatkan makanan berbahaya, mengandungi benda asing atau punca keracunan makanan di bawah Seksyen 13 / 13B "
            "Akta Makanan 1983 adalah KES SERIUS YANG TIDAK BOLEH DIKOMPAUN. Wajib buka IP serta-merta, jalankan persampelan rasmi ke Juruanalisis "
            "Makanan, dan dapatkan sanksi TPR (Seksyen 32A Akta 281) untuk pendakwaan terus di mahkamah."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menyediakan atau menjual makanan mengandungi bahan beracun / memudaratkan kesihatan",
                "seksyen_kesalahan": "Seksyen 13(1) Akta Makanan 1983 (baca bersama S.33A jika syarikat)",
                "seksyen_hukuman": "Seksyen 13(1) Akta Makanan 1983",
                "hukuman_maksimum": "Denda tidak melebihi RM100,000 atau penjara tidak melebihi 10 tahun atau kedua-duanya",
                "boleh_kompaun": "TIDAK BOLEH DIKOMPAUN — Pendakwaan Terus Mahkamah Majistret (Sanksi TPR S.32A).",
            },
            {
                "perihal": "Menjual makanan yang diaduk (mengandungi benda asing / kotor / busuk seperti bangkai lipas/dawai)",
                "seksyen_kesalahan": "Seksyen 13B(1) dibaca bersama Seksyen 13B(2)(d)/(e) Akta Makanan 1983",
                "seksyen_hukuman": "Seksyen 13B(4) Akta Makanan 1983",
                "hukuman_maksimum": "Denda tidak melebihi RM20,000 atau penjara tidak melebihi 5 tahun atau kedua-duanya",
                "boleh_kompaun": "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus.",
            },
        ],
        "sop_lapangan": [
            "Terima laporan pengadu (FIR), rakam percakapan Seksyen 112 pengadu/mangsa & resit pembelian.",
            "Jalankan persampelan rasmi mengikut Seksyen 4, 5 & 6 Akta Makanan 1983 dan lak sampel dengan meterai rasmi KKM.",
            "Hantar sampel kepada Juruanalisis Makanan yang diwartakan (Jabatan Kimia / MKAK) berserta Borang Permintaan Analisis.",
            "PENTING: Apabila Perakuan Juruanalisis (Seksyen 19) diterima, serahkan satu salinan kepada OKS SEKURANG-KURANGNYA 10 HARI JELAS sebelum tarikh perbicaraan (Seksyen 19(2) Akta 281).",
        ],
        "eksibit_wajib": [
            "Sampel makanan / bahan bukti fizikal yang dilak KKM + rekod rantaian stor",
            "Perakuan Juruanalisis Makanan di bawah Seksyen 19 Akta Makanan 1983 + bukti serahan 10 hari kepada OKS",
            "Resit pembelian, Laporan Pengadu (FIR), Rekod perubatan mangsa (jika keracunan)",
            "Rakaman S.112 Pengadu, Pegawai Perubatan, PPKP & OKS + Izin Mendakwa TPR S.32A",
        ],
        "perangkap_kesilapan": [
            "KESALAHAN PROSEDUR S.19(2): Gagal menyerahkan salinan Perakuan Juruanalisis kepada OKS sekurang-kurangnya 10 hari jelas sebelum bicara menyebabkan laporan makmal ditolak mahkamah!",
            "Membenarkan kes Seksyen 13 / 13B ditawarkan kompaun (kesalahan ini tidak boleh dikompaun).",
        ],
        "templat_ringkas": (
            "Kesalahan: Menjual atau menyediakan makanan yang diaduk / mengandungi benda asing atau memudaratkan kesihatan "
            "di bawah Seksyen 13B(1) dibaca bersama Seksyen 13B(2)(e) dan boleh dihukum di bawah Seksyen 13B(4) Akta Makanan 1983. "
            "Sampel telah dihantar ke MKAK/Jabatan Kimia bagi Perakuan Juruanalisis Seksyen 19."
        ),
    },
    {
        "id": "ak154_aedes_premis",
        "akta_utama": "Akta 154",
        "tajuk": "Pembiakan Larva Nyamuk Aedes di Rumah Kediaman / Premis Perniagaan",
        "keywords": [
            "aedes", "larva", "jentik-jentik", "jentik", "denggi", "takungan air", "takungan",
            "nyamuk", "entomologi", "seksyen 13 akta 154", "ak 154", "pembiakan nyamuk",
        ],
        "negative_keywords": ["tapak bina", "tapak pembinaan", "kontraktor", "cidb", "fogging", "halang semburan"],
        "keputusan_tindakan": "KOMPAUN S.25 DAHULU (Maksimum RM500 — 14 Hari); BUKA IP JIKA GAGAL BAYAR",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Bagi rumah kediaman atau premis perniagaan biasa (bukan tapak pembinaan), Seksyen 25 Akta 154 membenarkan tawaran kompaun "
            "maksimum RM500 dengan tempoh bayaran 14 hari. Jika gagal bayar selepas tamat tempoh (dan laporan entomologi positif Aedes), buka IP."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Membiak / membenarkan pembiakan serangga pembawa penyakit (larva nyamuk Aedes)",
                "seksyen_kesalahan": "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154",
                "seksyen_hukuman": "Seksyen 23(a) [Kesalahan Pertama] / Seksyen 23(b) [Ulangan] Akta 154",
                "hukuman_maksimum": "Pertama: Denda maks RM10,000 / penjara maks 2 tahun | Kedua: Denda maks RM50,000 / penjara 5 tahun",
                "boleh_kompaun": "Boleh kompaun RM500.00 (had statutori mutlak S.25 Akta 154 — tempoh 14 hari) untuk kes premis biasa.",
            }
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa (S.3/S.5 Akta 154) dan periksa bersama pemunya/penghuni premis.",
            "Apabila menemui takungan berjentik-jentik, tunjukkan larva hidup kepada penghuni sebelum memungut sampel.",
            "Ambil gambar bekas (sudut jauh + dekat), pungut larva guna pipet ke dalam botol spesimen, dan terus pasang lak KKM bernombor siri.",
            "Lengkapkan Borang Mengambil Larva + Pelan Lakar premis dan minta tandatangan penghuni.",
            "Hantar botol ke Makmal Entomologi dan dapatkan Sijil Perakuan Pengecaman Spesies (Aedes aegypti / albopictus) sebelum mengkompaun/mendakwa.",
        ],
        "eksibit_wajib": [
            "Botol spesimen larva berlak KKM + Borang Kutipan Larva bertandatangan penghuni",
            "Sijil Perakuan Entomologi yang mengesahkan spesies Aedes aegypti / albopictus",
            "Gambar foto bukti bekas pembiakan & lokasi + Sijil Seksyen 90A(2)",
            "Pelan Lakar kedudukan bekas bertandatangan IO & bukti hakmilik/penghuni (bil air/api/SSM)",
        ],
        "perangkap_kesilapan": [
            "AMARAN HAD KOMPAUN S.25: Kompaun Akta 154 TIDAK BOLEH melebihi RM500.00!",
            "Nombor siri lak pada botol mesti SAMA 100% dengan nombor pada Borang Kutipan Larva dan Laporan Entomologi (jika berbeza, rantaian eksibit gagal).",
        ],
        "templat_ringkas": (
            "Kesalahan: Membiarkan air jernih bertakung dalam bekas di premis yang membiak larva nyamuk Aedes aegypti "
            "yang melanggar Seksyen 13(1) dibaca bersama Seksyen 13(2) dan boleh dihukum di bawah Seksyen 23(a) Akta 154. "
            "Spesimen larva dikutip, dilak rasmi dan disahkan oleh Makmal Entomologi."
        ),
    },
    {
        "id": "ak154_aedes_tapak_bina",
        "akta_utama": "Akta 154",
        "tajuk": "Pembiakan Larva Aedes di Tapak Pembinaan & Perintah Penutupan Tapak Binaan",
        "keywords": [
            "tapak bina", "tapak pembinaan", "construction site", "kontraktor utama", "kontraktor",
            "cidb", "perintah tutup tapak", "pemaju", "surat setuju terima", "seksyen 8 akta 154",
        ],
        "keputusan_tindakan": "WAJIB BUKA IP TERUS TANPA KOMPAUN + KELUARKAN PERINTAH SEKSYEN 8(1) AKTA 154",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Mengikut dasar penguatkuasaan KKM bagi tapak pembinaan yang berisiko tinggi mencetuskan wabak denggi maut, "
            "kes pembiakan Aedes di tapak pembinaan TIDAK ditawarkan kompaun RM500, sebaliknya mesti dikeluarkan "
            "Perintah Penutupan / Pemusnahan Seksyen 8(1) dan terus dibuka IP terhadap syarikat kontraktor utama."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Pembiakan larva nyamuk Aedes di kawasan tapak pembinaan",
                "seksyen_kesalahan": "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154",
                "seksyen_hukuman": "Seksyen 23(a)/(b) Akta 154",
                "hukuman_maksimum": "Pertama: Denda maks RM10,000 / penjara 2 tahun | Ulangan: Denda maks RM50,000 / penjara 5 tahun",
                "boleh_kompaun": "TIADA KOMPAUN bagi tapak pembinaan mengikut dasar semasa KKM — Terus Buka IP untuk mahkamah.",
            },
            {
                "perihal": "Jika kontraktor ingkar Perintah Penutupan / Pemusnahan Seksyen 8(1)",
                "seksyen_kesalahan": "Seksyen 8(8) Akta 154",
                "seksyen_hukuman": "Seksyen 23 Akta 154",
                "hukuman_maksimum": "Denda sehingga RM10,000 / RM50,000 atau penjara",
                "boleh_kompaun": "Buka IP Terus (Asingkan Borang 114 daripada pertuduhan Seksyen 13(1)!).",
            },
        ],
        "sop_lapangan": [
            "Jalankan pemeriksaan bersama Pengurus Projek / Safety Health Officer (SHO) kontraktor utama.",
            "Setiap bekas positif dikutip dalam botol spesimen berasingan dengan nombor siri lak KKM tersendiri dan gambar bertarikh.",
            "Serahkan Perintah Seksyen 8(1) Akta 154 (Penutupan tapak / pembersihan wajib).",
            "Dapatkan carian rasmi SSM syarikat kontraktor utama berserta salinan Pendaftaran CIDB / Surat Setuju Terima (SST) / Papan Tanda Projek untuk membuktikan entiti pengawal tapak.",
        ],
        "eksibit_wajib": [
            "Botol spesimen larva berlak KKM + Laporan Entomologi bagi setiap bekas positif",
            "Salinan Perintah Seksyen 8(1) bertandatangan terima SHO/Pengurus Tapak",
            "Cetakan SSM Syarikat Kontraktor Utama + Sijil S.90A, salinan CIDB/SST & lesen PBT",
            "Pelan Lakar tapak pembinaan menunjukkan zon/aras pembiakan bertandatangan IO",
        ],
        "perangkap_kesilapan": [
            "JANGAN campurkan pertuduhan Seksyen 8(8) [Ingkar Perintah] dan Seksyen 13(1) [Pembiakan] dalam satu Borang 114 (Pertindihan Pertuduhan S.163 KTJ).",
            "Pastikan tarikh pada Laporan Entomologi, Borang Kutipan Larva dan Pelan Lakar 100% selari.",
        ],
        "templat_ringkas": (
            "Kesalahan: Membiarkan air bertakung dalam beberapa bekas/zon di tapak pembinaan yang membiak larva nyamuk Aedes aegypti "
            "yang melanggar Seksyen 13(1) dibaca bersama Seksyen 13(2) dan boleh dihukum di bawah Seksyen 23(a) Akta 154. "
            "Perintah Penutupan Seksyen 8(1) telah diserahkan dan IP dibuka terus terhadap kontraktor utama."
        ),
    },
    {
        "id": "ak342_tibi_ingkar",
        "akta_utama": "Akta 342",
        "tajuk": "Pesakit Tibi (PTB Smear Positif) Cicir Rawatan / Ingkar Perintah Rawatan atau Halang Pegawai",
        "keywords": [
            "smear positif", "afb positif", "cicir rawatan", "cicir ubat", "mangkir rawatan",
            "defaulter", "tbis 10d", "mdr-tb", "tbis 10a-1", "sambung rawatan",
            "ingkar perintah rawatan", "seksyen 22(b)", "seksyen 22 akta 342", "arahan rawatan",
            "tibi", "tuberkulosis",
        ],
        "negative_keywords": [
            "smear negatif", "afb negatif", "ptb smear negatif", "disaring tibi", "saringan tibi",
            "belum mula rawatan", "taknak mulakan", "taknak mula", "enggan mulakan", "enggan mula",
            "mula rawatan", "mulakan rawatan", "presumptive",
        ],
        "incompatible_with": ["ak342_tibi_smear_negatif_enggan_mula"],
        "keputusan_tindakan": "BUKA IP TERUS TANPA KOMPAUN (Seksyen 22(b) & Seksyen 24(a) Akta 342 Pindaan Akta A1742)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Pesakit Tibi PTB Smear Positif yang enggan menyambung rawatan berisiko menularkan penyakit maut serta mencipta kuman kebal ubat (MDR-TB). "
            "Kes di bawah Seksyen 22(b) Akta 342 perlu dibuka IP untuk mendapatkan Saman & Izin Mendakwa TPR bagi pendakwaan di Mahkamah Majistret."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Enggan mematuhi perintah sah Pegawai Diberi Kuasa untuk menjalani / menyambung rawatan penyakit berjangkit (Tibi)",
                "seksyen_kesalahan": "Seksyen 22(b) Akta 342 (APPPB 1988) [atau dibaca bersama S.15(1) bagi kontak enggan pemerhatian]",
                "seksyen_hukuman": "Seksyen 24(a) [Individu] / Seksyen 24(b) [Pertubuhan Perbadanan] Akta 342 (Pindaan Akta A1742)",
                "hukuman_maksimum": "Individu: Denda tidak melebihi RM10,000 atau penjara tidak melebihi dua (2) tahun atau kedua-duanya | Syarikat: Denda maks RM100,000",
                "boleh_kompaun": "TIDAK DISYORKAN KOMPAUN — Pendakwaan Terus di Mahkamah Majistret + Hujahan Pemberatan Hukuman.",
            }
        ],
        "sop_lapangan": [
            "Pastikan Notis Arahan Menjalani Rawatan Penyakit Berjangkit telah dikeluarkan dan DISERAHKAN SECARA TANGAN kepada pesakit dengan tandatangan terima pesakit dan saksi PPKP.",
            "Jika pesakit gagal hadir klinik mengikut tarikh ditetapkan, lengkapkan notis cicir TBIS 10D/10Da, jalankan lawatan pengesanan ke rumah & rekod setiap usaha pengesanan dalam Diari Siasatan (DS).",
            "Susun Kronologi Kes lengkap (tarikh mula diagnosis, tarikh AOR/cicir, tarikh serahan notis arahan, tarikh gagal hadir), Kertas Cadangan IO, serta Minit IP (Am 6) semakan KPPKP U7 & UIP JKN.",
            "Rakam percakapan S.112 KTJ PPKP pengesan/pegawai perubatan, siapkan Sijil 90A (bagi e-Notifikasi & foto), dan pohon Izin Dakwa TPR bagi mengeluarkan Saman (Mahkamah 111) & Pertuduhan (Mahkamah 114).",
        ],
        "eksibit_wajib": [
            "Borang Notifikasi (e-Notifikasi / Peraturan Borang Notis 2005) + Sijil S.90A",
            "Salinan Keputusan Makmal Tibi TBIS 20C (mengesahkan kahak PTB Smear Positif)",
            "Notis Arahan Menjalani Rawatan Penyakit Berjangkit bertandatangan terima pesakit & saksi",
            "Borang TBIS 10A-1, Kad Rawatan TBIS 10-I, TBIS 10A-3, TBIS 10D & TBIS 10Da, dan Surat AOR (jika ada)",
            "Jadual Kronologi Kes, Diari Siasatan lengkap, dan 6 Perkara Hujahan Pemberatan Hukuman (risiko penularan awam & MDR-TB)",
        ],
        "perangkap_kesilapan": [
            "KESALAHAN AKTA BIASA: JANGAN sekali-kali tulis 'Seksyen 22(b) Akta 514' (Akta 514 ialah OSHA 1994!). Akta Tibi ialah Akta 342 [APPPB 1988]!",
            "Pastikan bukti serahan tangan Notis Arahan Rawatan asal wujud supaya OKT tidak mendakwa tidak pernah diberi notis.",
        ],
        "templat_ringkas": (
            "Kesalahan: Tidak mematuhi perintah sah yang dikeluarkan oleh pegawai diberi kuasa iaitu enggan menjalani dan menyambung semula rawatan penyakit Tuberkulosis (PTB Smear Positif) "
            "sejenis penyakit berjangkit sebagaimana diarahkan di bawah Notis Arahan Menjalani Rawatan Penyakit Berjangkit. "
            "Perbuatan ini melanggar Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] dan boleh dihukum di bawah Seksyen 24(a) akta yang sama (Pindaan Akta A1742)."
        ),
    },
    {
        "id": "ak342_tibi_smear_negatif_enggan_mula",
        "akta_utama": "Akta 342",
        "tajuk": "Kes Disaring Tibi / PTB Smear Negatif (AFB Negatif) Enggan Memulakan Rawatan",
        "keywords": [
            "smear negatif", "afb negatif", "ptb smear negatif", "disaring tibi", "saringan tibi",
            "mula rawatan", "mulakan rawatan", "belum mula rawatan", "taknak mulakan", "taknak mula",
            "enggan mulakan", "enggan mula", "genexpert", "kultur tibi", "presumptive tb", "aor tibi",
            "seksyen 14 akta 342", "seksyen 15(1)", "tibi", "ptb",
        ],
        "negative_keywords": ["smear positif", "afb positif", "cicir rawatan", "cicir ubat", "tbis 10d", "defaulter"],
        "incompatible_with": ["ak342_tibi_ingkar"],
        "keputusan_tindakan": "SAHKAN DIAGNOSIS KLINIKAL DAHULU (MO/FMS — X-Ray Dada/GeneXpert/Kultur TBIS 20C) & SERAH NOTIS ARAHAN SAH — JANGAN TERUS BUKA IP S.22(b)",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Kes disaring Tibi atau PTB Smear Negatif (AFB Negatif) yang enggan memulakan rawatan TIDAK sama dengan kes PTB Smear Positif cicir rawatan (TBIS 10D). "
            "Jika kes masih peringkat saringan atau keputusan kahak AFB negatif tanpa pengesahan klinikal MO/FMS (X-Ray Dada/GeneXpert MTB/kultur TBIS 20C) serta tanpa Notis Arahan bertulis yang diserahkan secara tangan, "
            "pembukaan IP Seksyen 22(b) berisiko tinggi ditolak TPR/Mahkamah kerana gagal membuktikan pesakit disahkan menghidap penyakit berjangkit aktif dan tiada perintah bertulis sah yang diingkari. "
            "Sahkan diagnosis klinikal & e-Notifikasi S.10 dahulu; guna S.15(1)/S.18(1)(a) untuk ujian lanjut atau S.14/Notis Arahan Rawatan bertulis — hanya buka IP S.22(b) & S.24 jika pesakit masih ingkar selepas serahan tangan notis sah."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Fasa 1 (Saringan / Belum Disahkan Aktif): Perintah Pemerhatian, Pengawasan & Ujian Lanjutan",
                "seksyen_kesalahan": "Seksyen 15(1) & Seksyen 18(1)(a)/(f) Akta 342 [APPPB 1988] + kaunseling & Borang Enggan Rawatan (AOR)",
                "seksyen_hukuman": "Seksyen 22(b) dibaca bersama Seksyen 24(a) Akta 342 (hanya jika ingkar Perintah bertulis S.15(1) yang diserahkan)",
                "hukuman_maksimum": "Pindaan Akta A1742 (kuat kuasa 1 Mei 2025): Individu denda maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "JANGAN buka IP S.22(b) atau tuduh MDR-TB selagi ujian pengesahan (GeneXpert/Kultur/MO) & notis bertulis belum lengkap.",
            },
            {
                "perihal": "Fasa 2 (Selepas Disahkan PTB Aktif oleh MO/FMS & Dinotifikasi S.10): Ingkar Notis Arahan Rawatan / Pengasingan S.14",
                "seksyen_kesalahan": "Seksyen 22(b) Akta 342 [ingkar Notis Arahan Menjalani Rawatan / Perintah Pengasingan Seksyen 14 bertulis]",
                "seksyen_hukuman": "Seksyen 24(a) Akta 342 [APPPB 1988] (Pindaan Akta A1742)",
                "hukuman_maksimum": "Denda maks RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "Buka IP terus HANYA selepas bukti diagnosis aktif MO/FMS & bukti serahan tangan Notis Arahan bertulis lengkap.",
            },
        ],
        "sop_lapangan": [
            "Semak status klinikal dengan Pegawai Perubatan (MO) / FMS / Pakar Klinik Tibi: adakah kes masih disyaki Tibi (saringan awal) atau telah disahkan PTB Smear Negatif aktif berdasarkan X-Ray Dada (CXR), GeneXpert MTB/RIF atau ujian Kultur pada Borang Makmal TBIS 20C.",
            "Pastikan kes telah didaftarkan dalam e-Notifikasi (Seksyen 10 Akta 342 / Peraturan Borang Notis 2005) sekiranya disahkan menghidap Tibi aktif.",
            "Jika keputusan pengesahan masih belum muktamad (tunggu GeneXpert/kultur): jalankan kaunseling bersemuka (MO + PPKP), rekod Borang Enggan Rawatan / AOR bertandatangan pesakit & saksi, dan pertimbangkan Perintah Pemerhatian/Pengawasan bertulis di bawah Seksyen 15(1) / S.18(1)(a) Akta 342 untuk hadir ujian pengesahan.",
            "Hanya apabila MO/FMS mengesahkan PTB aktif dan rawatan wajib dimulakan: keluarkan Notis Arahan Menjalani Rawatan Penyakit Berjangkit / Perintah Seksyen 14 secara bertulis dan buat SERAHAN TANGAN RASMI (tandatangan terima pesakit + saksi PPKP, atau catatan 'Enggan Tandatangan' + saksi + Pos Berdaftar AR).",
            "Sekiranya pesakit masih ingkar tarikh dalam notis bertulis tersebut, barulah buka Fail IP Seksyen 22(b) dengan melampirkan Laporan Pengesahan MO/FMS (wajib sebagai saksi mahkamah), keputusan GeneXpert/Kultur/X-Ray, notis asal, S.112 KTJ dan Diari Siasatan.",
        ],
        "eksibit_wajib": [
            "Laporan Pengesahan Klinikal Bertulis MO / FMS / Pakar Perubatan (mengesahkan PTB Smear Negatif aktif melalui X-Ray Dada / GeneXpert MTB / Kultur)",
            "Keputusan Makmal TBIS 20C (AFB Smear Negatif serta keputusan GeneXpert MTB/RIF atau Ujian Kultur)",
            "Cetakan e-Notifikasi Seksyen 10 Akta 342 + Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Borang Kaunseling & Borang Enggan Rawatan / Surat AOR (bagi fasa penolakan awal klinik)",
            "Notis Arahan Menjalani Rawatan / Perintah S.14 atau S.15(1) bertandatangan terima pesakit & saksi PPKP (WAJIB wujud sebelum IP S.22(b) dibuka)",
        ],
        "perangkap_kesilapan": [
            "JANGAN paksa pakai templat 'PTB Smear Positif Cicir Rawatan' atau nyatakan pesakit telah 'mula & cicir ubat / TBIS 10D' sedangkan rawatan belum pernah dimulakan dan AFB negatif — TPR akan menolak dakwaan kerana percanggahan fakta material (S.152–154 KTJ)!",
            "Arahan lisan doktor/jururawat di klinik BUKAN perintah bertulis di bawah Seksyen 22(b) — notis/perintah bertulis Akta 342 wajib diserahkan dahulu sebelum kesalahan ingkar terbentuk.",
            "Jangan tulis 'Akta 514' (OSHA 1994); semua tindakan kawalan Tibi ialah di bawah Akta 342 [APPPB 1988].",
        ],
        "templat_ringkas": (
            "Kesalahan / Siasatan: Pengendalian kes disaring Tibi / PTB Smear Negatif (AFB Negatif) yang enggan memulakan rawatan di klinik kesihatan. "
            "Tindakan undang-undang dijalankan mengikut Seksyen 15(1) / Seksyen 14 Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] selepas pengesahan diagnosis oleh Pegawai Perubatan melalui X-Ray/GeneXpert/Kultur TBIS 20C serta e-Notifikasi Seksyen 10, "
            "sebelum pertimbangan pendakwaan Seksyen 22(b) & Seksyen 24(a) Akta 342 sekiranya notis perintah bertulis serahan tangan diingkari."
        ),
    },
    {
        "id": "ak342_wabak_tutup_premis_hfmd",
        "akta_utama": "Akta 342",
        "tajuk": "Wabak Penyakit Berjangkit di Taska / Tadika / Sekolah / Kolam Rekreasi (HFMD / Leptospirosis) & Saringan Kontak",
        "keywords": [
            "hfmd", "taska", "tadika", "wabak", "kolam renang", "leptospirosis", "kencing tikus",
            "measles", "difteria", "kolera", "kontak rapat", "tutup taska", "seksyen 18(1)(d)",
            "seksyen 18 akta 342", "enggan saringan", "e-notifikasi", "klinik swasta gagal notifikasi",
        ],
        "negative_keywords": ["dapur restoran", "lemak grease trap", "lilati", "covid", "covid-19", "hso", "influenza"],
        "keputusan_tindakan": "PERINTAH TUTUP / DISINFEKSI S.18(1)(d)&(f) AKTA 342 (atau S.15(1) Pengawasan Kontak; S.10(2) jika klinik gagal notifikasi)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Premis bukan makanan seperti taska, tadika, sekolah, pusat rekreasi atau kem yang menjadi kluster wabak HFMD, Leptospirosis atau Measles "
            "ditutup untuk kerja disinfeksi dan kawalan perebakan menggunakan Seksyen 18(1)(d) & (f) Akta 342 (BUKAN Seksyen 11 Akta 281 yang khusus untuk premis makanan!). "
            "Kontak rapat berisiko yang enggan menjalani pemeriksaan/pengawasan boleh diarahkan melalui Perintah Seksyen 15(1)."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Ingkar perintah penutupan premis wabak / halang kerja disinfeksi atau langkah kawalan wabak",
                "seksyen_kesalahan": "Seksyen 22(b) / Seksyen 22(a) Akta 342 (ingkar Perintah Seksyen 18(1)(d) / halang pegawai)",
                "seksyen_hukuman": "Seksyen 24(a) [Individu] / Seksyen 24(b) [Syarikat] Akta 342 (Pindaan Akta A1742)",
                "hukuman_maksimum": "Individu: Denda maks RM10,000 / penjara maks 2 tahun | Syarikat: Denda maks RM100,000 (Akta A1742).",
                "boleh_kompaun": "Perintah Tutup S.18(1)(d) dikuatkuasa serta-merta; jika diingkari, terus buka IP S.22(b) tanpa kompromi keselamatan kanak-kanak/awam.",
            }
        ],
        "sop_lapangan": [
            "Sahkan kes kluster wabak melalui semakan e-Notifikasi (Seksyen 10 Akta 342) dan siasatan epidemiologi lapangan.",
            "Serahkan Notis Perintah Penutupan Premis Sementara di bawah Seksyen 18(1)(d) Akta 342 kepada pengusaha taska/sekolah/pusat rekreasi berserta arahan pembersihan & disinfeksi di bawah Seksyen 18(1)(f).",
            "Jika terdapat kontak rapat yang enggan disaring atau diasingkan sementara, keluarkan Perintah Pemerhatian/Pengawasan bertulis di bawah Seksyen 15(1) Akta 342.",
            "Bagi pengamal perubatan/klinik swasta yang gagal membuat notifikasi penyakit berjangkit, dokumentasikan bukti rekod pesakit dan buka kertas siasatan Seksyen 10(2) Akta 342.",
        ],
        "eksibit_wajib": [
            "Notis Perintah Penutupan Premis Seksyen 18(1)(d) / Seksyen 15(1) Akta 342 bertandatangan terima",
            "Rekod e-Notifikasi kes indeks & laporan siasatan wabak epidemiologi PKD",
            "Gambar foto lokasi kluster/tampalan notis penutupan + Sijil S.90A(2)",
        ],
        "perangkap_kesilapan": [
            "JANGAN guna Seksyen 11 Akta Makanan 1983 untuk menutup taska/tadika/kolam renang — gunakan Seksyen 18(1)(d) Akta 342!",
            "Pastikan tarikh kuat kuasa & syarat pembukaan semula (pemeriksaan disinfeksi lulus) dinyatakan jelas dalam perintah penutupan.",
        ],
        "templat_ringkas": (
            "Kesalahan / Tindakan: Penutupan premis bukan makanan dan arahan disinfeksi bagi membendung penularan wabak penyakit berjangkit "
            "di bawah Seksyen 18(1)(d) & Seksyen 18(1)(f) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]. "
            "Sebarang keingkaran terhadap perintah tersebut merupakan kesalahan di bawah Seksyen 22(b) dan boleh dihukum di bawah Seksyen 24 akta yang sama."
        ),
    },
    {
        "id": "ak281_makanan_luput_label",
        "akta_utama": "Akta 281",
        "tajuk": "Makanan Tamat Tempoh (Expired), Pelabelan Tiada Bahasa Melayu atau Mesin Jual Air / Premis Tak Berdaftar",
        "keywords": [
            "tamat tempoh", "luput tarikh", "tarikh luput", "expired", "peraturan 14(9)",
            "label bahasa melayu", "tiada label", "peraturan 10", "mesin jual air", "mja",
            "360c", "tidak berdaftar fosim", "fosim", "peraturan 3", "ppm 1985",
        ],
        "negative_keywords": ["benda asing", "keracunan", "paku"],
        "keputusan_tindakan": "SITA STOK / LAK MESIN (S.4(1)(f) AKTA 281) & NOTIS S.32B / BUKA IP (ikut jenis kesalahan & nilai kes)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Menjual makanan tamat tarikh luput (Peraturan 14(9) PPM 1985), pelabelan tidak mematuhi Peraturan 10/11 PPM 1985, "
            "mengendali Mesin Jual Air tanpa lesen sah KKM (Peraturan 360C(4) PPM 1985), atau menjalankan premis makanan tanpa pendaftaran FoSIM (Peraturan 3(1) PPKM 2009) "
            "wajib didokumentasikan dengan sitaan produk/mesin dan tindakan Notis S.32B atau buka IP sekiranya berskala besar/berulang/ingkar."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menjual / mempamer untuk jualan makanan yang telah tamat tarikh luput",
                "seksyen_kesalahan": "Peraturan 14(9)(b) Peraturan-Peraturan Makanan 1985 [Ubah tarikh luput: P.14(7)]",
                "seksyen_hukuman": "Peraturan 397(2) Peraturan-Peraturan Makanan 1985 dibaca bersama Akta Makanan 1983 [Akta 281]",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "Sita semua stok tamat tempoh di bawah S.4(1)(f) Akta 281; boleh tawar kompaun S.32B atau buka IP bagi kesalahan besar/berulang.",
            },
            {
                "perihal": "Mengendali Mesin Jual Air (MJA) tanpa lesen KKM / Premis tak daftar FoSIM",
                "seksyen_kesalahan": "Peraturan 360C(4) PPM 1985 [MJA] / Peraturan 3(1) PPKM 2009 [Tiada Pendaftaran Premis]",
                "seksyen_hukuman": "Peraturan 397(2) PPM 1985 / Peraturan 3(2) PPKM 2009",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun.",
                "boleh_kompaun": "Lak/tahan operasi MJA tanpa lesen; premis tak daftar FoSIM lazimnya boleh dikompaun S.32B berserta arahan daftar.",
            },
        ],
        "sop_lapangan": [
            "Ambil gambar produk di rak jualan menunjukkan dengan jelas tarikh luput (EXP/Best Before) atau keadaan label sebelum dialihkan.",
            "Sita kesemua unit makanan tamat tempoh atau tanpa label sah di bawah Seksyen 4(1)(f) Akta Makanan 1983, senaraikan kuantiti/jenama dan dapatkan tandatangan terima pemilik.",
            "Bagi Mesin Jual Air (MJA) tanpa lesen P.360C atau lesen tamat tempoh 2 tahun, rekod nombor siri mesin, pemilik syarikat pada pelekat mesin & SSM sebelum tindakan pengelakan/kompaun.",
        ],
        "eksibit_wajib": [
            "Sampel/stok produk makanan tamat tempoh atau berlabel salah yang disita & dilak (P1..Pn)",
            "Borang Senarai Barang Disita & resit pembelian (jika ujian beli) / gambar tarikh luput + Sijil S.90A(2)",
            "Carian SSM syarikat pengendali/peruncit berserta Sijil S.90A",
        ],
        "perangkap_kesilapan": [
            "Jangan campurkan tarikh luput (P.14(9) PPM 1985) dengan makanan rosak/tercemar fizikal (S.13B Akta 281) tanpa membezakan fakta kesalahan pada Borang 114.",
            "Bagi produk tamat tempoh, pastikan tarikh tamat pada bungkusan jelas terbaca dalam gambar bukti sebelum kes tamat tempoh dipertikai pembelaan.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menjual atau mendedahkan untuk jualan makanan yang telah tamat tempoh tarikh akhir penggunaan yang melanggar "
            "Peraturan 14(9)(b) Peraturan-Peraturan Makanan 1985 di bawah Akta Makanan 1983 [Akta 281]. "
            "Semua produk terlibat telah disita di bawah Seksyen 4(1)(f) Akta Makanan 1983 bagi tujuan pembuktian."
        ),
    },
    {
        "id": "ak154_halang_fogging_ingkar_s8",
        "akta_utama": "Akta 154",
        "tajuk": "Menghalang Pegawai Semburan Kabus (Fogging) atau Ingkar Perintah Pembersihan Seksyen 8(1) Akta 154",
        "keywords": [
            "halang fogging", "halang semburan", "fogging", "semburan kabus", "seksyen 21 akta 154",
            "ingkar perintah seksyen 8", "seksyen 8(8)", "lot semak", "tanah terbiar", "enggan bagi masuk",
        ],
        "negative_keywords": ["tapak pembinaan", "cidb", "kontraktor utama"],
        "keputusan_tindakan": "BUKA IP TERUS TANPA KOMPAUN (Seksyen 21 / Seksyen 8(8) Akta 154) & BANTUAN POLIS S.24 JIKA PERLU",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Menghalang, menggertak atau enggan memberi akses kepada pegawai KKM menjalankan semburan kabus (fogging) dan kawalan denggi "
            "ialah kesalahan jenayah serius di bawah Seksyen 21 Akta 154. Begitu juga kegagalan mematuhi Notis/Perintah Pembersihan Seksyen 8(1) selepas tamat tempoh notis ialah kesalahan Seksyen 8(8) Akta 154. "
            "Kedua-duanya wajib dibuka IP untuk pendakwaan dan boleh memohon bantuan PDRM di bawah Seksyen 24 Akta 154 jika dihalang keras."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menghalang / mengganggu pegawai diberi kuasa menjalankan tugas pemeriksaan atau semburan kabus (fogging)",
                "seksyen_kesalahan": "Seksyen 21 Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                "seksyen_hukuman": "Seksyen 21 dibaca bersama Seksyen 23 Akta 154",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "BUKA IP TERUS — kesalahan menghalang pegawai tidak wajar diselesaikan dengan kompaun biasa.",
            },
            {
                "perihal": "Ingkar Perintah Pembersihan / Pemusnahan Tempat Pembiakan Seksyen 8(1)",
                "seksyen_kesalahan": "Seksyen 8(8) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                "seksyen_hukuman": "Seksyen 23(a) Akta 154",
                "hukuman_maksimum": "Kesalahan pertama: Denda <= RM10,000 atau penjara <= 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "Buka IP Terus (boleh disusuli kerja pembersihan oleh pihak berkuasa & tuntutan kos di bawah S.8(6)-(7)).",
            },
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa Rasmi KKM serta terangkan tujuan semburan kabus/pemeriksaan secara berhemah dan rekodkan butiran penolakan dalam Diari Siasatan serta rakaman S.112 saksi PPKP/pasukan kawalan vektor.",
            "Jika diugut atau dihalang keras di lokasi wabak denggi, buat laporan polis dan mohon bantuan polis di bawah Seksyen 24 Akta 154.",
            "Bagi kes S.8(8), pastikan Notis Perintah Seksyen 8(1) asal mempunyai bukti serahan rasmi (tangan/tampal + gambar tarikh serah & tarikh tamat notis sebelum pemeriksaan ulangan).",
        ],
        "eksibit_wajib": [
            "Laporan Polis (jika ancaman/halangan keras) & Diari Siasatan pasukan fogging / vektor",
            "Notis Perintah Seksyen 8(1) bertandatangan terima / bukti tampalan premis (bagi kes S.8(8))",
            "Gambar foto sebelum dan selepas tamat tempoh notis + Sijil S.90A(2)",
            "Percakapan S.112 KTJ PPKP & pembantu kesihatan awam (saksi kejadian)",
        ],
        "perangkap_kesilapan": [
            "Jangan lupa buktikan serahan sah Notis Seksyen 8(1) terlebih dahulu sebelum menuduh di bawah Seksyen 8(8)!",
            "Asingkan pertuduhan S.21 (halangan) dan S.13(1) (pembiakan) dalam Borang 114 berasingan.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menghalang pegawai diberi kuasa daripada menjalankan pemeriksaan / semburan kabus kawalan vektor Aedes "
            "yang melanggar Seksyen 21 Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]."
        ),
    },
    {
        "id": "ak_silang_agensi_kacau_ganggu_racun",
        "akta_utama": "Rujukan Silang Agensi (Akta 171 / Akta 366 / Akta 586 / Akta 260)",
        "tajuk": "Kes Kacau Ganggu PBT (Akta 171), Vape Dadah/Racun (Akta 366), Klinik Swasta (Akta 586) & Pengasapan (Akta 260)",
        "keywords": [
            "kacau ganggu", "bau busuk", "najis lembu", "ternakan", "parit tersumbat", "akta 171",
            "racun berjadual", "magic mushroom", "vape dadah", "akta 366", "akta 368", "farmasi",
            "ckaps", "klinik tak berdaftar", "akta 586", "hidrogen sianida", "pengasapan", "fumigation", "akta 260",
            "pencemaran sungai", "jas", "akta 127",
        ],
        "keputusan_tindakan": "SIASAT AWAL & RUJUK SILANG AGENSI BERKUASA (PBT / Farmasi JKN / PDRM / CKAPS / JAS)",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Kes seperti bau busuk/kumbahan bukan makanan (Seksyen 80–82 Akta Kerajaan Tempatan 1976 [Akta 171]), cecair vape disyaki mengandungi dadah/racun berjadual (Akta Racun 1952 [Akta 366] / Akta Jualan Dadah [Akta 368]), "
            "klinik swasta tidak berdaftar (Akta 586 CKAPS) atau pencemaran industri (Akta 127 JAS) berada di bawah akta khusus atau tindakan bersepadu. "
            "Rujuk silang agensi berkenaan supaya tindakan tidak dibatalkan atas alasan melebihi bidang kuasa."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Kacau ganggu kesihatan awam (bau busuk ternakan, longkang, sisa domestik bukan makanan)",
                "seksyen_kesalahan": "Seksyen 80, 81 & 82 Akta Kerajaan Tempatan 1976 [Akta 171] (Bidang kuasa PBT)",
                "seksyen_hukuman": "Peruntukan Notis Kacau Ganggu PBT di bawah Akta 171",
                "hukuman_maksimum": "Perintah menghentikan kacau ganggu PBT / denda & kos kerja pembetulan oleh PBT.",
                "boleh_kompaun": "PPKP siasat punca vektor/air; rujuk kes kacau ganggu bukan pembiakan Aedes kepada PBT.",
            },
            {
                "perihal": "Cecair vape disyaki mengandungi dadah sintetik / racun berjadual (atau pengasapan gas beracun Akta 260)",
                "seksyen_kesalahan": "Akta Racun 1952 [Akta 366] / Akta Dadah Berbahaya 1952 / Akta 260 [Pengasapan Hidrogen Sianida]",
                "seksyen_hukuman": "Disiasat Penguatkuasaan Farmasi JKN / JSJN PDRM (atau Unit Kesihatan Pekerjaan KKM bagi Akta 260)",
                "hukuman_maksimum": "Tertakluk penalti jenayah berat di bawah Akta Racun / Dadah / Akta 260.",
                "boleh_kompaun": "Serah/operasi bersepadu bersama Cawangan Penguatkuasaan Farmasi JKN / PDRM & ujian makmal Jabatan Kimia.",
            },
        ],
        "sop_lapangan": [
            "Jalankan siasatan awal di lokasi untuk mengesahkan fakta (adakah terdapat pembiakan Aedes di bawah Akta 154 atau pencemaran air KMAM/BAKAS).",
            "Jika kes sahih melibatkan kacau ganggu PBT (Akta 171), tulis minit rujukan rasmi berserta gambar bertarikh kepada Jabatan Kesihatan/Penguatkuasaan PBT.",
            "Jika menemui perisa vape disyaki racun/dadah atau ubat tanpa nombor MAL/NOT, JANGAN sita bersendirian tanpa koordinasi — hubungi segera Penguatkuasaan Farmasi JKN / PDRM (atau CKAPS JKN bagi klinik swasta Akta 586).",
        ],
        "eksibit_wajib": [
            "Laporan Siasatan Awal PPKP berserta koordinat lokasi & gambar bertarikh (+ Sijil S.90A(2))",
            "Surat / Memo Rujukan Rasmi Antara Agensi (PBT / Farmasi JKN / CKAPS / JAS / PDRM)",
        ],
        "perangkap_kesilapan": [
            "JANGAN paksa guna Akta 154 atau Akta 281 untuk aduan bau tahi lembu atau longkang tersumbat tanpa penemuan larva Aedes atau pengendalian makanan — kes berisiko dibatalkan kerana di luar bidang kuasa akta.",
        ],
        "templat_ringkas": (
            "Laporan Rujukan Silang Agensi: Siasatan awal mendapati isu terletak di bawah bidang kuasa / penguatkuasaan bersepadu "
            "(Akta 171 PBT / Akta 366 Farmasi / Akta 586 CKAPS / Akta 260 / Akta 127 JAS). "
            "Dokumen dan gambar lapangan dilampirkan untuk tindakan susulan pihak berkuasa berkaitan."
        ),
    },
    {
        "id": "ak342_covid_positif_tempat_kerja",
        "akta_utama": "Akta 342",
        "tajuk": "Pekerja Positif COVID-19 / Jangkitan Respiratori Hadir Bekerja & Aduan Majikan kepada Unit CDC",
        "keywords": [
            "covid positif", "positif covid", "kes covid", "covid-19", "covid",
            "datang kerja", "datng kerja", "hadir bekerja", "masuk kerja",
            "pekerja positif", "majikan adukan", "aduan majikan", "unit cdc",
            "hso", "mysejahtera", "influenza", "kluster tempat kerja",
            "seksyen 12", "12(1)", "seksyen 25 akta 342",
        ],
        "negative_keywords": [
            "tibi", "tuberkulosis", "ptb", "smear positif", "smear negatif", "afb negatif", "tbis",
            "hfmd", "taska", "tadika", "leptospirosis", "kencing tikus", "kolam renang",
            "keracunan makanan", "aedes", "vape", "rokok",
        ],
        "incompatible_with": [
            "ak342_tibi_ingkar",
            "ak342_tibi_smear_negatif_enggan_mula",
            "ak342_wabak_tutup_premis_hfmd",
        ],
        "keputusan_tindakan": (
            "TIDAK BOLEH KOMPAUN SERTA-MERTA (Tiada HSO Mandatori sejak 15 Julai 2024) — "
            "SIASAT RISIKO KLUSTER UNIT CDC & NASIHAT PENCEGAHAN; KOMPAUN S.25 / IP S.22(b) HANYA JIKA INGKAR PERINTAH BERTULIS S.15(1)/S.14"
        ),
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Bermula 15 Julai 2024 (dasar KKM 'Hidup Bersama COVID-19'), Perintah Pengawasan dan Pemerhatian di Rumah (HSO) mandatori MySejahtera telah dimansuhkan "
            "dan COVID-19 diurus seperti jangkitan saluran pernafasan akut (ARI) biasa melalui penilaian klinikal doktor/cuti sakit serta pemakaian pelitup muka. "
            "Tanpa Perintah Pengawasan Seksyen 15(1) atau Pengasingan Seksyen 14 Akta 342 yang dikeluarkan dan diserahkan secara bertulis, TIADA kesalahan Seksyen 22(b) untuk dikompaun. "
            "Selain itu, Seksyen 12(1) Akta 342 BUKAN kesalahan boleh kompaun di bawah Jadual Pertama P.U. (A) 139/2025 (berkuat kuasa 1 Mei 2025) serta amat sukar dibuktikan tanpa perintah bertulis. "
            "Urusan cuti sakit (Seksyen 60F Akta Kerja 1955), arahan pulang/bekerja dari rumah dan tatatertib pekerja ialah tanggungjawab majikan di bawah dasar sumber manusia & OSHA 1994 [Akta 514] (S.15 & S.24), manakala Unit CDC PKD menumpukan siasatan risiko kluster tempat kerja."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Kes COVID-19 Biasa Tanpa Perintah Bertulis S.15(1)/S.14 (Dasar Semasa KKM Pasca 15 Julai 2024)",
                "seksyen_kesalahan": "TIADA KESALAHAN BOLEH KOMPAUN di bawah Akta 342 (Pengurusan majikan: S.60F Akta Kerja 1955 / S.15 & S.24 OSHA 1994 [Akta 514])",
                "seksyen_hukuman": "Tindakan Kesihatan Awam Unit CDC PKD (nasihat pencegahan, pengesahan e-Notifikasi & penilaian risiko kluster tempat kerja)",
                "hukuman_maksimum": "Tiada kompaun Akta 342. Pertimbangan Perintah S.15(1) / Penutupan Disinfeksi S.18(1)(d) hanya jika wujud wabak/kluster serius.",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN — Jangan keluarkan notis kompaun tanpa perintah bertulis yang sah diingkari.",
            },
            {
                "perihal": "HANYA JIKA Pekerja Ingkar Perintah Bertulis Seksyen 15(1) / Seksyen 14 Akta 342 Yang Sah Diserahkan (Kes Kluster/Wabak Khas)",
                "seksyen_kesalahan": "Seksyen 22(b) Akta 342 [APPPB 1988] (ingkar perintah sah pegawai diberi kuasa)",
                "seksyen_hukuman": "Seksyen 24(a) [Individu] / Seksyen 24(b) [Syarikat] Akta 342 (Pindaan Akta A1742 berkuat kuasa 1 Mei 2025)",
                "hukuman_maksimum": "Individu: Denda maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya | Syarikat: Denda maks RM100,000",
                "boleh_kompaun": (
                    "Boleh dikompaun di bawah Seksyen 25 Akta 342 (Pindaan Akta A1742) & P.U. (A) 139/2025 "
                    "HANYA DENGAN KEIZINAN BERTULIS PENDAKWA RAYA: maks RM5,000 (individu) / RM50,000 (pertubuhan perbadanan), atau buka IP jika ingkar tegar."
                ),
            },
            {
                "perihal": "Rujukan Terhad: Sengaja Mendedahkan Orang Lain kepada Risiko Jangkitan (Kes Keterlaluan Sahaja — Bukan Rutin)",
                "seksyen_kesalahan": "Seksyen 12(1) dibaca bersama Seksyen 12(3) Akta 342 [APPPB 1988]",
                "seksyen_hukuman": "Seksyen 24(a) Akta 342 (Pindaan Akta A1742)",
                "hukuman_maksimum": "Individu: Denda maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya",
                "boleh_kompaun": (
                    "TIDAK BOLEH DIKOMPAUN (Seksyen 12(1)/(3) tiada dalam Jadual Pertama P.U. (A) 139/2025) — "
                    "hanya melalui IP & beban bukti amat tinggi (wajib bukti makmal rasmi, pengetahuan awal & pendedahan aktif cuai/niat jahat)."
                ),
            },
        ],
        "sop_lapangan": [
            "Sahkan status kes melalui semakan e-Notifikasi (Seksyen 10 Akta 342) dan tanyakan jenis ujian: ujian RTK-Ag kendiri di rumah BUKAN pengesahan rasmi kes di bawah garis panduan KKM sejak 15 Julai 2024.",
            "Semak rekod PKD sama ada sebarang Perintah Pengawasan/Pemerhatian bertulis Seksyen 15(1) atau Pengasingan Seksyen 14 Akta 342 pernah dikeluarkan dan diserahkan secara tangan kepada pekerja tersebut.",
            "Jalankan penilaian risiko epidemiologi Unit CDC di tempat kerja: kenal pasti sama ada kes terpencil tunggal atau wujud kluster/wabak aktif (beberapa kes positif/bergejala serentak atau melibatkan golongan rentan seperti wad/pusat jagaan/taska).",
            "Jika kes terpencil tanpa perintah bertulis: JANGAN tawarkan kompaun; beri nasihat kawalan jangkitan (pekerja dapatkan pemeriksaan doktor/cuti sakit jika tidak sihat, pakai pelitup muka, sanitasi permukaan & pengudaraan premis) dan jelaskan kepada majikan bahawa pengurusan cuti/bekerja dari rumah adalah di bawah tanggungjawab majikan (Akta Kerja 1955 S.60F & OSHA 1994 Akta 514 S.15/S.24).",
            "HANYA jika siasatan Unit CDC mengesahkan kluster serius/risiko awam tinggi dan tiada kerjasama: pertimbangkan pengeluaran Perintah bertulis Seksyen 15(1) / Seksyen 14 (serahan tangan + tandatangan terima/saksi PPKP) dan/atau arahan disinfeksi/penutupan sementara premis Seksyen 18(1)(d)&(f). Tindakan S.22(b)/S.25 (dengan keizinan bertulis TPR) hanya diambil jika perintah bertulis sah itu diingkari.",
        ],
        "eksibit_wajib": [
            "Rekod Aduan Rasmi Majikan & Laporan Siasatan Epidemiologi Awal Unit CDC PKD (menilai status kes terpencil vs kluster tempat kerja)",
            "Semakan Cetakan e-Notifikasi Seksyen 10 Akta 342 / keputusan ujian makmal profesional (jika disahkan fasiliti kesihatan) + Sijil S.90A(2)",
            "Surat / Rekod Nasihat Pencegahan & Pengurusan Kes kepada Majikan dan Pekerja (bukti tindakan kesihatan awam PKD tanpa salah guna kuasa)",
            "HANYA JIKA TINDAKAN LANJUT S.22(b): Salinan asal Perintah S.15(1) / S.14 bertandatangan terima & saksi PPKP, bukti kehadiran mengingkari perintah (rekod kedatangan/CCTV + S.90A), percakapan S.112 KTJ saksi, dan Keizinan Bertulis Pendakwa Raya (jika tawar kompaun S.25)",
        ],
        "perangkap_kesilapan": [
            "PERANGKAP KOMPAUN TIDAK SAH #1: JANGAN tawarkan kompaun Seksyen 22(b) tanpa Perintah bertulis Seksyen 15(1)/Seksyen 14 yang diserahkan secara sah — HSO mandatori MySejahtera telah dimansuhkan sejak 15 Julai 2024!",
            "PERANGKAP KOMPAUN TIDAK SAH #2: JANGAN keluarkan notis kompaun di bawah Seksyen 12(1) Akta 342 — Seksyen 12(1)/(3) BUKAN kesalahan boleh kompaun dalam Jadual Pertama P.U. (A) 139/2025!",
            "PERANGKAP PINDAAN AKTA A1742 (1 MEI 2025): Di bawah Seksyen 25 baharu, had kompaun bukan lagi RM1,000 (kini maks RM5,000 individu / RM50,000 pertubuhan perbadanan) DAN pengkompaunan tertakluk kepada keizinan bertulis Pendakwa Raya serta hanya untuk seksyen dalam Jadual Pertama P.U. (A) 139/2025 (S.10(2), S.11(5), S.21A(3), S.22(b)/(c)/(d)).",
            "JANGAN jadikan Unit CDC/PPKP sebagai alat tatatertib sumber manusia majikan — arahan pulang kerja, cuti sakit (S.60F Akta Kerja 1955), bekerja dari rumah dan tatatertib pekerja ialah tanggungjawab majikan di bawah dasar syarikat & OSHA 1994 (Akta 514 S.15 & S.24).",
        ],
        "templat_ringkas": (
            "Laporan Siasatan Aduan Unit CDC (Akta 342): Aduan majikan berkaitan pekerja disyaki/positif COVID-19 hadir bekerja. "
            "Selaras dasar KKM 'Hidup Bersama COVID-19' (berkuat kuasa 15 Julai 2024), HSO mandatori telah dimansuhkan dan tiada perintah bertulis Seksyen 15(1)/Seksyen 14 Akta 342 dikeluarkan terhadap pekerja berkenaan; "
            "justeru tiada tindakan kompaun Seksyen 22(b) atau Seksyen 12(1) Akta 342 dikenakan. "
            "Unit CDC PKD telah menjalankan penilaian risiko kluster tempat kerja, memberi nasihat kawalan jangkitan/penilaian MC doktor, dan memaklumkan majikan mengenai pengurusan kehadiran/cuti di bawah bidang kuasa HR (Akta Kerja 1955 & OSHA 1994 [Akta 514])."
        ),
    },
]


class _AdvisorChargeItemSchema(BaseModel):
    perihal: str = Field(...)
    seksyen_kesalahan: str = Field(...)
    seksyen_hukuman: str = Field(...)
    hukuman_maksimum: str = Field(...)
    boleh_kompaun: str = Field(...)


class _AdvisorLLMSchema(BaseModel):
    status_kesalahan: Optional[str] = None
    akta_disyorkan: Optional[str] = None
    tajuk_nasihat: str = Field(...)
    ringkasan_keputusan: Optional[str] = None
    keputusan_tindakan: str = Field(...)
    sesuai_buka_ip: bool = Field(...)
    alasan_keputusan: str = Field(...)
    sebab_tidak_menyalahi: Optional[str] = None
    langkah_susulan_ppkp: List[str] = Field(default_factory=list)
    cadangan_pertuduhan: List[_AdvisorChargeItemSchema] = Field(default_factory=list)
    sop_lapangan: List[str] = Field(default_factory=list)
    eksibit_wajib: List[str] = Field(default_factory=list)
    perangkap_kesilapan: List[str] = Field(default_factory=list)
    templat_ringkas: str = Field(...)


class UIPAdvisorService:
    """Enjin Penasihat Undang-Undang & Prosedur Lapangan UIP KKM."""

    MIN_SCENARIO_SCORE = 1.8

    _NO_OFFENCE_SCENARIO_IDS = {
        "ak852_s17_unsur_tidak_terpenuhi",
        "ak342_covid_positif_tempat_kerja",
        "ak342_tibi_smear_negatif_enggan_mula",
        "ak_silang_agensi_kacau_ganggu_racun",
        "unindexed_statute_guard",
    }

    def __init__(self, router: UIPModelRouter, db: Optional[Any] = None) -> None:
        self.router = router
        self.db = db
        self._consult_cache: Dict[str, Dict[str, Any]] = {}

    def clear_cache(self) -> None:
        """Mengosongkan cache konsultasi apabila tetapan atau kunci API diubah."""
        self._consult_cache.clear()

    def list_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": s["id"],
                "akta_utama": s["akta_utama"],
                "tajuk": s["tajuk"],
                "keputusan_tindakan": s["keputusan_tindakan"],
                "sesuai_buka_ip": s["sesuai_buka_ip"],
                "cadangan_pertuduhan": s["cadangan_pertuduhan"],
            }
            for s in UIP_SCENARIO_LIBRARY
        ]

    @staticmethod
    def _kw_in_text(kw: str, text_low: str) -> bool:
        """Padanan kata kunci bersempadan perkataan agar subkata seperti 'tb' tidak padan dalam 'ptb'."""
        if not kw:
            return False
        return bool(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", text_low))

    @classmethod
    def _score_scenario(
        cls,
        scenario: Dict[str, Any],
        q_low: str,
        akta_hint: str = "Semua",
    ) -> tuple[float, float, int, List[str]]:
        """Mengira skor senario menggunakan padanan frasa terpanjang & penalti kata kunci negatif."""
        matched_kws: List[str] = []
        kw_score = 0.0
        for kw in sorted(scenario.get("keywords", []), key=len, reverse=True):
            kw_low = kw.lower()
            if any(kw_low in prev for prev in matched_kws):
                continue
            if cls._kw_in_text(kw_low, q_low):
                matched_kws.append(kw_low)
                if " " in kw_low:
                    kw_score += 3.2
                elif len(kw_low) > 5:
                    kw_score += 2.2
                else:
                    kw_score += 1.2

        neg_hits = sum(
            1 for nkw in scenario.get("negative_keywords", []) if cls._kw_in_text(nkw.lower(), q_low)
        )
        net_kw_score = kw_score - (neg_hits * 6.0)
        act_bonus = (
            0.8
            if (akta_hint and akta_hint != "Semua" and akta_hint in str(scenario.get("akta_utama", "")))
            else 0.0
        )
        return net_kw_score + act_bonus, net_kw_score, neg_hits, matched_kws

    @staticmethod
    def _canonicalize_akta_code(raw_act: str, fallback: str) -> str:
        low = (raw_act or "").strip().lower()
        if not low:
            return fallback
        if "342" in low or "penyakit berjangkit" in low or "apppb" in low:
            return "Akta 342"
        if "852" in low or "produk merokok" in low:
            return "Akta 852"
        if "281" in low or "akta makanan" in low or "ppkm" in low or "ppm 1985" in low:
            return "Akta 281"
        if "154" in low or "serangga pembawa penyakit" in low:
            return "Akta 154"
        m = re.search(r"akta\s+(\d+)", low)
        if m:
            return f"Akta {m.group(1)}"
        return raw_act.strip()

    @staticmethod
    def _format_section_label(section: str, akta_code: str) -> str:
        """Mengelakkan pengulangan seperti 'Seksyen 48 Akta 852 (Akta 852)'."""
        clean_sec = (section or "").strip()
        clean_act = (akta_code or "").strip()
        if not clean_act or clean_act.lower() in clean_sec.lower():
            return clean_sec or clean_act
        return f"{clean_sec} ({clean_act})"

    @staticmethod
    def _enforcement_power_for_act(akta_code: str) -> str:
        low = (akta_code or "").lower()
        if "852" in low:
            return "Kad Kuasa S.24(2), Pemeriksaan/Siasatan S.25–S.30, Sitaan S.35–S.36, Notis S.47 & Kompaun S.48 Akta 852"
        if "281" in low or "ppkm" in low or "ppm" in low:
            return "Kuasa Pemeriksaan & Sitaan S.4, Penutupan Premis S.11, Notis S.32B & Kompaun S.33 Akta Makanan 1983 [Akta 281]"
        if "154" in low:
            return "Kuasa Pemeriksaan S.3/S.5, Perintah Pembersihan/Penutupan S.8(1), Bantuan Polis S.24 & Kompaun S.25 Akta 154"
        if "342" in low or "apppb" in low:
            return "Kuasa Pemeriksaan S.14/S.15(1), Penutupan & Disinfeksi S.18(1)(d)&(f), serta Kompaun S.25 (Pindaan Akta A1742)"
        return f"Kuasa pemeriksaan & penguatkuasaan di bawah {akta_code or 'Akta Kesihatan Awam KKM'}"

    @classmethod
    def _enrich_two_branch_structure(
        cls,
        result: Dict[str, Any],
        question: str,
        *,
        is_fallback: bool = False,
    ) -> Dict[str, Any]:
        """Memastikan setiap respons Tanya Pakar UIP dikelaskan tegas kepada TIADA_KESALAHAN atau ADA_KESALAHAN."""
        q_low = (question or "").lower()
        sc_id = str(result.get("scenario_id") or "")
        akta_code = str(result.get("akta_disyorkan") or "Akta KKM")
        keputusan_up = str(result.get("keputusan_tindakan") or "").upper()
        explicit_status = str(result.get("status_kesalahan") or "").strip().upper()
        elem_evals = result.get("element_evaluations") or []
        any_blocked = any(
            isinstance(ev, dict) and bool(ev.get("action_blocked")) for ev in elem_evals
        )

        if explicit_status in ("TIADA_KESALAHAN", "ADA_KESALAHAN"):
            status_kesalahan = explicit_status
        elif (
            sc_id in cls._NO_OFFENCE_SCENARIO_IDS
            or any_blocked
            or any(
                k in keputusan_up
                for k in (
                    "TIADA KESALAHAN",
                    "BUKAN KESALAHAN",
                    "DITOLAK / TIADA TINDAKAN",
                    "TIDAK BOLEH KOMPAUN SERTA-MERTA",
                    "AKTA BELUM DIINDEKS",
                )
            )
        ):
            status_kesalahan = "TIADA_KESALAHAN"
        else:
            status_kesalahan = "ADA_KESALAHAN"

        result["status_kesalahan"] = status_kesalahan
        result["is_fallback_response"] = bool(
            is_fallback or sc_id in ("rag_custom_query", "unindexed_statute_guard")
        )

        # Ringkasan keputusan 1-2 baris yang tegas & bahasa kerja PPKP
        if not str(result.get("ringkasan_keputusan") or "").strip():
            raw_kep = str(result.get("keputusan_tindakan") or "").strip()
            result["ringkasan_keputusan"] = raw_kep

        if status_kesalahan == "TIADA_KESALAHAN":
            # Pastikan sebab & langkah susulan sentiasa lengkap
            if not str(result.get("sebab_tidak_menyalahi") or "").strip():
                result["sebab_tidak_menyalahi"] = str(result.get("alasan_keputusan") or "").strip()
            if not result.get("langkah_susulan_ppkp"):
                result["langkah_susulan_ppkp"] = list(result.get("sop_lapangan") or [])
            result["punca_kuasa"] = None
        else:
            # Cabang B (ADA_KESALAHAN): bina objek Punca Kuasa yang jelas di bahagian atas
            charges = result.get("cadangan_pertuduhan") or []
            primary = charges[0] if charges and isinstance(charges[0], dict) else {}
            comp_txt = str(primary.get("boleh_kompaun") or "").strip()
            comp_low = comp_txt.lower()
            is_comp_flag = bool(
                comp_txt
                and (
                    "boleh kompaun" in comp_low
                    or "boleh dikompaun" in comp_low
                    or "kompaun rm" in comp_low
                )
            ) and not any(
                neg in comp_low
                for neg in ("tidak boleh kompaun", "tidak boleh dikompaun", "tiada kompaun", "tidak disyorkan kompaun")
            )
            has_obd_minor = any(
                k in f"{q_low} {akta_code.lower()} {str(primary.get('seksyen_kesalahan') or '').lower()} {str(result.get('tajuk_nasihat') or '').lower()}"
                for k in ("pelajar", "budak", "murid", "obd", "bawah 18", "bawah umur", "sekolah", "17(1)", "13(3)", "kanak-kanak", "taska", "tadika")
            )
            peringatan_611 = (
                "Peringatan Akta Kanak-Kanak 2001 [Akta 611]: Kes ini melibatkan kanak-kanak / pelajar bawah 18 tahun (OBD). "
                "Wajib maklumkan ibu bapa atau penjaga, lindungi identiti/privasi kanak-kanak (Seksyen 15 Akta 611), "
                "dan patuhi tatacara Mahkamah Bagi Kanak-Kanak (Seksyen 83 Akta 611) sekiranya kes dirujuk ke mahkamah."
                if has_obd_minor
                else None
            )
            result["punca_kuasa"] = {
                "akta": akta_code,
                "seksyen_kesalahan": str(primary.get("seksyen_kesalahan") or akta_code),
                "seksyen_hukuman": str(primary.get("seksyen_hukuman") or "-"),
                "had_hukuman": str(primary.get("hukuman_maksimum") or "-"),
                "status_kompaun": comp_txt or ("Boleh Kompaun" if is_comp_flag else "Terus Mahkamah (Buka IP)"),
                "boleh_kompaun_flag": is_comp_flag,
                "kuasa_penguatkuasaan": cls._enforcement_power_for_act(akta_code),
                "peringatan_akta_611": peringatan_611,
            }
            result.setdefault("sebab_tidak_menyalahi", "")
            result.setdefault("langkah_susulan_ppkp", [])

        return result

    @classmethod
    def _build_rag_fallback_scenario(
        cls,
        question: str,
        akta_hint: str,
        rag_hits: List[Any],
        offence_doc_ids: Optional[set[str]] = None,
    ) -> Dict[str, Any]:
        """Templat rujukan berasaskan RAG statutori apabila soalan di luar templat teras (sekat Seksyen 2 — Tafsiran)."""
        # Tapis keluar Seksyen 1 / Seksyen 2 (Tafsiran/Tajuk Ringkas) & seksyen bukan kesalahan daripada dicalonkan sebagai caj
        def _is_def_chunk(chunk: Any) -> bool:
            sec_low = str(getattr(chunk, "section", "") or "").lower()
            if any(m in sec_low for m in ("tafsiran", "tajuk ringkas", "permulaan kuat kuasa", "interpretation", "short title")):
                return True
            if re.match(r"^(?:seksyen|section)\s+[12]\b", sec_low):
                cid = str(getattr(chunk, "chunk_id", "") or "")
                if offence_doc_ids is not None and cid not in offence_doc_ids:
                    return True
            return False

        clean_hits = [c for c in rag_hits if not _is_def_chunk(c)]
        offence_hits = (
            [c for c in clean_hits if str(getattr(c, "chunk_id", "") or "") in offence_doc_ids]
            if offence_doc_ids
            else clean_hits
        )
        charge_hits = offence_hits[:2]
        top_hit = (charge_hits[0] if charge_hits else (clean_hits[0] if clean_hits else None))

        akta_label = (
            akta_hint
            if akta_hint and akta_hint != "Semua"
            else (top_hit.akta_code if top_hit else "Akta Kesihatan Awam KKM")
        )
        citations_summary = ", ".join(
            dict.fromkeys(cls._format_section_label(c.section, c.akta_code) for c in (charge_hits or clean_hits[:2]))
        ) or "Pustaka Akta KKM"

        charges_list = [
            {
                "perihal": f"Peruntukan berkaitan di bawah {c.akta_code}",
                "seksyen_kesalahan": cls._format_section_label(c.section, c.akta_code),
                "seksyen_hukuman": "Semak peruntukan hukuman dalam Teks Asal Akta di bawah.",
                "hukuman_maksimum": c.max_fine_hint or "Tertakluk had hukuman di bawah Akta berkaitan.",
                "boleh_kompaun": c.is_compoundable_hint or "Semak jadual kompaun akta / rujuk Pegawai Pendakwa & UIP JKN.",
            }
            for c in charge_hits
        ]

        return {
            "id": "rag_custom_query",
            "akta_utama": akta_label,
            "tajuk": f"Keputusan & Panduan Tindakan ({akta_label})",
            "ringkasan_keputusan": (
                f"Semak peruntukan berkaitan ({citations_summary}) dan sahkan fakta serta kuasa di lokasi sebelum mengeluarkan notis atau membuka IP."
            ),
            "keputusan_tindakan": (
                f"Semak peruntukan berkaitan ({citations_summary}) — sahkan fakta dan kuasa sebelum keluarkan notis atau buka IP."
            ),
            "sesuai_buka_ip": False,
            "alasan_keputusan": (
                f"Berdasarkan soalan anda, rujukan terdekat dalam Pustaka Akta ialah {citations_summary}. "
                "Sila semak teks asal akta di bawah atau tekan Analisa AI untuk panduan kes khusus."
            ),
            "cadangan_pertuduhan": charges_list,
            "sop_lapangan": [
                "Tunjukkan Kad Kuasa Rasmi KKM sebelum memulakan pemeriksaan atau siasatan di lokasi.",
                "Sahkan identiti pihak terlibat (MyKad individu / carian rasmi SSM jika syarikat) dan bidang kuasa akta terpakai.",
                "Rakam gambar bertarikh + Sijil S.90A(2), catat Diari Siasatan, dan semak Teks Asal Akta sebelum mengambil tindakan kompaun atau membuka IP.",
            ],
            "eksibit_wajib": [
                "Diari Siasatan (DS) & Percakapan S.112 KTJ pegawai pengesan / saksi",
                "Gambar foto lokasi/kejadian berwarna bertarikh + Sijil Seksyen 90A(2) Akta Keterangan 1950",
                "Salinan Notis / Perintah bertulis bertandatangan terima (jika tindakan melibatkan pematuhan perintah)",
            ],
            "perangkap_kesilapan": [
                "Pastikan akta dan seksyen yang dipilih benar-benar merupakan peruntukan kesalahan yang sepadan dengan fakta lapangan.",
            ],
            "templat_ringkas": (
                f"Rujukan siasatan awal di bawah {akta_label} berkaitan situasi: {question.strip()[:220]}."
            ),
            "is_fallback_response": True,
        }

    @classmethod
    def _match_composite_scenarios(
        cls,
        question: str,
        akta_hint: str = "Semua",
        scenario_id: Optional[str] = None,
    ) -> tuple[Dict[str, Any], float, bool]:
        if scenario_id:
            for s in UIP_SCENARIO_LIBRARY:
                if s["id"] == scenario_id:
                    return s, 10.0, True

        q_low = question.lower()
        scored: List[tuple[float, float, int, List[str], Dict[str, Any]]] = []
        for s in UIP_SCENARIO_LIBRARY:
            total, kw_score, neg_hits, matched_kws = cls._score_scenario(s, q_low, akta_hint=akta_hint)
            scored.append((total, kw_score, neg_hits, matched_kws, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        primary_total, primary_kw, primary_neg, primary_kws, primary = scored[0]
        if primary_kw < cls.MIN_SCENARIO_SCORE:
            return primary, max(0.0, primary_kw), False

        # Gabung secara automatik hanya jika kesalahan kedua sah, serasi & berbeza kata kunci
        merged = dict(primary)
        if len(scored) > 1:
            sec_total, sec_kw, sec_neg, sec_kws, secondary = scored[1]
            incompatible = set(primary.get("incompatible_with", [])) | set(secondary.get("incompatible_with", []))
            distinct_sec_kws = [k for k in sec_kws if k not in set(primary_kws)]
            if (
                secondary["id"] != primary["id"]
                and secondary["id"] not in incompatible
                and primary["id"] not in incompatible
                and sec_neg == 0
                and sec_kw >= 3.2
                and primary_kw >= 2.4
                and len(distinct_sec_kws) >= 1
            ):
                def _dedup(items: List[str]) -> List[str]:
                    seen = set()
                    out = []
                    for it in items:
                        if it not in seen:
                            seen.add(it)
                            out.append(it)
                    return out

                merged = {
                    "id": f"{primary['id']}+{secondary['id']}",
                    "akta_utama": primary["akta_utama"],
                    "tajuk": f"{primary['tajuk']} + {secondary['tajuk']}",
                    "keputusan_tindakan": f"{primary['keputusan_tindakan']} | DAN {secondary['keputusan_tindakan']}",
                    "sesuai_buka_ip": bool(primary["sesuai_buka_ip"] or secondary["sesuai_buka_ip"]),
                    "alasan_keputusan": (
                        f"Kes gabungan dikesan di lapangan:\n"
                        f"(1) {primary['alasan_keputusan']}\n"
                        f"(2) {secondary['alasan_keputusan']} "
                        f"PENTING: Asingkan setiap kesalahan ke dalam Borang 114 / Notis berlainan (S.163 KTJ)."
                    ),
                    "cadangan_pertuduhan": list(primary["cadangan_pertuduhan"]) + list(secondary["cadangan_pertuduhan"]),
                    "sop_lapangan": _dedup(list(primary["sop_lapangan"]) + list(secondary["sop_lapangan"])),
                    "eksibit_wajib": _dedup(list(primary["eksibit_wajib"]) + list(secondary["eksibit_wajib"])),
                    "perangkap_kesilapan": _dedup(list(primary["perangkap_kesilapan"]) + list(secondary["perangkap_kesilapan"])),
                    "templat_ringkas": f"{primary['templat_ringkas']} Selain itu, {secondary['templat_ringkas']}",
                }

        return merged, primary_kw, True

    @staticmethod
    def _build_prefilled_case_template(
        scenario: Dict[str, Any],
        officer_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        io_name = "[Sila isi Nama Pegawai Penyiasat (IO)]"
        kad_kuasa = "[No. Kad Kuasa]"
        daerah = "[Sila isi Daerah, Negeri]"
        if officer_profile:
            io_name = officer_profile.get("full_name") or io_name
            kad_kuasa = officer_profile.get("kkm_authority_card_no") or kad_kuasa
            pkd = officer_profile.get("district_pkd") or ""
            jkn = officer_profile.get("state_jkn") or ""
            if pkd or jkn:
                daerah = f"{pkd.replace('Pejabat Kesihatan Daerah ', '')}, {jkn.replace('Jabatan Kesihatan Negeri ', '')}".strip(", ")

        return (
            f"KERTAS SIASATAN UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)\n"
            f"NO. IP: PKD/UIP/2026/[Sila isi No. Siri]\n"
            f"DAERAH: {daerah}\n"
            f"AKTA: {scenario['akta_utama']}\n\n"
            f"1. BUTIRAN PEMERIKSAAN\n"
            f"Tarikh Kejadian: [Tarikh kejadian]\n"
            f"Masa Kejadian: [Masa kejadian]\n"
            f"Nama Premis: [Nama Premis / Lokasi]\n"
            f"No. SSM: [No. Daftar SSM jika syarikat / - jika individu]\n"
            f"Alamat Kejadian: [Alamat penuh kejadian]\n"
            f"Nama Suspek (OKT): [Nama Penuh OKS ikut MyKad]\n"
            f"No. K/P: [XXXXXX-XX-XXXX]\n"
            f"Pegawai Penyiasat (IO): {io_name} (No. Kad Kuasa: {kad_kuasa})\n\n"
            f"2. RINGKASAN KESALAHAN\n"
            f"{scenario['templat_ringkas']}\n"
        )

    @staticmethod
    def _normalize_charge_items(
        raw_items: Any,
        fallback_items: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        if not isinstance(raw_items, list) or not raw_items:
            return fallback_items
        normalized: List[Dict[str, str]] = []
        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            base = fallback_items[idx] if idx < len(fallback_items) else (fallback_items[0] if fallback_items else {})
            normalized.append(
                {
                    "perihal": str(item.get("perihal") or item.get("kesalahan") or base.get("perihal") or "Kesalahan Statutori"),
                    "seksyen_kesalahan": str(item.get("seksyen_kesalahan") or item.get("seksyen") or base.get("seksyen_kesalahan") or "-"),
                    "seksyen_hukuman": str(item.get("seksyen_hukuman") or item.get("hukuman") or base.get("seksyen_hukuman") or "-"),
                    "hukuman_maksimum": str(item.get("hukuman_maksimum") or base.get("hukuman_maksimum") or "-"),
                    "boleh_kompaun": str(item.get("boleh_kompaun") or item.get("kompaun") or base.get("boleh_kompaun") or "-"),
                }
            )
        return normalized or fallback_items

    def consult(
        self,
        question: str,
        akta_hint: str = "Semua",
        scenario_id: Optional[str] = None,
        use_ai: bool = False,
        officer_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from backend.rag.legal_engine import (
            canonical_akta_code_for_statute,
            evaluate_offence_elements_against_facts,
            get_legal_library,
            is_non_offence_or_definition_section,
            is_passive_vape_possession_question,
            validate_legal_output,
        )

        legal_lib = get_legal_library()
        lib_snapshot = legal_lib.to_snapshot_dict()

        # FASA 3.1: Carian Hibrid Wajib Sebelum Menjawab (Mandatory Closed-Book Grounding)
        grounding = legal_lib.search_closed_book_grounding(
            question=question,
            akta_hint=akta_hint,
            top_k=4,
        )

        # FASA 5.2: Jika akta belum dimuat naik PDF rasminya (total_sections_indexed == 0), enggan meneka!
        if grounding.get("unindexed_statute"):
            unidx = grounding["unindexed_statute"]
            sid = unidx["statute_id"]
            unidx_msg = (
                f"AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA: Peruntukan bagi {sid} ({unidx.get('official_title_bm', '')}) "
                "belum dimuat naik PDF Warta Kerajaan Rasmi ke dalam Pustaka Akta. "
                "Sistem enggan meneka nombor seksyen atau had denda tanpa teks asal Warta."
            )
            res_unidx: Dict[str, Any] = {
                "scenario_id": "unindexed_statute_guard",
                "status_kesalahan": "TIADA_KESALAHAN",
                "akta_disyorkan": unidx.get("canonical_akta_code") or sid,
                "tajuk_nasihat": f"AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA ({sid})",
                "ringkasan_keputusan": f"Fail PDF Warta rasmi bagi {sid} belum dimuat naik. Muat naik PDF Warta dahulu sebelum mengeluarkan notis atau pertuduhan.",
                "keputusan_tindakan": "AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA",
                "sesuai_buka_ip": False,
                "alasan_keputusan": unidx_msg,
                "sebab_tidak_menyalahi": unidx_msg,
                "langkah_susulan_ppkp": [
                    f"Muat naik fail PDF Warta Kerajaan Rasmi ({sid}.pdf) daripada lom.agc.gov.my melalui tab Admin Warta.",
                    "Semak teks seksyen dan sahkan Warta sebelum menggunakan rujukan akta ini.",
                ],
                "cadangan_pertuduhan": [],
                "sop_lapangan": [
                    f"Muat naik fail PDF Warta Kerajaan Rasmi ({sid}.pdf) daripada lom.agc.gov.my melalui tab Admin Warta.",
                    "Semak teks seksyen dan sahkan Warta sebelum menggunakan rujukan akta ini.",
                ],
                "eksibit_wajib": [],
                "perangkap_kesilapan": [unidx_msg],
                "templat_ringkas": unidx_msg,
                "draf_teks_kes_cadangan": "",
                "engine_used": "Pustaka Akta KKM",
                "ai_attempted": False,
                "ai_succeeded": False,
                "fallback_reason": None,
                "from_qa_collection": False,
                "matched_collection_id": None,
                "matched_collection_question": None,
                "matched_collection_similarity": None,
                "matched_collection_ask_count": None,
                "statute_library_version": legal_lib.statute_library_version,
                "cache_status": "ACTIVE",
                "unindexed_statute": True,
                "element_evaluations": [],
                "repealed_warnings": grounding.get("repealed_matches") or [],
                "statutory_citations": [],
            }
            self._enrich_two_branch_structure(res_unidx, question, is_fallback=True)
            res_unidx["legal_validation"] = validate_legal_output(
                res_unidx, lib_snapshot, question_context=f"{question} {akta_hint}"
            )
            return res_unidx

        # CABANG A (TIADA_KESALAHAN): Pemilikan pasif vape/rokok dalam beg/checking bag oleh pelajar tanpa bukti menghisap/menggunakan/membeli
        s17_offence = next(
            (o for o in legal_lib.master_offences_matrix if o["offence_id"] == "AKTA_852_S17_1"),
            None,
        )
        if s17_offence and is_passive_vape_possession_question(question):
            s17_eval = evaluate_offence_elements_against_facts(question, s17_offence)
            if s17_eval["action_blocked"]:
                s17_verbatim = [
                    {
                        "chunk_id": s["doc_id"],
                        "doc_id": s["doc_id"],
                        "statute_id": s["statute_id"],
                        "akta_code": "Akta 852",
                        "akta_title": "Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
                        "section": f"Seksyen {s['section_code']} - {s['section_heading']}",
                        "text": s["verbatim_text_bm"],
                        "score": 0.99,
                        "verbatim": True,
                    }
                    for s in legal_lib.statute_sections_verbatim
                    if s["doc_id"] in ("AKTA_852__S17", "AKTA_852__S13")
                ]
                sebab_txt = (
                    "Seksyen 17(1) Akta 852 hanya terpakai bagi perbuatan 'merokok, mengunyah atau menggunakan' produk tembakau "
                    "atau produk pengganti tembakau (termasuk vape) oleh Orang Belum Dewasa (bawah 18 tahun), manakala Seksyen 13(3) "
                    "hanya terpakai jika terbukti perbuatan 'membeli'. Unsur perbuatan menghisap/menggunakan TIDAK TERPENUHI dalam kes ini — "
                    "pemilikan vape dalam beg semata-mata telah digugurkan selepas PPKHT 2004 (Peraturan 13(1)) dimansuhkan."
                )
                langkah_susulan = [
                    "Tindakan Pentadbiran Sekolah: Serahkan urusan rampasan vape dan tindakan tatatertib dalam kawasan sekolah kepada pihak pentadbiran sekolah di bawah peraturan disiplin Kementerian Pendidikan Malaysia (KPM) berserta pemakluman kepada ibu bapa/penjaga.",
                    "Syarat Buka Siasatan Seksyen 17(1) Akta 852: Hanya boleh keluarkan Notis S.47 / kompaun S.48 terhadap pelajar jika ada saksi mata (guru/pengawas) atau rakaman CCTV yang jelas membuktikan pelajar sedang menghisap, mengunyah atau menggunakan vape tersebut.",
                    "Syarat Buka Siasatan Seksyen 13(1) & Seksyen 13(3) Akta 852: Dapatkan maklumat secara berhemah daripada pelajar mengenai premis/kedai yang menjual vape itu. Jika terdapat bukti jualan (resit, keterangan atau operasi pemantauan kedai), siasat penjual di bawah Seksyen 13(1) (dan pembelian OBD di bawah Seksyen 13(3) jika transaksi belian terbukti).",
                ]
                trap_res: Dict[str, Any] = {
                    "scenario_id": "ak852_s17_unsur_tidak_terpenuhi",
                    "status_kesalahan": "TIADA_KESALAHAN",
                    "akta_disyorkan": "Akta 852",
                    "tajuk_nasihat": "TIADA KESALAHAN DI BAWAH AKTA 852",
                    "ringkasan_keputusan": "Jangan keluarkan Notis S.47 atau kompaun atas pemilikan vape dalam beg semata-mata.",
                    "keputusan_tindakan": (
                        "TIADA KESALAHAN DI BAWAH AKTA 852 — Pemilikan dalam beg bukan kesalahan Seksyen 17(1) "
                        "(Unsur mandatori tidak terpenuhi; jangan keluarkan Notis S.47 atau kompaun)"
                    ),
                    "sesuai_buka_ip": False,
                    "alasan_keputusan": sebab_txt,
                    "sebab_tidak_menyalahi": sebab_txt,
                    "langkah_susulan_ppkp": langkah_susulan,
                    "cadangan_pertuduhan": [],
                    "sop_lapangan": langkah_susulan,
                    "eksibit_wajib": [
                        "Tiada barang kes pertuduhan S.17(1) terhadap pelajar — rekodkan maklumat risikan kedai penjual sahaja jika mahu menyiasat di bawah Seksyen 13(1) Akta 852.",
                    ],
                    "perangkap_kesilapan": [
                        "JANGAN guna Peraturan 13(1) PPKHT 2004 (telah dimansuhkan oleh Akta 852).",
                        "JANGAN keluarkan Notis S.47 atau kompaun S.17(1) atas pemilikan dalam beg semata-mata tanpa bukti menghisap, mengunyah, menggunakan atau membeli.",
                    ],
                    "templat_ringkas": (
                        "Semakan Akta 852: Pemilikan vape dalam beg pelajar tanpa bukti menghisap, mengunyah, menggunakan (S.17(1)) "
                        "atau membeli (S.13(3)) bukan suatu kesalahan di bawah Akta 852. Tiada Notis S.47 atau kompaun dikeluarkan kepada pelajar."
                    ),
                    "engine_used": "Rujukan Akta KKM",
                    "ai_attempted": False,
                    "ai_succeeded": False,
                    "fallback_reason": None,
                    "from_qa_collection": False,
                    "matched_collection_id": None,
                    "matched_collection_question": None,
                    "matched_collection_similarity": None,
                    "matched_collection_ask_count": None,
                    "statute_library_version": legal_lib.statute_library_version,
                    "cache_status": "ACTIVE",
                    "element_evaluations": [s17_eval],
                    "repealed_warnings": grounding.get("repealed_matches") or [],
                    "statutory_citations": s17_verbatim,
                }
                trap_res["draf_teks_kes_cadangan"] = ""
                self._enrich_two_branch_structure(trap_res, question, is_fallback=False)
                trap_res["legal_validation"] = validate_legal_output(
                    trap_res, lib_snapshot, question_context=question
                )
                return trap_res

        verbatim_by_doc_id: Dict[str, Dict[str, Any]] = {
            s["doc_id"]: s for s in legal_lib.statute_sections_verbatim
        }
        offence_doc_ids: set[str] = {
            s["doc_id"] for s in legal_lib.statute_sections_verbatim if s.get("is_offence_provision")
        }

        # 0. Semak Koleksi Soalan & Jawapan Pakar dahulu apabila pengguna tidak memaksa Analisa AI segar
        if (
            not use_ai
            and not scenario_id
            and self.db is not None
            and len((question or "").strip()) >= 8
        ):
            try:
                matched_qa = self.db.find_similar_answered_question(
                    question=question,
                    akta_hint=akta_hint,
                )
            except Exception as exc:
                logger.warning("Carian Koleksi Q&A Pakar gagal (non-fatal): %s", exc)
                matched_qa = None

            if matched_qa and isinstance(matched_qa.get("answer"), dict):
                ans = dict(matched_qa["answer"])
                # Tolak cache rosak (fallback / Seksyen 2 Tafsiran)
                ans_dump_low = str(ans.get("cadangan_pertuduhan") or "").lower()
                if (
                    ans.get("scenario_id") not in ("rag_custom_query", "unindexed_statute_guard")
                    and "seksyen 2" not in ans_dump_low
                    and "tafsiran" not in ans_dump_low
                ):
                    self._enrich_two_branch_structure(ans, question, is_fallback=False)
                    # Sahkan jawapan cache menggunakan validate_legal_output sebelum dipetik semula
                    val_check = validate_legal_output(ans, lib_snapshot, question_context=question)
                    if val_check["passed"]:
                        # Pulihkan teks verbatim 100% aksara-demi-aksara daripada statute_sections_verbatim
                        restored_cits: List[Dict[str, Any]] = []
                        for c_item in ans.get("statutory_citations") or []:
                            if not isinstance(c_item, dict):
                                continue
                            did = str(c_item.get("doc_id") or c_item.get("chunk_id") or "")
                            if did in verbatim_by_doc_id:
                                s_v = verbatim_by_doc_id[did]
                                restored_cits.append(
                                    {
                                        **c_item,
                                        "chunk_id": s_v["doc_id"],
                                        "doc_id": s_v["doc_id"],
                                        "statute_id": s_v["statute_id"],
                                        "text": s_v["verbatim_text_bm"],
                                        "verbatim": True,
                                    }
                                )
                        if not restored_cits:
                            restored_cits = [
                                {
                                    "chunk_id": vh["doc_id"],
                                    "doc_id": vh["doc_id"],
                                    "statute_id": vh["statute_id"],
                                    "akta_code": vh["akta_code"],
                                    "akta_title": vh["akta_code"],
                                    "section": f"{vh['section_code']} - {vh['section_heading']}",
                                    "text": vh["verbatim_text_bm"],
                                    "score": vh["score"],
                                    "verbatim": True,
                                }
                                for vh in (grounding.get("verbatim_sections") or [])
                            ]
                        ans["statutory_citations"] = restored_cits
                        resolved_act = str(
                            ans.get("akta_disyorkan") or matched_qa.get("akta_group") or "Akta 852"
                        )
                        ans["akta_disyorkan"] = resolved_act
                        ans["draf_teks_kes_cadangan"] = self._build_prefilled_case_template(
                            {
                                "akta_utama": resolved_act,
                                "templat_ringkas": str(
                                    ans.get("templat_ringkas") or ans.get("keputusan_tindakan") or ""
                                ),
                            },
                            officer_profile=officer_profile,
                        )
                        sim_pct = int(matched_qa.get("similarity_percent") or 100)
                        src_label = (
                            "AI Terdahulu" if matched_qa.get("is_ai_answered") else "Rujukan UIP"
                        )
                        ans["engine_used"] = f"Koleksi Q&A Pakar ({src_label} · Padanan {sim_pct}%)"
                        ans["ai_attempted"] = False
                        ans["ai_succeeded"] = bool(matched_qa.get("is_ai_answered"))
                        ans["fallback_reason"] = None
                        ans["from_qa_collection"] = True
                        ans["matched_collection_id"] = matched_qa.get("id")
                        ans["matched_collection_question"] = matched_qa.get("question")
                        ans["matched_collection_similarity"] = sim_pct
                        ans["matched_collection_ask_count"] = int(matched_qa.get("ask_count") or 1)
                        ans["statute_library_version"] = legal_lib.statute_library_version
                        ans["cache_status"] = "ACTIVE"
                        ans["legal_validation"] = val_check
                        return ans

        matched, kw_score, confident_match = self._match_composite_scenarios(
            question, akta_hint=akta_hint, scenario_id=scenario_id
        )
        rag_query = (
            f"{question} {matched['akta_utama']} {matched['tajuk']}"
            if confident_match
            else question
        )
        effective_rag_akta = (
            None
            if akta_hint in ("", "Semua")
            else akta_hint
        )
        if not effective_rag_akta and confident_match and matched.get("akta_utama", "").startswith("Akta "):
            effective_rag_akta = matched["akta_utama"]

        rag_hits = self.router.rag_store.search_statutes(
            query=rag_query,
            akta_filter=effective_rag_akta,
            top_k=5,
        )
        if not confident_match:
            matched = self._build_rag_fallback_scenario(
                question, akta_hint, rag_hits, offence_doc_ids=offence_doc_ids
            )

        # Pastikan pautan wajib Akta Induk <-> Akta Pindaan (AMENDMENT_COMPANIONS) sentiasa aktif apabila Akta 342 / Akta 281 disyorkan
        matched_akta_code = str(matched.get("akta_utama") or "")
        applied_companions = list(grounding.get("amendment_companions_applied") or [])
        if (
            ("342" in matched_akta_code and "AKTA_342_PINDAAN_2025" not in applied_companions)
            or ("281" in matched_akta_code and "AKTA_281_PINDAAN_2024" not in applied_companions)
        ):
            grounding = legal_lib.search_closed_book_grounding(
                question=question,
                akta_hint=matched_akta_code,
                top_k=4,
            )

        # FASA 3.4 & 5.3: Pastikan `statutory_citations` memaparkan `verbatim_text_bm` 100% aksara-demi-aksara tanpa Seksyen 2 Tafsiran
        q_low_cit = (question or "").lower()
        asks_def_cit = any(
            k in q_low_cit for k in ("tafsiran", "definisi", "maksud ", "seksyen 2", "sek. 2", "s.2 ")
        )
        verbatim_by_text: Dict[str, Dict[str, Any]] = {
            s["verbatim_text_bm"]: s for s in legal_lib.statute_sections_verbatim
        }
        citations_dict: List[Dict[str, Any]] = []
        seen_cit_texts: set[str] = set()

        for vh in grounding.get("verbatim_sections") or []:
            v_txt = vh["verbatim_text_bm"]
            allow_pu257_scope = vh.get("doc_id") in (
                "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA",
                "AKTA_852_PERINTAH_LARANGAN_2024__P2",
            )
            if not asks_def_cit and not allow_pu257_scope and is_non_offence_or_definition_section(vh):
                continue
            if v_txt not in seen_cit_texts:
                seen_cit_texts.add(v_txt)
                citations_dict.append(
                    {
                        "chunk_id": vh["doc_id"],
                        "doc_id": vh["doc_id"],
                        "statute_id": vh["statute_id"],
                        "akta_code": vh["akta_code"],
                        "akta_title": vh["akta_code"],
                        "section": f"Seksyen {vh['section_code']} - {vh['section_heading']}"
                        if not str(vh["section_code"]).lower().startswith(("seksyen", "peraturan", "jadual"))
                        else f"{vh['section_code']} - {vh['section_heading']}",
                        "text": v_txt,
                        "score": vh["score"],
                        "verbatim": True,
                    }
                )

        for c in rag_hits:
            if c.text in verbatim_by_text and c.text not in seen_cit_texts:
                s_obj = verbatim_by_text[c.text]
                if not asks_def_cit and is_non_offence_or_definition_section(s_obj):
                    continue
                seen_cit_texts.add(c.text)
                citations_dict.append(
                    {
                        "chunk_id": s_obj["doc_id"],
                        "doc_id": s_obj["doc_id"],
                        "statute_id": s_obj["statute_id"],
                        "akta_code": c.akta_code,
                        "akta_title": c.akta_title,
                        "section": c.section,
                        "text": s_obj["verbatim_text_bm"],
                        "score": c.score,
                        "verbatim": True,
                    }
                )

        if not citations_dict and legal_lib.statute_sections_verbatim:
            # Cari seksyen kesalahan sebenar dari Akta yang sepadan — JANGAN sekali-kali jatuh ke Seksyen 1 / Seksyen 2 Tafsiran!
            fallback_sec = next(
                (
                    s
                    for s in legal_lib.statute_sections_verbatim
                    if s.get("is_offence_provision")
                    and not is_non_offence_or_definition_section(s)
                    and (
                        not matched_akta_code
                        or matched_akta_code.lower() in canonical_akta_code_for_statute(s["statute_id"]).lower()
                    )
                ),
                None,
            ) or next(
                (
                    s
                    for s in legal_lib.statute_sections_verbatim
                    if s.get("is_offence_provision") and not is_non_offence_or_definition_section(s)
                ),
                None,
            )
            if fallback_sec:
                fb_act = canonical_akta_code_for_statute(fallback_sec["statute_id"])
                citations_dict.append(
                    {
                        "chunk_id": fallback_sec["doc_id"],
                        "doc_id": fallback_sec["doc_id"],
                        "statute_id": fallback_sec["statute_id"],
                        "akta_code": fb_act,
                        "akta_title": fb_act,
                        "section": f"Seksyen {fallback_sec['section_code']} - {fallback_sec['section_heading']}"
                        if not str(fallback_sec["section_code"]).lower().startswith(("seksyen", "peraturan", "jadual"))
                        else f"{fallback_sec['section_code']} - {fallback_sec['section_heading']}",
                        "text": fallback_sec["verbatim_text_bm"],
                        "score": 0.85,
                        "verbatim": True,
                    }
                )

        element_evals = [
            off["element_evaluation"]
            for off in (grounding.get("candidate_offences") or [])
            if isinstance(off.get("element_evaluation"), dict)
        ]

        # Jika soalan menyebut undang-undang yang telah dimansuhkan (cth. PPKHT 2004 / Ordinan Darurat 2021), masukkan amaran jelas
        repealed_warnings = grounding.get("repealed_matches") or []
        perangkap_merged = list(matched.get("perangkap_kesilapan") or [])
        for rw in repealed_warnings:
            msg = f"{rw['warning_message_bm']} ({rw['key_differences_note']})"
            if msg not in perangkap_merged:
                perangkap_merged.insert(0, msg)

        # Mulakan dengan matriks SOP pakar tempatan / rujukan RAG (< 15ms)
        result: Dict[str, Any] = {
            "scenario_id": matched["id"],
            "akta_disyorkan": matched["akta_utama"],
            "tajuk_nasihat": matched["tajuk"],
            "ringkasan_keputusan": matched.get("ringkasan_keputusan") or matched["keputusan_tindakan"],
            "keputusan_tindakan": matched["keputusan_tindakan"],
            "sesuai_buka_ip": matched["sesuai_buka_ip"],
            "alasan_keputusan": matched["alasan_keputusan"],
            "cadangan_pertuduhan": matched["cadangan_pertuduhan"],
            "sop_lapangan": matched["sop_lapangan"],
            "eksibit_wajib": matched["eksibit_wajib"],
            "perangkap_kesilapan": perangkap_merged,
            "templat_ringkas": matched["templat_ringkas"],
            "engine_used": "Rujukan Pantas UIP" if confident_match else "Carian Akta UIP",
            "ai_attempted": False,
            "ai_succeeded": False,
            "fallback_reason": None,
            "from_qa_collection": False,
            "matched_collection_id": None,
            "matched_collection_question": None,
            "matched_collection_similarity": None,
            "matched_collection_ask_count": None,
            "statute_library_version": legal_lib.statute_library_version,
            "cache_status": "ACTIVE",
            "element_evaluations": element_evals,
            "repealed_warnings": repealed_warnings,
            "amendment_companions_applied": grounding.get("amendment_companions_applied") or [],
            "is_fallback_response": bool(matched.get("is_fallback_response", False)),
        }

        effective_question = question.strip()
        if not effective_question or effective_question.lower().startswith("rujuk templat situasi ini"):
            effective_question = matched["tajuk"]

        ai_requested = bool(use_ai)
        # Kesan soalan bernuansa (mengandungi alasan/pembelaan, pengecualian, syarat sempadan atau perbandingan pihak)
        # supaya 'Semak Kes Ini' juga menggunakan penaakulan AI (bukan melambak templat kaku yang menjawab soalan lain!)
        q_nuance_low = effective_question.lower()
        is_nuanced_question = (not scenario_id) and (
            any(
                m in q_nuance_low
                for m in (
                    "atas alasan", "alasan ", "alasan:", "mendakwa", "dakwa ", "tuan tanah",
                    "pihak universiti", "pihak pengurusan", "tanggungjawab siapa", "siapa yang salah",
                    "baru pindah", "dah pasang", "sudah pasang", "juruwang", "tidak pegang makanan",
                    "open car park", "open air", "tempat letak kereta awam terbuka", "parkir terbuka",
                    "luar bangunan", "luar 3 meter", "kabinet bertutup", "kabinet legap", "opaque",
                    "menyental", "berkunci mangga", "outstation", "bersiar-siar",
                )
            )
            or (
                bool(re.search(r"\b(?:tetapi|tapi|namun|walaupun|kecuali|melainkan)\b", q_nuance_low))
                and len(effective_question.split()) >= 14
            )
        )
        # Kekalkan laluan pantas tempatan bagi senario tersuai yang memang dibina tepat untuk kes sempadan tersebut
        fast_handled_nuance_ids = {
            "ak852_tanda_larangan_premis",
            "ak852_larangan_merokok_bangunan_mall_parkir",
            "ak342_tibi_smear_negatif_enggan_mula",
            "ak342_covid_positif_tempat_kerja",
            "ak281_makanan_luput_pelabelan",
        }
        auto_ai_needed = (
            (not confident_match)
            or (is_nuanced_question and matched.get("id") not in fast_handled_nuance_ids)
        ) and len(effective_question) >= 12
        should_call_ai = ai_requested or auto_ai_needed

        if should_call_ai and self.router._genai_client is None:
            result["ai_attempted"] = ai_requested
            if ai_requested:
                result["fallback_reason"] = (
                    "Fungsi Semakan Mendalam AI belum diaktifkan oleh pentadbir sistem. Paparan menggunakan rujukan akta tempatan."
                )
        elif should_call_ai:
            result["ai_attempted"] = True
            cache_key = "|".join(
                [
                    legal_lib.statute_library_version,
                    effective_question.lower(),
                    akta_hint,
                    scenario_id or "",
                    "deep" if ai_requested else "auto",
                    settings.reasoning_model,
                    settings.multimodal_model,
                    settings.standard_fallback_model,
                ]
            )
            # Apabila pengguna klik secara eksplisit 'Semakan Mendalam dengan AI' (use_ai=True),
            # sentiasa jalankan analisis AI segar (jangan pulangkan cache lama) supaya pengguna nampak kupasan mendalam yang baharu!
            cached_ai = None if ai_requested else self._consult_cache.get(cache_key)
            if cached_ai:
                result.update(cached_ai)
                result["ai_attempted"] = True
                result["ai_succeeded"] = True
                result["fallback_reason"] = None
                result["is_fallback_response"] = False
                result["engine_used"] = f"{cached_ai.get('engine_used', 'Analisis AI')} [Cache]"
            else:
                statutory_context_block = grounding["statutory_context_block"]
                amendment_directives_list = grounding.get("amendment_directives") or []
                amendment_rule_str = (
                    "6) KEUTAMAAN AKTA PINDAAN TERKINI (MANDATORI): "
                    + " | ".join(amendment_directives_list)
                    + "\n"
                    if amendment_directives_list
                    else ""
                )
                # Semak sama ada templat padanan selari dengan kesalahan teratas grounding supaya templat tidak memutarbelitkan AI!
                top_cand_sec = str((grounding.get("candidate_offences") or [{}])[0].get("offence_section") or "").lower()
                matched_first_sec = str((matched.get("cadangan_pertuduhan") or [{}])[0].get("seksyen_kesalahan") or "").lower()
                top_sec_digits = re.findall(r"\d+[A-Za-z]?", top_cand_sec)
                preset_aligns_with_grounding = bool(
                    scenario_id
                    or not top_sec_digits
                    or (top_sec_digits[0] in matched_first_sec)
                )
                charges_summary = "\n".join(
                    f"- {c.get('perihal', '')}: {c.get('seksyen_kesalahan', '')} | Hukuman: {c.get('seksyen_hukuman', '')}"
                    for c in matched.get("cadangan_pertuduhan", [])
                )
                ref_block = (
                    f"RUJUKAN TEMPLAT SOP UMUM ({matched['tajuk']}) — GUNAKAN SEBAGAI PANDUAN SAHAJA, ABAIKAN JIKA SOALAN PPKP MEMBINCANGKAN KESALAHAN/PIHAK/PENGECUALIAN BERBEZA:\n"
                    f"Keputusan asas templat: {matched['keputusan_tindakan']}\n"
                    f"Pertuduhan templat:\n{charges_summary}\n\n"
                    if (confident_match and preset_aligns_with_grounding)
                    else "ANALISIS TERUS DARIPADA SOALAN PPKP, [KATALOG RINGKAS SEMUA KESALAHAN DOMAIN], DAN [TEKS PENUH VERBATIM WARTA] DI BAWAH.\n\n"
                )
                deep_mode_instruction = (
                    "\nMOD SEMAKAN MENDALAM (DIMINTA KHUSUS OLEH PEGAWAI):\n"
                    "- Jawab soalan sebenar yang ditanya oleh pegawai secara TERUS TERANG pada ayat pertama `ringkasan_keputusan` (cth: boleh kompaun atau tidak, alasan pihak premis sah atau ditolak).\n"
                    "- Nilai setiap fakta, alasan/pembelaan, pengecualian Jadual, dan siapa yang memikul liabiliti statutori (cth. tuan punya vs penghuni, penyewa vs pengurusan bangunan, individu vs syarikat) berdasarkan teks verbatim Warta dalam <STATUTORY_CONTEXT>.\n"
                    "- Nyatakan strategi pembuktian kukuh, eksibit kritikal, dan potensi hujah pembelaan yang perlu dijangka oleh PPKP/TPR.\n"
                    if ai_requested
                    else ""
                )
                base_closed_book_prompt = (
                    "Anda ialah Ketua UIP / Pegawai Pendakwa Kanan Kementerian Kesihatan Malaysia (KKM) yang amat teliti dan pintar dalam undang-undang kesihatan awam.\n"
                    "Jawab SOALAN TEPAT YANG DITANYA OLEH PPKP menggunakan Bahasa Melayu kerja harian PPKP yang jelas, padat, praktikal di lapangan, dan tepat.\n"
                    "ARAHAN KUNCI TERTUTUP & KETEPATAN PENAAKULAN (STRICT CLOSED-BOOK REASONING):\n"
                    "0) FOKUS 100% PADA SOALAN SEBENAR PEGAWAI: Baca dengan teliti apa yang ditanya (siapa pelaku/pihak terlibat, apa perbuatan atau peninggalan, apa alasan/pengecualian yang disebut). "
                    "JANGAN sesekali menjawab tentang seksyen lain yang tidak ditanya (contohnya: jika soalan tentang tiada tanda larangan merokok oleh peniaga, rujuk Seksyen 18(1)(a) & P.U. (A) 258/2024 — BUKAN Seksyen 16(2) perokok individu!). "
                    "Semak [KATALOG RINGKAS SEMUA KESALAHAN DOMAIN] dan [TEKS PENUH VERBATIM WARTA] untuk memilih seksyen yang PALING TEPAT.\n"
                    "1) WAJIB kelaskan `status_kesalahan` kepada tepat satu daripada 2 nilai: `TIADA_KESALAHAN` atau `ADA_KESALAHAN`, serta tulis `ringkasan_keputusan` 1–2 baris yang tegas dan terus menjawab soalan pegawai.\n"
                    "   - Jika `TIADA_KESALAHAN`: jelaskan dengan tepat mengapa perbuatan/situasi itu tidak menjadi kesalahan atau termasuk dalam pengecualian Jadual dalam `sebab_tidak_menyalahi`, berikan langkah susulan pentadbiran/bukti tambahan dalam `langkah_susulan_ppkp`, dan kosongkan `cadangan_pertuduhan`.\n"
                    "   - Jika `ADA_KESALAHAN`: letakkan seksyen kesalahan PALING UTAMA bagi soalan pegawai di indeks pertama `cadangan_pertuduhan[0]`, nyatakan hukuman & status kompaun tepat, tindakan segera, SOP lapangan bernombor kronologi, dan eksibit wajib.\n"
                    "2) Anda DILARANG KERAS memetik mana-mana nombor seksyen, peraturan, denda, atau kompaun yang TIDAK WUJUD dalam blok <STATUTORY_CONTEXT> di bawah, dan DILARANG mencadangkan Seksyen 2 (Tafsiran) sebagai seksyen kesalahan.\n"
                    "3) WAJIB semak unsur mandatori dan pengecualian/perangkap sebenar dalam teks Warta sebelum memutuskan kesalahan. "
                    "Jika fakta soalan jelas memenuhi pengecualian statutori atau unsur mandatori tidak dipenuhi (cth. pemilikan pasif vape pelajar tanpa menghisap/membeli, merokok di tempat letak kereta awam terbuka R&R Bil. 24, kabinet bertutup legap P.U.(A) 260/2024, pembersihan dapur tanpa menjual semasa perintah tutup S.11, makanan luput diasingkan untuk pelupusan, takungan kosong tiada larva S.13(1) Akta 154, premis berkunci tiada penghuni S.21 Akta 154, atau COVID-19 pasca 15 Julai 2024 tanpa perintah bertulis S.15(1)/S.14), WAJIB tetapkan `status_kesalahan = 'TIADA_KESALAHAN'`.\n"
                    "4) DILARANG mencadangkan sebarang akta/peraturan dalam SENARAI HITAM PERUNTUKAN DIMANSUHKAN (seperti PPKHT 2004 atau Ordinan Darurat 2021).\n"
                    "5) Bagi setiap cadangan_pertuduhan (jika ADA_KESALAHAN), wajib sertakan 5 kunci tepat: perihal, seksyen_kesalahan, seksyen_hukuman, hukuman_maksimum, boleh_kompaun.\n"
                    f"{amendment_rule_str}"
                    f"{deep_mode_instruction}\n"
                    f"SOALAN PPKP:\n{effective_question}\n\n"
                    f"{ref_block}"
                    f"{statutory_context_block}"
                )
                model_candidates = (
                    [
                        settings.reasoning_model,
                        "gemini-3.8-flash",
                        settings.multimodal_model,
                        settings.standard_fallback_model,
                    ]
                    if ai_requested
                    else ["gemini-3.8-flash", settings.multimodal_model, settings.standard_fallback_model]
                )
                ai_json, used_model = self.router._call_gemini_structured_json(
                    model_candidates=model_candidates,
                    input_payload=base_closed_book_prompt,
                    schema=_AdvisorLLMSchema.model_json_schema(),
                    temperature=0.15 if ai_requested else 0.1,
                    prefer_flash=not ai_requested,
                    prefer_fast_gc=True,
                    max_output_tokens=3400 if ai_requested else 2800,
                )

                def _build_ai_patch(raw_ai: Dict[str, Any]) -> Dict[str, Any]:
                    raw_status = str(raw_ai.get("status_kesalahan") or "").strip().upper()
                    raw_charges = raw_ai.get("cadangan_pertuduhan")
                    fallback_charges = matched.get("cadangan_pertuduhan", []) if preset_aligns_with_grounding else []
                    patch: Dict[str, Any] = {
                        "akta_disyorkan": self._canonicalize_akta_code(
                            str(raw_ai.get("akta_disyorkan") or ""),
                            result["akta_disyorkan"],
                        ),
                        "tajuk_nasihat": str(raw_ai.get("tajuk_nasihat") or result["tajuk_nasihat"]),
                        "ringkasan_keputusan": str(
                            raw_ai.get("ringkasan_keputusan")
                            or raw_ai.get("keputusan_tindakan")
                            or result["ringkasan_keputusan"]
                        ),
                        "keputusan_tindakan": str(raw_ai.get("keputusan_tindakan") or result["keputusan_tindakan"]),
                        "sesuai_buka_ip": bool(raw_ai.get("sesuai_buka_ip", result["sesuai_buka_ip"])),
                        "alasan_keputusan": str(raw_ai.get("alasan_keputusan") or result["alasan_keputusan"]),
                        "sebab_tidak_menyalahi": str(raw_ai.get("sebab_tidak_menyalahi") or ""),
                        "langkah_susulan_ppkp": list(raw_ai.get("langkah_susulan_ppkp") or []),
                        "cadangan_pertuduhan": (
                            []
                            if raw_status == "TIADA_KESALAHAN"
                            else self._normalize_charge_items(raw_charges, fallback_charges)
                        ),
                        "sop_lapangan": list(raw_ai.get("sop_lapangan") or result["sop_lapangan"]),
                        "eksibit_wajib": list(raw_ai.get("eksibit_wajib") or result["eksibit_wajib"]),
                        "perangkap_kesilapan": list(raw_ai.get("perangkap_kesilapan") or result["perangkap_kesilapan"]),
                        "templat_ringkas": str(raw_ai.get("templat_ringkas") or result["templat_ringkas"]),
                    }
                    if raw_status in ("TIADA_KESALAHAN", "ADA_KESALAHAN"):
                        patch["status_kesalahan"] = raw_status
                    return patch

                # FASA 3.3: Pengesah Kod Pasca-Penjanaan + Self-Correction Retry jika gagal validasi
                if ai_json:
                    candidate_patch = _build_ai_patch(ai_json)
                    ai_val = validate_legal_output(
                        candidate_patch, lib_snapshot, question_context=effective_question
                    )
                    if not ai_val["passed"]:
                        retry_prompt = (
                            f"{base_closed_book_prompt}\n\n"
                            "AMARAN SELF-CORRECTION (RALAT VALIDASI PUSTAKA AKTA PADA JAWAPAN SEBELUMNYA):\n"
                            f"{ai_val['warning_banner']}\n"
                            "Sila betulkan jawapan anda serta-merta dengan membuang semua petikan seksyen tidak wujud/dimansuhkan dan mematuhi semakan unsur mandatori!"
                        )
                        retry_json, retry_model = self.router._call_gemini_structured_json(
                            model_candidates=model_candidates,
                            input_payload=retry_prompt,
                            schema=_AdvisorLLMSchema.model_json_schema(),
                            temperature=0.0,
                            prefer_flash=True,
                            prefer_fast_gc=True,
                            max_output_tokens=2800,
                        )
                        if retry_json:
                            candidate_patch = _build_ai_patch(retry_json)
                            used_model = f"{retry_model} [Self-Corrected]"
                            ai_val = validate_legal_output(
                                candidate_patch, lib_snapshot, question_context=effective_question
                            )

                    if ai_val["passed"]:
                        engine_prefix = "Semakan Mendalam AI" if ai_requested else "Analisis AI"
                        ai_patch = {
                            **candidate_patch,
                            "engine_used": f"{engine_prefix} ({used_model})",
                            "ai_attempted": True,
                            "ai_succeeded": True,
                            "fallback_reason": None,
                            "is_fallback_response": False,
                            "legal_validation": ai_val,
                        }
                        if len(self._consult_cache) >= 64:
                            self._consult_cache.clear()
                        self._consult_cache[cache_key] = ai_patch
                        result.update(ai_patch)
                    else:
                        result["ai_attempted"] = True
                        result["ai_succeeded"] = False
                        result["fallback_reason"] = ai_val["warning_banner"]
                        result["legal_validation"] = ai_val
                else:
                    err_detail = self.router._last_ai_error or (
                        "Semakan Mendalam AI tidak dapat dicapai buat sementara waktu. Paparan menggunakan rujukan tempatan."
                    )
                    logger.warning("Tanya Pakar fallback ke enjin tempatan: %s", err_detail)
                    result["ai_attempted"] = True
                    result["ai_succeeded"] = False
                    result["fallback_reason"] = err_detail

        # PENYELARASAN PASCA-JAWAPAN: Selaraskan `element_evaluations` dan `statutory_citations`
        # supaya 100% sepadan dengan kesalahan SEBENAR yang dipilih oleh jawapan (bukan sisa pra-AI yang bercanggah!)
        self._reconcile_post_answer_grounding(
            result=result,
            effective_question=effective_question,
            legal_lib=legal_lib,
            citations_dict=citations_dict,
            verbatim_by_doc_id=verbatim_by_doc_id,
        )

        self._enrich_two_branch_structure(
            result,
            effective_question,
            is_fallback=bool(result.get("is_fallback_response") and not result.get("ai_succeeded")),
        )
        result["draf_teks_kes_cadangan"] = (
            ""
            if result.get("status_kesalahan") == "TIADA_KESALAHAN"
            else self._build_prefilled_case_template(
                {**matched, "akta_utama": result["akta_disyorkan"], "templat_ringkas": result["templat_ringkas"]},
                officer_profile=officer_profile,
            )
        )
        result["statutory_citations"] = citations_dict
        if "legal_validation" not in result or result["legal_validation"] is None:
            result["legal_validation"] = validate_legal_output(
                result, lib_snapshot, question_context=effective_question
            )
        return result

    @staticmethod
    def _reconcile_post_answer_grounding(
        *,
        result: Dict[str, Any],
        effective_question: str,
        legal_lib: Any,
        citations_dict: List[Dict[str, Any]],
        verbatim_by_doc_id: Dict[str, Dict[str, Any]],
    ) -> None:
        """Menyelaraskan `element_evaluations` & susunan `statutory_citations` mengikut kesalahan sebenar yang dipilih."""
        from backend.rag.legal_engine import (
            canonical_akta_code_for_statute,
            evaluate_offence_elements_against_facts,
        )

        status_up = str(result.get("status_kesalahan") or "").upper()
        charges = [c for c in (result.get("cadangan_pertuduhan") or []) if isinstance(c, dict)]
        ans_act = str(result.get("akta_disyorkan") or "").upper()

        if status_up == "TIADA_KESALAHAN":
            # Hanya kekalkan penilaian unsur yang benar-benar disekat / mempunyai unsur TIDAK TERPENUHI
            # dan pastikan tiada unsur hijau TERPENUHI dipaparkan pada kad TIADA_KESALAHAN.
            cleaned_no_off_evals: List[Dict[str, Any]] = []
            for ev in result.get("element_evaluations") or []:
                if not isinstance(ev, dict):
                    continue
                els = ev.get("element_evaluations") or []
                has_unmet = bool(ev.get("action_blocked")) or any(
                    str(e.get("status") or "").upper() == "TIDAK TERPENUHI" for e in els
                )
                if not has_unmet:
                    continue
                sanitized_els = [
                    {
                        **e,
                        "status": "PERLU BUKTI TAMBAHAN"
                        if str(e.get("status") or "").upper() == "TERPENUHI"
                        else e.get("status"),
                    }
                    for e in els
                ]
                cleaned_no_off_evals.append(
                    {
                        **ev,
                        "all_elements_satisfied": False,
                        "element_evaluations": sanitized_els,
                    }
                )
            result["element_evaluations"] = cleaned_no_off_evals[:2]
            return

        if not charges:
            return

        # Padankan kesalahan sebenar dalam `cadangan_pertuduhan` dengan entri `master_offences_matrix`
        matched_offs: List[Dict[str, Any]] = []
        seen_oids: set[str] = set()
        for ch in charges[:2]:
            ch_sec = str(ch.get("seksyen_kesalahan") or "").lower()
            sec_m = re.search(r"(?:seksyen|peraturan|s\.|p\.)\s*(\d+[a-z]?(?:\(\d+\))?)", ch_sec, re.I)
            if not sec_m:
                continue
            sec_full = sec_m.group(1).lower()
            sec_base = re.findall(r"^\d+[a-z]?", sec_full)[0]
            ch_act_digits = re.findall(r"\b(852|281|154|342|593|56|611)\b", ch_sec)
            if not ch_act_digits:
                ch_act_digits = re.findall(r"\b(852|281|154|342|593|56|611)\b", ans_act)
            is_ppkm_ch = "ppkm" in ch_sec or "95/2009" in ch_sec
            is_ppm_ch = "ppm" in ch_sec or "1985" in ch_sec

            best_off = None
            best_rank = -1
            for off in legal_lib.master_offences_matrix:
                oid = str(off.get("offence_id") or "")
                if oid in seen_oids or oid == "AKTA_852_PERATURAN_TANDA_2024_PERATURAN_2":
                    continue
                sid = str(off.get("statute_id") or "").upper()
                o_sec = str(off.get("offence_section") or "").lower()
                if is_ppkm_ch and sid != "PPKM_2009":
                    continue
                if is_ppm_ch and sid != "PPM_1985":
                    continue
                if ch_act_digits and not (is_ppkm_ch or is_ppm_ch):
                    c_act = canonical_akta_code_for_statute(sid)
                    if not any(d in c_act or d in sid for d in ch_act_digits):
                        continue
                rank = 0
                if sec_full in o_sec:
                    rank = 3
                elif re.search(rf"\b{re.escape(sec_base)}(?:\(|\b)", o_sec):
                    rank = 2
                if rank > best_rank:
                    best_rank = rank
                    best_off = off
            if best_off and best_rank >= 2:
                seen_oids.add(best_off["offence_id"])
                matched_offs.append(best_off)

        if matched_offs:
            result["element_evaluations"] = [
                evaluate_offence_elements_against_facts(effective_question, off)
                for off in matched_offs
            ]
            # Pastikan seksyen verbatim daripada kesalahan yang benar-benar dipilih berada di bahagian paling atas `citations_dict`
            existing_ids = {str(c.get("doc_id") or c.get("chunk_id") or "") for c in citations_dict}
            priority_cits: List[Dict[str, Any]] = []
            priority_ids: set[str] = set()
            for off in matched_offs:
                for did in off.get("source_section_doc_ids") or []:
                    if did in verbatim_by_doc_id and did not in priority_ids:
                        s_v = verbatim_by_doc_id[did]
                        priority_ids.add(did)
                        act_c = canonical_akta_code_for_statute(s_v["statute_id"])
                        sc_code = str(s_v["section_code"])
                        priority_cits.append(
                            {
                                "chunk_id": s_v["doc_id"],
                                "doc_id": s_v["doc_id"],
                                "statute_id": s_v["statute_id"],
                                "akta_code": act_c,
                                "akta_title": act_c,
                                "section": f"Seksyen {sc_code} - {s_v['section_heading']}"
                                if not sc_code.lower().startswith(("seksyen", "peraturan", "jadual"))
                                else f"{sc_code} - {s_v['section_heading']}",
                                "text": s_v["verbatim_text_bm"],
                                "score": 0.98,
                                "verbatim": True,
                            }
                        )
            if priority_cits:
                rest = [
                    c for c in citations_dict
                    if str(c.get("doc_id") or c.get("chunk_id") or "") not in priority_ids
                ]
                citations_dict[:] = priority_cits + rest[: max(0, 10 - len(priority_cits))]
