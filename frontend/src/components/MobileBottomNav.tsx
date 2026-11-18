"use client";

import React from "react";
import {
  BookOpen,
  FileCheck2,
  FileText,
  MessageSquareQuote,
  Scale,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";

interface MobileBottomNavProps {
  activeMode: ActiveAppMode;
  onSelectMode: (mode: ActiveAppMode) => void;
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
    label: "Pakar UIP",
    icon: <MessageSquareQuote className="h-4 w-4" />,
  },
  {
    id: "compound",
    matches: ["compound"],
    label: "Kompaun",
    icon: <FileCheck2 className="h-4 w-4" />,
  },
  {
    id: "draft",
    matches: ["draft"],
    label: "Bina IP",
    icon: <FileText className="h-4 w-4" />,
  },
  {
    id: "audit",
    matches: ["audit", "redaction"],
    label: "Audit IP",
    icon: <Scale className="h-4 w-4" />,
  },
  {
    id: "guide",
    matches: ["guide"],
    label: "Panduan",
    icon: <BookOpen className="h-4 w-4" />,
  },
];

export default function MobileBottomNav({
  activeMode,
  onSelectMode,
}: MobileBottomNavProps) {
  return (
    <nav
      aria-label="Navigasi Mudah Alih i-UIP Nerus"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-700/60 bg-[#0f2744] text-white shadow-lg lg:hidden"
    >
      <div className="grid grid-cols-5">
        {MOBILE_ITEMS.map((item) => {
          const active = item.matches.includes(activeMode);
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectMode(item.id)}
              className={`flex min-h-[54px] flex-col items-center justify-center gap-0.5 px-1 py-1.5 text-[10px] font-bold transition ${
                active
                  ? "bg-blue-600/90 text-amber-300"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              }`}
            >
              {item.icon}
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
