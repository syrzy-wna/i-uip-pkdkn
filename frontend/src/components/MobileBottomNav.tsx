"use client";

import React from "react";
import {
  BookOpen,
  Database,
  FileCheck2,
  FileText,
  MessageSquareQuote,
  Scale,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";

interface MobileBottomNavProps {
  activeMode: ActiveAppMode;
  onSelectMode: (mode: ActiveAppMode) => void;
  badges?: Partial<Record<ActiveAppMode, string>>;
}

const MOBILE_ITEMS: Array<{
  id: ActiveAppMode;
  matches: ActiveAppMode[];
  label: string;
  icon: React.ReactNode;
}> = [
  {
    id: "advisor",
    matches: ["advisor"],
    label: "Pakar",
    icon: <MessageSquareQuote className="h-5 w-5" />,
  },
  {
    id: "directory",
    matches: ["directory"],
    label: "Direktori",
    icon: <Database className="h-5 w-5" />,
  },
  {
    id: "compound",
    matches: ["compound"],
    label: "Kompaun",
    icon: <FileCheck2 className="h-5 w-5" />,
  },
  {
    id: "audit",
    matches: ["audit", "redaction"],
    label: "Semak IP",
    icon: <Scale className="h-5 w-5" />,
  },
  {
    id: "draft",
    matches: ["draft"],
    label: "Bina IP",
    icon: <FileText className="h-5 w-5" />,
  },
  {
    id: "guide",
    matches: ["guide"],
    label: "Panduan",
    icon: <BookOpen className="h-5 w-5" />,
  },
];

export default function MobileBottomNav({
  activeMode,
  onSelectMode,
  badges,
}: MobileBottomNavProps) {
  return (
    <nav
      aria-label="Navigasi Mudah Alih i-UIP Nerus"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-700/70 bg-[#0f2744] text-white shadow-lg pb-safe lg:hidden"
    >
      <div className="grid grid-cols-6">
        {MOBILE_ITEMS.map((item) => {
          const active = item.matches.includes(activeMode);
          const badge = badges?.[item.id];
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectMode(item.id)}
              className={`relative flex min-h-[56px] flex-col items-center justify-center gap-0.5 border-t-2 px-1 py-1.5 text-[11px] font-bold transition ${
                active
                  ? "border-amber-400 bg-blue-600/85 text-amber-200"
                  : "border-transparent text-slate-300 hover:bg-white/10 hover:text-white"
              }`}
            >
              {badge && (
                <span className="absolute right-1.5 top-1 rounded-full bg-amber-400 px-1.5 text-[10px] font-extrabold leading-tight text-slate-950">
                  {badge}
                </span>
              )}
              {item.icon}
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
