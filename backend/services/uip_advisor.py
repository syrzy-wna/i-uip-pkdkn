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
                "seksyen_kesalahan": "Seksyen 10(1) Akta 852 dibaca bersama Peraturan 6 P.U. (A) 260/2024 (jika syarikat baca bersama S.51)",
                "seksyen_hukuman": "Seksyen 10(2)(a)/(b) [Individu] atau Seksyen 10(3)(a) [Pertubuhan Perbadanan] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara maks 1 tahun | Syarikat: Denda RM20,000 – RM100,000 / penjara 2 tahun",
                "boleh_kompaun": "Boleh kompaun mengikut jadual P.U. (A) 259/2024 (Notis S.47, tempoh 30 hari) ATAU terus buka IP jika enggan patuh/berulang.",
            }
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa Rasmi KKM (Seksyen 25 Akta 852) kepada pemilik atau penjaga premis.",
            "Ambil gambar sudut jauh dan dekat menunjukkan pod/rokok dipamer secara terbuka sebelum disentuh.",
            "Jalankan pemeriksaan (Seksyen 26/30) dan sita semua unit yang dipamerkan secara salah di bawah Seksyen 35 Akta 852.",
            "Isi Borang Senarai Benda Disita di bawah Seksyen 36 Akta 852 di tempat kejadian, dapatkan tandatangan terima pemilik dan serahkan satu salinan.",
            "Lak (seal) barang kes dengan nombor siri lak KKM, lukis Pelan Lakar premis dan rekod masuk ke Stor Eksibit PKD.",
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
            "Jangan hanya tuduh pekerja kaunter warga asing tanpa menyemak pemilik syarikat/pengarah dalam SSM (Seksyen 51).",
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
        "tajuk": "Pelajar / Orang Belum Dewasa (OBD < 18 Tahun) Merokok / Hisap Vape di Tepi Jalan atau Tempat Awam",
        "keywords": [
            "budak sekolah", "pelajar sekolah", "pelajar merokok", "tepi jalan", "hisap rokok", "hisap vape",
            "menghisap rokok", "seragam sekolah", "pondok bas", "seksyen 17", "17(1)",
            "obd merokok", "remaja merokok", "bawah umur hisap",
        ],
        "negative_keywords": ["jual kepada", "menjual rokok", "kedai jual", "tanda larangan"],
        "incompatible_with": ["ak852_larangan_merokok"],
        "keputusan_tindakan": "OBD MEROKOK: NOTIS KESALAHAN S.47 & KOMPAUN S.48 (BUKA IP JIKA ENGGAN BAYAR / JUALAN KEDAI: S.13(1))",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Bagi pelajar sekolah atau individu bawah 18 tahun (OBD) yang dikesan menghisap rokok atau vape di tepi jalan/kawasan awam, "
            "kesalahan di bawah Seksyen 17(1) Akta 852 boleh ditawarkan kompaun [P.U. (A) 259/2024] berserta pemakluman kepada ibu bapa/penjaga. "
            "Hanya buka IP ke atas OBD jika gagal jelas kompaun (untuk Perintah Khidmat Masyarakat / denda S.17(2)), TETAPI wajib siasat kedai/penjual di bawah S.13(1)!"
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "OBD (< 18 tahun) merokok, mengunyah, menggunakan atau memiliki apa-apa produk merokok",
                "seksyen_kesalahan": "Seksyen 17(1) Akta 852",
                "seksyen_hukuman": "Seksyen 17(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM500 atau Perintah Khidmat Masyarakat (Akta 852)",
                "boleh_kompaun": "Boleh kompaun di bawah Seksyen 48 [P.U. (A) 259/2024] dengan Notis S.47 (maklumkan ibu bapa/penjaga).",
            },
            {
                "perihal": "Penjual / Pekedai (Jika dikenal pasti menjual rokok/vape kepada pelajar tersebut)",
                "seksyen_kesalahan": "Seksyen 13(1) Akta 852",
                "seksyen_hukuman": "Seksyen 13(2) [Individu] / Seksyen 13(3) [Syarikat] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara 1 tahun | Syarikat: RM20,000 – RM100,000",
                "boleh_kompaun": "Siasatan terhadap penjual disyorkan Buka IP Terus.",
            },
        ],
        "sop_lapangan": [
            "Tunjukkan Kad Kuasa Rasmi KKM (Seksyen 25 Akta 852) secara berhemah apabila melihat OBD sedang menghisap rokok/vape.",
            "Ambil gambar atau video ringkas kejadian serta puntung rokok/peranti vape yang masih dipegang sebagai bukti masa kejadian.",
            "Semak MyKad / Kad Pelajar untuk sahkan umur di bawah 18 tahun pada tarikh kejadian, dan catat butiran ibu bapa/penjaga.",
            "Keluarkan Notis Seksyen 47 (Seksyen 17(1) Akta 852), ambil pengesahan serahan, dan dapatkan maklumat kedai penjual untuk siasatan susulan Seksyen 13(1).",
        ],
        "eksibit_wajib": [
            "Salinan MyKad / Pengesahan JPN OBD (membuktikan umur di bawah 18 tahun)",
            "Salinan pendua Notis Seksyen 47 bertandatangan terima / saksi + rekod makluman penjaga",
            "Puntung rokok / peranti vape yang dirampas (jika kes mahkamah/sitaan S.36)",
            "Gambar foto kejadian + Sijil Seksyen 90A(2)",
        ],
        "perangkap_kesilapan": [
            "JANGAN caj pelajar di bawah Seksyen 16(2) jika lokasi kejadian di tepi jalan terbuka yang bukan kawasan larangan P.U.(A) 257/2024 — caj di bawah Seksyen 17(1) Akta 852!",
            "Pastikan salinan bukti tarikh lahir (MyKad/JPN) ada untuk membuktikan status OBD (< 18 tahun).",
        ],
        "templat_ringkas": (
            "Kesalahan: Orang Belum Dewasa (< 18 tahun) didapati merokok / memiliki produk merokok di tempat awam "
            "yang melanggar Seksyen 17(1) Akta 852 dan boleh dihukum di bawah Seksyen 17(2) Akta 852. "
            "Notis Seksyen 47 serta makluman kepada penjaga telah dilaksanakan."
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
        "keputusan_tindakan": "PENJUAL: BUKA IP TERUS (Kes Serius) | OBD MEROKOK: KOMPAUN S.48 / KHIDMAT MASYARAKAT",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Menjual produk merokok kepada kanak-kanak/remaja di bawah 18 tahun merupakan keutamaan penguatkuasaan KKM "
            "dengan penalti berat sehingga RM100,000 bagi syarikat. Penjual disyorkan dibuka IP dan disita bukti transaksi, "
            "manakala OBD yang membeli/merokok boleh dikeluarkan Notis S.47 / kompaun S.17 dengan pemakluman penjaga."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Penjual: Menjual produk merokok / rokok elektronik kepada Orang Belum Dewasa (< 18 tahun)",
                "seksyen_kesalahan": "Seksyen 13(1) Akta 852",
                "seksyen_hukuman": "Seksyen 13(2) [Individu] / Seksyen 13(3) [Syarikat] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara maks 1 tahun | Syarikat: Denda RM20,000 – RM100,000",
                "boleh_kompaun": "Kes penjual kepada OBD disyorkan Buka IP terus untuk pendakwaan.",
            },
            {
                "perihal": "OBD: Membeli / Merokok / Memiliki produk merokok di bawah umur 18 tahun",
                "seksyen_kesalahan": "Seksyen 13(4) [Membeli] atau Seksyen 17(1) [Merokok/Memiliki] Akta 852",
                "seksyen_hukuman": "Seksyen 17(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM500 atau Perintah Khidmat Masyarakat",
                "boleh_kompaun": "Boleh dikompaun di bawah Seksyen 48 P.U. (A) 259/2024 (maklumkan ibu bapa/penjaga).",
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
            "yang melanggar Seksyen 13(1) Akta 852 dan boleh dihukum di bawah Seksyen 13(2) Akta 852. "
            "Barang kes telah disita di bawah Seksyen 35/36 Akta 852 dan salinan MyKad OBD dilampirkan."
        ),
    },
    {
        "id": "ak852_larangan_merokok",
        "akta_utama": "Akta 852",
        "tajuk": "Merokok / Vape di Tempat Larangan (Restoran) & Pemilik Tiada Papan Tanda Kod QR / Sedia Ashtray",
        "keywords": [
            "kawasan larangan merokok", "larangan merokok", "tempat makan", "tanda amaran", "tanda larangan",
            "kod qr", "ashtray", "bekas abu", "rokok dalam restoran", "merokok di restoran",
            "seksyen 16", "seksyen 18 akta 852", "257/2024", "258/2024",
        ],
        "negative_keywords": ["tepi jalan", "budak sekolah", "najis tikus", "suntikan tifoid"],
        "incompatible_with": ["ak852_obd_merokok_tepi_jalan"],
        "keputusan_tindakan": "KOMPAUN DAHULU (Notis S.47 / Kompaun S.48 — 30 Hari); BUKA IP HANYA JIKA GAGAL BAYAR",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Kesalahan individu merokok di restoran (S.16(2)) serta pemilik premis gagal mempamer tanda larangan QR atau "
            "menyediakan bekas abu rokok (S.18(1)) adalah kesalahan boleh kompaun lazim. IO/PPKP hendaklah keluar Notis Seksyen 47 "
            "dahulu dengan tempoh bayaran 30 hari; hanya buka IP jika kompaun tidak dijelaskan selepas tamat 30 hari."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Individu merokok / hisap vape di kawasan tempat makan / larangan",
                "seksyen_kesalahan": "Seksyen 16(2) Akta 852 dibaca bersama P.U. (A) 257/2024",
                "seksyen_hukuman": "Seksyen 16(3) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM5,000",
                "boleh_kompaun": "Kompaun RM250.00 di bawah Seksyen 48 [P.U. (A) 259/2024] — tempoh bayaran 30 hari.",
            },
            {
                "perihal": "Pemilik premis gagal pamer tanda amaran Kod QR atau sediakan bekas abu rokok",
                "seksyen_kesalahan": "Seksyen 18(1)(a) [Tiada tanda/P.U.(A) 258/2024] atau Seksyen 18(1)(b) [Bekas abu rokok] Akta 852",
                "seksyen_hukuman": "Seksyen 18(2) Akta 852",
                "hukuman_maksimum": "Denda tidak melebihi RM5,000",
                "boleh_kompaun": "Boleh dikompaun di bawah Seksyen 48 [P.U. (A) 259/2024] — tempoh bayaran 30 hari.",
            },
        ],
        "sop_lapangan": [
            "Ambil gambar perokok sedang memegang/menghembus asap atau wap vape di dalam premis (termasuk jarak 3 meter dari meja makan luar).",
            "Ambil gambar keadaan dinding premis (jika tiada tanda larangan Kod QR) atau gambar bekas abu rokok di atas meja.",
            "Tunjukkan Kad Kuasa, periksa MyKad dan serahkan Notis Seksyen 47 (tandatangan terima; jika enggan tandatangan, catat 'Enggan Tandatangan' berserta saksi PPKP).",
            "Jika kompaun tidak dibayar selepas 30 hari (rujuk pengesahan Unit Hasil PKD), barulah buka Fail IP dan sediakan Borang 114.",
        ],
        "eksibit_wajib": [
            "Salinan pendua Notis Seksyen 47 bertandatangan terima / catatan saksi enggan tandatangan",
            "Gambar foto bukti (puntung rokok/vape/papan tanda/ashtray) + Sijil Seksyen 90A(2)",
            "Sijil / Pengesahan Unit Hasil PKD bahawa kompaun tidak dibayar selepas tamat 30 hari (jika dibawa ke mahkamah)",
        ],
        "perangkap_kesilapan": [
            "JANGAN tulis 'melanggar Seksyen 16(1)' — Seksyen 16(1) ialah kuasa Menteri mengisytiharkan tempat larangan; kesalahan perokok ialah Seksyen 16(2)!",
            "Jangan hantar kes ke mahkamah sebelum tempoh kompaun 30 hari Akta 852 tamat sepenuhnya.",
        ],
        "templat_ringkas": (
            "Kesalahan: Menghisap rokok / rokok elektronik di tempat makan yang diisytiharkan sebagai kawasan larangan merokok di bawah P.U. (A) 257/2024 "
            "yang melanggar Seksyen 16(2) Akta 852 dan boleh dihukum di bawah Seksyen 16(3) Akta 852. "
            "Notis Seksyen 47 dan tawaran kompaun Seksyen 48 [30 hari] telah diserahkan."
        ),
    },
    {
        "id": "ak852_iklan_vape",
        "akta_utama": "Akta 852",
        "tajuk": "Iklan, Poster, Bunting atau Promosi Produk Vape / Rokok (Fizikal atau Skrin Digital)",
        "keywords": [
            "iklan rokok", "iklan vape", "papan iklan", "poster iklan", "bunting", "promosi vape",
            "tajaan", "skrin digital", "media sosial", "seksyen 7 akta 852", "seksyen 9 akta 852",
        ],
        "keputusan_tindakan": "SITA POSTER/IKLAN (S.35/S.36) & BUKA IP TERUS (S.7(1) TIDAK BOLEH KOMPAUN di bawah P.U.(A) 259/2024)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Kes iklan dan promosi vape melanggar Seksyen 7(1) / Seksyen 9(1) Akta 852. "
            "Seksyen 7(1) tidak disenaraikan sebagai kesalahan boleh kompaun di bawah Jadual Pertama P.U. (A) 259/2024; "
            "bahan iklan fizikal wajib disita di bawah S.35/36, atau tangkapan skrin digital dicetak dengan Sijil Seksyen 90A(2) untuk membuka IP."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menyiarkan / mempamerkan iklan produk merokok atau rokok elektronik",
                "seksyen_kesalahan": "Seksyen 7(1) Akta 852 [atau Seksyen 9(1) jika promosi harga/diskaun]",
                "seksyen_hukuman": "Seksyen 7(2) [Individu] / Seksyen 7(3) [Pertubuhan Perbadanan] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara 1 tahun | Syarikat: Denda RM20,000 – RM100,000",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN di bawah Jadual Pertama P.U. (A) 259/2024 bagi S.7(1) — wajib buka IP untuk pendakwaan.",
            }
        ],
        "sop_lapangan": [
            "Ambil gambar keseluruhan kedai serta gambar jelas poster/gegantung/skrin LED iklan vape sebelum menyentuh bahan.",
            "Sita poster atau papan iklan fizikal di bawah Seksyen 35 dan keluarkan Borang Senarai Sitaan Seksyen 36 Akta 852.",
            "Jika iklan di skrin LED/media sosial rasmi kedai, ambil gambar skrin serta cetak paparan tersebut bersama Sijil Seksyen 90A(2).",
        ],
        "eksibit_wajib": [
            "Bahan iklan/poster fizikal yang disita & dilak KKM + Borang S.36",
            "Gambar foto bukti & cetakan paparan iklan digital + Sijil Seksyen 90A(2)",
            "Carian Rasmi SSM + Sijil S.90A bagi membuktikan entiti yang menyiarkan iklan",
        ],
        "perangkap_kesilapan": [
            "KESALAHAN DUPLICITY (S.163 KTJ): Jangan campur Seksyen 7(1) [Iklan] dan Seksyen 10(1) [Pameran produk] dalam satu Borang 114 yang sama — wajib asingkan kepada 2 Borang 114 berbeza!",
        ],
        "templat_ringkas": (
            "Kesalahan: Menyiarkan atau menyebabkan disiarkan iklan promosi rokok elektronik (vape) di premis perniagaan "
            "yang melanggar Seksyen 7(1) Akta 852 dan boleh dihukum di bawah Seksyen 7(2)/(3) Akta 852."
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
            "Dapatkan carian rasmi SSM syarikat kontraktor utama berserta salinan Pendaftaran CIDB / Surat Setuju Terima (LOA) / Papan Tanda Projek untuk membuktikan entiti pengawal tapak.",
        ],
        "eksibit_wajib": [
            "Botol spesimen larva berlak KKM + Laporan Entomologi bagi setiap bekas positif",
            "Salinan Perintah Seksyen 8(1) bertandatangan terima SHO/Pengurus Tapak",
            "Cetakan SSM Syarikat Kontraktor Utama + Sijil S.90A, salinan CIDB/LOA & lesen PBT",
            "Pelan Lakar tapak pembinaan menunjukkan zon/aras pembiakan bertandatangan IO",
        ],
        "perangkap_kesilapan": [
            "JANGAN campurkan pertuduhan Seksyen 8(8) [Ingkar Perintah] dan Seksyen 13(1) [Pembiakan] dalam satu Borang 114 (Duplicity S.163 KTJ).",
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
        "keputusan_tindakan": "BUKA IP TERUS TANPA KOMPAUN (Seksyen 22(b) & Seksyen 24(a) Akta 342 [APPPB 88])",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Pesakit Tibi PTB Smear Positif yang enggan menyambung rawatan berisiko menularkan penyakit maut serta mencipta kuman kebal ubat (MDR-TB). "
            "Kes di bawah Seksyen 22(b) Akta 342 perlu dibuka IP untuk mendapatkan Saman & Izin Mendakwa TPR bagi perintah mahkamah/penjara pemulihan."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Enggan mematuhi perintah sah Pegawai Diberi Kuasa untuk menjalani / menyambung rawatan penyakit berjangkit (Tibi)",
                "seksyen_kesalahan": "Seksyen 22(b) Akta 342 (APPPB 1988) [atau dibaca bersama S.15(1) bagi kontak enggan pemerhatian]",
                "seksyen_hukuman": "Seksyen 24(a) Akta 342 [Kesalahan kedua: Seksyen 24(b)]",
                "hukuman_maksimum": "Penjara tidak melebihi dua (2) tahun atau denda atau kedua-duanya (Kesalahan ulangan: penjara maks 5 tahun)",
                "boleh_kompaun": "TIDAK DISYORKAN KOMPAUN — Pendakwaan Terus di Mahkamah Majistret + Pemberatan Hukuman.",
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
            "Jadual Kronologi Kes, Diari Siasatan lengkap, dan 6 Poin Hujahan Pemberatan Hukuman (risiko penularan awam & MDR-TB)",
        ],
        "perangkap_kesilapan": [
            "KESALAHAN AKTA BIASA: JANGAN sekali-kali tulis 'Seksyen 22(b) Akta 514' (Akta 514 ialah OSHA 1994!). Akta Tibi ialah Akta 342 [APPPB 1988]!",
            "Pastikan bukti serahan tangan Notis Arahan Rawatan asal wujud supaya OKT tidak mendakwa tidak pernah diberi notis.",
        ],
        "templat_ringkas": (
            "Kesalahan: Tidak mematuhi perintah sah yang dikeluarkan oleh pegawai diberi kuasa iaitu enggan menjalani dan menyambung semula rawatan penyakit Tuberkulosis (PTB Smear Positif) "
            "sejenis penyakit berjangkit sebagaimana diarahkan di bawah Notis Arahan Menjalani Rawatan Penyakit Berjangkit. "
            "Perbuatan ini melanggar Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] dan boleh dihukum di bawah Seksyen 24(a) akta yang sama."
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
        "keputusan_tindakan": "SAHKAN DIAGNOSIS KLINIKAL DAHULU (MO/FMS — CXR/GeneXpert/Kultur TBIS 20C) & SERAH NOTIS ARAHAN SAH — JANGAN TERUS BUKA IP S.22(b)",
        "sesuai_buka_ip": False,
        "alasan_keputusan": (
            "Kes disaring Tibi atau PTB Smear Negatif (AFB Negatif) yang enggan memulakan rawatan TIDAK sama dengan kes PTB Smear Positif cicir rawatan (TBIS 10D). "
            "Jika kes masih peringkat saringan atau keputusan kahak AFB negatif tanpa pengesahan klinikal MO/FMS (CXR/GeneXpert MTB/kultur TBIS 20C) serta tanpa Notis Arahan bertulis yang diserahkan secara tangan, "
            "pembukaan IP Seksyen 22(b) berisiko tinggi ditolak TPR/Mahkamah kerana gagal membuktikan pesakit disahkan menghidap penyakit berjangkit aktif dan tiada perintah statutori sah yang diingkari. "
            "Sahkan diagnosis klinikal & e-Notifikasi S.10 dahulu; guna S.15(1)/S.18(1)(a) untuk ujian lanjut atau S.14/Notis Arahan Rawatan bertulis — hanya buka IP S.22(b) & S.24 jika pesakit masih ingkar selepas serahan tangan notis sah."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Fasa 1 (Saringan / Belum Disahkan Aktif): Perintah Pemerhatian, Pengawasan & Ujian Lanjutan",
                "seksyen_kesalahan": "Seksyen 15(1) & Seksyen 18(1)(a)/(f) Akta 342 [APPPB 1988] + kaunseling & Borang Enggan Rawatan (AOR)",
                "seksyen_hukuman": "Seksyen 22(b) dibaca bersama Seksyen 24 Akta 342 (hanya jika ingkar Perintah bertulis S.15(1) yang diserahkan)",
                "hukuman_maksimum": "Pindaan Akta A1742 (kuat kuasa 1 Mei 2025): Individu denda maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "JANGAN buka IP S.22(b) atau tuduh MDR-TB selagi ujian pengesahan (GeneXpert/Kultur/MO) & notis bertulis belum lengkap.",
            },
            {
                "perihal": "Fasa 2 (Selepas Disahkan PTB Aktif oleh MO/FMS & Dinotifikasi S.10): Ingkar Notis Arahan Rawatan / Pengasingan S.14",
                "seksyen_kesalahan": "Seksyen 22(b) Akta 342 [ingkar Notis Arahan Menjalani Rawatan / Perintah Pengasingan Seksyen 14 bertulis]",
                "seksyen_hukuman": "Seksyen 24 Akta 342 [APPPB 1988] (pindaan Akta A1742; atau S.24(a)/(b) bagi kesalahan terdahulu)",
                "hukuman_maksimum": "Denda maks RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "Buka IP terus HANYA selepas bukti diagnosis aktif MO/FMS & bukti serahan tangan Notis Arahan bertulis lengkap.",
            },
        ],
        "sop_lapangan": [
            "Semak status klinikal dengan Pegawai Perubatan (MO) / FMS / Pakar Klinik Tibi: adakah kes masih suspek saringan (presumptive TB) atau telah disahkan PTB Smear Negatif aktif berdasarkan CXR, GeneXpert MTB/RIF atau Kultur (C&S) pada Borang Makmal TBIS 20C.",
            "Pastikan kes telah didaftarkan dalam e-Notifikasi (Seksyen 10 Akta 342 / Peraturan Borang Notis 2005) sekiranya disahkan menghidap Tibi aktif.",
            "Jika keputusan pengesahan masih belum muktamad (tunggu GeneXpert/kultur): jalankan kaunseling bersemuka (MO + PPKP), rekod Borang Enggan Rawatan / AOR bertandatangan pesakit & saksi, dan pertimbangkan Perintah Pemerhatian/Pengawasan bertulis di bawah Seksyen 15(1) / S.18(1)(a) Akta 342 untuk hadir ujian pengesahan.",
            "Hanya apabila MO/FMS mengesahkan PTB aktif dan rawatan wajib dimulakan: keluarkan Notis Arahan Menjalani Rawatan Penyakit Berjangkit / Perintah Seksyen 14 secara bertulis dan buat SERAHAN TANGAN RASMI (tandatangan terima pesakit + saksi PPKP, atau catatan 'Enggan Tandatangan' + saksi + Pos Berdaftar AR).",
            "Sekiranya pesakit masih ingkar tarikh dalam notis bertulis tersebut, barulah buka Fail IP Seksyen 22(b) dengan melampirkan Laporan Pengesahan MO/FMS (wajib sebagai saksi mahkamah), keputusan GeneXpert/Kultur/CXR, notis asal, S.112 KTJ dan Diari Siasatan.",
        ],
        "eksibit_wajib": [
            "Laporan Pengesahan Klinikal Bertulis MO / FMS / Pakar Perubatan (mengesahkan PTB Smear Negatif aktif melalui CXR / GeneXpert MTB / Kultur)",
            "Keputusan Makmal TBIS 20C (AFB Smear Negatif serta keputusan GeneXpert MTB/RIF atau Kultur & Sensitiviti)",
            "Cetakan e-Notifikasi Seksyen 10 Akta 342 + Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Borang Kaunseling & Borang Enggan Rawatan / Surat AOR (bagi fasa penolakan awal klinik)",
            "Notis Arahan Menjalani Rawatan / Perintah S.14 atau S.15(1) bertandatangan terima pesakit & saksi PPKP (WAJIB wujud sebelum IP S.22(b) dibuka)",
        ],
        "perangkap_kesilapan": [
            "JANGAN paksa pakai templat 'PTB Smear Positif Cicir Rawatan' atau nyatakan pesakit telah 'mula & cicir ubat / TBIS 10D' sedangkan rawatan belum pernah dimulakan dan AFB negatif — TPR akan menolak dakwaan kerana percanggahan fakta material (S.152–154 KTJ)!",
            "Arahan lisan doktor/jururawat di klinik BUKAN perintah statutori bertulis di bawah Seksyen 22(b) — notis/perintah bertulis Akta 342 wajib diserahkan dahulu sebelum kesalahan ingkar terbentuk.",
            "Jangan tulis 'Akta 514' (OSHA 1994); semua tindakan kawalan Tibi ialah di bawah Akta 342 [APPPB 1988].",
        ],
        "templat_ringkas": (
            "Kesalahan / Siasatan: Pengendalian kes disaring Tibi / PTB Smear Negatif (AFB Negatif) yang enggan memulakan rawatan di klinik kesihatan. "
            "Tindakan statutori dijalankan mengikut Seksyen 15(1) / Seksyen 14 Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] selepas pengesahan diagnosis oleh Pegawai Perubatan melalui CXR/GeneXpert/Kultur TBIS 20C serta e-Notifikasi Seksyen 10, "
            "sebelum pertimbangan pendakwaan Seksyen 22(b) & Seksyen 24 Akta 342 sekiranya notis perintah bertulis serahan tangan diingkari."
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
                "seksyen_hukuman": "Seksyen 24 Akta 342 [APPPB 1988]",
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
                "perihal": "Menjual / mempamer untuk jualan makanan yang telah tamat tarikh luput (expired)",
                "seksyen_kesalahan": "Peraturan 14(9)(b) Peraturan-Peraturan Makanan 1985 [Ubah tarikh luput: P.14(7)]",
                "seksyen_hukuman": "Seksyen 32A / Peraturan 397 PPM 1985 dibaca bersama Akta Makanan 1983 [Akta 281]",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                "boleh_kompaun": "Sita semua stok tamat tempoh di bawah S.4(1)(f) Akta 281; boleh tawar kompaun S.32B atau buka IP bagi kesalahan besar/berulang.",
            },
            {
                "perihal": "Mengendali Mesin Jual Air (MJA) tanpa lesen KKM / Premis tak daftar FoSIM",
                "seksyen_kesalahan": "Peraturan 360C(4) PPM 1985 [MJA] / Peraturan 3(1) PPKM 2009 [Tiada Pendaftaran Premis]",
                "seksyen_hukuman": "Peraturan 397 PPM 1985 / Peraturan 3(2) PPKM 2009",
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
            "Rujuk silang agensi berkenaan supaya tindakan tidak dibatalkan atas alasan luar bidang kuasa (ultra vires)."
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
            "JANGAN paksa guna Akta 154 atau Akta 281 untuk aduan bau tahi lembu atau longkang tersumbat tanpa penemuan larva Aedes atau pengendalian makanan — kes berisiko dicabar ultra vires.",
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
            "dan COVID-19 diurus seperti jangkitan saluran pernafasan akut (ARI) biasa melalui penilaian klinikal doktor/MC serta pemakaian pelitup muka. "
            "Tanpa Perintah Pengawasan Seksyen 15(1) atau Pengasingan Seksyen 14 Akta 342 yang dikeluarkan dan diserahkan secara bertulis, TIADA kesalahan Seksyen 22(b) untuk dikompaun. "
            "Selain itu, Seksyen 12(1) Akta 342 BUKAN kesalahan boleh kompaun di bawah Jadual Pertama P.U. (A) 139/2025 (berkuat kuasa 1 Mei 2025) serta amat sukar dibuktikan tanpa HSO bertulis. "
            "Urusan cuti sakit/MC (Seksyen 60F Akta Kerja 1955), arahan pulang/WFH dan tatatertib pekerja ialah tanggungjawab majikan di bawah polisi HR & OSHA 1994 [Akta 514] (S.15 & S.24), manakala Unit CDC PKD menumpukan siasatan risiko kluster tempat kerja."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Kes COVID-19 Biasa Tanpa Perintah Bertulis S.15(1)/S.14 (Dasar Semasa KKM Pasca 15 Julai 2024)",
                "seksyen_kesalahan": "TIADA KESALAHAN BOLEH KOMPAUN di bawah Akta 342 (Pengurusan HR majikan: S.60F Akta Kerja 1955 / S.15 & S.24 OSHA 1994 [Akta 514])",
                "seksyen_hukuman": "Tindakan Kesihatan Awam Unit CDC PKD (nasihat pencegahan, pengesahan e-Notifikasi & penilaian risiko kluster tempat kerja)",
                "hukuman_maksimum": "Tiada kompaun Akta 342. Pertimbangan Perintah S.15(1) / Penutupan Disinfeksi S.18(1)(d) hanya jika wujud wabak/kluster serius.",
                "boleh_kompaun": "TIDAK BOLEH KOMPAUN — Jangan keluarkan notis kompaun tanpa perintah statutori bertulis yang sah diingkari.",
            },
            {
                "perihal": "HANYA JIKA Pekerja Ingkar Perintah Bertulis Seksyen 15(1) / Seksyen 14 Akta 342 Yang Sah Diserahkan (Kes Kluster/Wabak Khas)",
                "seksyen_kesalahan": "Seksyen 22(b) Akta 342 [APPPB 1988] (ingkar perintah sah pegawai diberi kuasa)",
                "seksyen_hukuman": "Seksyen 24 Akta 342 (Pindaan Akta A1742 berkuat kuasa 1 Mei 2025)",
                "hukuman_maksimum": "Individu: Denda maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya | Syarikat: Denda maks RM100,000",
                "boleh_kompaun": (
                    "Boleh dikompaun di bawah Seksyen 25 Akta 342 (Pindaan Akta A1742) & P.U. (A) 139/2025 "
                    "HANYA DENGAN KEIZINAN BERTULIS PENDAKWA RAYA: maks RM5,000 (individu) / RM50,000 (pertubuhan perbadanan), atau buka IP jika ingkar tegar."
                ),
            },
            {
                "perihal": "Rujukan Statutori Terhad: Sengaja Mendedahkan Orang Lain kepada Risiko Jangkitan (Kes Keterlaluan Sahaja — Bukan Rutin)",
                "seksyen_kesalahan": "Seksyen 12(1) dibaca bersama Seksyen 12(3) Akta 342 [APPPB 1988]",
                "seksyen_hukuman": "Seksyen 24 Akta 342 (Pindaan Akta A1742)",
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
            "Jalankan penilaian risiko epidemiologi Unit CDC di tempat kerja: kenal pasti sama ada kes sporadik tunggal atau wujud kluster/wabak aktif (beberapa kes positif/bergejala serentak atau melibatkan golongan rentan seperti wad/pusat jagaan/taska).",
            "Jika kes sporadik tanpa HSO/perintah bertulis: JANGAN tawarkan kompaun; beri nasihat kawalan jangkitan (pekerja dapatkan pemeriksaan doktor/MC jika tidak sihat, pakai pelitup muka, sanitasi permukaan & pengudaraan premis) dan jelaskan kepada majikan bahawa pengurusan cuti/WFH/arahan pulang adalah di bawah bidang kuasa HR majikan (Akta Kerja 1955 S.60F & OSHA 1994 Akta 514 S.15/S.24).",
            "HANYA jika siasatan Unit CDC mengesahkan kluster serius/risiko awam tinggi dan tiada kerjasama: pertimbangkan pengeluaran Perintah bertulis Seksyen 15(1) / Seksyen 14 (serahan tangan + tandatangan terima/saksi PPKP) dan/atau arahan disinfeksi/penutupan sementara premis Seksyen 18(1)(d)&(f). Tindakan S.22(b)/S.25 (dengan keizinan bertulis TPR) hanya diambil jika perintah bertulis sah itu diingkari.",
        ],
        "eksibit_wajib": [
            "Rekod Aduan Rasmi Majikan & Laporan Siasatan Epidemiologi Awal Unit CDC PKD (menilai status sporadik vs kluster tempat kerja)",
            "Semakan Cetakan e-Notifikasi Seksyen 10 Akta 342 / keputusan ujian makmal profesional (jika disahkan fasiliti kesihatan) + Sijil S.90A(2)",
            "Surat / Rekod Nasihat Pencegahan & Pengurusan Kes kepada Majikan dan Pekerja (bukti tindakan kesihatan awam PKD tanpa salah guna kuasa)",
            "HANYA JIKA ESKALASI S.22(b): Salinan asal Perintah S.15(1) / S.14 bertandatangan terima & saksi PPKP, bukti kehadiran mengingkari perintah (rekod kedatangan/CCTV + S.90A), percakapan S.112 KTJ saksi, dan Keizinan Bertulis Pendakwa Raya (jika tawar kompaun S.25)",
        ],
        "perangkap_kesilapan": [
            "PERANGKAP KOMPAUN ULTRA VIRES #1: JANGAN tawarkan kompaun Seksyen 22(b) tanpa Perintah bertulis Seksyen 15(1)/Seksyen 14 yang diserahkan secara sah — HSO mandatori MySejahtera telah dimansuhkan sejak 15 Julai 2024!",
            "PERANGKAP KOMPAUN ULTRA VIRES #2: JANGAN keluarkan notis kompaun di bawah Seksyen 12(1) Akta 342 — Seksyen 12(1)/(3) BUKAN kesalahan boleh kompaun dalam Jadual Pertama P.U. (A) 139/2025!",
            "PERANGKAP PINDAAN AKTA A1742 (1 MEI 2025): Di bawah Seksyen 25 baharu, had kompaun bukan lagi RM1,000 (kini maks RM5,000 individu / RM50,000 pertubuhan perbadanan) DAN pengkompaunan tertakluk kepada keizinan bertulis Pendakwa Raya serta hanya untuk seksyen dalam Jadual Pertama P.U. (A) 139/2025 (S.10(2), S.11(5), S.21A(3), S.22(b)/(c)/(d)).",
            "JANGAN jadikan Unit CDC/PPKP sebagai alat tatatertib HR majikan — arahan pulang kerja, cuti sakit (MC S.60F Akta Kerja 1955), WFH dan tatatertib pekerja ialah tanggungjawab majikan di bawah polisi syarikat & OSHA 1994 (Akta 514 S.15 & S.24).",
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
    akta_disyorkan: Optional[str] = None
    tajuk_nasihat: str = Field(...)
    keputusan_tindakan: str = Field(...)
    sesuai_buka_ip: bool = Field(...)
    alasan_keputusan: str = Field(...)
    cadangan_pertuduhan: List[_AdvisorChargeItemSchema] = Field(default_factory=list)
    sop_lapangan: List[str] = Field(default_factory=list)
    eksibit_wajib: List[str] = Field(default_factory=list)
    perangkap_kesilapan: List[str] = Field(default_factory=list)
    templat_ringkas: str = Field(...)


class UIPAdvisorService:
    """Enjin Penasihat Undang-Undang & Prosedur Lapangan UIP KKM."""

    MIN_SCENARIO_SCORE = 1.8

    def __init__(self, router: UIPModelRouter) -> None:
        self.router = router
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

    @classmethod
    def _build_rag_fallback_scenario(
        cls,
        question: str,
        akta_hint: str,
        rag_hits: List[Any],
    ) -> Dict[str, Any]:
        """Templat rujukan berasaskan RAG statutori apabila soalan di luar 17 templat teras."""
        top_hit = rag_hits[0] if rag_hits else None
        akta_label = (
            akta_hint
            if akta_hint and akta_hint != "Semua"
            else (top_hit.akta_code if top_hit else "Akta Kesihatan Awam KKM")
        )
        citations_summary = ", ".join(
            dict.fromkeys(cls._format_section_label(c.section, c.akta_code) for c in rag_hits[:3])
        ) or "Pangkalan data statutori tempatan"
        return {
            "id": "rag_custom_query",
            "akta_utama": akta_label,
            "tajuk": f"Rujukan Statutori UIP Mengikut Situasi Soalan ({akta_label})",
            "keputusan_tindakan": (
                f"RUJUK PERUNTUKAN STATUTORI TERPILIH ({citations_summary}) — SAHKAN FAKTA & SERAHAN NOTIS SEBELUM BUKA IP"
            ),
            "sesuai_buka_ip": False,
            "alasan_keputusan": (
                f"Soalan anda tiada padanan tepat dalam templat ringkas sedia ada, maka enjin memadankan peruntukan terdekat daripada stor undang-undang ({citations_summary}). "
                "Klik butang Analisa AI untuk huraian kes khusus mengikut elemen pembuktian dan SOP PPKP."
            ),
            "cadangan_pertuduhan": [
                {
                    "perihal": f"Peruntukan berkaitan daripada {c.akta_title}",
                    "seksyen_kesalahan": cls._format_section_label(c.section, c.akta_code),
                    "seksyen_hukuman": "Semak peruntukan penalti dalam petikan Akta di tab 'Petikan Akta'.",
                    "hukuman_maksimum": c.max_fine_hint or "Tertakluk had hukuman di bawah Akta berkaitan.",
                    "boleh_kompaun": c.is_compoundable_hint or "Semak jadual kompaun akta / rujuk Pegawai Pendakwa & UIP JKN.",
                }
                for c in rag_hits[:2]
            ],
            "sop_lapangan": [
                "Tunjukkan Kad Kuasa Rasmi KKM sebelum memulakan pemeriksaan atau siasatan di lokasi.",
                "Sahkan status entiti (MyKad OKT / carian rasmi SSM jika syarikat) dan bidang kuasa akta terpakai.",
                "Rekod gambar bertarikh + Sijil S.90A(2), catat Diari Siasatan, dan rujuk petikan Akta berkaitan atau klik Analisa AI untuk langkah kes khusus.",
            ],
            "eksibit_wajib": [
                "Diari Siasatan (DS) & Percakapan S.112 KTJ pegawai pengesan / saksi",
                "Gambar foto lokasi/kejadian berwarna bertarikh + Sijil Seksyen 90A(2) Akta Keterangan 1950",
                "Salinan Notis / Perintah bertulis bertandatangan terima (jika tindakan melibatkan pematuhan perintah)",
            ],
            "perangkap_kesilapan": [
                "Pastikan akta dan seksyen yang digunakan berpadanan dengan status fakta lapangan serta kuasa di bawah akta tersebut.",
            ],
            "templat_ringkas": (
                f"Rujukan siasatan awal di bawah {akta_label} berkaitan situasi: {question.strip()[:220]}."
            ),
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
        matched, kw_score, confident_match = self._match_composite_scenarios(
            question, akta_hint=akta_hint, scenario_id=scenario_id
        )
        rag_query = (
            f"{question} {matched['akta_utama']} {matched['tajuk']}"
            if confident_match
            else question
        )
        rag_hits = self.router.rag_store.search_statutes(
            query=rag_query,
            akta_filter=None if akta_hint in ("", "Semua") else akta_hint,
            top_k=5,
        )
        if not confident_match:
            matched = self._build_rag_fallback_scenario(question, akta_hint, rag_hits)

        citations_dict = [
            {
                "akta_code": c.akta_code,
                "akta_title": c.akta_title,
                "section": c.section,
                "text": c.text,
                "score": c.score,
            }
            for c in rag_hits
        ]

        # Mulakan dengan matriks SOP pakar tempatan / rujukan RAG (< 15ms)
        result: Dict[str, Any] = {
            "scenario_id": matched["id"],
            "akta_disyorkan": matched["akta_utama"],
            "tajuk_nasihat": matched["tajuk"],
            "keputusan_tindakan": matched["keputusan_tindakan"],
            "sesuai_buka_ip": matched["sesuai_buka_ip"],
            "alasan_keputusan": matched["alasan_keputusan"],
            "cadangan_pertuduhan": matched["cadangan_pertuduhan"],
            "sop_lapangan": matched["sop_lapangan"],
            "eksibit_wajib": matched["eksibit_wajib"],
            "perangkap_kesilapan": matched["perangkap_kesilapan"],
            "templat_ringkas": matched["templat_ringkas"],
            "engine_used": "Mod Pantas — Matriks SOP UIP KKM + Strict RAG"
            if confident_match
            else "Mod Pantas — Strict Statutory RAG UIP",
            "ai_attempted": False,
            "ai_succeeded": False,
            "fallback_reason": None,
        }

        effective_question = question.strip()
        if not effective_question or effective_question.lower().startswith("rujuk templat situasi ini"):
            effective_question = matched["tajuk"]

        # Benarkan AI berjalan apabila use_ai=True (walaupun scenario_id dipilih), ATAU apabila tiada padanan yakin
        ai_requested = bool(use_ai)
        auto_ai_needed = (not confident_match) and len(effective_question) >= 12
        should_call_ai = ai_requested or auto_ai_needed

        if should_call_ai and self.router._genai_client is None:
            result["ai_attempted"] = ai_requested
            if ai_requested:
                result["fallback_reason"] = (
                    "Kunci API Gemini belum dikonfigurasi pada pelayan (tetapkan GEMINI_API_KEY dalam Tetapan Sistem)."
                )
        elif should_call_ai:
            result["ai_attempted"] = True
            cache_key = "|".join(
                [
                    effective_question.lower(),
                    akta_hint,
                    scenario_id or "",
                    "deep" if ai_requested else "auto",
                    settings.reasoning_model,
                    settings.multimodal_model,
                    settings.standard_fallback_model,
                ]
            )
            cached_ai = self._consult_cache.get(cache_key)
            if cached_ai:
                result.update(cached_ai)
                result["ai_attempted"] = True
                result["ai_succeeded"] = True
                result["fallback_reason"] = None
                result["engine_used"] = f"{cached_ai.get('engine_used', 'Gemini AI')} [Cache]"
            else:
                rag_text = "\n\n".join(f"[{c.akta_title} | {c.section}]\n{c.text}" for c in rag_hits)
                charges_summary = "\n".join(
                    f"- {c.get('perihal', '')}: {c.get('seksyen_kesalahan', '')} | Hukuman: {c.get('seksyen_hukuman', '')}"
                    for c in matched.get("cadangan_pertuduhan", [])
                )
                ref_block = (
                    f"MATRIKS SOP RUJUKAN TERDEKAT ({matched['tajuk']}):\n"
                    f"Keputusan asas: {matched['keputusan_tindakan']}\n"
                    f"Pertuduhan rujukan:\n{charges_summary}\n\n"
                    if confident_match
                    else "TIADA TEMPLAT SEDIA ADA YANG PADAN — analisis terus daripada fakta soalan dan RUJUKAN AKTA SEBENAR di bawah.\n\n"
                )
                prompt = (
                    "Anda ialah Ketua UIP / Pegawai Pendakwa Kanan Kementerian Kesihatan Malaysia (KKM).\n"
                    "Jawab soalan PPKP ini menggunakan Bahasa Melayu kerja harian PPKP yang jelas, padat, terperinci, dan tepat (jangan guna ayat sastera).\n"
                    "ARAHAN KETAT:\n"
                    "1) Petik HANYA Seksyen dan Peraturan yang wujud secara sah dalam undang-undang Malaysia / RUJUKAN AKTA SEBENAR di bawah.\n"
                    "2) JANGAN menyalin membuta tuli templat rujukan jika fakta soalan PPKP berbeza (contoh: kes COVID-19 pasca 15 Julai 2024 tanpa HSO mandatori vs perintah bertulis S.15(1)/S.14, PTB Smear Negatif vs Smear Positif, kes bukan makanan seperti taska S.18(1)(d) vs S.11 Akta 281, atau kes rujukan silang Akta 171/366/586/260).\n"
                    "3) Ubah suai akta_disyorkan, tajuk_nasihat, keputusan_tindakan, sesuai_buka_ip, alasan_keputusan, SOP, eksibit dan perangkap_kesilapan agar 100% menepati situasi sebenar soalan.\n"
                    "4) Bagi setiap cadangan_pertuduhan, wajib sertakan 5 kunci tepat: perihal, seksyen_kesalahan, seksyen_hukuman, hukuman_maksimum, boleh_kompaun.\n\n"
                    f"SOALAN PPKP:\n{effective_question}\n\n"
                    f"{ref_block}"
                    f"RUJUKAN AKTA SEBENAR (RAG):\n{rag_text}"
                )
                model_candidates = (
                    [
                        "gemini-3.8-flash",
                        settings.multimodal_model,
                        settings.reasoning_model,
                        settings.standard_fallback_model,
                    ]
                    if ai_requested
                    else ["gemini-3.8-flash", settings.multimodal_model, settings.standard_fallback_model]
                )
                ai_json, used_model = self.router._call_gemini_structured_json(
                    model_candidates=model_candidates,
                    input_payload=prompt,
                    schema=_AdvisorLLMSchema.model_json_schema(),
                    temperature=0.1,
                    prefer_flash=not ai_requested,
                    prefer_fast_gc=True,
                    max_output_tokens=2600,
                )
                if ai_json:
                    normalized_charges = self._normalize_charge_items(
                        ai_json.get("cadangan_pertuduhan"),
                        matched.get("cadangan_pertuduhan", []),
                    )
                    ai_act = self._canonicalize_akta_code(
                        str(ai_json.get("akta_disyorkan") or ""),
                        result["akta_disyorkan"],
                    )
                    ai_patch = {
                        "akta_disyorkan": ai_act,
                        "tajuk_nasihat": str(ai_json.get("tajuk_nasihat") or result["tajuk_nasihat"]),
                        "keputusan_tindakan": str(ai_json.get("keputusan_tindakan") or result["keputusan_tindakan"]),
                        "sesuai_buka_ip": bool(ai_json.get("sesuai_buka_ip", result["sesuai_buka_ip"])),
                        "alasan_keputusan": str(ai_json.get("alasan_keputusan") or result["alasan_keputusan"]),
                        "cadangan_pertuduhan": normalized_charges,
                        "sop_lapangan": list(ai_json.get("sop_lapangan") or result["sop_lapangan"]),
                        "eksibit_wajib": list(ai_json.get("eksibit_wajib") or result["eksibit_wajib"]),
                        "perangkap_kesilapan": list(ai_json.get("perangkap_kesilapan") or result["perangkap_kesilapan"]),
                        "templat_ringkas": str(ai_json.get("templat_ringkas") or result["templat_ringkas"]),
                        "engine_used": f"{used_model} + Strict Statutory RAG",
                        "ai_attempted": True,
                        "ai_succeeded": True,
                        "fallback_reason": None,
                    }
                    if len(self._consult_cache) >= 64:
                        self._consult_cache.clear()
                    self._consult_cache[cache_key] = ai_patch
                    result.update(ai_patch)
                else:
                    err_detail = self.router._last_ai_error or (
                        "Analisa AI tidak dapat dicapai buat sementara waktu. Paparan menggunakan rujukan statutori tempatan."
                    )
                    logger.warning("Tanya Pakar fallback ke enjin tempatan: %s", err_detail)
                    result["ai_attempted"] = True
                    result["ai_succeeded"] = False
                    result["fallback_reason"] = err_detail

        result["draf_teks_kes_cadangan"] = self._build_prefilled_case_template(
            {**matched, "templat_ringkas": result["templat_ringkas"]},
            officer_profile=officer_profile,
        )
        result["statutory_citations"] = citations_dict
        return result
