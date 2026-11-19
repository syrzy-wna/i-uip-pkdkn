"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  BookOpenCheck,
  Compass,
  Copy,
  FileText,
  FolderTree,
  Layers,
  Loader2,
  Search,
  ShieldAlert,
} from "lucide-react";
import { queryStatutoryRag } from "@/lib/api";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { StatutoryCitation } from "@/lib/types";

type GuideSection =
  | "cara_guna"
  | "carta_alir"
  | "cheat_sheet"
  | "fail_5w1h"
  | "kesilapan_maut"
  | "carian_akta";

interface AppGuidePanelProps {
  onNavigateMode?: (mode: ActiveAppMode) => void;
}

const CHEAT_SHEET_ROWS = [
  {
    akta: "Akta 852",
    kesalahan: "Iklan & Promosi Rokok/Vape",
    seksyen: "Seksyen 7(1) / 9(1)",
    hukuman: "S.7(2) Ind. / S.7(3) Syk.",
    tindakan: "Sita S.35/36 & Buka IP / Jadual P.U.(A) 259",
    isIp: true,
  },
  {
    akta: "Akta 852",
    kesalahan: "Pamer Terbuka Vape/Rokok",
    seksyen: "S.10(1) + P.6 P.U.(A) 260/2024",
    hukuman: "S.10(2) Ind. / S.10(3) Syk.",
    tindakan: "Sita S.35/36 & Buka IP / Notis S.47",
    isIp: true,
  },
  {
    akta: "Akta 852",
    kesalahan: "Jual kepada OBD (<18 thn)",
    seksyen: "Seksyen 13(1)",
    hukuman: "S.13(2) Ind. / S.13(3) Syk.",
    tindakan: "Buka IP Terus (Sita & S.112 OBD)",
    isIp: true,
  },
  {
    akta: "Akta 852",
    kesalahan: "Merokok di Restoran / Larangan",
    seksyen: "S.16(2) + P.U.(A) 257/2024",
    hukuman: "Seksyen 16(3) (Maks RM5,000)",
    tindakan: "Kompaun S.48 (RM250 / 30 hari)",
    isIp: false,
  },
  {
    akta: "Akta 852",
    kesalahan: "Premis Tiada Tanda QR / Ashtray",
    seksyen: "S.18(1)(a)/(b) + P.U.(A) 258/2024",
    hukuman: "Seksyen 18(2) (Maks RM5,000)",
    tindakan: "Kompaun S.48 (Notis S.47 / 30 hari)",
    isIp: false,
  },
  {
    akta: "Akta 281",
    kesalahan: "Premis Makanan Kotor (<70%)",
    seksyen: "Peraturan 11(1) / 34(1) PPKM 2009",
    hukuman: "Peraturan 11(2) / 34(2)",
    tindakan: "Perintah Tutup S.11 + Notis S.32B",
    isIp: false,
  },
  {
    akta: "Akta 281",
    kesalahan: "Pengendali Tiada Tifoid / LPM",
    seksyen: "P.31(1) [Tifoid] / P.30(1) [LPM]",
    hukuman: "P.31(3) / P.30(3) PPKM 2009",
    tindakan: "Kompaun S.33 (Notis S.32B / 14 hari)",
    isIp: false,
  },
  {
    akta: "Akta 281",
    kesalahan: "Makanan Beracun / Benda Asing",
    seksyen: "Seksyen 13(1) / 13B(1)&(2)",
    hukuman: "Seksyen 13(1) / 13B(4)",
    tindakan: "Wajib Buka IP Terus (Sanksi S.32A)",
    isIp: true,
  },
  {
    akta: "Akta 154",
    kesalahan: "Aedes Kediaman / Premis Biasa",
    seksyen: "Seksyen 13(1) dibaca S.13(2)",
    hukuman: "Seksyen 23(a)/(b)",
    tindakan: "Kompaun S.25 Maks RM500 (14 hari)",
    isIp: false,
  },
  {
    akta: "Akta 154",
    kesalahan: "Aedes Tapak Pembinaan",
    seksyen: "S.13(1)&(2) [Ingkar tutup: S.8(8)]",
    hukuman: "Seksyen 23(a)/(b)",
    tindakan: "Perintah S.8(1) + Buka IP Terus",
    isIp: true,
  },
  {
    akta: "Akta 342",
    kesalahan: "Tibi Cicir Rawatan / Ingkar Perintah",
    seksyen: "Seksyen 22(b) [APPPB 1988]",
    hukuman: "Seksyen 24(a)/(b)",
    tindakan: "Buka IP Terus (Saman 111 & M.114)",
    isIp: true,
  },
];

export default function AppGuidePanel({ onNavigateMode }: AppGuidePanelProps) {
  const [section, setSection] = useState<GuideSection>("cara_guna");
  const [aktaSearch, setAktaSearch] = useState("Semua");
  const [ragQuery, setRagQuery] = useState("");
  const [ragResults, setRagResults] = useState<StatutoryCitation[]>([]);
  const [ragLoading, setRagLoading] = useState(false);

  const handleSearchStatute = async () => {
    if (!ragQuery.trim()) return;
    setRagLoading(true);
    try {
      const res = await queryStatutoryRag(ragQuery, aktaSearch);
      setRagResults(res.results);
    } catch {
      setRagResults([]);
    } finally {
      setRagLoading(false);
    }
  };

  const tabs: Array<{ id: GuideSection; label: string; icon: React.ReactNode }> = [
    { id: "cara_guna", label: "1. Cara Guna Aplikasi", icon: <Compass className="h-3.5 w-3.5" /> },
    { id: "carta_alir", label: "2. Carta Alir Kerja UIP", icon: <Layers className="h-3.5 w-3.5" /> },
    { id: "cheat_sheet", label: "3. Cheat Sheet 4 Akta", icon: <BookOpenCheck className="h-3.5 w-3.5" /> },
    { id: "fail_5w1h", label: "4. Susunan IP & 5W1H B.114", icon: <FolderTree className="h-3.5 w-3.5" /> },
    { id: "kesilapan_maut", label: "5. 10 Kesilapan Maut PPKP", icon: <ShieldAlert className="h-3.5 w-3.5" /> },
    { id: "carian_akta", label: "6. Cari Teks Akta Rasmi", icon: <BookOpen className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-gradient-to-r from-[#0f2744] to-slate-800 p-4 text-white">
        <h3 className="text-sm font-bold">
          Buku Panduan Lengkap i-UIP Nerus &amp; SOP Penguatkuasaan UIP KKM
        </h3>
        <p className="mt-1 text-xs text-slate-200">
          Rujukan lengkap harian untuk PPKP dan Pegawai Penyiasat (IO) PKD Kuala Nerus — dari tindakan lokasi,
          pengkompaunan, penyediaan Kertas Siasatan (IP) hingga semakan Pra-TPR &amp; Mahkamah.
        </p>
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSection(t.id)}
              className={`inline-flex min-h-[38px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-bold transition ${
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
          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
              LANGKAH A — AKAUN PEGAWAI
            </span>
            <h4 className="text-xs font-bold text-slate-900">1. Lengkapkan Profil Akaun Pegawai</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Klik nama anda di bar atas untuk mengisi Jawatan, Gred SSPA (U5–U14), No. Kad Kuasa KKM, Mahkamah Majistret dan model komputer/kamera pejabat. Semua maklumat ini terus masuk secara automatik ke dalam Borang 114, Notis Kompaun &amp; Sijil 90A.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-800">
              LANGKAH B — TANYA PAKAR UIP
            </span>
            <h4 className="text-xs font-bold text-slate-900">2. Rujuk Seksyen &amp; Prosedur Kes</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Tidak pasti kes tertentu perlu kompaun dulu, perintah tutup premis atau buka IP terus? Taip situasi di modul <strong>Tanya Pakar</strong>, kemudian tekan{" "}
              <em>Buka Draf Kes Ini dalam Editor IP</em> atau <em>Isi ke Borang Notis Kompaun</em>.
            </p>
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("advisor")}
                className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-800 hover:bg-indigo-100"
              >
                Buka Tanya Pakar <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
              LANGKAH C — NOTIS KOMPAUN &amp; BACA GAMBAR
            </span>
            <h4 className="text-xs font-bold text-slate-900">3. Semak 10 Perkara Notis Kompaun</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Ambil foto SSM/notis atau muat naik gambar di Langkah 2 dan tekan{" "}
              <strong>Baca &amp; Masukkan Teks Dari Fail Ini ke Catatan</strong>. Di modul <strong>Notis Kompaun</strong>, sistem semak had denda statutori (cth: Akta 154 maks RM500), MyKad 12 digit, dan saksi serahan sebelum muat turun `.docx`.
            </p>
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("compound")}
                className="inline-flex items-center gap-1 rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100"
              >
                Buka Notis Kompaun <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800">
              LANGKAH D — SEMAK IP &amp; BINA DOKUMEN WORD
            </span>
            <h4 className="text-xs font-bold text-slate-900">4. Semak 20 Kriteria, Edit &amp; Muat Turun IP (.docx)</h4>
            <p className="text-xs leading-relaxed text-slate-600">
              Muat naik PDF/Word IP atau taip fakta kes untuk jalankan semakan Pra-TPR 20 perkara (mengesan ralat seperti S.38/S.44/Akta 514/Peraturan 30 atau tiada Sijil 90A). Selepas itu klik <strong>Bina Fail IP</strong>, edit mana-mana kotak putih jika perlu, dan muat turun Word rasmi (<code>.docx</code>).
            </p>
            {onNavigateMode && (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onNavigateMode("audit")}
                  className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-800 hover:bg-slate-200"
                >
                  Buka Semak IP <ArrowRight className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateMode("draft")}
                  className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100"
                >
                  Buka Bina Fail IP <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
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
                "Laksanakan Audit 20 Kriteria Pra-TPR dalam i-UIP Nerus sehingga tiada kuiri GAGAL.",
                "Hantar ke KPPKP U7 / UIP Negeri untuk semakan dan dapatkan Izin Mendakwa (Sanksi) bertulis TPR di bawah S.376(3) KTJ (atau S.32A Akta Makanan).",
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
        <>
          {/* Kad Responsif untuk Mobile (< md) */}
          <div className="space-y-2 md:hidden">
            {CHEAT_SHEET_ROWS.map((row, idx) => (
              <div key={idx} className="rounded-xl border border-slate-200 bg-white p-3 text-xs space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[10px] font-bold text-white">
                    {row.akta}
                  </span>
                  <span
                    className={`text-[10px] font-bold ${
                      row.isIp ? "text-rose-700" : "text-emerald-800"
                    }`}
                  >
                    {row.tindakan}
                  </span>
                </div>
                <div className="font-bold text-slate-900">{row.kesalahan}</div>
                <div className="text-[11px] text-slate-700">
                  <strong>Seksyen:</strong> {row.seksyen} • <strong>Hukuman:</strong> {row.hukuman}
                </div>
              </div>
            ))}
          </div>

          {/* Jadual Desktop (md+) */}
          <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white md:block">
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
                {CHEAT_SHEET_ROWS.map((row, idx) => (
                  <tr key={idx}>
                    <td className="px-3 py-2 font-bold text-slate-900">{row.akta}</td>
                    <td className="px-3 py-2">{row.kesalahan}</td>
                    <td className="px-3 py-2 font-semibold">{row.seksyen}</td>
                    <td className="px-3 py-2">{row.hukuman}</td>
                    <td
                      className={`px-3 py-2 font-bold ${
                        row.isIp ? "text-rose-700" : "text-emerald-800"
                      }`}
                    >
                      {row.tindakan}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
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
              Susunan Bahagian Fail Kertas Siasatan PKD (A – G)
            </h4>
            <ul className="space-y-1 text-xs text-slate-700">
              <li><strong>Bahagian A:</strong> Kertas Minit (Am 6), Izin Mendakwa TPR, Kertas Cadangan IO &amp; Fakta Kes.</li>
              <li><strong>Bahagian B:</strong> Borang 114 (Pertuduhan), Borang 143 (Pengaduan) &amp; Saman (Mahkamah 111).</li>
              <li><strong>Bahagian C:</strong> Notis S.32B / S.47, Notis Kompaun, Sijil Unit Hasil &amp; Kad AR Pos Berdaftar.</li>
              <li><strong>Bahagian D:</strong> Borang Sitaan (S.36) / Perintah S.11 / S.8, Pelan Lakar, Gambar Warna &amp; Sijil 90A.</li>
              <li><strong>Bahagian E:</strong> Rakaman Percakapan S.112 KTJ &amp; Senarai Saksi Pendakwaan (SP).</li>
              <li><strong>Bahagian F:</strong> Carian SSM, Kad Kuasa &amp; Laporan Makmal (S.19) / Entomologi.</li>
              <li><strong>Bahagian G:</strong> Diari Siasatan (Seksyen 119 KTJ) &amp; Kronologi Kes.</li>
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

      {/* 6. CARI TEKS AKTA RASMI */}
      {section === "carian_akta" && (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-extrabold text-slate-900">
                Carian Ayat &amp; Seksyen Akta Rasmi
              </h4>
              <p className="text-xs text-slate-500">
                Cari peruntukan tepat Akta 852, Akta 281, Akta 154, Akta 342, KTJ atau Akta Keterangan.
              </p>
            </div>
            <select
              value={aktaSearch}
              onChange={(e) => setAktaSearch(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-800 sm:text-xs"
            >
              <option value="Semua">Semua Akta KKM</option>
              <option value="Akta 852">Akta 852</option>
              <option value="Akta 281">Akta 281</option>
              <option value="Akta 154">Akta 154</option>
              <option value="Akta 342">Akta 342</option>
            </select>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={ragQuery}
              onChange={(e) => setRagQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearchStatute();
              }}
              placeholder="cth: Seksyen 36 sitaan, Peraturan 31 tifoid, Seksyen 13 Aedes..."
              className="flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-800 focus:border-blue-500 focus:outline-none sm:text-sm"
            />
            <button
              type="button"
              disabled={ragLoading}
              onClick={handleSearchStatute}
              className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {ragLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Cari
            </button>
          </div>

          {ragResults.length > 0 && (
            <div className="space-y-2.5 pt-1">
              {ragResults.map((item, idx) => (
                <div
                  key={`${item.akta_code}-${idx}`}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-extrabold text-teal-800">
                      {item.akta_code} • {item.section}
                    </span>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard?.writeText(item.text)}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-700 hover:bg-slate-100"
                    >
                      <Copy className="h-3.5 w-3.5" /> Salin
                    </button>
                  </div>
                  <p className="mt-1.5 whitespace-pre-line leading-relaxed text-slate-700">
                    {item.text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
