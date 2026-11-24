"use client";

import React from "react";
import {
  Cpu,
  FileCheck2,
  FolderOpen,
  HelpCircle,
  Home,
  MessageSquareQuote,
  Scale,
  Settings,
  UserCheck,
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
  useOllama?: boolean;
  onToggleOllama?: (val: boolean) => void;
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
    id: "home",
    matches: ["home"],
    label: "Utama",
    icon: <Home className="h-4 w-4" />,
  },
  {
    id: "advisor",
    matches: ["advisor", "directory"],
    label: "Pakar & Akta",
    icon: <MessageSquareQuote className="h-4 w-4" />,
  },
  {
    id: "compound",
    matches: ["compound"],
    label: "Kompaun",
    icon: <FileCheck2 className="h-4 w-4" />,
  },
  {
    id: "audit",
    matches: ["audit", "draft", "redaction"],
    label: "Fail IP",
    icon: <Scale className="h-4 w-4" />,
  },
];

export default function TopNavbar({
  activeMode,
  onSelectMode,
  caseCount,
  onOpenCases,
  onOpenSettings,
  officer,
  isDevAdmin,
  onOpenAccount,
  onOpenSplash,
  onOpenDevConsole,
}: TopNavbarProps) {
  const firstName = officer?.full_name
    ? officer.full_name.replace(/^(PPKP|PKP|DR\.?|EN\.?|PN\.?|CIK)\s+/i, "").split(" ")[0]
    : "";

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/40 bg-[#0f2744] text-white shadow-sm">
      <div className="mx-auto flex h-14 max-w-[1440px] flex-nowrap items-center justify-between gap-2 px-3 sm:px-5">
        {/* Kiri: Identiti Rasmi */}
        <button
          type="button"
          onClick={onOpenSplash}
          title="Kembali ke Halaman Utama"
          className="flex min-w-0 items-center gap-2.5 text-left transition hover:opacity-90"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/logo-iuip-nerus.png"
            alt="Logo i-UIP Nerus"
            className="h-9 w-9 shrink-0 rounded-full bg-white p-0.5 object-contain shadow-sm ring-1 ring-white/40"
          />
          <div className="min-w-0">
            <div className="truncate text-sm font-extrabold tracking-tight text-white sm:text-base">
              i-UIP Nerus
            </div>
            <p className="truncate text-xs font-medium text-slate-300">
              {officer?.district_pkd || "Unit Inspektorat & Perundangan KKM"}
            </p>
          </div>
        </button>

        {/* Tengah: 4 Ruang Kerja Utama Desktop (Seragam Dengan Bar Bawah Telefon) */}
        <nav
          aria-label="Navigasi Utama"
          className="hidden items-center gap-1 rounded-xl bg-white/10 p-1 lg:flex"
        >
          {PRIMARY_MODES.map((m) => {
            const active = m.matches.includes(activeMode);
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => onSelectMode(m.id)}
                aria-current={active ? "page" : undefined}
                className={`inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-lg px-3.5 text-xs font-bold transition ${
                  active
                    ? "bg-white text-[#0f2744] shadow-sm"
                    : "text-slate-200 hover:bg-white/10 hover:text-white"
                }`}
              >
                {m.icon}
                <span>{m.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Kanan: Kawalan Tenang & Jelas */}
        <div className="flex shrink-0 items-center gap-1.5 text-xs">
          <button
            type="button"
            onClick={onOpenCases}
            title="Buka Fail Kes Tersimpan"
            className="hidden min-h-[44px] items-center gap-1.5 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-bold text-white ring-1 ring-white/15 transition hover:bg-white/20 lg:inline-flex"
          >
            <FolderOpen className="h-4 w-4 shrink-0 text-slate-200" />
            <span>Fail Saya</span>
            <span className="rounded-full bg-white/20 px-1.5 py-0.5 text-xs font-extrabold text-white">
              {caseCount}
            </span>
          </button>

          <button
            type="button"
            onClick={() => onSelectMode("guide")}
            title="SOP Lapangan & Panduan Ringkas"
            aria-label="SOP Lapangan dan Panduan Ringkas"
            className={`inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold transition ${
              activeMode === "guide"
                ? "bg-white text-[#0f2744] shadow-sm"
                : "bg-white/10 text-slate-100 ring-1 ring-white/15 hover:bg-white/20"
            }`}
          >
            <HelpCircle className="h-4 w-4 shrink-0" />
            <span className="hidden xl:inline">Panduan</span>
          </button>

          <button
            type="button"
            onClick={onOpenAccount}
            title={officer ? `Profil: ${officer.full_name}` : "Log Masuk Akaun Pegawai"}
            aria-label={officer ? `Profil ${officer.full_name}` : "Log Masuk Akaun Pegawai"}
            className={`inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              officer
                ? "bg-white/15 text-white ring-1 ring-white/25 hover:bg-white/25"
                : "bg-white text-[#0f2744] hover:bg-slate-100"
            }`}
          >
            <UserCheck className="h-4 w-4 shrink-0" />
            <span className="hidden max-w-[115px] truncate sm:inline">
              {officer ? firstName || officer.full_name : "Log Masuk"}
            </span>
          </button>

          {isDevAdmin && (
            <>
              <button
                type="button"
                onClick={onOpenDevConsole}
                title="Konsol Pembangun"
                aria-label="Konsol Pembangun"
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-bold text-amber-200 ring-1 ring-white/20 hover:bg-white/20"
              >
                <Cpu className="h-4 w-4" />
                <span className="hidden xl:inline">Pembangun</span>
              </button>

              <button
                type="button"
                onClick={onOpenSettings}
                title="Tetapan Sistem AI"
                aria-label="Tetapan Sistem AI"
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg bg-white/10 text-white ring-1 ring-white/20 hover:bg-white/20"
              >
                <Settings className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
