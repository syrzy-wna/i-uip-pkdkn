"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  FileCheck2,
  FolderOpen,
  MessageSquareQuote,
  Scale,
  ShieldCheck,
  UserCheck,
  X,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";
import { useLockBodyScroll } from "@/lib/uiHelpers";
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

const TOTAL_STEPS = 5;

const STEP_LABELS = [
  "Pengenalan",
  "Pakar & Akta",
  "Notis Kompaun",
  "Fail IP",
  "Mula Bertugas",
];

const CORE_ACTS = [
  {
    no: "Akta 852",
    name: "Kawalan Produk Merokok Demi Kesihatan Awam 2024",
    scope: "Vape, merokok kawasan larangan, pameran terbuka, pelajar bawah 18 tahun.",
  },
  {
    no: "Akta 281",
    name: "Akta Makanan 1983 & PPKM 2009",
    scope: "Premis kotor S.11, suntikan tifoid P.31, latihan pengendali P.30, kompaun S.32B.",
  },
  {
    no: "Akta 154",
    name: "Pemusnahan Serangga Pembawa Penyakit 1975",
    scope: "Pembiakan Aedes S.13, Perintah S.8, had kompaun S.25 maksimum RM500.",
  },
  {
    no: "Akta 342",
    name: "Pencegahan & Pengawalan Penyakit Berjangkit 1988",
    scope: "Pesakit Tibi cicir rawatan, ingkar perintah S.22 dan S.24.",
  },
  {
    no: "Akta 593 & 56",
    name: "Kanun Tatacara Jenayah & Akta Keterangan 1950",
    scope: "Rakaman S.112, Diari S.119, Penzahiran S.51A, Pelupusan S.407/407A & Sijil S.90A.",
  },
  {
    no: "Akta 574, 344, 388 & 92",
    name: "Kanun Keseksaan, Akta Polis, Akta Tafsiran & Mahkamah Rendah",
    scope: "Rujukan silang halang/ugut PPKP (S.186/353/506), sijil palsu (S.465/471), bantuan polis (S.20(3)(c)), 10 hari bersih (S.54) & had mahkamah (S.63/64/87).",
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

  useLockBodyScroll(open);

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
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") goNext();
      else if (e.key === "ArrowLeft") goPrev();
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-2.5 backdrop-blur-sm sm:p-5"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 shadow-2xl"
      >
        {/* Header */}
        <div className="shrink-0 border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span className="inline-flex shrink-0 items-center rounded-full bg-[#0f2744] px-2.5 py-0.5 text-[11px] font-bold text-white">
                {step + 1} / {TOTAL_STEPS}
              </span>
              <span className="truncate text-xs font-bold text-slate-700">
                {STEP_LABELS[step]}
              </span>
            </div>

            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup pengenalan ringkas"
              className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-[#0f2744] transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Badan */}
        <div
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          className="flex-1 overflow-y-auto p-4 sm:p-6"
        >
          {/* KAD 1: PENGENALAN */}
          {step === 0 && (
            <div className="space-y-4">
              <div className="rounded-2xl bg-[#0f2744] p-5 text-white shadow-sm sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/images/logo-iuip-nerus.png"
                      alt="Logo i-UIP Nerus"
                      className="h-11 w-11 shrink-0 rounded-full bg-white p-0.5 object-contain shadow"
                    />
                    <div className="rounded-lg bg-white px-2.5 py-1">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src="/images/logo-pkdkn.png"
                        alt="Logo i-UIP Nerus"
                        className="h-6 w-auto object-contain"
                      />
                    </div>
                  </div>
                  <span className="text-[11px] font-bold text-amber-300">
                    UIP • KKM Seluruh Malaysia
                  </span>
                </div>

                <h2
                  id="onboarding-card-title"
                  className="mt-4 text-2xl font-extrabold tracking-tight text-white sm:text-3xl"
                >
                  Pengenalan Ringkas i-UIP Nerus
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-slate-200 sm:text-sm">
                  Pembantu kerja harian PPKP, PKP dan Pegawai Penyiasat (IO) — daripada rujukan di
                  lokasi operasi hingga Fail IP sedia untuk semakan Timbalan Pendakwa Raya (TPR).
                </p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
                {officer?.full_name && (
                  <p className="mb-1.5 text-xs font-extrabold text-[#0f2744]">
                    Selamat bertugas, {officer.full_name}.
                  </p>
                )}
                <p className="text-xs leading-relaxed text-slate-700 sm:text-sm">
                  Semua tugas utama disusun dalam <strong>3 ruang kerja ringkas</strong>:
                </p>
                <ul className="mt-3 space-y-2 text-xs text-slate-700 sm:text-sm">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>
                      <strong>Pakar &amp; Akta:</strong> Tanya situasi di lokasi, semak senarai
                      kesalahan dan rujuk teks penuh 11 akta rasmi (KKM + rujukan silang).
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>
                      <strong>Notis Kompaun:</strong> Ambil foto Sijil SSM, semak 10 perkara wajib
                      dan muat turun Notis Word (.docx).
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>
                      <strong>Fail IP:</strong> Muat naik PDF Kertas Siasatan, semak 20 kriteria
                      Pra-TPR, sunting Borang 114 dan muat turun Word (.docx).
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* KAD 2: PAKAR & AKTA */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-[#0f2744]">
                  <MessageSquareQuote className="h-3.5 w-3.5" />
                  Ruang Kerja 1 • Rujukan Di Lokasi
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-extrabold text-slate-900"
                >
                  Pakar &amp; Akta
                </h2>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600 sm:text-sm">
                  Taip situasi sebenar di lokasi operasi. Sistem akan memaklumkan secara jelas sama
                  ada terdapat kesalahan atau tidak, berserta seksyen tepat, langkah SOP dan teks
                  penuh Warta.
                </p>

                <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {CORE_ACTS.map((act) => (
                    <div
                      key={act.no}
                      className="rounded-xl border border-slate-200 bg-slate-50/70 p-2.5"
                    >
                      <div className="text-xs font-extrabold text-[#0f2744]">{act.no}</div>
                      <div className="text-[11px] font-bold text-slate-800">{act.name}</div>
                      <p className="mt-0.5 text-[11px] text-slate-600">{act.scope}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("advisor");
                  }}
                  className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                >
                  Buka Pakar &amp; Akta <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 3: NOTIS KOMPAUN */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-[#0f2744]">
                  <FileCheck2 className="h-3.5 w-3.5" />
                  Ruang Kerja 2 • 3 Langkah Kemas
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-extrabold text-slate-900"
                >
                  Notis Kompaun
                </h2>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600 sm:text-sm">
                  Sediakan Notis Kompaun yang sah tanpa tersilap had amaun atau tertinggal maklumat
                  wajib.
                </p>

                <ul className="mt-4 space-y-2 text-xs text-slate-700 sm:text-sm">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>
                      <strong>Ambil Foto Sijil SSM / Notis:</strong> Nama syarikat, No. SSM dan
                      alamat diisi secara automatik.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>
                      <strong>Semakan 10 Perkara Wajib:</strong> Mengesan amaran had undang-undang
                      (contohnya had RM500 Akta 154) sebelum dicetak.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>
                      <strong>Muat Turun Word (.docx):</strong> Notis rasmi sedia dicetak dan
                      diserahkan kepada penerima.
                    </span>
                  </li>
                </ul>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("compound");
                  }}
                  className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                >
                  Buka Notis Kompaun <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 4: FAIL IP */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-[#0f2744]">
                  <Scale className="h-3.5 w-3.5" />
                  Ruang Kerja 3 • 1 Aliran Bersepadu
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-extrabold text-slate-900"
                >
                  Fail IP (Semak Pra-TPR &amp; Jana Word)
                </h2>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600 sm:text-sm">
                  Ikut 3 langkah mudah supaya Kertas Siasatan lengkap sebelum dihantar kepada TPR:
                </p>

                <ol className="mt-4 space-y-2.5 text-xs text-slate-700 sm:text-sm">
                  <li className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                    <strong>Langkah 1 — Bahan Kes:</strong> Muat naik PDF Kertas Siasatan, foto
                    dokumen atau tampal catatan kes. Teks dibaca secara automatik.
                  </li>
                  <li className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                    <strong>Langkah 2 — Semak Pra-TPR:</strong> Sistem menyemak 20 perkara kritikal
                    (seksyen, tarikh/masa, susunan Fail A–G dan Sijil S.90A).
                  </li>
                  <li className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                    <strong>Langkah 3 — Sunting &amp; Muat Turun Word:</strong> Baiki kesilapan terus
                    pada Borang 114, Saman 111, S.112, Diari dan Sijil 90A, semak semula skor dan
                    muat turun fail Word (.docx).
                  </li>
                </ol>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateMode("audit");
                  }}
                  className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                >
                  Buka Fail IP <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* KAD 5: PRIVASI & 3 LANGKAH MULA SEKARANG */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-800">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Perlindungan Data Sulit (Akta Rahsia Rasmi 1972 &amp; PDPA)
                </span>
                <h2
                  id="onboarding-card-title"
                  className="mt-2.5 text-xl font-extrabold text-slate-900"
                >
                  3 Langkah Mula Sekarang
                </h2>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600 sm:text-sm">
                  Nama OKT, No. K/P dan No. SSM dilindungi secara automatik semasa semakan AI, dan
                  dipulihkan semula apabila anda memuat turun dokumen Word rasmi.
                </p>

                <div className="mt-4 space-y-2.5">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-xs text-slate-700">
                    <strong>1. Lengkapkan Profil Pegawai:</strong> Masukkan No. Kad Kuasa dan
                    butiran peranti Sijil S.90A sekali sahaja supaya diisi secara automatik dalam
                    setiap notis dan Fail IP.
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-xs text-slate-700">
                    <strong>2. Cuba Contoh Kes 10 Saat:</strong> Di halaman Utama, klik mana-mana
                    butang contoh untuk melihat hasil Pakar, Kompaun atau Semakan Pra-TPR dengan
                    serta-merta.
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-xs text-slate-700">
                    <strong>3. Simpan &amp; Sambung Bila-bila Masa:</strong> Semua kes anda
                    disimpan dalam menu <strong>Fail Saya</strong>.
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenCases();
                  }}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  <FolderOpen className="h-4 w-4 text-slate-500" />
                  Buka Fail Saya
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenProfile();
                  }}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                >
                  <UserCheck className="h-4 w-4" />
                  Lengkapkan Profil
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Navigasi */}
        <div className="pb-safe shrink-0 border-t border-slate-200 bg-white px-4 py-3 sm:px-6">
          <div className="mb-1 flex items-center justify-center gap-1">
            {STEP_LABELS.map((label, idx) => {
              const active = idx === step;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => setStep(idx)}
                  title={`${idx + 1}. ${label}`}
                  aria-label={`Pergi ke langkah ${idx + 1}: ${label}`}
                  className="inline-flex min-h-[44px] min-w-[32px] items-center justify-center px-1"
                >
                  <span
                    className={`block h-2.5 rounded-full transition-all ${
                      active ? "w-6 bg-[#0f2744]" : "w-2.5 bg-slate-300 hover:bg-slate-400"
                    }`}
                  />
                </button>
              );
            })}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex min-h-[40px] cursor-pointer items-center gap-2 text-xs font-medium text-slate-600 select-none">
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(e) => onToggleDontShowAgain(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 accent-[#0f2744]"
              />
              <span>Jangan paparkan lagi pada masa hadapan</span>
            </label>

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={goPrev}
                disabled={step === 0}
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ArrowLeft className="h-4 w-4" />
                Sebelum
              </button>

              {step < TOTAL_STEPS - 1 ? (
                <button
                  type="button"
                  onClick={goNext}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-slate-800"
                >
                  Seterusnya
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-slate-800"
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
