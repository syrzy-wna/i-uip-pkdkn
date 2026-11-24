"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Compass,
  FileText,
  FolderTree,
  Layers,
  ShieldAlert,
  Sparkles,
  UserCheck,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";

type GuideSection = "cara_guna" | "carta_alir" | "fail_5w1h" | "kesilapan_biasa";

interface AppGuidePanelProps {
  onNavigateMode?: (mode: ActiveAppMode) => void;
  onOpenOnboarding?: () => void;
  onOpenProfile?: () => void;
}

export default function AppGuidePanel({
  onNavigateMode,
  onOpenOnboarding,
  onOpenProfile,
}: AppGuidePanelProps) {
  const [section, setSection] = useState<GuideSection>("cara_guna");

  const tabs: Array<{ id: GuideSection; label: string; icon: React.ReactNode }> = [
    { id: "cara_guna", label: "1. Cara Guna Ringkas", icon: <Compass className="h-4 w-4" /> },
    { id: "carta_alir", label: "2. Carta Alir 4 Fasa", icon: <Layers className="h-4 w-4" /> },
    { id: "fail_5w1h", label: "3. Susunan Fail A–G & Tip Borang 114", icon: <FolderTree className="h-4 w-4" /> },
    { id: "kesilapan_biasa", label: "4. 10 Kesilapan Lazim PPKP", icon: <ShieldAlert className="h-4 w-4" /> },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-[#0f2744] p-5 text-white shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-extrabold sm:text-lg">
              Panduan Ringkas &amp; SOP Lapangan UIP
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-slate-200 sm:text-sm">
              Rujukan pantas langkah operasi di lokasi, susunan Fail IP (Bahagian A–G), tip menulis Borang 114 dan 10 kesilapan lazim yang menyebabkan Fail IP ditolak TPR.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("home")}
                className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-white ring-1 ring-white/20 hover:bg-white/20"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali ke Utama
              </button>
            )}
            {onOpenOnboarding && (
              <button
                type="button"
                onClick={onOpenOnboarding}
                className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl bg-white/10 px-3.5 py-2 text-xs font-bold text-amber-200 ring-1 ring-white/20 hover:bg-white/20"
              >
                <Sparkles className="h-4 w-4" />
                Pengenalan Ringkas
              </button>
            )}
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("directory")}
                className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl bg-white px-3.5 py-2 text-xs font-extrabold text-[#0f2744] shadow-sm hover:bg-slate-100"
              >
                <BookOpen className="h-4 w-4" />
                Cari Seksyen / Teks Akta →
              </button>
            )}
          </div>
        </div>

        <div className="mt-4 flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSection(t.id)}
              className={`inline-flex min-h-[44px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                section === t.id
                  ? "bg-white text-[#0f2744] shadow-sm"
                  : "bg-white/10 text-slate-100 hover:bg-white/20"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* 1. CARA GUNA RINGKAS */}
      {section === "cara_guna" && (
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
          <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-[#0f2744]">
              Langkah 1 • Profil Pegawai
            </span>
            <h3 className="text-sm font-extrabold text-slate-900">Simpan No. Kad Kuasa Sekali Sahaja</h3>
            <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
              Tekan ikon profil anda di bahagian atas kanan untuk mengisi Gred SSPA, No. Kad Kuasa KKM, Mahkamah Majistret dan model kamera/komputer pejabat. Semua maklumat ini akan diisi secara automatik pada Notis Kompaun, Borang 114 dan Sijil 90A.
            </p>
            {onOpenProfile && (
              <button
                type="button"
                onClick={onOpenProfile}
                className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-[#0f2744] hover:underline"
              >
                <UserCheck className="h-3.5 w-3.5" />
                Buka Profil Pegawai <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-[#0f2744]">
              Langkah 2 • Di Lokasi Pemeriksaan
            </span>
            <h3 className="text-sm font-extrabold text-slate-900">Rujuk Seksyen &amp; SOP di Pakar &amp; Akta</h3>
            <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
              Taip situasi yang anda temui di lokasi (cth. pelajar hisap vape atau restoran kotor) untuk menyemak seksyen tepat, sama ada boleh kompaun atau wajib buka IP, serta senarai bukti yang perlu diambil sebelum meninggalkan premis.
            </p>
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("advisor")}
                className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-[#0f2744] hover:underline"
              >
                Buka Pakar &amp; Akta <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-[#0f2744]">
              Langkah 3 • Keluarkan Kompaun
            </span>
            <h3 className="text-sm font-extrabold text-slate-900">Imbas Foto SSM &amp; Semak 10 Perkara Wajib</h3>
            <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
              Di menu <strong>Kompaun</strong>, ambil foto Sijil SSM atau pilih kesalahan lazim dengan 1 klik. Sistem akan menyemak had amaun (cth. Akta 154 maksimum RM500), tempoh bayaran (14/30 hari), dan kesahihan MyKad/Pasport sebelum muat turun fail Word.
            </p>
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("compound")}
                className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-[#0f2744] hover:underline"
              >
                Buka Notis Kompaun <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-[#0f2744]">
              Langkah 4 • Urus Fail IP (Pra-TPR)
            </span>
            <h3 className="text-sm font-extrabold text-slate-900">Semak 20 Perkara &amp; Muat Turun Fail Word</h3>
            <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
              Di menu <strong>Fail IP</strong>, muat naik PDF atau gambar bukti kes (Langkah 1), semak 20 perkara Pra-TPR (Langkah 2), sunting mana-mana ruangan borang yang masih kurang dan muat turun Pakej Fail IP lengkap dalam Word (Langkah 3).
            </p>
            {onNavigateMode && (
              <button
                type="button"
                onClick={() => onNavigateMode("audit")}
                className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-[#0f2744] hover:underline"
              >
                Buka Fail IP <ArrowRight className="h-3.5 w-3.5" />
              </button>
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
              steps: [
                "Daftar barang kes dalam Buku Daftar Barang Kes dan simpan dalam Stor Eksibit Berkunci Pejabat Kesihatan.",
                "Sediakan Laporan Pengadu (FIR) dengan tarikh dan masa yang selaras.",
                "Cetak gambar foto berwarna bertarikh & berkapsyen daripada komputer pejabat dan terus tandatangani Sijil Seksyen 90A(2) Akta Keterangan 1950.",
                "Hantar sampel makanan (MKAK/Jabatan Kimia) atau botol larva (Makmal Entomologi) dengan nombor lak yang tepat.",
              ],
            },
            {
              fasa: "FASA 3: PENYEDIAAN KERTAS SIASATAN (IP)",
              steps: [
                "Bagi kes berkompaun (S.48 Akta 852 / S.33 Akta 281 / S.25 Akta 154), tunggu tempoh tamat (30 hari / 14 hari) dan dapatkan Sijil Pengesahan Unit Hasil Tidak Dibayar.",
                "Buka Fail IP, tulis Minit 1 (Borang Am 6), buat Carian Rasmi SSM (e-Info/MyData) + Sijil 90A.",
                "Rakam Percakapan Seksyen 112 KTJ Pengadu, Saksi Pengiring, Saksi Pakar & OKS berserta Amaran S.112(2)&(3) dan tandatangan S.112(5).",
                "Lengkapkan Diari Siasatan (S.119 KTJ), Kronologi Kes, Fakta Kes, Kertas Cadangan IO, Pengaduan Borang 143 & Pertuduhan Borang 114.",
              ],
            },
            {
              fasa: "FASA 4: SEMAKAN UIP, IZIN MENDAKWA TPR & MAHKAMAH",
              steps: [
                "Jalankan 20 Semakan Pra-TPR dalam i-UIP Nerus sehingga tiada perkara GAGAL.",
                "Hantar kepada KPPKP / UIP Negeri untuk semakan dan dapatkan Izin Mendakwa (Keizinan Pendakwa Raya) bertulis di bawah S.376(3) KTJ, S.41 Akta 852, S.32A Akta 281, S.22A Akta 154 atau S.23 Akta 342.",
                "Daftar Borang 114, Borang 143 & Saman (Mahkamah 111) di Mahkamah Majistret dan serahkan Saman kepada tertuduh.",
                "Sediakan Perkara Pemberatan Hukuman untuk dibacakan oleh Pegawai Pendakwa jika OKT mengaku salah atau disabitkan.",
              ],
            },
          ].map((f, i) => (
            <div key={i} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-extrabold text-[#0f2744]">{f.fasa}</h3>
              <ol className="mt-2.5 list-decimal space-y-1.5 pl-5 text-xs leading-relaxed text-slate-700 sm:text-sm">
                {f.steps.map((st, idx) => (
                  <li key={idx}>{st}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}

      {/* 3. SUSUNAN FAIL IP & TIP BORANG 114 */}
      {section === "fail_5w1h" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
              <FileText className="h-4 w-4 text-[#0f2744]" />
              Formula 5W1H Penulisan Borang 114
            </h3>
            <ol className="list-decimal space-y-2 pl-5 text-xs leading-relaxed text-slate-700 sm:text-sm">
              <li>
                <strong>Siapa (OKT):</strong> Nama penuh &amp; No. K/P mengikut MyKad (atau Nama Syarikat + No. SSM)
                berserta kapasiti (cth: sebagai pemunya / penghuni / pengendali).
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

          <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
              <FolderTree className="h-4 w-4 text-[#0f2744]" />
              Susunan Fail Kertas Siasatan Pejabat Kesihatan (7 Bahagian A – G)
            </h3>
            <ul className="space-y-2 text-xs leading-relaxed text-slate-700 sm:text-sm">
              <li><strong>Bahagian A:</strong> Kertas Minit (Am 6), Izin Mendakwa TPR, Kertas Cadangan IO &amp; Fakta Kes.</li>
              <li><strong>Bahagian B:</strong> Borang 114 (Pertuduhan), Borang 143 (Pengaduan) &amp; Saman (Mahkamah 111).</li>
              <li><strong>Bahagian C:</strong> Notis S.32B / S.47, Notis Kompaun, Sijil Unit Hasil &amp; Kad AR Pos Berdaftar.</li>
              <li><strong>Bahagian D:</strong> Borang Sitaan (S.36) / Perintah S.11 / S.8, Pelan Lakar, Gambar Warna &amp; Sijil 90A.</li>
              <li><strong>Bahagian E:</strong> Rakaman Percakapan S.112 KTJ &amp; Senarai Saksi Pendakwaan (SP).</li>
              <li><strong>Bahagian F:</strong> Carian SSM, Kad Kuasa &amp; Laporan Makmal (S.19/S.20) / Entomologi.</li>
              <li><strong>Bahagian G:</strong> Diari Siasatan (Seksyen 119 KTJ) &amp; Kronologi Kes.</li>
            </ul>
          </div>
        </div>
      )}

      {/* 4. 10 KESILAPAN LAZIM PPKP */}
      {section === "kesilapan_biasa" && (
        <div className="space-y-3 rounded-2xl border border-rose-200 bg-white p-5 shadow-sm">
          <h3 className="flex items-center gap-2 text-sm font-extrabold text-rose-950">
            <AlertTriangle className="h-4 w-4 text-rose-600" />
            10 Kesilapan Lazim Punca Fail IP Ditolak TPR atau Gagal di Mahkamah
          </h3>
          <ol className="list-decimal space-y-2 pl-5 text-xs leading-relaxed text-slate-800 sm:text-sm">
            <li>Mencampurkan 2 kesalahan berlainan dalam satu Borang 114 (<strong>Pertindihan Pertuduhan — S.163 KTJ</strong>).</li>
            <li>Tersalah petik seksyen: menulis <strong>S.38</strong> untuk sitaan Akta 852, <strong>S.44</strong> untuk kompaun Akta 852, <strong>P.30</strong> untuk suntikan tifoid, atau <strong>Akta 514</strong> untuk kes Tibi (sepatutnya Akta 342).</li>
            <li>Tiada <strong>Sijil Seksyen 90A(2)</strong> pada gambar digital &amp; cetakan SSM (atau tiada klausa <em>&quot;sepanjang pengetahuan dan kepercayaan saya&quot;</em>).</li>
            <li>Tarikh atau masa antara Borang Pemeriksaan, Label Botol/Barang Kes, Laporan Makmal &amp; Borang 114 bercanggah.</li>
            <li>Rantaian barang kes terputus — tiada nombor siri lak KKM atau nombor lak di botol berbeza dengan Laporan Entomologi.</li>
            <li>Rakaman <strong>Seksyen 112 KTJ</strong> tiada nota Amaran S.112(2)&amp;(3) atau tiada tandatangan saksi &amp; jurubahasa pada perakuan S.112(5).</li>
            <li>Menuduh pekerja juruwang warga asing bagi kesalahan pemunya/penghuni premis tanpa Carian SSM atau Lesen PBT.</li>
            <li>Lupa menyerahkan salinan <strong>Perakuan Juruanalisis Makanan (S.20(ii) Akta 281)</strong> kepada tertuduh sekurang-kurangnya <strong>10 hari jelas</strong> sebelum perbicaraan.</li>
            <li>Mendaftar kes ke mahkamah tanpa <strong>Izin Mendakwa bertulis TPR</strong> atau setelah tamat had masa (cth. 150 hari di bawah S.19(2) Akta 281).</li>
            <li>Tiada bukti serahan Notis Kompaun / Arahan Rawatan / Perintah Tutup (tiada tandatangan terima atau tiada saksi PPKP + Kad AR Pos Berdaftar).</li>
          </ol>
        </div>
      )}
    </div>
  );
}
