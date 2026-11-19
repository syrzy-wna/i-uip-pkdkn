"""Modul Tanya Pakar UIP (Penasihat Kes, Seksyen Pertuduhan & SOP Lapangan KKM).

Membantu PPKP / IO / Pegawai Pendakwa menjawab soalan sebenar di lapangan:
- Kesalahan ini nak caj seksyen apa (Kesalahan & Hukuman tepat)?
- Boleh kompaun dahulu, perintah tutup premis, atau wajib buka IP terus?
- Apa prosedur lapangan langkah demi langkah & apa dokumen/eksibit wajib?
- Apa perangkap kesilapan biasa yang sering kena kuiri TPR?
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.model_router import UIPModelRouter

UIP_SCENARIO_LIBRARY: List[Dict[str, Any]] = [
    {
        "id": "ak852_pamer_vape",
        "akta_utama": "Akta 852",
        "tajuk": "Kedai Serbaneka Pamer Rokok / Vape Secara Terbuka di Kaunter",
        "keywords": [
            "pamer", "pameran", "terbuka", "kaunter", "vape", "rokok elektronik",
            "pod", "kedai runcit", "serbaneka", "kabinet", "ak 852", "852", "260/2024",
        ],
        "keputusan_tindakan": "SITA & BUKA IP TERUS (atau Notis S.47 / Kompaun S.48 ikut arahan KKM)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Pameran terbuka vape atau rokok di kaunter jualan merupakan kesalahan larangan pameran "
            "berimpak komersial tinggi di bawah P.U. (A) 260/2024. Barang pameran wajib disita di bawah "
            "Seksyen 35 & 36 Akta 852 bagi memelihara eksibit sebelum dibuka IP atau dikompaun mengikut jadual P.U. (A) 259/2024."
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
            "budak sekolah", "pelajar", "tepi jalan", "hisap rokok", "menghisap", "seragam sekolah",
            "pondok bas", "bawah umur", "remaja", "obd", "seksyen 17", "17(1)", "membeli rokok",
        ],
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
            "jual rokok", "jual vape", "menjual", "penjual", "pekedai", "kaunter jual",
            "resit", "18 tahun", "obd", "seksyen 13", "bawah umur",
        ],
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
            "merokok", "tempat makan", "restoran", "kedai makan", "larangan", "qr", "tanda amaran",
            "ashtray", "bekas abu", "seksyen 16", "seksyen 18", "257/2024", "258/2024",
        ],
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
            "iklan", "poster", "bunting", "papan iklan", "promosi", "tajaan", "skrin", "media sosial",
            "seksyen 7", "seksyen 9",
        ],
        "keputusan_tindakan": "SITA POSTER/IKLAN & BUKA IP TERUS (atau Kompaun ikut jadual P.U.(A) 259/2024)",
        "sesuai_buka_ip": True,
        "alasan_keputusan": (
            "Kes iklan dan promosi vape melanggar Seksyen 7(1) / Seksyen 9(1) Akta 852. Bahan iklan fizikal perlu disita di bawah S.35/36, "
            "atau jika iklan dipapar di skrin/internet, perlu tangkapan skrin bercetak dengan Sijil Seksyen 90A(2) untuk membuka IP."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Menyiarkan / mempamerkan iklan produk merokok atau rokok elektronik",
                "seksyen_kesalahan": "Seksyen 7(1) Akta 852 [atau Seksyen 9(1) jika promosi harga/diskaun]",
                "seksyen_hukuman": "Seksyen 7(2) [Individu] / Seksyen 7(3) [Pertubuhan Perbadanan] Akta 852",
                "hukuman_maksimum": "Individu: Denda maks RM20,000 / penjara 1 tahun | Syarikat: Denda RM20,000 – RM100,000",
                "boleh_kompaun": "Boleh dikompaun mengikut jadual P.U. (A) 259/2024 atau terus Buka IP bagi kesalahan serius/berulang.",
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
            "premis kotor", "kotor", "tikus", "najis tikus", "lipas", "lalat", "lilati", "perangkap minyak",
            "tutup premis", "seksyen 11", "peraturan 11", "peraturan 34", "70%",
        ],
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
            "tifoid", "typhoid", "suntikan", "vaksin", "lpm", "latihan pengendali", "apron",
            "penutup kepala", "kasut", "kuku", "cincin", "peraturan 30", "peraturan 31", "peraturan 32", "peraturan 33",
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
                "seksyen_kesalahan": "Peraturan 32(1) PPKM 2009 [Kuku/jam/cincin: Peraturan 33(1)]",
                "seksyen_hukuman": "Peraturan 32(2) PPKM 2009 [Peraturan 33(2)]",
                "hukuman_maksimum": "Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun",
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
            "keracunan", "benda asing", "paku", "kaca", "bangkai", "beracun", "kimia", "bakteria",
            "persampelan", "sampel makanan", "juruanalisis", "mkak", "seksyen 13", "seksyen 13b", "seksyen 19",
        ],
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
            "aedes", "larva", "jentik", "jentik-jentik", "denggi", "takungan", "nyamuk",
            "seksyen 13", "ak 154", "154", "entomologi", "kediaman", "premis",
        ],
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
            "tapak bina", "tapak pembinaan", "construction", "kontraktor", "cidb", "seksyen 8",
            "perintah tutup tapak", "pemaju", "loa", "projek",
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
            "tibi", "tb", "tuberkulosis", "cicir rawatan", "cicir ubat", "defaulter", "smear positif",
            "tbis", "mdr-tb", "penyakit berjangkit", "seksyen 22", "seksyen 24", "ak 342", "342", "arahan rawatan",
        ],
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
]


class _AdvisorLLMSchema(BaseModel):
    tajuk_nasihat: str = Field(...)
    keputusan_tindakan: str = Field(...)
    sesuai_buka_ip: bool = Field(...)
    alasan_keputusan: str = Field(...)
    cadangan_pertuduhan: List[Dict[str, str]] = Field(default_factory=list)
    sop_lapangan: List[str] = Field(default_factory=list)
    eksibit_wajib: List[str] = Field(default_factory=list)
    perangkap_kesilapan: List[str] = Field(default_factory=list)
    templat_ringkas: str = Field(...)


class UIPAdvisorService:
    """Enjin Penasihat Undang-Undang & Prosedur Lapangan UIP KKM."""

    def __init__(self, router: UIPModelRouter) -> None:
        self.router = router
        self._consult_cache: Dict[str, Dict[str, Any]] = {}

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
    def _match_composite_scenarios(
        question: str, akta_hint: str = "Semua", scenario_id: Optional[str] = None
    ) -> tuple[Dict[str, Any], float]:
        if scenario_id:
            for s in UIP_SCENARIO_LIBRARY:
                if s["id"] == scenario_id:
                    return s, 10.0

        q_low = question.lower()
        scored: List[tuple[float, float, Dict[str, Any]]] = []
        for s in UIP_SCENARIO_LIBRARY:
            kw_score = 0.0
            for kw in s["keywords"]:
                if kw in q_low:
                    kw_score += 2.2 if len(kw) > 5 else 1.2
            if any(w in q_low for w in s["tajuk"].lower().split() if len(w) >= 5):
                kw_score += 0.6
            act_bonus = 1.0 if (akta_hint and akta_hint != "Semua" and akta_hint == s["akta_utama"]) else 0.0
            scored.append((kw_score + act_bonus, kw_score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        primary_total, primary_kw, primary = scored[0]

        # Gabung secara automatik jika pengguna bertanya tentang 2 kesalahan serentak (cth: kotor + tiada tifoid)
        merged = dict(primary)
        if len(scored) > 1:
            sec_total, sec_kw, secondary = scored[1]
            if sec_kw >= 2.8 and primary_kw >= 2.4 and secondary["id"] != primary["id"]:
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

        return merged, primary_kw

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

    def consult(
        self,
        question: str,
        akta_hint: str = "Semua",
        scenario_id: Optional[str] = None,
        use_ai: bool = False,
        officer_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        matched, kw_score = self._match_composite_scenarios(
            question, akta_hint=akta_hint, scenario_id=scenario_id
        )
        rag_hits = self.router.rag_store.search_statutes(
            query=f"{question} {matched['akta_utama']} {matched['tajuk']}",
            akta_filter=None if akta_hint in ("", "Semua") else akta_hint,
            top_k=4,
        )
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

        # Mulakan dengan matriks SOP pakar tempatan (< 15ms)
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
            "engine_used": "Mod Pantas — Matriks SOP UIP KKM + Strict RAG",
        }

        # Panggil AI Gemini Flash HANYA jika user aktifkan Mod AI atau soalan di luar pustaka (<1.2)
        should_call_ai = (
            self.router._genai_client is not None
            and not scenario_id
            and len(question.strip()) >= 12
            and (use_ai or kw_score < 1.2)
        )
        if should_call_ai:
            cache_key = f"{question.strip().lower()}|{akta_hint}"
            cached_ai = self._consult_cache.get(cache_key)
            if cached_ai:
                result.update(cached_ai)
                result["engine_used"] = f"{cached_ai.get('engine_used', 'Gemini Flash')} [Cache]"
            else:
                rag_text = "\n\n".join(f"[{c.akta_title} | {c.section}]\n{c.text}" for c in rag_hits)
                prompt = (
                    "Anda ialah Ketua UIP / Pegawai Pendakwa Kanan Kementerian Kesihatan Malaysia (KKM).\n"
                    "Jawab soalan PPKP ini menggunakan Bahasa Melayu kerja harian PPKP yang jelas, padat, dan tepat (jangan guna ayat sastera).\n"
                    "ARAHAN KETAT:\n"
                    "1) Petik HANYA Seksyen dan Peraturan yang wujud dalam RUJUKAN AKTA SEBENAR atau MATRIKS SOP UIP di bawah.\n"
                    "2) Nyatakan jelas: (a) Seksyen Kesalahan & Hukuman boleh dicaj, (b) Boleh kompaun dahulu atau wajib buka IP terus / perintah tutup, "
                    "(c) Langkah SOP lapangan, (d) Eksibit wajib, dan (e) Perangkap kesilapan biasa.\n\n"
                    f"SOALAN PPKP:\n{question}\n\n"
                    f"MATRIKS SOP RUJUKAN PALING HAMPIR ({matched['tajuk']}):\n"
                    f"Keputusan asas: {matched['keputusan_tindakan']}\n"
                    f"Pertuduhan rujukan: {matched['cadangan_pertuduhan']}\n\n"
                    f"RUJUKAN AKTA SEBENAR (RAG):\n{rag_text}"
                )
                ai_json, used_model = self.router._call_gemini_structured_json(
                    model_candidates=[
                        settings.multimodal_model,
                        settings.reasoning_model,
                    ],
                    input_payload=prompt,
                    schema=_AdvisorLLMSchema.model_json_schema(),
                    temperature=0.1,
                    prefer_flash=True,
                )
                if ai_json:
                    ai_patch = {
                        "tajuk_nasihat": ai_json.get("tajuk_nasihat") or result["tajuk_nasihat"],
                        "keputusan_tindakan": ai_json.get("keputusan_tindakan") or result["keputusan_tindakan"],
                        "sesuai_buka_ip": ai_json.get("sesuai_buka_ip", result["sesuai_buka_ip"]),
                        "alasan_keputusan": ai_json.get("alasan_keputusan") or result["alasan_keputusan"],
                        "cadangan_pertuduhan": ai_json.get("cadangan_pertuduhan") or result["cadangan_pertuduhan"],
                        "sop_lapangan": ai_json.get("sop_lapangan") or result["sop_lapangan"],
                        "eksibit_wajib": ai_json.get("eksibit_wajib") or result["eksibit_wajib"],
                        "perangkap_kesilapan": ai_json.get("perangkap_kesilapan") or result["perangkap_kesilapan"],
                        "templat_ringkas": ai_json.get("templat_ringkas") or result["templat_ringkas"],
                        "engine_used": f"{used_model} + Strict Statutory RAG",
                    }
                    if len(self._consult_cache) >= 64:
                        self._consult_cache.clear()
                    self._consult_cache[cache_key] = ai_patch
                    result.update(ai_patch)

        result["draf_teks_kes_cadangan"] = self._build_prefilled_case_template(
            {**matched, "templat_ringkas": result["templat_ringkas"]},
            officer_profile=officer_profile,
        )
        result["statutory_citations"] = citations_dict
        return result
