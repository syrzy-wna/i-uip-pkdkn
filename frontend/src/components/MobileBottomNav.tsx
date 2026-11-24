"use client";

import React, { useEffect, useState } from "react";
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
  casesOpen?: boolean;
  onSelectMode: (mode: ActiveAppMode) => void;
  onOpenCases?: () => void;
  caseCount?: number;
  badges?: Partial<Record<ActiveAppMode, string>>;
}

export default function MobileBottomNav({
  activeMode,
  casesOpen = false,
  onSelectMode,
  onOpenCases,
  caseCount = 0,
  badges,
}: MobileBottomNavProps) {
  // Sembunyikan bar bawah semasa papan kekunci telefon dibuka supaya tidak menutup ruang menaip.
  const [typing, setTyping] = useState(false);
  useEffect(() => {
    let rafId: number | null = null;
    const isField = (el: Element | null) =>
      !!el &&
      ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) &&
      (el as HTMLInputElement).type !== "file" &&
      (el as HTMLInputElement).type !== "checkbox" &&
      (el as HTMLInputElement).type !== "radio";
    const onIn = (e: FocusEvent) => {
      if (rafId !== null) window.cancelAnimationFrame(rafId);
      setTyping(isField(e.target as Element));
    };
    const onOut = () => {
      if (rafId !== null) window.cancelAnimationFrame(rafId);
      rafId = window.requestAnimationFrame(() => {
        setTyping(isField(document.activeElement));
      });
    };
    window.addEventListener("focusin", onIn);
    window.addEventListener("focusout", onOut);
    return () => {
      if (rafId !== null) window.cancelAnimationFrame(rafId);
      window.removeEventListener("focusin", onIn);
      window.removeEventListener("focusout", onOut);
    };
  }, []);

  const rawIpBadge = badges?.audit || badges?.draft;
  const formattedIpBadge = rawIpBadge
    ? rawIpBadge.endsWith("%")
      ? `${Math.round(parseFloat(rawIpBadge))}%`
      : rawIpBadge
    : undefined;
  const formattedCaseBadge =
    caseCount > 99 ? "99+" : caseCount > 0 ? String(caseCount) : undefined;

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
      active: !casesOpen && activeMode === "home",
      icon: <Home className="h-5 w-5" />,
      onClick: () => onSelectMode("home"),
    },
    {
      key: "advisor",
      label: "Pakar & Akta",
      active: !casesOpen && (activeMode === "advisor" || activeMode === "directory"),
      icon: <MessageSquareQuote className="h-5 w-5" />,
      onClick: () => onSelectMode("advisor"),
    },
    {
      key: "compound",
      label: "Kompaun",
      active: !casesOpen && activeMode === "compound",
      icon: <FileCheck2 className="h-5 w-5" />,
      onClick: () => onSelectMode("compound"),
    },
    {
      key: "ip",
      label: "Fail IP",
      active:
        !casesOpen &&
        (activeMode === "audit" || activeMode === "draft" || activeMode === "redaction"),
      badge: formattedIpBadge,
      icon: <Scale className="h-5 w-5" />,
      onClick: () => onSelectMode("audit"),
    },
    {
      key: "cases",
      label: "Fail Saya",
      active: casesOpen,
      badge: formattedCaseBadge,
      icon: <FolderOpen className="h-5 w-5" />,
      onClick: () => {
        if (onOpenCases) onOpenCases();
      },
    },
  ];

  if (typing) return null;

  return (
    <nav
      aria-label="Navigasi Mudah Alih"
      className="pb-safe fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white text-slate-700 shadow-[0_-4px_16px_rgba(15,39,68,0.08)] lg:hidden"
    >
      <div className="grid grid-cols-5">
        {navItems.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={item.onClick}
            aria-current={item.active ? "page" : undefined}
            className={`relative flex min-h-[60px] flex-col items-center justify-center gap-1 border-t-2 px-1 py-1.5 text-[11px] font-bold transition ${
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
            <span className="max-w-full truncate">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
