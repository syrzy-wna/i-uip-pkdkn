"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  BookOpenCheck,
  Compass,
  FileText,
  FolderTree,
  Layers,
  ShieldAlert,
} from "lucide-react";

type GuideSection = "cara_guna" | "carta_alir" | "cheat_sheet" | "fail_5w1h" | "kesilapan_maut";

export default function AppGuidePanel() {
  const [section, setSection] = useState<GuideSection>("cara_guna");

  const tabs: Array<{ id: GuideSection; label: string; icon: React.ReactNode }> = [
    { id: "cara_guna", label: "1. Cara Guna Aplikasi", icon: <Compass className="h-3.5 w-3.5" /> },
    { id: "carta_alir", label: "2. Carta Alir Kerja UIP", icon: <Layers className="h-3.5 w-3.5" /> },
    { id: "cheat_sheet", label: "3. Cheat Sheet 4 Akta", icon: <BookOpenCheck className="h-3.5 w-3.5" /> },
    { id: "fail_5w1h", label: "4. Susunan IP & 5W1H B.114", icon: <FolderTree className="h-3.5 w-3.5" /> },
    { id: "kesilapan_maut", label: "5. 10 Kesilapan Maut PPKP", icon: <ShieldAlert className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-gradient-to-r from-[#0f2744] to-slate-800 p-4 text-white">
        <h3 className="text-sm font-bold">
          Buku Panduan Lengkap UIP-Command &amp; SOP Penguatkuasaan UIP KKM
        </h3>
        <p className="mt-1 text-xs text-slate-200">
          Rujukan lengkap harian untuk PPKP baharu dan Pegawai Penyiasat (IO) PKD — dari tindakan lokasi,
          pengkompaunan, penyediaan Kertas Siasatan (IP) hingga semakan Pra-TPR &amp; Mahkamah.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSection(t.id)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                section === t.id
                  ? "bg-amber-400 text-slate-950 shadow-sm"
                  : "bg-white/10 text-slate-100 hover:bg-white/20"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* 1. CARA GUNA APLIKASI */}
      {section === "cara_guna" && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-1.5">
            <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
              LANGKAH A — AKAUN PEGAWAI
            </span>
            <h4 className="text-xs font-bold text-slate-900">1. Daftar / Log Masuk Akaun Pegawai</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Klik butang <strong>Akaun Pegawai</strong> di bar atas untuk mendaftar nama penuh, jawatan,
              No. Kad Kuasa KKM, PKD/JKN, Mahkamah Majistret dan model komputer/kamera pejabat.
              Setiap kali anda menjana IP atau Notis Kompaun, butiran ini diisi automatik tanpa perlu taip semula.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-1.5">
            <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-800">
              LANGKAH B — TANYA PAKAR UIP
            </span>
            <h4 className="text-xs font-bold text-slate-900">2. Rujuk Seksyen &amp; Prosedur Kes</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Tidak pasti kes tertentu perlu kompaun dulu, perintah tutup premis atau buka IP terus?
              Buka tab <strong>Tanya Pakar UIP</strong>, taip situasi kejadian atau klik 10 kad situasi.
              Klik <em>Guna Cadangan Ini</em> untuk memindahkan draf ke Editor IP secara 1-klik.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-1.5">
            <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
              LANGKAH C — NOTIS KOMPAUN &amp; EKSTRAK GAMBAR
            </span>
            <h4 className="text-xs font-bold text-slate-900">3. Semak 10 Perkara Notis Kompaun</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Muat naik gambar SSM / barang kes di sebelah kiri dan tekan <strong>Baca Gambar / PDF</strong>.
              Buka tab <strong>Semak Notis Kompaun</strong> untuk mengesahkan had denda statutori (cth: Akta 154 maks RM500),
              format MyKad 12 digit, dan kesahihan saksi jika OKS enggan tandatangan.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-1.5">
            <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800">
              LANGKAH D — AUDIT PRA-TPR &amp; .DOCX RASMI
            </span>
            <h4 className="text-xs font-bold text-slate-900">4. Audit 20 Kriteria &amp; Muat Turun IP (.docx)</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Sebelum hantar IP kepada KPPKP atau TPR, klik <strong>Semak IP (20 Perkara)</strong> untuk menangkap ralat
              seperti percanggahan tarikh, kesilapan petikan seksyen (S.38/S.44/Akta 514/Peraturan 30), atau ketiadaan Sijil 90A.
              Selepas itu klik <strong>Jana Fail IP &amp; Borang 114</strong> dan muat turun fail Word rasmi (<code>.docx</code>).
            </p>
          </div>
        </div>
      )}

      {/* 2. CARTA ALIR 4 FASA KERJA UIP */}
      {section === "carta_alir" && (
        <div className="space-y-3">
          {[
            {
              fasa: "FASA 1: SEMASA OPERASI DI LAPANGAN (60 MINIT PERTAMA)",
              color: "border-blue-300 bg-blue-50/50",
              steps: [
                "Perkenalkan diri & tunjukkan Kad Kuasa Rasmi KKM di hadapan saksi pengiring.",
                "Ambil gambar foto digital sudut jauh dan dekat SEBELUM menyentuh barang bukti atau meminta pekerja membersihkannya.",
                "Jalankan penyitaan (S.35/36 Akta 852 / S.4 Akta 281), Perintah Tutup (S.11 Akta 281 / S.8 Akta 154), atau kutip larva Aedes berlak siri KKM.",
                "Serahkan salinan notis/borang kepada OKS dengan tandatangan terima (jika enggan tandatangan, catat 'Enggan Tandatangan' berserta saksi PPKP).",
                "Lukis Pelan Lakar lokasi kejadian di tempat operasi.",
              ],
            },
            {
              fasa: "FASA 2: TINDAKAN BALIK PEJABAT (DALAM TEMPOH 24 JAM)",
              color: "border-emerald-300 bg-emerald-50/50",
              steps: [
                "Daftar barang kes dalam Buku Daftar Barang Kes dan simpan dalam Stor Eksibit Berkunci PKD.",
                "Sediakan Laporan Pengadu (FIR) dengan tarikh dan masa konsisten.",
                "Cetak gambar foto berwarna bertarikh & berkapsyen daripada komputer pejabat dan terus tandatangani Sijil Seksyen 90A(2) Akta Keterangan 1950.",
                "Hantar sampel makanan (MKAK/Jabatan Kimia) atau botol larva (Makmal Entomologi) dengan nombor lak yang tepat.",
              ],
            },
            {
              fasa: "FASA 3: PENYEDIAAN KERTAS SIASATAN (IP)",
              color: "border-amber-300 bg-amber-50/50",
              steps: [
                "Bagi kes berkompaun (S.48 Akta 852 / S.33 Akta 281 / S.25 Akta 154), tunggu tempoh tamat (30 hari / 14 hari) dan dapatkan Sijil Pengesahan Unit Hasil Tidak Dibayar.",
                "Buka Fail IP, tulis Minit 1 (Borang Am 6), buat Carian Rasmi SSM (e-Info/MyData) + Sijil 90A.",
                "Rakam Percakapan Seksyen 112 KTJ Pengadu, Saksi Pengiring, Saksi Pakar & OKS berserta Amaran S.112(2)&(3) dan tandatangan S.112(5).",
                "Lengkapkan Diari Siasatan (S.119 KTJ), Kronologi Kes, Fakta Kes, Kertas Cadangan IO, Pengaduan Borang 143 & Pertuduhan Borang 114.",
              ],
            },
            {
              fasa: "FASA 4: SEMAKAN UIP, IZIN MENDAKWA TPR & MAHKAMAH",
              color: "border-indigo-300 bg-indigo-50/50",
              steps: [
                "Laksanakan Audit 20 Kriteria Pra-TPR dalam UIP-Command sehingga tiada kuiri GAGAL.",
                "Hantar ke KPPKP U36 / UIP Negeri untuk semakan dan dapatkan Izin Mendakwa (Sanksi) bertulis TPR di bawah S.376(3) KTJ (atau S.32A Akta Makanan).",
                "Daftar Borang 114, Borang 143 & Saman (Mahkamah 111) di Mahkamah Majistret dan serahkan Saman kepada OKS.",
                "Sediakan Hujahan Pemberatan Hukuman untuk dibacakan oleh Pegawai Pendakwa jika OKT mengaku salah / disabitkan.",
              ],
            },
          ].map((f, i) => (
            <div key={i} className={`rounded-xl border p-3.5 ${f.color}`}>
              <h4 className="text-xs font-bold text-slate-900">{f.fasa}</h4>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-slate-700">
                {f.steps.map((st, idx) => (
                  <li key={idx}>{st}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}

      {/* 3. CHEAT SHEET 4 AKTA TERAS */}
      {section === "cheat_sheet" && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-[11px] font-bold text-slate-800">
              <tr>
                <th className="border-b px-3 py-2">Akta</th>
                <th className="border-b px-3 py-2">Kesalahan Lazim</th>
                <th className="border-b px-3 py-2">Seksyen Kesalahan</th>
                <th className="border-b px-3 py-2">Seksyen Hukuman</th>
                <th className="border-b px-3 py-2">Kompaun / Buka IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-[11px] text-slate-700">
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 852</td>
                <td className="px-3 py-2">Iklan &amp; Promosi Rokok/Vape</td>
                <td className="px-3 py-2 font-semibold">Seksyen 7(1) / 9(1)</td>
                <td className="px-3 py-2">S.7(2) Ind. / S.7(3) Syk.</td>
                <td className="px-3 py-2">Sita S.35/36 &amp; Buka IP / Jadual P.U.(A) 259</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 852</td>
                <td className="px-3 py-2">Pamer Terbuka Vape/Rokok</td>
                <td className="px-3 py-2 font-semibold">S.10(1) + P.6 P.U.(A) 260/2024</td>
                <td className="px-3 py-2">S.10(2) Ind. / S.10(3) Syk.</td>
                <td className="px-3 py-2">Sita S.35/36 &amp; Buka IP / Notis S.47</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 852</td>
                <td className="px-3 py-2">Jual kepada OBD (&lt;18 thn)</td>
                <td className="px-3 py-2 font-semibold">Seksyen 13(1)</td>
                <td className="px-3 py-2">S.13(2) Ind. / S.13(3) Syk.</td>
                <td className="px-3 py-2 text-rose-700 font-bold">Buka IP Terus (Sita &amp; S.112 OBD)</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 852</td>
                <td className="px-3 py-2">Merokok di Restoran / Larangan</td>
                <td className="px-3 py-2 font-semibold">S.16(2) + P.U.(A) 257/2024</td>
                <td className="px-3 py-2">Seksyen 16(3) (Maks RM5,000)</td>
                <td className="px-3 py-2 text-emerald-800 font-semibold">Kompaun S.48 (RM250 / 30 hari)</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 852</td>
                <td className="px-3 py-2">Premis Tiada Tanda QR / Ashtray</td>
                <td className="px-3 py-2 font-semibold">S.18(1)(a)/(b) + P.U.(A) 258/2024</td>
                <td className="px-3 py-2">Seksyen 18(2) (Maks RM5,000)</td>
                <td className="px-3 py-2 text-emerald-800 font-semibold">Kompaun S.48 (Notis S.47 / 30 hari)</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 281</td>
                <td className="px-3 py-2">Premis Makanan Kotor (&lt;70%)</td>
                <td className="px-3 py-2 font-semibold">Peraturan 11(1) / 34(1) PPKM 2009</td>
                <td className="px-3 py-2">Peraturan 11(2) / 34(2)</td>
                <td className="px-3 py-2">Perintah Tutup S.11 + Notis S.32B</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 281</td>
                <td className="px-3 py-2">Pengendali Tiada Tifoid / LPM</td>
                <td className="px-3 py-2 font-semibold">P.31(1) [Tifoid] / P.30(1) [LPM]</td>
                <td className="px-3 py-2">P.31(3) / P.30(3) PPKM 2009</td>
                <td className="px-3 py-2 text-emerald-800 font-semibold">Kompaun S.33 (Notis S.32B / 14 hari)</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 281</td>
                <td className="px-3 py-2">Makanan Beracun / Benda Asing</td>
                <td className="px-3 py-2 font-semibold">Seksyen 13(1) / 13B(1)&amp;(2)</td>
                <td className="px-3 py-2">Seksyen 13(1) / 13B(4)</td>
                <td className="px-3 py-2 text-rose-700 font-bold">Wajib Buka IP Terus (Sanksi S.32A)</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 154</td>
                <td className="px-3 py-2">Aedes Kediaman / Premis Biasa</td>
                <td className="px-3 py-2 font-semibold">Seksyen 13(1) dibaca S.13(2)</td>
                <td className="px-3 py-2">Seksyen 23(a)/(b)</td>
                <td className="px-3 py-2 text-emerald-800 font-semibold">Kompaun S.25 Maks RM500 (14 hari)</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 154</td>
                <td className="px-3 py-2">Aedes Tapak Pembinaan</td>
                <td className="px-3 py-2 font-semibold">S.13(1)&amp;(2) [Ingkar tutup: S.8(8)]</td>
                <td className="px-3 py-2">Seksyen 23(a)/(b)</td>
                <td className="px-3 py-2 text-rose-700 font-bold">Perintah S.8(1) + Buka IP Terus</td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-bold text-slate-900">Akta 342</td>
                <td className="px-3 py-2">Tibi Cicir Rawatan / Ingkar Perintah</td>
                <td className="px-3 py-2 font-semibold">Seksyen 22(b) [APPPB 1988]</td>
                <td className="px-3 py-2">Seksyen 24(a)/(b)</td>
                <td className="px-3 py-2 text-rose-700 font-bold">Buka IP Terus (Saman 111 &amp; M.114)</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* 4. SUSUNAN FAIL IP & FORMULA 5W1H */}
      {section === "fail_5w1h" && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-2">
            <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
              <FileText className="h-4 w-4 text-blue-700" />
              Formula Emas 5W1H Penulisan Borang 114
            </h4>
            <ol className="list-decimal space-y-1.5 pl-4 text-xs text-slate-700">
              <li>
                <strong>Siapa (OKS):</strong> Nama penuh &amp; No. K/P ikut MyKad (atau Nama Syarikat + No. SSM)
                beserta kapasiti (cth: sebagai pemunya / penghuni / pengendali).
              </li>
              <li>
                <strong>Bila:</strong> Tarikh dan waktu tepat (<em>&quot;pada 14 Oktober 2026, jam lebih kurang 10.45 pagi&quot;</em>).
              </li>
              <li>
                <strong>Di Mana:</strong> Alamat penuh tempat kejadian termasuk Daerah dan Negeri bidang kuasa Mahkamah Majistret.
              </li>
              <li>
                <strong>Apa Perbuatan:</strong> Terangkan perbuatan salah mengikut istilah sebenar Seksyen/Peraturan.
              </li>
              <li>
                <strong>Undang-Undang:</strong> Pisahkan Seksyen Kesalahan dan Seksyen Hukuman
                (<strong>1 kesalahan = 1 Borang 114 berasingan</strong> mengikut Seksyen 163 KTJ).
              </li>
            </ol>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3.5 space-y-2">
            <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
              <FolderTree className="h-4 w-4 text-emerald-700" />
              Susunan Indeks Fail Kertas Siasatan PKD
            </h4>
            <ul className="space-y-1 text-xs text-slate-700">
              <li><strong>Folio A:</strong> Kertas Minit `(Am 6)` (Minit 1–10), Kertas Cadangan IO &amp; Surat Izin Mendakwa TPR.</li>
              <li><strong>Folio B:</strong> Pengaduan `(Mahkamah 143)`, Saman `(Mahkamah 111)`, Pertuduhan `(Mahkamah 114)`.</li>
              <li><strong>Folio C:</strong> Fakta Kes, Kronologi Kes, Senarai Saksi (SP) &amp; Senarai Barang Kes (Eksibit P).</li>
              <li><strong>Folio D:</strong> Notis S.32B / S.47 / Arahan Rawatan, Pengesahan Unit Hasil &amp; Kad AR Pos Berdaftar.</li>
              <li><strong>Folio E:</strong> Borang Sitaan S.36, Perintah S.11 / S.8, Pelan Lakar, Gambar Warna &amp; Sijil Seksyen 90A(2).</li>
              <li><strong>Folio F:</strong> Rakaman Percakapan Seksyen 112 KTJ (Pengadu, Saksi, Pakar &amp; OKT).</li>
              <li><strong>Folio G &amp; H:</strong> Carian SSM, Kad Kuasa, Laporan Makmal/Entomologi &amp; Diari Siasatan `(S.119 KTJ)`.</li>
            </ul>
          </div>
        </div>
      )}

      {/* 5. 10 KESILAPAN MAUT PPKP */}
      {section === "kesilapan_maut" && (
        <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-4 space-y-2">
          <h4 className="flex items-center gap-1.5 text-xs font-bold text-rose-950">
            <AlertTriangle className="h-4 w-4 text-rose-600" />
            10 Kesilapan Maut PPKP Yang Menyebabkan IP Ditolak TPR atau Kalah di Mahkamah
          </h4>
          <ol className="list-decimal space-y-1.5 pl-5 text-xs text-slate-800">
            <li>Mencampurkan 2 kesalahan berlainan dalam satu Borang 114 (<strong>Duplicity — S.163 KTJ</strong>).</li>
            <li>Tersalah petik seksyen: menulis <strong>S.38</strong> untuk sitaan Akta 852, <strong>S.44</strong> untuk kompaun Akta 852, <strong>P.30</strong> untuk suntikan tifoid, atau <strong>Akta 514</strong> untuk kes Tibi (sepatutnya Akta 342).</li>
            <li>Tiada <strong>Sijil Seksyen 90A(2)</strong> pada gambar digital &amp; cetakan SSM (atau tiada klausa <em>&quot;sepanjang pengetahuan dan kepercayaan saya&quot;</em>).</li>
            <li>Tarikh atau masa antara Borang Pemeriksaan, Label Botol/Barang Kes, Laporan Makmal &amp; Borang 114 bercanggah.</li>
            <li>Rantaian barang kes terputus — tiada nombor siri lak KKM atau nombor lak di botol berbeza dengan Laporan Entomologi.</li>
            <li>Rakaman <strong>Seksyen 112 KTJ</strong> tiada nota Amaran S.112(2)&amp;(3) atau tiada tandatangan saksi &amp; jurubahasa pada perakuan S.112(5).</li>
            <li>Menuduh pekerja juruwang warga asing bagi kesalahan pemunya/penghuni premis tanpa Carian SSM atau Lesen PBT.</li>
            <li>Lupa menyerahkan salinan <strong>Perakuan Juruanalisis Makanan (S.19 Akta 281)</strong> kepada tertuduh sekurang-kurangnya <strong>10 hari jelas</strong> sebelum perbicaraan.</li>
            <li>Mendaftar kes ke mahkamah tanpa <strong>Izin Mendakwa (Sanksi) bertulis TPR</strong> atau setelah tamat had masa.</li>
            <li>Tiada bukti serahan Notis Kompaun / Arahan Rawatan / Perintah Tutup (tiada tandatangan terima atau tiada saksi PPKP + Kad AR Pos Berdaftar).</li>
          </ol>
        </div>
      )}
    </div>
  );
}
