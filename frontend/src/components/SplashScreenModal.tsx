"use client";

import React, { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  FileText,
  Mail,
  MessageSquareQuote,
  Monitor,
  Scale,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { OfficerProfile } from "@/lib/types";

interface SplashScreenModalProps {
  open: boolean;
  officer: OfficerProfile | null;
  onEnterApp: (mode: ActiveAppMode) => void;
  onOpenGoogleAuth: () => void;
  onOpenEmailAuth: (initialTab: "login" | "register") => void;
  onClose: () => void;
}

export default function SplashScreenModal({
  open,
  officer,
  onEnterApp,
  onOpenGoogleAuth,
  onOpenEmailAuth,
  onClose,
}: SplashScreenModalProps) {
  const [previewDevice, setPreviewDevice] = useState<"desktop" | "mobile">("desktop");

  if (!open) return null;

  const isMobilePreview = previewDevice === "mobile";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/80 p-3 backdrop-blur-sm sm:p-6">
      <div
        className={`relative w-full overflow-hidden rounded-3xl border border-slate-700/60 bg-white shadow-2xl transition-all duration-300 ${
          isMobilePreview ? "max-w-[400px]" : "max-w-5xl"
        }`}
      >
        {/* Bar Kawalan Pratonton Versi Website vs Mobile Web */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-100 px-4 py-2 text-[11px]">
          <div className="flex items-center gap-1.5 font-bold text-slate-700">
            <ShieldCheck className="h-4 w-4 text-emerald-700" />
            <span>Skrin Utama i-UIP Nerus • PKD Kuala Nerus</span>
          </div>

          <div className="flex items-center gap-1.5">
            <div className="hidden items-center rounded-lg bg-slate-200/80 p-0.5 sm:inline-flex">
              <button
                type="button"
                onClick={() => setPreviewDevice("desktop")}
                className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[10px] font-bold transition ${
                  previewDevice === "desktop"
                    ? "bg-white text-[#0f2744] shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Monitor className="h-3 w-3" /> Versi Website
              </button>
              <button
                type="button"
                onClick={() => setPreviewDevice("mobile")}
                className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[10px] font-bold transition ${
                  previewDevice === "mobile"
                    ? "bg-white text-[#0f2744] shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Smartphone className="h-3 w-3" /> Versi Mobile Web
              </button>
            </div>
            {officer ? (
              <button
                type="button"
                onClick={onClose}
                title="Tutup & Masuk ke Aplikasi"
                className="rounded-lg p-1 text-slate-500 hover:bg-slate-200 hover:text-slate-900"
              >
                <X className="h-4 w-4" />
              </button>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-900 ring-1 ring-amber-300">
                Wajib Daftar / Log Masuk
              </span>
            )}
          </div>
        </div>

        {/* Kandungan Splash Screen (Responsif Desktop 12-Col / Mobile Stack) */}
        <div className={isMobilePreview ? "flex flex-col" : "grid grid-cols-1 md:grid-cols-12"}>
          {/* BAHAGIAN HERO IDENTITI PKD KUALA NERUS */}
          <div
            className={`flex flex-col justify-between bg-gradient-to-br from-[#08192e] via-[#0f2744] to-[#133b69] text-white ${
              isMobilePreview ? "p-5" : "p-6 md:col-span-5 md:p-7"
            }`}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-400/20 px-2.5 py-1 text-[10px] font-bold text-amber-300 ring-1 ring-amber-400/40">
                  <Sparkles className="h-3 w-3" /> KKM • JKN Terengganu
                </span>
                <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-300 ring-1 ring-emerald-400/30">
                  Web + Mobile
                </span>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-400/20 ring-1 ring-amber-300/50">
                  <Scale className="h-7 w-7 text-amber-300" />
                </div>
                <div>
                  <h2 className="text-2xl font-extrabold tracking-tight text-white">
                    i-UIP Nerus
                  </h2>
                  <p className="text-xs font-medium text-amber-200">
                    Unit Inspektorat dan Perundangan (UIP)
                  </p>
                </div>
              </div>

              <div className="rounded-xl bg-white/10 p-3 text-xs leading-relaxed text-slate-100 ring-1 ring-white/15">
                <div className="font-bold text-white">
                  Pejabat Kesihatan Daerah Kuala Nerus, Terengganu
                </div>
                <p className="mt-1 text-[11px] text-slate-200">
                  Platform pintar PPKP &amp; Pegawai Penyiasat: semakan prosedur lapangan,
                  notis kompaun sifar kecacatan, bina Kertas Siasatan &amp; Borang 114 (`.docx`),
                  serta audit Pra-TPR.
                </p>
              </div>

              {!isMobilePreview && (
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-slate-950/35 p-2 ring-1 ring-white/10">
                    <div className="text-sm font-extrabold text-amber-300">11 SOP</div>
                    <div className="text-[10px] text-slate-300">Tanya Pakar</div>
                  </div>
                  <div className="rounded-lg bg-slate-950/35 p-2 ring-1 ring-white/10">
                    <div className="text-sm font-extrabold text-emerald-300">20 Semak</div>
                    <div className="text-[10px] text-slate-300">Audit Pra-TPR</div>
                  </div>
                  <div className="rounded-lg bg-slate-950/35 p-2 ring-1 ring-white/10">
                    <div className="text-sm font-extrabold text-sky-300">.DOCX</div>
                    <div className="text-[10px] text-slate-300">B.114 / S.112</div>
                  </div>
                </div>
              )}
            </div>

            {/* Kredit Rasmi Pembangun: g.dev/syrzy */}
            <div className="mt-5 border-t border-white/15 pt-3.5">
              <a
                href="https://g.dev/syrzy"
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center justify-between rounded-xl bg-white/10 px-3 py-2 text-xs ring-1 ring-white/20 transition hover:bg-white/20"
              >
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-300">
                    Dibangunkan oleh Dev
                  </div>
                  <div className="font-extrabold text-amber-300 group-hover:underline">
                    g.dev/syrzy
                  </div>
                </div>
                <ExternalLink className="h-4 w-4 text-slate-300 group-hover:text-white" />
              </a>
            </div>
          </div>

          {/* BAHAGIAN KANAN: AKAUN GOOGLE / EMEL & PINTASAN TUGAS */}
          <div
            className={`flex flex-col justify-between bg-slate-50 ${
              isMobilePreview ? "p-4 space-y-4" : "p-6 md:col-span-7 space-y-5"
            }`}
          >
            {/* Akses Akaun Pegawai */}
            <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-xs font-bold text-slate-900">
                  {officer
                    ? "Sesi Pegawai Aktif"
                    : "Daftar / Log Masuk Akaun Pegawai PKD"}
                </h3>
                {officer && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                    <CheckCircle2 className="h-3 w-3" /> Log Masuk
                  </span>
                )}
              </div>

              {officer ? (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-emerald-50/70 p-2.5 text-xs">
                  <div>
                    <div className="font-bold text-slate-900">{officer.full_name}</div>
                    <div className="text-[11px] text-slate-600">
                      {officer.district_pkd} • {officer.grade}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onEnterApp("advisor")}
                    className="inline-flex items-center gap-1 rounded-lg bg-[#0f2744] px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800"
                  >
                    Masuk Aplikasi <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={onOpenGoogleAuth}
                    className="flex w-full items-center justify-center gap-2.5 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold text-slate-800 shadow-xs transition hover:border-blue-400 hover:bg-blue-50/40"
                  >
                    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        fill="#4285F4"
                        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z"
                      />
                    </svg>
                    <span>Teruskan dengan Google (Daftar / Log Masuk Mudah)</span>
                  </button>

                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => onOpenEmailAuth("login")}
                      className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-[#0f2744] px-3 py-2 text-xs font-bold text-white hover:bg-slate-800"
                    >
                      <Mail className="h-3.5 w-3.5" />
                      Log Masuk Emel
                    </button>
                    <button
                      type="button"
                      onClick={() => onOpenEmailAuth("register")}
                      className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-700 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-800"
                    >
                      <UserCheck className="h-3.5 w-3.5" />
                      Daftar Emel Biasa
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* 4 Kad Pintasan Mula Tugas */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800">
                  {officer
                    ? "Pilih Tugas Utama untuk Mula Serta-Merta:"
                    : "Pratonton Modul (Sila Daftar / Log Masuk Dahulu Untuk Akses):"}
                </h3>
                <span className="text-[10px] font-semibold text-slate-500">
                  {officer ? "Mod Pantas Aktif" : "Terkunci"}
                </span>
              </div>

              <div className={isMobilePreview ? "space-y-2" : "grid grid-cols-1 gap-2 sm:grid-cols-2"}>
                <button
                  type="button"
                  onClick={() => (officer ? onEnterApp("advisor") : onOpenGoogleAuth())}
                  className={`flex items-start gap-2.5 rounded-xl border border-indigo-200 bg-white p-3 text-left transition ${
                    officer
                      ? "hover:border-indigo-400 hover:bg-indigo-50/50"
                      : "opacity-75 hover:border-blue-300"
                  }`}
                >
                  <div className="rounded-lg bg-indigo-100 p-2 text-indigo-700">
                    <MessageSquareQuote className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">1. Tanya Pakar UIP</div>
                    <div className="text-[11px] text-slate-600">
                      Semak seksyen caj, kompaun vs buka IP &amp; SOP lapangan
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => (officer ? onEnterApp("compound") : onOpenGoogleAuth())}
                  className={`flex items-start gap-2.5 rounded-xl border border-amber-200 bg-white p-3 text-left transition ${
                    officer
                      ? "hover:border-amber-400 hover:bg-amber-50/50"
                      : "opacity-75 hover:border-blue-300"
                  }`}
                >
                  <div className="rounded-lg bg-amber-100 p-2 text-amber-800">
                    <FileCheck2 className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">2. Semak Notis Kompaun</div>
                    <div className="text-[11px] text-slate-600">
                      Sahkan had denda, MyKad &amp; bukti serahan sebelum cetakan
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => (officer ? onEnterApp("draft") : onOpenGoogleAuth())}
                  className={`flex items-start gap-2.5 rounded-xl border border-blue-200 bg-white p-3 text-left transition ${
                    officer
                      ? "hover:border-blue-400 hover:bg-blue-50/50"
                      : "opacity-75 hover:border-blue-300"
                  }`}
                >
                  <div className="rounded-lg bg-blue-100 p-2 text-blue-700">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">3. Bina IP &amp; Borang 114</div>
                    <div className="text-[11px] text-slate-600">
                      Jana Minit Am 6, B.114, DS, S.112 &amp; Sijil 90A (.docx)
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => (officer ? onEnterApp("audit") : onOpenGoogleAuth())}
                  className={`flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-white p-3 text-left transition ${
                    officer
                      ? "hover:border-emerald-400 hover:bg-emerald-50/50"
                      : "opacity-75 hover:border-blue-300"
                  }`}
                >
                  <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
                    <Scale className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">4. Audit IP (Pra-TPR)</div>
                    <div className="text-[11px] text-slate-600">
                      Kesan kesilapan seksyen, tarikh bercanggah &amp; privasi PDPA
                    </div>
                  </div>
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-3">
              <span className="text-[11px] text-slate-500">
                Optimum untuk Pelayar Desktop &amp; Telefon Pintar (Mobile Web)
              </span>
              {officer ? (
                <button
                  type="button"
                  onClick={() => onEnterApp("audit")}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
                >
                  Terus Masuk ke Sistem <ArrowRight className="h-3.5 w-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onOpenGoogleAuth}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-blue-700 px-4 py-2 text-xs font-bold text-white hover:bg-blue-800"
                >
                  Daftar / Log Masuk untuk Masuk <ArrowRight className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
