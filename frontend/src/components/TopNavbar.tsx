"use client";

import React, { useState } from "react";
import {
  BookOpen,
  Cpu,
  Database,
  FileCheck2,
  FileText,
  FolderOpen,
  Home,
  Layers,
  Menu,
  MessageSquareQuote,
  Scale,
  Settings,
  ShieldCheck,
  UserCheck,
  WifiOff,
  X,
} from "lucide-react";
import type { OfficerProfile, SystemStatus } from "@/lib/types";

export type ActiveAppMode =
  | "home"
  | "advisor"
  | "directory"
  | "compound"
  | "audit"
  | "draft"
  | "redaction"
  | "guide";

interface TopNavbarProps {
  status: SystemStatus | null;
  activeMode: ActiveAppMode;
  onSelectMode: (mode: ActiveAppMode) => void;
  useOllama: boolean;
  onToggleOllama: (val: boolean) => void;
  caseCount: number;
  onOpenCases: () => void;
  onOpenSettings: () => void;
  officer: OfficerProfile | null;
  isDevAdmin: boolean;
  onOpenAccount: () => void;
  onOpenSplash: () => void;
  onOpenOnboarding?: () => void;
  onOpenDevConsole: () => void;
}

const PRIMARY_MODES: Array<{
  id: ActiveAppMode;
  matches: ActiveAppMode[];
  label: string;
  icon: React.ReactNode;
}> = [
  {
    id: "advisor",
    matches: ["advisor"],
    label: "Tanya Pakar",
    icon: <MessageSquareQuote className="h-4 w-4" />,
  },
  {
    id: "directory",
    matches: ["directory"],
    label: "Direktori Akta",
    icon: <Database className="h-4 w-4" />,
  },
  {
    id: "compound",
    matches: ["compound"],
    label: "Notis Kompaun",
    icon: <FileCheck2 className="h-4 w-4" />,
  },
  {
    id: "audit",
    matches: ["audit", "redaction"],
    label: "Semak IP",
    icon: <Scale className="h-4 w-4" />,
  },
  {
    id: "draft",
    matches: ["draft"],
    label: "Bina Fail IP",
    icon: <FileText className="h-4 w-4" />,
  },
  {
    id: "guide",
    matches: ["guide"],
    label: "Panduan",
    icon: <BookOpen className="h-4 w-4" />,
  },
];

export default function TopNavbar({
  status,
  activeMode,
  onSelectMode,
  useOllama,
  onToggleOllama,
  caseCount,
  onOpenCases,
  onOpenSettings,
  officer,
  isDevAdmin,
  onOpenAccount,
  onOpenSplash,
  onOpenOnboarding,
  onOpenDevConsole,
}: TopNavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const ollamaOk = status?.ollama.connected ?? false;
  const geminiLive = status?.gemini.api_key_configured ?? false;

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/40 bg-[#0f2744] text-white shadow-sm">
      <div className="mx-auto flex h-14 max-w-[1600px] flex-nowrap items-center justify-between gap-2 px-3 sm:px-4">
        {/* Identiti Rasmi: Logo i-UIP Nerus + PKD Kuala Nerus */}
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            onClick={onOpenSplash}
            title="Kembali ke Menu Mula (Pilih Tugasan) — PKD Kuala Nerus"
            className="flex min-w-0 items-center gap-2 text-left transition hover:opacity-90"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-iuip-nerus.png"
              alt="Logo i-UIP Nerus"
              className="h-9 w-9 shrink-0 rounded-full bg-white p-0.5 object-contain shadow-sm ring-2 ring-amber-400/70"
            />
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h1 className="truncate text-sm font-extrabold tracking-tight text-white sm:text-base">
                  i-UIP Nerus
                </h1>
              </div>
              <p className="truncate text-[11px] font-medium text-slate-300">
                PKD Kuala Nerus
              </p>
            </div>
          </button>

          <div
            title="Pejabat Kesihatan Daerah Kuala Nerus — Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus"
            className="hidden shrink-0 items-center rounded-lg bg-white/95 px-2 py-1 shadow-sm 2xl:flex"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-pkdkn.png"
              alt="Logo PKD Kuala Nerus"
              className="h-5 w-auto object-contain"
            />
          </div>
        </div>

        {/* Bar Navigasi Tunggal Desktop (1 baris bersih, tiada teks bertindih) */}
        <nav
          aria-label="Navigasi Utama Desktop"
          className="hidden items-center gap-1 rounded-xl bg-slate-900/50 p-1 ring-1 ring-white/10 lg:flex"
        >
          <button
            type="button"
            onClick={() => onSelectMode("home")}
            title="Menu Mula Tugasan"
            className={`inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-bold transition ${
              activeMode === "home"
                ? "bg-amber-400 text-slate-950 shadow-sm"
                : "text-slate-300 hover:bg-white/10 hover:text-white"
            }`}
          >
            <Home className="h-3.5 w-3.5" />
            <span className="hidden xl:inline">Mula</span>
          </button>

          {PRIMARY_MODES.map((m) => {
            const active = m.matches.includes(activeMode);
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => onSelectMode(m.id)}
                className={`inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 text-xs font-bold transition ${
                  active
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-200 hover:bg-white/10 hover:text-white"
                }`}
              >
                {m.icon}
                <span>{m.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Kawalan Kanan: Fokus Tugas + Akaun */}
        <div className="flex shrink-0 items-center gap-1.5 text-xs">
          {onOpenOnboarding && (
            <button
              type="button"
              onClick={onOpenOnboarding}
              title="Panduan Kad Fungsi i-UIP Nerus (8 Kad)"
              aria-label="Panduan Kad Fungsi i-UIP Nerus"
              className="hidden min-h-[36px] items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-bold text-amber-100 ring-1 ring-white/15 transition hover:bg-white/20 lg:inline-flex"
            >
              <Layers className="h-4 w-4 text-amber-300" />
              <span className="hidden xl:inline">Fungsi</span>
            </button>
          )}

          <button
            type="button"
            onClick={onOpenCases}
            title="Buka Senarai Fail Kes Tersimpan"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-amber-400 px-2.5 py-1.5 text-xs font-extrabold text-slate-950 shadow-sm hover:bg-amber-300 sm:min-h-[36px]"
          >
            <FolderOpen className="h-4 w-4 shrink-0" />
            <span className="hidden sm:inline">Daftar Kes</span>
            <span className="sm:hidden">Kes</span>
            <span className="rounded-full bg-slate-950/15 px-1.5 py-0.5 text-[11px] font-extrabold">
              {caseCount}
            </span>
          </button>

          <button
            type="button"
            onClick={onOpenAccount}
            title={`Akaun Pegawai (${geminiLive ? "AI Awan Aktif" : "Mod Rujukan Tempatan"})`}
            className={`inline-flex min-h-[40px] items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold shadow-sm transition sm:min-h-[36px] ${
              officer
                ? "bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                : "bg-white text-[#0f2744] hover:bg-slate-100"
            }`}
          >
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                geminiLive ? "bg-blue-700" : "bg-slate-700"
              }`}
            />
            <UserCheck className="h-4 w-4 shrink-0" />
            <span className="hidden max-w-[125px] truncate sm:inline">
              {officer ? officer.full_name : "Log Masuk"}
            </span>
          </button>

          {isDevAdmin && (
            <>
              <button
                type="button"
                onClick={onOpenDevConsole}
                title="Konsol Pembangun (g.dev/syrzy)"
                className="hidden min-h-[36px] items-center gap-1 rounded-lg bg-indigo-500/35 px-2.5 py-1.5 text-xs font-bold text-amber-200 ring-1 ring-amber-300/40 hover:bg-indigo-500/50 lg:inline-flex"
              >
                <Cpu className="h-3.5 w-3.5" />
                <span className="hidden xl:inline">Konsol Pembangun</span>
                <span className="xl:hidden">Pembangun</span>
              </button>

              <button
                type="button"
                onClick={onOpenSettings}
                title="Tetapan Enjin AI"
                aria-label="Tetapan Enjin AI"
                className="hidden min-h-[36px] items-center justify-center rounded-lg bg-white/10 p-2 text-xs font-semibold text-white ring-1 ring-white/20 hover:bg-white/20 lg:inline-flex"
              >
                <Settings className="h-4 w-4" />
              </button>
            </>
          )}

          {/* Menu Tambahan Mobile (< lg) */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label="Menu Tambahan & Status Sistem"
            className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg bg-white/10 text-white ring-1 ring-white/20 hover:bg-white/20 lg:hidden"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Panel Drawer Ringkas untuk Mobile (< lg) */}
      {mobileMenuOpen && (
        <div className="border-t border-white/15 bg-[#0b1f38] px-3 py-3 text-xs lg:hidden">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between gap-2.5 rounded-xl bg-white/10 px-3 py-2">
              <div className="shrink-0 rounded-lg bg-white px-2 py-1 shadow-sm">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/images/logo-pkdkn.png"
                  alt="Logo PKD Kuala Nerus"
                  className="h-6 w-auto object-contain"
                />
              </div>
              <p className="text-[11px] italic leading-snug text-amber-200">
                &ldquo;Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus&rdquo;
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white/10 px-3 py-2">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-sky-300" />
                <span>
                  Enjin:{" "}
                  <strong>{geminiLive ? "AI Awan Aktif" : "Mod Rujukan Tempatan"}</strong>
                </span>
              </div>
              <span className="inline-flex items-center gap-1 rounded bg-teal-500/20 px-2 py-0.5 text-[11px] font-bold text-teal-200">
                <Database className="h-3 w-3" /> {status?.rag.chunks_indexed ?? 0} Seksyen Akta
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  onSelectMode("directory");
                  setMobileMenuOpen(false);
                }}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-teal-600/35 px-3 font-bold text-teal-100 ring-1 ring-teal-400/40 hover:bg-teal-600/50"
              >
                <Database className="h-4 w-4 text-teal-200" />
                Direktori Akta
              </button>

              <button
                type="button"
                onClick={() => {
                  onSelectMode("guide");
                  setMobileMenuOpen(false);
                }}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-white/10 px-3 font-bold text-white hover:bg-white/20"
              >
                <BookOpen className="h-4 w-4 text-amber-300" />
                Panduan Pengguna
              </button>

              <button
                type="button"
                onClick={() => {
                  onSelectMode("home");
                  setMobileMenuOpen(false);
                }}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-white/10 px-3 font-bold text-white hover:bg-white/20"
              >
                <Home className="h-4 w-4 text-amber-300" />
                Menu Mula
              </button>

              <button
                type="button"
                onClick={() => {
                  onToggleOllama(!useOllama);
                }}
                className={`inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg px-3 font-bold ${
                  ollamaOk && useOllama
                    ? "bg-emerald-500/25 text-emerald-200 ring-1 ring-emerald-400/40"
                    : "bg-slate-700 text-slate-100"
                }`}
              >
                {ollamaOk ? (
                  <ShieldCheck className="h-4 w-4 text-emerald-300" />
                ) : (
                  <WifiOff className="h-4 w-4 text-amber-300" />
                )}
                Privasi: {ollamaOk && useOllama ? "AI Tempatan" : "Tempatan"}
              </button>
            </div>

            {onOpenOnboarding && (
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  onOpenOnboarding();
                }}
                className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg bg-[#9e1b32] px-3 font-extrabold text-white ring-1 ring-[#e9c98a]/40 hover:bg-[#6d0f21]"
              >
                <Layers className="h-4 w-4 text-[#e9c98a]" />
                Lihat 8 Kad Fungsi Aplikasi
              </button>
            )}

            {isDevAdmin && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onOpenDevConsole();
                  }}
                  className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 font-bold text-white"
                >
                  <Cpu className="h-4 w-4" />
                  Konsol Pembangun
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onOpenSettings();
                  }}
                  className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg bg-white/15 px-3 font-bold text-white"
                >
                  <Settings className="h-4 w-4" />
                  Tetapan AI
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
