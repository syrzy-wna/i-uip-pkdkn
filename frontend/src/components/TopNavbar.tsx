"use client";

import React from "react";
import {
  BookOpen,
  Cpu,
  Database,
  FileCheck2,
  FileText,
  FolderOpen,
  MessageSquareQuote,
  Scale,
  Settings,
  ShieldCheck,
  UserCheck,
  WifiOff,
} from "lucide-react";
import type { OfficerProfile, SystemStatus } from "@/lib/types";

export type ActiveAppMode = "advisor" | "compound" | "draft" | "audit" | "redaction" | "guide";

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
  onOpenAccount: () => void;
  onOpenSplash: () => void;
  onOpenDevConsole: () => void;
}

const PRIMARY_MODES: Array<{
  id: ActiveAppMode;
  matches: ActiveAppMode[];
  label: string;
  sub: string;
  icon: React.ReactNode;
}> = [
  {
    id: "advisor",
    matches: ["advisor"],
    label: "1. Tanya Pakar UIP",
    sub: "Seksyen, Caj & SOP",
    icon: <MessageSquareQuote className="h-4 w-4" />,
  },
  {
    id: "compound",
    matches: ["compound"],
    label: "2. Notis Kompaun",
    sub: "Semak 10 Perkara",
    icon: <FileCheck2 className="h-4 w-4" />,
  },
  {
    id: "draft",
    matches: ["draft"],
    label: "3. Bina Fail IP & .docx",
    sub: "B.114, DS, S.112, 90A",
    icon: <FileText className="h-4 w-4" />,
  },
  {
    id: "audit",
    matches: ["audit", "redaction"],
    label: "4. Audit IP (Pra-TPR)",
    sub: "20 Kriteria & PDPA",
    icon: <Scale className="h-4 w-4" />,
  },
  {
    id: "guide",
    matches: ["guide"],
    label: "5. Panduan & SOP",
    sub: "Carta Alir & Akta",
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
  onOpenAccount,
  onOpenSplash,
  onOpenDevConsole,
}: TopNavbarProps) {
  const ollamaOk = status?.ollama.connected ?? false;
  const geminiLive = status?.gemini.api_key_configured ?? false;

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-[#0f2744] text-white shadow-sm">
      <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-2.5 px-3 py-2 sm:px-4 sm:py-2.5">
        {/* Identiti Sistem: i-UIP Nerus (PKD Kuala Nerus) */}
        <button
          type="button"
          onClick={onOpenSplash}
          title="Klik untuk buka semula Skrin Utama (Splash Screen Website & Mobile)"
          className="flex items-center gap-2.5 text-left transition hover:opacity-90"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 ring-1 ring-amber-400/50">
            <Scale className="h-5 w-5 text-amber-300" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-1.5">
              <h1 className="text-base font-extrabold tracking-tight text-white">
                i-UIP Nerus
              </h1>
              <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold text-emerald-300 ring-1 ring-emerald-400/30">
                PKD Kuala Nerus
              </span>
              <span className="hidden rounded bg-amber-400/15 px-1.5 py-0.5 text-[9px] font-semibold text-amber-200 ring-1 ring-amber-400/30 sm:inline-block">
                Dev: g.dev/syrzy
              </span>
            </div>
            <p className="text-[11px] text-slate-300">
              Unit Inspektorat &amp; Perundangan • PKD Kuala Nerus, Terengganu
            </p>
          </div>
        </button>

        {/* Bar Navigasi Tunggal Desktop (Mobile guna MobileBottomNav) */}
        <nav className="hidden flex-wrap items-center gap-1 rounded-xl bg-slate-900/55 p-1 ring-1 ring-white/10 lg:flex">
          {PRIMARY_MODES.map((m) => {
            const active = m.matches.includes(activeMode);
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => onSelectMode(m.id)}
                className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-left transition ${
                  active
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                {m.icon}
                <div>
                  <div className="text-xs font-bold leading-tight">{m.label}</div>
                  <div className="text-[10px] leading-tight opacity-80">{m.sub}</div>
                </div>
              </button>
            );
          })}
        </nav>

        {/* Status Sambungan, Daftar Kes, Akaun & Tetapan */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <button
            type="button"
            onClick={() => onToggleOllama(!useOllama)}
            title="Klik untuk tukar mod penyamaran data sulit tempatan (Ollama PC / Regex KKM)"
            className={`hidden items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium ring-1 transition 2xl:flex ${
              ollamaOk && useOllama
                ? "bg-emerald-500/20 text-emerald-200 ring-emerald-400/40"
                : "bg-amber-500/15 text-amber-200 ring-amber-400/30"
            }`}
          >
            {ollamaOk ? (
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" />
            ) : (
              <WifiOff className="h-3.5 w-3.5 text-amber-300" />
            )}
            <span>{ollamaOk ? `Ollama (${status?.ollama.configured_model})` : "Privasi Regex"}</span>
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            title="Status AI Gemini & RAG"
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 transition hover:opacity-90 ${
              geminiLive
                ? "bg-blue-500/20 text-blue-200 ring-blue-400/40"
                : "bg-slate-700/80 text-slate-200 ring-slate-500/50"
            }`}
          >
            <Cpu className="h-3.5 w-3.5" />
            <span>{geminiLive ? "AI Aktif" : "Luar Talian"}</span>
          </button>

          <div
            title="Pangkalan Akta Verbatim RAG"
            className="hidden items-center gap-1 rounded-full bg-teal-500/20 px-2 py-1 text-[11px] font-medium text-teal-200 ring-1 ring-teal-400/30 xl:flex"
          >
            <Database className="h-3.5 w-3.5" />
            <span>{status?.rag.chunks_indexed ?? 0} Seksyen</span>
          </div>

          <button
            type="button"
            onClick={onOpenCases}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-2.5 py-1.5 text-xs font-bold text-slate-950 shadow-sm hover:bg-amber-400"
          >
            <FolderOpen className="h-3.5 w-3.5" />
            Daftar Kes ({caseCount})
          </button>

          <button
            type="button"
            onClick={onOpenAccount}
            title="Akaun Pegawai Sebenar (Auto-Isi Borang 114 & Sijil 90A)"
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold shadow-sm transition ${
              officer
                ? "bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                : "bg-white text-[#0f2744] hover:bg-slate-100"
            }`}
          >
            <UserCheck className="h-3.5 w-3.5" />
            <span className="max-w-[130px] truncate">
              {officer ? officer.full_name : "Daftar / Log Masuk"}
            </span>
          </button>

          <button
            type="button"
            onClick={onOpenDevConsole}
            title="Konsol Pembangun (g.dev/syrzy): Semak Pengguna, Aktiviti & Kos API"
            className="inline-flex items-center gap-1 rounded-lg bg-indigo-500/30 px-2.5 py-1.5 text-xs font-bold text-amber-200 ring-1 ring-amber-300/40 hover:bg-indigo-500/50"
          >
            <Cpu className="h-3.5 w-3.5" />
            Konsol Dev
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            title="Tetapan Kunci API Gemini & Ollama"
            className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-semibold text-white ring-1 ring-white/20 hover:bg-white/20"
          >
            <Settings className="h-3.5 w-3.5" />
            Tetapan
          </button>
        </div>
      </div>
    </header>
  );
}
