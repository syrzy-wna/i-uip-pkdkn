"""Kes rujukan realistik kerja harian PPKP di PKD / UIP KKM (disemak mengikut Akta sebenar)."""

from __future__ import annotations

from typing import Dict, List

SAMPLE_CASES: List[Dict[str, str]] = [
    {
        "id": "kes-akta-852-vape",
        "title": "Kes 1: Akta 852 — Kedai Serbaneka Iklan & Pamer Vape di Kaunter",
        "akta_utama": "Akta 852",
        "workflow": "audit_ip",
        "badge": "Belum Ada Sijil 90A",
        "summary": "Operasi penguatkuasaan Akta 852 di kedai serbaneka. Sitaan dibuat di bawah Seksyen 35/36, tetapi Sijil Seksyen 90A untuk gambar cetak belum dilampirkan.",
        "text": """KERTAS SIASATAN UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)
NO. IP: PKD-PTG/UIP/852/2026/019
DAERAH: Petaling, Selangor
AKTA: Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] - Seksyen 7(1) & Seksyen 10(1) dibaca bersama Peraturan 6 P.U. (A) 260/2024

1. BUTIRAN PEMERIKSAAN
Tarikh Kejadian: 14 Oktober 2026
Masa Kejadian: 10.45 pagi
Nama Premis: Kedai Serbaneka Harmoni Jaya Sdn. Bhd.
No. SSM: 202101034892 (1435192-K)
Alamat Kejadian: No. 18, Jalan PJS 8/9, Bandar Sunway, 46150 Petaling Jaya, Selangor
Nama Suspek (OKT): Mohd Hafizuddin bin Kamaruddin
No. K/P: 890415-10-5321
No. Tel: 012-7748392
Pegawai Penyiasat (IO): PPKP Ahmad Faizal bin Ramli (No. Kad Kuasa: KKM-PKD-0842)
Saksi: Nurul Ain binti Zulkifli (No. K/P: 950821-08-6124, Juruwang Kedai)

2. RINGKASAN KESALAHAN
Kesalahan: Menyiarkan papan iklan promosi rokok elektronik (vape) di kaunter bayaran yang melanggar Seksyen 7(1) Akta 852 serta mempamerkan 24 kotak pod dan cecair rokok elektronik secara terbuka di kaunter jualan yang melanggar Seksyen 10(1) Akta 852 dibaca bersama Peraturan 6 Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Kawalan Penjualan) 2024 [P.U. (A) 260/2024].
PPKP Ahmad Faizal bin Ramli telah menunjukkan Kad Kuasa rasmi KKM-PKD-0842 (Seksyen 24(2) Akta 852) sebelum pemeriksaan dijalankan. Suspek mengaku sebagai pengarah dan pengurus premis (liabiliti pengarah di bawah Seksyen 49 Akta 852). Penyitaan dibuat di bawah Seksyen 35 Akta 852 dan Borang Senarai Benda Disita di bawah Seksyen 36 Akta 852 telah disediakan, satu salinan diserahkan kepada suspek dengan akuan tandatangan terima.

3. SEMAKAN DOKUMEN DALAM FAIL IP
- Laporan Pengadu (FIR) & Borang Pemeriksaan: Dilampirkan dan konsisten tarikh 14 Oktober 2026 jam 10.45 pagi.
- Diari Siasatan (DS): Disediakan mengikut susunan masa di bawah Seksyen 119 KTJ dari 14 Oktober 2026 hingga 16 Oktober 2026.
- Rakaman S.112 KTJ (Saksi): Percakapan saksi Nurul Ain binti Zulkifli diambil dalam Bahasa Melayu pada 14 Oktober 2026 jam 2.30 petang. Amaran Seksyen 112(2) dan (3) KTJ dibacakan mengikut Seksyen 112(4) KTJ dan ditandatangani oleh saksi serta IO mengikut Seksyen 112(5) KTJ.
- Rakaman S.112 KTJ (OKT): Diambil dalam Bahasa Melayu pada 15 Oktober 2026 setelah amaran Seksyen 112(2) & (3) KTJ dibaca dan ditandatangani tanpa paksaan.
- Barang Kes / Eksibit: 24 unit pod dan cecair vape dilabel Eksibit P4A-P4X, dilak menggunakan lak keselamatan KKM siri #88412 dan direkod keluar-masuk stor eksibit berkunci PKD Petaling.
- Carian SSM: Cetakan e-Info SSM bertarikh 15 Oktober 2026 dilampirkan menunjukkan suspek ialah pengarah Kedai Serbaneka Harmoni Jaya Sdn. Bhd.
- Pelan Lakar Premis: Pelan lakar kedudukan kaunter dan rak pameran yang ditandatangani oleh IO dilampirkan.
- Gambar Bukti Digital: 8 keping gambar warna diambil guna kamera Nikon Coolpix pejabat pada 14 Oktober 2026 jam 10.50 pagi dan dicetak melalui komputer pejabat. (CATATAN: Sijil Seksyen 90A Akta Keterangan 1950 masih belum ditandatangani dan belum dilampirkan dalam IP ini).
- Pendakwaan Terus & Had Masa: Kes masih dalam had masa pendakwaan; kesalahan Seksyen 7(1) dan Seksyen 10(1) Akta 852 tidak boleh dikompaun di bawah P.U. (A) 259/2024 (tiada tawaran kompaun — terus dibuka IP dengan bukti serahan Borang Senarai Benda Disita S.36 bertandatangan terima dan memohon Izin Mendakwa TPR).
- Borang 114 & Pengaduan Borang 143: Draf pertuduhan berasingan disediakan di bawah Seksyen 7(1) (dihukum di bawah Seksyen 7(2)(b) bagi syarikat) dan Seksyen 10(1) dibaca bersama Peraturan 6 P.U. (A) 260/2024 (dihukum di bawah Seksyen 10(2)(b)), dan menunggu Izin Mendakwa TPR.
""",
    },
    {
        "id": "kes-akta-281-makanan",
        "title": "Kes 2: Akta Makanan 1983 — Premis Kotor & Makanan Tercemar (Sedia Hantar TPR)",
        "akta_utama": "Akta 281",
        "workflow": "ip_builder",
        "badge": "Lengkap / Sedia TPR",
        "summary": "IP lengkap di bawah Peraturan 11(1) & 34 PPKM 2009 [P.U. (A) 95/2009], Notis Seksyen 32B, Perakuan Juruanalisis Makanan S.19, Rakaman S.112 dan Sijil 90A.",
        "text": """KERTAS SIASATAN UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)
NO. IP: PKD-KLG/UIP/281/2026/042
DAERAH: Klang, Selangor
AKTA: Akta Makanan 1983 [Akta 281] & Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] - Peraturan 11(1) & Peraturan 31(2)

1. BUTIRAN PEMERIKSAAN
Tarikh Kejadian: 03 November 2026
Masa Kejadian: 09.15 pagi
Nama Premis: Restoran Bintang Utara Bistro
No. SSM: SA0549123-M
Alamat Kejadian: No. 42, Jalan Batu Nilam 4, Bandar Bukit Tinggi, 41200 Klang, Selangor
Nama Pemilik (OKT): Sivakumar a/l Subramaniam
No. K/P: 781104-10-5891
No. Tel: 019-3321984
Pegawai Penyiasat (IO): PPKP Siti Nurhaliza binti Hassan (No. Kad Kuasa: KKM-SEL-2190)
Saksi: Muhammad Danish bin Azman (No. K/P: 980210-10-5117, PPKP Pengiring)

2. RINGKASAN KESALAHAN
Kesalahan: Menjalankan premis makanan dalam keadaan tidak bersih dengan penemuan najis tikus di meja penyediaan makanan, lipas hidup di bawah rak pinggan, perangkap minyak tersumbat (melanggar Peraturan 11(1) dan Peraturan 34 PPKM 2009), serta sebagai tuan punya premis gagal memastikan pengendali makanan mendapat suntikan vaksinasi antitifoid yang sah (melanggar Peraturan 31(2) PPKM 2009) dan tanpa Sijil Latihan Pengendali Makanan (Peraturan 30(1) PPKM 2009). Perintah Penutupan Premis Tidak Suci di bawah Seksyen 11 Akta Makanan 1983 telah disampaikan dan ditandatangani terima pada 03 November 2026.

3. SEMAKAN DOKUMEN DALAM FAIL IP
- Laporan Pengadu (FIR) & Borang Pemeriksaan Premis Makanan (KMM): Lengkap dengan tarikh dan masa yang sama iaitu 03 November 2026 jam 09.15 pagi.
- Carian SSM & Lesen PBT: Cetakan e-Info SSM SA0549123-M (Seksyen 33A untuk liabiliti syarikat jika berkenaan) dan salinan lesen premis PBT dilampirkan.
- Rakaman S.112 KTJ: Percakapan Saksi 1 (Muhammad Danish bin Azman) dan OKT (Sivakumar a/l Subramaniam) diambil dengan amaran Seksyen 112(2) & (3) KTJ (menurut Seksyen 112(4) KTJ), dibaca semula dan ditandatangani oleh semua pihak serta jurubahasa Bahasa Tamil mengikut Seksyen 112(5) KTJ.
- Diari Siasatan (DS): Lengkap mengikut susunan masa (Seksyen 119 KTJ) dari hari operasi sehingga IP ditutup.
- Barang Kes & Perakuan Juruanalisis Makanan (Seksyen 19): Sampel makanan siap masak yang tercemar diambil mengikut tatacara persampelan Akta 281, dilabel tanda eksibit (Eksibit P1–P3), dilak dengan lak rasmi KKM siri #KLG-331, direkod keluar-masuk stor eksibit PKD Klang, dan dihantar ke Makmal Kesihatan Awam Kebangsaan (MKAK). Perakuan Juruanalisis Makanan di bawah Seksyen 19 Akta Makanan 1983 mengesahkan pencemaran bakteria patogen (salinan perakuan diserahkan kepada OKT sekurang-kurangnya 10 hari genap sebelum perbicaraan menurut Seksyen 19(2)); manakala penemuan najis tikus dan lipas dibuktikan melalui Borang Pemeriksaan KMM serta 12 keping gambar berwarna yang jelas, bertarikh 03 November 2026, berkapsyen lokasi tepat dan dirakam oleh jurugambar PPKP Muhammad Danish bin Azman.
- Kad Kuasa Pegawai: Salinan Kad Kuasa rasmi KKM (Seksyen 3 Akta Makanan 1983) dan surat pelantikan PPKP pemeriksa serta Pegawai Penyiasat (IO) dilampirkan.
- Sijil Seksyen 90A(2) Akta Keterangan 1950: Sijil Seksyen 90A lengkap dengan butiran kamera, komputer Dell OptiPlex pejabat PKD Klang, pencetak HP, serta klausa sepanjang pengetahuan dan kepercayaan ditandatangani oleh PPKP Siti Nurhaliza binti Hassan bagi 12 keping gambar digital dan cetakan e-Info SSM.
- Pelan Lakar Premis: Pelan lakar kawasan dapur, stor kering dan kedudukan eksibit yang lengkap bertandatangan IO serta bertarikh 03 November 2026 dilampirkan.
- Borang 114, Pengaduan Borang 143 & Fakta Kes: Fakta Kes disusun objektif mengikut kronologi sebelum, semasa dan selepas pemeriksaan selari dengan Laporan Pengadu (FIR) dan Borang 114. Draf pertuduhan berasingan di bawah Peraturan 11(1) dibaca bersama Peraturan 11(2) PPKM 2009 serta Peraturan 31(2) dibaca bersama Peraturan 31(3) PPKM 2009 disemak tanpa pertindihan pertuduhan, berserta draf permohonan Izin Mendakwa TPR di bawah Seksyen 32A Akta Makanan 1983.
- Notis Seksyen 32B & Kompaun Seksyen 33: Notis Seksyen 32B beserta tawaran kompaun RM 500.00 di bawah Seksyen 33 Akta Makanan 1983 telah diserahkan secara tangan dengan akuan terima; pengesahan Unit Hasil menunjukkan tempoh bayaran 14 hari sudah tamat tanpa bayaran dan masih dalam had masa pendakwaan.
""",
    },
    {
        "id": "kes-akta-154-aedes",
        "title": "Kes 3: Akta 154 — Pembiakan Aedes di Tapak Binaan (Ada Kuiri Kritikal)",
        "akta_utama": "Akta 154",
        "workflow": "audit_ip",
        "badge": "Kritikal / Kuiri TPR",
        "summary": "IP kes Aedes di tapak binaan yang mempunyai tarikh bercanggah, tiada nombor lak botol spesimen, S.112 belum ditandatangan, dan tiada Sijil 90A.",
        "text": """KERTAS SIASATAN UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)
NO. IP: PKD-JHR/UIP/154/2026/007
DAERAH: Johor Bahru, Johor
AKTA: Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154] - Seksyen 13(1) dibaca bersama Seksyen 13(2) dan boleh dihukum di bawah Seksyen 23(a)

1. BUTIRAN PEMERIKSAAN
Tarikh Kejadian: 20 September 2026
Masa Kejadian: 08.40 pagi
Nama Premis: Tapak Pembinaan Projek Residensi Maju (Apex Bina Construction Sdn. Bhd.)
No. SSM: 201801009821 (1271825-P)
Alamat Kejadian: Lot 4501, Mukim Tebrau, 81100 Johor Bahru, Johor
Nama Pengurus Tapak (OKT): Tan Wei Ming
No. K/P: 840919-01-5523
Pegawai Penyiasat (IO): PPKP Zulhilmi bin Mansor

2. RINGKASAN & MASALAH DOKUMEN IP
Kesalahan: Membiarkan air jernih bertakung dalam 3 bekas plastik terbuka di tingkat bawah tapak binaan yang membiak larva nyamuk Aedes aegypti.
- Borang Sampel / Eksibit: 3 botol spesimen larva dikutip, tetapi borang serahan ke makmal entomologi tidak mempunyai nombor lak (seal) yang jelas pada rantaian barang kes.
- Laporan Entomologi: Mengesahkan spesies Aedes aegypti tetapi tarikh kutipan tertulis 22 September 2026 yang berbeza dengan tarikh pemeriksaan 20 September 2026.
- Rakaman Seksyen 112 KTJ: Draf percakapan pekerja tapak ada tetapi belum ditandatangani oleh saksi dan tiada nota amaran Seksyen 112(2)/(3) KTJ.
- Sijil Seksyen 90A Akta Keterangan 1950: Tiada Sijil Seksyen 90A dilampirkan bagi gambar digital tempat pembiakan.
- Borang 114: Draf pertuduhan masih mencampurkan Seksyen 8 dan Seksyen 13 dalam satu pertuduhan yang sama (pertindihan pertuduhan).
""",
    },
    {
        "id": "kes-akta-342-tibi",
        "title": "Kes 4: Akta 342 — Pesakit Tibi (PTB Smear Positif) Cicir Rawatan (Templat Sebenar PKD/JKNS)",
        "akta_utama": "Akta 342",
        "workflow": "ip_builder",
        "badge": "Templat Sebenar Tibi",
        "summary": "Struktur lengkap IP Kes Tibi (Seksyen 22(b) & 24(a) Akta 342 Pindaan Akta A1742) berpandukan aliran PKD, JKNS, Izin Dakwa TPR, Borang TBIS, Mahkamah 111/114/143 & Pemberatan Hukuman.",
        "text": """KERTAS SIASATAN UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)
NO. IP: PKD-SPG/UIP/342/2026/010
DAERAH: Sepang, Selangor
AKTA: Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] - Seksyen 22(b) dibaca bersama Seksyen 24(a) (Pindaan Akta A1742)

1. BUTIRAN PEMERIKSAAN & PESAKIT (OKS)
Tarikh Kejadian: 13 Januari 2026
Masa Kejadian: 8.30 pagi
Nama Premis: Klinik Kesihatan Sungai Pelek
Alamat Kejadian: No. 39, Taman KSM, 43950 Sungai Pelek, Sepang, Selangor
Nama Suspek (OKT): Muthusamy a/l Ramasamy
No. K/P: 641228-10-5599
No. Tel: 017-6483143
Pegawai Penyiasat (IO): PPKP Ahmad Rasfanjani bin Jawahir (No. Kad Kuasa: KKM-SEL-0412)
Pegawai Pengadu: PPKP Nur Hafizah binti Mohamad Shahidin (No. K/P: 860222-26-5224, Kad Kuasa: KKM-SEL-0659)
Saksi: PPKP Geraldine Neo Hui Hwang (No. K/P: 900829-13-6334, PPKP Pengiring)

2. RINGKASAN KESALAHAN & KRONOLOGI KES TIBI
Kesalahan: Tidak mematuhi perintah sah yang dikeluarkan oleh pegawai diberi kuasa iaitu enggan menjalani dan menyambung semula rawatan penyakit Tuberkulosis (PTB Smear Positif) sejenis penyakit berjangkit di Klinik Kesihatan Sungai Pelek sebagaimana diarahkan di bawah Notis Arahan Menjalani Rawatan Penyakit Berjangkit bertarikh 28 Disember 2025 (tempoh 7 hari dan tarikh rawatan ditetapkan 10 Januari 2026). Perbuatan ini melanggar Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] dan boleh dihukum di bawah Seksyen 24(a) akta yang sama (sebagaimana dipinda oleh Akta A1742).

3. DOKUMEN WAJIB & EKSHIBIT KES TIBI (P1 - P5 & TBIS)
- Kad Kuasa Pegawai & Identiti OKS (Individu): Salinan Kad Kuasa rasmi KKM (Seksyen 2 & 3 Akta 342) serta surat pelantikan pegawai pemeriksa/IO dilampirkan. Oleh kerana OKS ialah pesakit individu (bukan syarikat), semakan identiti MyKad/JPN dilampirkan.
- P1: Fakta Kes bertandatangan Pegawai Pendakwa PKD.
- P2: Borang Notifikasi Penyakit Berjangkit (Peraturan Borang Notis 2005 / e-Notifikasi).
- P3: Borang Permohonan & Keputusan Makmal TBIS 20C yang mengesahkan kahak PTB Smear Positif (1+ / 2+).
- P4: Notis Arahan Menjalani Rawatan Penyakit Berjangkit bertarikh 28 Disember 2025 yang diserahkan secara tangan dengan akuan tandatangan terima OKS serta saksi PPKP Nur Hafizah binti Mohamad Shahidin.
- P5: Notis Pesakit Tibi Cicir Rawatan (TBIS 10D) dan Maklum Balas Pengesanan (TBIS 10Da) bertarikh 13 Januari 2026.
- Dokumen Sokongan TBIS: Borang Permulaan Rawatan TBIS 10A-1, Kad Rawatan TBIS 10-I, Maklumat Penyiasatan Kes Tibi TBIS 10A-3, dan Surat Pelepasan Atas Risiko Sendiri (AOR).
- Rakaman S.112 KTJ: Percakapan Saksi 1 (PPKP Nur Hafizah binti Mohamad Shahidin) dan Saksi Pengiring (PPKP Geraldine Neo Hui Hwang) dirakam lengkap dengan amaran Seksyen 112(2) & (3) KTJ (menurut S.112(4)), dibaca semula dan ditandatangani semua pihak menurut Seksyen 112(5) KTJ.
- Gambar Bukti, Pelan Lakar & Sijil Seksyen 90A(2): 6 keping gambar bukti berwarna bertarikh beserta pelan lakar lokasi kediaman OKS yang bertandatangan IO dilampirkan. Sijil Seksyen 90A(2) Akta Keterangan 1950 lengkap butiran kamera, komputer pejabat PKD Sepang, pencetak HP dan klausa sepanjang pengetahuan dan kepercayaan ditandatangani bagi gambar digital dan cetakan e-Notifikasi.
- Diari Siasatan (DS): Disusun lengkap oleh kedua-dua PPKP pengesan dan IO mengikut Seksyen 119 KTJ dari tarikh arahan doktor sehingga pengesanan gagal.
- Kertas Minit (Am 6) & Kertas Cadangan IO: Disemak oleh KPPKP U7 daerah dan UIP JKN Selangor (PKP U9) serta mendapat Izin Mendakwa TPR Selangor di bawah Seksyen 376(3) KTJ. Kes Seksyen 22(b) Akta 342 ini dibawa terus ke Mahkamah Majistret (tiada tawaran kompaun).
- Borang Mahkamah: Pengaduan kepada Majistret (Mahkamah 143), Saman (Mahkamah 111), Kertas Pertuduhan (Mahkamah 114), serta 6 Poin Pemberatan Hukuman (risiko penularan awam & Multi-Drug Resistant TB [MDR-TB]).
""",
    },
]
