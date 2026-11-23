"use client";

import React from "react";
import {
  FileCheck2,
  FolderOpen,
  Home,
  MessageSquareQuote,
  Scale,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";

interface MobileBottomNavProps {
  activeMode: ActiveAppMode;
  onSelectMode: (mode: ActiveAppMode) => void;
  onOpenCases?: () => void;
  caseCount?: number;
  badges?: Partial<Record<ActiveAppMode, string>>;
}

export default function MobileBottomNav({
  activeMode,
  onSelectMode,
  onOpenCases,
  caseCount = 0,
  badges,
}: MobileBottomNavProps) {
  const navItems: Array<{
    key: string;
    label: string;
    active: boolean;
    badge?: string;
    icon: React.ReactNode;
    onClick: () => void;
  }> = [
    {
      key: "home",
      label: "Utama",
      active: activeMode === "home",
      icon: <Home className="h-5 w-5" />,
      onClick: () => onSelectMode("home"),
    },
    {
      key: "advisor",
      label: "Pakar",
      active: activeMode === "advisor" || activeMode === "directory",
      icon: <MessageSquareQuote className="h-5 w-5" />,
      onClick: () => onSelectMode("advisor"),
    },
    {
      key: "compound",
      label: "Kompaun",
      active: activeMode === "compound",
      icon: <FileCheck2 className="h-5 w-5" />,
      onClick: () => onSelectMode("compound"),
    },
    {
      key: "ip",
      label: "Fail IP",
      active: activeMode === "audit" || activeMode === "draft" || activeMode === "redaction",
      badge: badges?.audit || badges?.draft,
      icon: <Scale className="h-5 w-5" />,
      onClick: () => onSelectMode("audit"),
    },
    {
      key: "cases",
      label: "Fail Saya",
      active: false,
      badge: caseCount > 0 ? String(caseCount) : undefined,
      icon: <FolderOpen className="h-5 w-5" />,
      onClick: () => {
        if (onOpenCases) onOpenCases();
      },
    },
  ];

  return (
    <nav
      aria-label="Navigasi Mudah Alih"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white text-slate-700 shadow-[0_-4px_16px_rgba(15,39,68,0.08)] pb-safe lg:hidden"
    >
      <div className="grid grid-cols-5">
        {navItems.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={item.onClick}
            aria-current={item.active ? "page" : undefined}
            className={`relative flex min-h-[60px] flex-col items-center justify-center gap-1 border-t-2 px-1 py-1.5 text-xs font-bold transition ${
              item.active
                ? "border-[#0f2744] bg-slate-50 text-[#0f2744]"
                : "border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <span className="relative inline-flex items-center justify-center">
              {item.icon}
              {item.badge && (
                <span className="absolute -right-3.5 -top-1.5 rounded-full bg-[#0f2744] px-1.5 py-0.5 text-[10px] font-extrabold leading-none text-white">
                  {item.badge}
                </span>
              )}
            </span>
            <span className="truncate">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
