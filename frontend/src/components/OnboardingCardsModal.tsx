"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  FileText,
  FolderOpen,
  MessageSquareQuote,
  Scale,
  ShieldCheck,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { OfficerProfile } from "@/lib/types";

interface OnboardingCardsModalProps {
  open: boolean;
  officer: OfficerProfile | null;
  dontShowAgain: boolean;
  onToggleDontShowAgain: (value: boolean) => void;
  onClose: () => void;
  onNavigateMode: (mode: ActiveAppMode) => void;
  onOpenCases: () => void;
  onOpenProfile: () => void;
}

const TOTAL_STEPS = 8;

const STEP_LABELS = [
  "Pengenalan",
  "Tanya Pakar",
  "Notis Kompaun",
  "Semak IP",
  "Bina Fail IP",
  "Panduan & Akta",
  "Profil & Privasi",
  "Impak & Mula",
];

const VERBATIM_ACTS = [
  {
    no: "Akta 852",
    name: "Kawalan Produk Merokok Demi Kesihatan Awam 2024",
    scope: "Pameran vape, iklan, OBD bawah 18 tahun, kawasan larangan merokok.",
  },
  {
    no: "Akta 281",
    name: "Akta Makanan 1983 & PPKM 2009",
    scope: "Premis kotor S.11, Tifoid P.31, LPM P.30, kompaun S.32B/S.33.",
  },
  {
    no: "Akta 154",
    name: "Pemusnahan Serangga Pembawa Penyakit 1975",
    scope: "Pembiakan Aedes S.13, Perintah S.8, kompaun S.25 maksimum RM500.",
  },
  {
    no: "Akta 342",
    name: "Pencegahan & Pengawalan Penyakit Berjangkit 1988",
    scope: "Tibi cicir rawatan, ingkar perintah S.22/S.24.",
  },
  {
    no: "Akta 593",
    name: "Kanun Tatacara Jenayah (KTJ)",
    scope: "Percakapan S.112, Diari Siasatan S.119, Saman S.111, Sanksi S.376, S.163.",
  },
  {
    no: "Akta 56",
    name: "Akta Keterangan 1950",
    scope: "Perakuan Dokumen Komputer / Gambar Digital Seksyen 90A(2).",
  },
];

const PRIVACY_FLOW_STEPS = [
  {
    step: "1 · Input",
    title: "Input Pegawai",
    desc: "Teks / PDF / Foto SSM",
  },
  {
    step: "2 · Lock",
    title: "Penyamaran Tempatan",
    desc: "Data ditutup tempatan sebelum awan",
  },
  {
    step: "3 · AI",
    title: "Semakan & AI",
    desc: "Pustaka Akta / AI Awan",
  },
  {
    step: "4 · Output",
    title: "Dokumen Rasmi",
    desc: "Borang 114 / S.112 / S.90A / Kompaun",
  },
];

export default function OnboardingCardsModal({
  open,
  officer,
  dontShowAgain,
  onToggleDontShowAgain,
  onClose,
  onNavigateMode,
  onOpenCases,
  onOpenProfile,
}: OnboardingCardsModalProps) {
  const [step, setStep] = useState(0);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (open) {
      setStep(0);
    }
  }, [open]);

  const goPrev = useCallback(() => {
    setStep((s) => Math.max(0, s - 1));
  }, []);

  const goNext = useCallback(() => {
    setStep((s) => Math.min(TOTAL_STEPS - 1, s + 1));
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowRight") {
        goNext();
      } else if (e.key === "ArrowLeft") {
        goPrev();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose, goNext, goPrev]);

  const handleTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    const t = e.touches[0];
    if (!t) return;
    touchStartRef.current = { x: t.clientX, y: t.clientY };
  };

  const handleTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    const start = touchStartRef.current;
    const t = e.changedTouches[0];
    touchStartRef.current = null;
    if (!start || !t) return;
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.3) {
      if (dx < 0) goNext();
      else goPrev();
    }
  };

  if (!open) return null;

  const progressPct = Math.round(((step + 1) / TOTAL_STEPS) * 100);

  return (
    <div
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-card-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-2.5 backdrop-blur-sm sm:p-5"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-[#9e1b32]/20 bg-[#f7f4ef] text-[#241b1b] shadow-2xl"
      >
        {/* Jalur Hiasan Rasmi Atas */}
        <div className="h-1.5 shrink-0 bg-gradient-to-r from-[#6d0f21] via-[#9e1b32] to-[#b98a2f]" />

        {/* Header Kemas dengan Penunjuk Kemajuan */}
        <div className="shrink-0 border-b border-[#241b1b]/10 bg-white/90 px-4 py-3 sm:px-6">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span className="inline-flex shrink-0 items-center rounded-full bg-[#9e1b32] px-2.5 py-0.5 text-[11px] font-extrabold text-white">
                Kad {step + 1} / {TOTAL_STEPS}
              </span>
              <span className="truncate text-xs font-bold text-[#6d0f21]">
                {STEP_LABELS[step]}
              </span>
            </div>

            <div className="flex shrink-0 items-center gap-1.5">
              <button
                type="button"
                onClick={onClose}
                className="min-h-[36px] rounded-lg px-2.5 text-xs font-bold text-[#5a4a4a] transition hover:bg-[#9e1b32]/10 hover:text-[#9e1b32]"
              >
                Langkau
              </button>
              <button
                type="button"
                onClick={onClose}
                aria-label="Tutup taklimat aplikasi"
                title="Tutup"
                className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg text-[#5a4a4a] transition hover:bg-[#9e1b32]/10 hover:text-[#9e1b32]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#9e1b32]/15">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#9e1b32] to-[#b98a2f] transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Badan Kad Tunggal (1 Kad Pada Satu Masa — Leret / Klik Seterusnya) */}
        <div
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          className="flex-1 overflow-y-auto p-4 sm:p-6"
        >
          {/* KAD 1: PENGENALAN i-UIP NERUS (HERO + BAHAGIAN 02) */}
          {step === 0 && (
            <div className="space-y-4">
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#400814] via-[#6d0f21] to-[#9e1b32] p-5 text-white shadow-md sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/images/logo-iuip-nerus.png"
                      alt="Logo i-UIP Nerus"
                      className="h-11 w-11 shrink-0 rounded-full bg-white p-0.5 object-contain shadow ring-2 ring-[#e9c98a]"
                    />
                    <div className="rounded-lg bg-white/95 px-2.5 py-1 shadow-sm">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src="/images/logo-pkdkn.png"
                        alt="Logo PKD Kuala Nerus"
                        className="h-6 w-auto object-contain sm:h-7"
                      />
                    </div>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#e9c98a]">
                    UIP • PKD Kuala Nerus
                  </span>
                </div>

                <div className="mt-4">
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.22em] text-[#e9c98a]">
                    Taklimat Pantas • Penguatkuasaan Kesihatan Awam
                  </p>
                  <h2
                    id="onboarding-card-title"
                    className="mt-1 text-3xl font-black tracking-tight text-white sm:text-4xl"
                  >
                    i-UIP <span className="text-[#e9c98a]">Nerus</span>
                  </h2>
                  <p className="mt-2 text-xs font-medium leading-relaxed text-white/90 sm:text-sm">
                    Platform Pintar Penguatkuasaan, Pengurusan Kertas Siasatan (IP), Semakan
                    Pra-TPR &amp; Notis Kompaun
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full border border-white/40 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                      Desktop &amp; Telefon Pintar
                    </span>
                    <span className="rounded-full border border-white/40 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                      PPKP · PKP · Pegawai Penyiasat (IO)
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 px-1">
                <div className="h-px flex-1 bg-[#241b1b]/15" />
                <p className="text-center text-[11px] font-semibold italic text-[#9e1b32]">
                  &ldquo;Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus&rdquo;
                </p>
                <div className="h-px flex-1 bg-[#241b1b]/15" />
              </div>

              <div className="rounded-2xl border border-[#9e1b32]/15 bg-white p-4 shadow-sm sm:p-5">
                {officer?.full_name && (
                  <p className="mb-1.5 text-xs font-extrabold text-[#6d0f21]">
                    Selamat datang, {officer.full_name}!
                  </p>
                )}
                <p className="text-xs leading-relaxed text-[#3c3232] sm:text-sm">
                  Aplikasi web responsif yang dibina khusus untuk{" "}
                  <strong className="text-[#9e1b32]">
                    PPKP, PKP dan Pegawai Penyiasat (IO)
                  </strong>
                  , menggabungkan tiga kekuatan dalam satu platform:{" "}
                  <strong className="text-[#9e1b32]">
                    enjin rujukan statutori berasaskan teks akta sebenar
                  </strong>
                  , sokongan{" "}
                  <strong className="text-[#9e1b32]">AI Multimodal &amp; Reasoning (Gemini)</strong>
                  , dan{" "}
                  <strong className="text-[#9e1b32]">Penyamaran Data Peribadi</strong> selaras
                  OSA 1972 &amp; PDPA.
                </p>
                <div className="mt-3 border-l-[3px] border-[#b98a2f] pl-3 text-xs font-semibold leading-relaxed text-[#5a4a4a]">
                  Matlamat: Fail Kertas Siasatan dan Notis Kompaun sentiasa kemas sebelum
                  dikemukakan kepada Timbalan Pendakwa Raya (TPR) atau didaftarkan di Mahkamah
                  Majistret.
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div className="rounded-xl bg-[#6d0f21] px-3.5 py-2.5 text-white shadow-sm">
                  <div className="text-lg font-black leading-none">6</div>
                  <div className="mt-1 text-[11px] font-semibold text-white/85">
                    Modul Utama Aliran Kerja Penguatkuasaan
                  </div>
                </div>
                <div className="rounded-xl border border-[#9e1b32] bg-white px-3.5 py-2.5 shadow-sm">
                  <div className="text-lg font-black leading-none text-[#9e1b32]">6</div>
                  <div className="mt-1 text-[11px] font-semibold text-[#5a4a4a]">
                    Akta Verbatim Rasmi Dalam Enjin Carian
                  </div>
                </div>
                <div className="rounded-xl bg-[#6d0f21] px-3.5 py-2.5 text-white shadow-sm">
                  <div className="text-sm font-black leading-tight text-[#e9c98a]">
                    OSA 1972 &amp; PDPA
                  </div>
                  <div className="mt-1 text-[11px] font-semibold text-white/85">
                    Penyamaran Identiti OKT/Saksi Tempatan
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* KAD 2: MODUL 01 — TANYA PAKAR UIP */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="relative rounded-2xl border border-[#9e1b32]/20 bg-white p-5 shadow-sm">
                <span className="pointer-events-none absolute right-5 top-3 text-4xl font-black text-[#b98a2f]/25">
                  01
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#9e1b32]/10 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#9e1b32]">
                  <MessageSquareQuote className="h-3.5 w-3.5" />
                  Modul 01 · Rujukan Di Lokasi
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Tanya Pakar UIP
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-[#4c3f3f] sm:text-sm">
                  Rujukan pantas di lokasi — seksyen kesalahan &amp; hukuman, keputusan{" "}
                  <strong>Kompaun vs Buka IP</strong>, langkah SOP dan amaran kesilapan biasa.
                </p>

                <ul className="mt-4 space-y-2 text-xs text-[#3c3232]">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#9e1b32]" />
                    <span>Taip situasi sebenar di lapangan (cth. vape, premis kotor, Aedes, Tibi/CDC).</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#9e1b32]" />
                    <span>Terima seksyen kesalahan tepat, bukti kritikal di lokasi &amp; langkah SOP serta-merta.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#9e1b32]" />
                    <span>Tekan butang <strong>Cuba AI</strong> untuk huraian kes khusus mengikut fakta.</span>
                  </li>
                </ul>
              </div>

              <div className="rounded-2xl border-t-[3px] border-[#9e1b32] bg-white p-4 shadow-sm">
                <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#b98a2f]">
                  Cabaran Lapangan Yang Diselesaikan
                </p>
                <h3 className="mt-1 text-sm font-extrabold text-[#9e1b32]">
                  Salah Petik Seksyen
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-[#4c3f3f]">
                  Rujukan salah (cth. S.38 / S.44 / P.30 / Akta 514) boleh menyebabkan kes
                  terbatal atau dikritik Timbalan Pendakwa Raya (TPR).
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("advisor");
                  }}
                  className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  Cuba Tanya Pakar <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 3: MODUL 02 — NOTIS KOMPAUN */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="relative rounded-2xl border border-[#9e1b32]/20 bg-white p-5 shadow-sm">
                <span className="pointer-events-none absolute right-5 top-3 text-4xl font-black text-[#b98a2f]/25">
                  02
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#b98a2f]/15 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#6d0f21]">
                  <FileCheck2 className="h-3.5 w-3.5" />
                  Modul 02 · Kompaun Sah &amp; Pantas
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Notis Kompaun
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-[#4c3f3f] sm:text-sm">
                  Imbas foto Sijil SSM, borang berpandu, semakan automatik 10 perkara wajib, dan
                  eksport Notis Word (<code>.docx</code>) sedia cetak.
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="rounded-lg border border-[#9e1b32]/20 bg-[#f7f4ef] px-3 py-1.5 text-xs font-bold text-[#6d0f21]">
                    Imbas Foto SSM
                  </span>
                  <span className="rounded-lg border border-[#9e1b32]/20 bg-[#f7f4ef] px-3 py-1.5 text-xs font-bold text-[#6d0f21]">
                    Semak 10 Perkara Wajib
                  </span>
                  <span className="rounded-lg border border-[#9e1b32]/20 bg-[#f7f4ef] px-3 py-1.5 text-xs font-bold text-[#6d0f21]">
                    Eksport Word (.docx)
                  </span>
                </div>
              </div>

              <div className="rounded-2xl border-t-[3px] border-[#9e1b32] bg-white p-4 shadow-sm">
                <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#b98a2f]">
                  Cabaran Lapangan Yang Diselesaikan
                </p>
                <h3 className="mt-1 text-sm font-extrabold text-[#9e1b32]">Kompaun Tidak Sah</h3>
                <p className="mt-1 text-xs leading-relaxed text-[#4c3f3f]">
                  Notis yang melanggar had statutori (cth. Akta 154 maksimum RM500 di bawah
                  Seksyen 25) menjejaskan kutipan pendapatan dan integriti penguatkuasaan.
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("compound");
                  }}
                  className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  Buka Notis Kompaun <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 4: MODUL 03 — SEMAK FAIL IP (PRA-TPR) */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="relative rounded-2xl border border-[#9e1b32]/20 bg-white p-5 shadow-sm">
                <span className="pointer-events-none absolute right-5 top-3 text-4xl font-black text-[#b98a2f]/25">
                  03
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#9e1b32]/10 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#9e1b32]">
                  <Scale className="h-3.5 w-3.5" />
                  Modul 03 · Audit 20 Kriteria Pra-TPR
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Semak Fail IP (Pra-TPR)
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-[#4c3f3f] sm:text-sm">
                  Audit automatik <strong>20 kriteria</strong> — kesan salah petik seksyen,
                  percanggahan tarikh/masa, susunan Bahagian A–G dan status Sijil Seksyen 90A.
                </p>

                <div className="mt-4 rounded-xl border border-[#241b1b]/10 bg-[#f7f4ef] p-3.5 text-xs text-[#3c3232]">
                  <p className="font-extrabold text-[#6d0f21]">Bahan yang boleh disemak:</p>
                  <p className="mt-1 leading-relaxed">
                    Muat naik <strong>PDF Kertas Siasatan</strong>,{" "}
                    <strong>gambar foto eksibit / dokumen</strong>, atau tampal{" "}
                    <strong>catatan fakta kes</strong> sebelum dihantar kepada TPR.
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border-t-[3px] border-[#9e1b32] bg-white p-4 shadow-sm">
                <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#b98a2f]">
                  Cabaran Lapangan Yang Diselesaikan
                </p>
                <h3 className="mt-1 text-sm font-extrabold text-[#9e1b32]">
                  Fail IP Dikembalikan
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-[#4c3f3f]">
                  Susunan Bahagian A–G yang tidak kemas, percanggahan tarikh/masa dan status Sijil
                  90A yang tidak jelas sering menyebabkan fail dikuiri atau dipulangkan oleh TPR.
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("audit");
                  }}
                  className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  Buka Semak Fail IP <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 5: MODUL 04 — BINA FAIL IP & .DOCX */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="relative rounded-2xl border border-[#9e1b32]/20 bg-white p-5 shadow-sm">
                <span className="pointer-events-none absolute right-5 top-3 text-4xl font-black text-[#b98a2f]/25">
                  04
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#9e1b32]/10 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#9e1b32]">
                  <FileText className="h-3.5 w-3.5" />
                  Modul 04 · Jana &amp; Sunting .docx
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Bina Fail IP &amp; Borang Word (.docx)
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-[#4c3f3f] sm:text-sm">
                  Jana dan sunting Kertas Siasatan dalam susunan kemas; eksport satu klik dokumen
                  rasmi siap untuk semakan TPR dan pendaftaran di Mahkamah Majistret.
                </p>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="rounded-xl border border-[#9e1b32]/15 bg-[#f7f4ef] px-3 py-2 text-xs font-bold text-[#6d0f21]">
                    Borang 114 (Pertuduhan)
                  </div>
                  <div className="rounded-xl border border-[#9e1b32]/15 bg-[#f7f4ef] px-3 py-2 text-xs font-bold text-[#6d0f21]">
                    Saman 111
                  </div>
                  <div className="rounded-xl border border-[#9e1b32]/15 bg-[#f7f4ef] px-3 py-2 text-xs font-bold text-[#6d0f21]">
                    Diari Siasatan (S.119)
                  </div>
                  <div className="rounded-xl border border-[#9e1b32]/15 bg-[#f7f4ef] px-3 py-2 text-xs font-bold text-[#6d0f21]">
                    Rakaman S.112 &amp; Sijil 90A
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border-t-[3px] border-[#9e1b32] bg-white p-4 shadow-sm">
                <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#b98a2f]">
                  Cabaran Lapangan Yang Diselesaikan
                </p>
                <h3 className="mt-1 text-sm font-extrabold text-[#9e1b32]">
                  Kertas Kerja Manual
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-[#4c3f3f]">
                  Borang 114, Saman 111, Diari Siasatan &amp; Rakaman S.112 yang disediakan secara
                  manual memakan masa dan mudah tidak konsisten antara dokumen.
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("draft");
                  }}
                  className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  Buka Bina Fail IP <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 6: MODUL 05 — BUKU PANDUAN & 6 AKTA VERBATIM */}
          {step === 5 && (
            <div className="space-y-4">
              <div className="relative rounded-2xl border border-[#9e1b32]/20 bg-white p-5 shadow-sm">
                <span className="pointer-events-none absolute right-5 top-3 text-4xl font-black text-[#b98a2f]/25">
                  05
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#b98a2f]/15 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#6d0f21]">
                  <BookOpen className="h-3.5 w-3.5" />
                  Modul 05 · Bukan Rumusan AI Semata-mata
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Buku Panduan &amp; 6 Akta Rasmi
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-[#4c3f3f]">
                  Rujukan digital 4 fasa operasi UIP, panduan ringkas 4 akta teras, Formula 5W1H,
                  senarai 10 kesilapan utama PPKP &amp; carian ayat akta sebenar.
                </p>

                <div className="mt-3.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {VERBATIM_ACTS.map((act) => (
                    <div
                      key={act.no}
                      className="rounded-xl border border-[#241b1b]/10 bg-[#f7f4ef] p-2.5"
                    >
                      <div className="flex items-baseline gap-1.5">
                        <span className="shrink-0 text-xs font-black text-[#9e1b32]">
                          {act.no}
                        </span>
                        <span className="text-[11px] font-bold leading-snug text-[#241b1b]">
                          {act.name}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] leading-snug text-[#5a4a4a]">{act.scope}</p>
                    </div>
                  ))}
                </div>

                <p className="mt-3 text-[11px] font-semibold text-[#8a7676]">
                  Sumber: fail teks akta rasmi disimpan dalam aplikasi (<code>data/akta/</code>) —
                  semua jawapan statutori disemak terhadap teks akta sebenar.
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("guide");
                  }}
                  className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  Buka Panduan &amp; Cari Akta <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 7: MODUL 06 & PRIVASI — PROFIL PEGAWAI, DAFTAR KES & OSA 1972 / PDPA */}
          {step === 6 && (
            <div className="space-y-4">
              <div className="relative rounded-2xl border border-[#9e1b32]/20 bg-white p-5 shadow-sm">
                <span className="pointer-events-none absolute right-5 top-3 text-4xl font-black text-[#b98a2f]/25">
                  06
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#9e1b32]/10 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#9e1b32]">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Modul 06 &amp; Privasi · OSA 1972 &amp; PDPA
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Profil Pegawai, Daftar Kes &amp; Keselamatan
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-[#4c3f3f]">
                  Log masuk selamat Google OAuth 2.0, gred SSPA{" "}
                  <strong>U5–U14 / UD9–UD14 / C9–C14</strong>, auto-isi No. Kad Kuasa &amp; Sijil
                  90A serta simpanan rekod kes berterusan.
                </p>

                <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {PRIVACY_FLOW_STEPS.map((item) => (
                    <div
                      key={item.step}
                      className="rounded-xl border border-[#9e1b32]/15 bg-[#f7f4ef] p-2.5 text-center"
                    >
                      <div className="text-[10px] font-black uppercase tracking-wider text-[#b98a2f]">
                        {item.step}
                      </div>
                      <div className="mt-1 text-xs font-extrabold text-[#241b1b]">{item.title}</div>
                      <p className="mt-1 text-[10px] leading-snug text-[#5a4a4a]">{item.desc}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-3 rounded-xl border border-[#241b1b]/10 bg-[#f7f4ef] p-3">
                  <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#9e1b32]">
                    Contoh Penyamaran Identiti Tempatan
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-[#4c3f3f]">
                    Nama OKT / Saksi →{" "}
                    <code className="rounded bg-[#9e1b32]/10 px-1.5 py-0.5 font-bold text-[#9e1b32]">
                      [NAMA_OKT_1]
                    </code>{" "}
                    · No. K/P →{" "}
                    <code className="rounded bg-[#9e1b32]/10 px-1.5 py-0.5 font-bold text-[#9e1b32]">
                      [NO_KP_1]
                    </code>{" "}
                    · No. SSM →{" "}
                    <code className="rounded bg-[#9e1b32]/10 px-1.5 py-0.5 font-bold text-[#9e1b32]">
                      [SSM_1]
                    </code>
                    . Nama PPKP penyiasat &amp; fakta seksyen dikekalkan. Tanpa kunci AI, semakan
                    statutori, carian akta, kompaun, penyamaran &amp; eksport <code>.docx</code>{" "}
                    tetap beroperasi.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenCases();
                  }}
                  className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl border border-[#9e1b32]/30 bg-white px-3.5 py-2 text-xs font-extrabold text-[#6d0f21] shadow-sm transition hover:bg-[#f7f4ef]"
                >
                  <FolderOpen className="h-4 w-4 text-[#b98a2f]" />
                  Buka Daftar Kes
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenProfile();
                  }}
                  className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  <UserCheck className="h-4 w-4" />
                  Profil Pegawai
                </button>
              </div>
            </div>
          )}

          {/* KAD 8: IMPAK BERBILANG ARAS & SEDIA BERTUGAS */}
          {step === 7 && (
            <div className="space-y-4">
              <div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#6d0f21] px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#e9c98a]">
                  <Sparkles className="h-3.5 w-3.5" />
                  Sedia Bertugas · PKD Kuala Nerus
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2 text-xl font-black text-[#241b1b] sm:text-2xl"
                >
                  Impak Kepada Pegawai, Jabatan &amp; Negara
                </h2>
              </div>

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                <div className="rounded-2xl border border-[#9e1b32]/15 bg-white p-4 shadow-sm">
                  <div className="text-[10px] font-extrabold uppercase tracking-wider text-[#b98a2f]">
                    Kepada Pegawai
                  </div>
                  <h3 className="mt-1.5 text-sm font-extrabold text-[#9e1b32]">
                    Keyakinan Penguatkuasaan
                  </h3>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-[#4c3f3f]">
                    Rujukan pantas di lokasi, kompaun sah dari awal dan Kertas IP berkualiti —
                    keyakinan PPKP meningkat.
                  </p>
                </div>

                <div className="rounded-2xl border border-[#9e1b32]/15 bg-white p-4 shadow-sm">
                  <div className="text-[10px] font-extrabold uppercase tracking-wider text-[#b98a2f]">
                    Kepada Jabatan
                  </div>
                  <h3 className="mt-1.5 text-sm font-extrabold text-[#9e1b32]">
                    Produktiviti &amp; Imej
                  </h3>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-[#4c3f3f]">
                    Fail siap untuk TPR tanpa ulang alik kertas kerja; produktiviti meningkat dan
                    imej profesional PKD Kuala Nerus terpelihara.
                  </p>
                </div>

                <div className="rounded-2xl bg-[#6d0f21] p-4 text-white shadow-sm">
                  <div className="text-[10px] font-extrabold uppercase tracking-wider text-[#e9c98a]">
                    Kepada Negara
                  </div>
                  <h3 className="mt-1.5 text-sm font-extrabold text-white">
                    Kutipan Pendapatan
                  </h3>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-white/90">
                    Notis sah &amp; lengkap meningkatkan kutipan kerajaan:{" "}
                    <strong>RM18.2 juta</strong> daripada 36,426 kompaun Akta 154 (2023);{" "}
                    <strong>RM2.3 juta</strong> daripada 6,775 kompaun kesihatan awam (Apr 2024).
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[#241b1b] px-4 py-3 text-white">
                <div className="space-y-1">
                  <div className="flex flex-wrap gap-1.5 text-[10px] font-extrabold">
                    <span className="rounded border border-white/20 bg-white/10 px-2 py-0.5">
                      6 MODUL
                    </span>
                    <span className="rounded border border-white/20 bg-white/10 px-2 py-0.5">
                      6 AKTA VERBATIM
                    </span>
                    <span className="rounded border border-white/20 bg-white/10 px-2 py-0.5">
                      OSA 1972 &amp; PDPA
                    </span>
                  </div>
                  <p className="text-xs font-extrabold text-[#e9c98a]">iuippkdkn.cloud.run</p>
                </div>

                <a
                  href="https://g.dev/syrzy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-right text-[11px] text-white/80 hover:text-white"
                >
                  <div className="text-[10px] uppercase tracking-wider text-white/60">
                    Dibangunkan oleh
                  </div>
                  <div className="inline-flex items-center gap-1 font-extrabold text-white">
                    <span>
                      g.dev/<span className="text-[#e9c98a]">syrzy</span>
                    </span>
                    <ExternalLink className="h-3 w-3" />
                  </div>
                  <div className="text-[10px] text-white/60">
                    untuk UIP · PKD Kuala Nerus · KKM
                  </div>
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Footer Navigasi Kad (Titik Langkah + Jangan Papar Semula + Sebelum/Seterusnya) */}
        <div className="shrink-0 border-t border-[#241b1b]/10 bg-white px-4 py-3 sm:px-6">
          {/* Penunjuk Titik Langkah (Klik Terus Mana-Mana Kad) */}
          <div className="mb-3 flex items-center justify-center gap-1.5">
            {STEP_LABELS.map((label, idx) => {
              const active = idx === step;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => setStep(idx)}
                  title={`Kad ${idx + 1}: ${label}`}
                  aria-label={`Pergi ke Kad ${idx + 1}: ${label}`}
                  className={`h-2.5 rounded-full transition-all ${
                    active ? "w-6 bg-[#9e1b32]" : "w-2.5 bg-[#9e1b32]/25 hover:bg-[#9e1b32]/50"
                  }`}
                />
              );
            })}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-[#5a4a4a] select-none">
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(e) => onToggleDontShowAgain(e.target.checked)}
                className="h-4 w-4 rounded border-[#9e1b32]/40 accent-[#9e1b32]"
              />
              <span>Jangan papar automatik masa log masuk</span>
            </label>

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={goPrev}
                disabled={step === 0}
                className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl border border-[#241b1b]/15 bg-[#f7f4ef] px-3.5 py-2 text-xs font-bold text-[#241b1b] transition hover:bg-[#ece6dc] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ArrowLeft className="h-4 w-4" />
                Sebelum
              </button>

              {step < TOTAL_STEPS - 1 ? (
                <button
                  type="button"
                  onClick={goNext}
                  className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#9e1b32] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#6d0f21]"
                >
                  Seterusnya
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#6d0f21] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-[#400814]"
                >
                  Mula Guna
                  <Check className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
