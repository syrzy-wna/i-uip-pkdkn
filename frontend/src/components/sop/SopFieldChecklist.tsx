"use client";

import React, { useState, useEffect } from "react";
import { CheckSquare, Square, RotateCcw, Copy, Check } from "lucide-react";
import type { SopSenaraiSemakItem } from "@/lib/types";
import { copyTextSafe } from "@/lib/uiHelpers";

interface SopFieldChecklistProps {
  fileStem: string;
  sopId: string;
  items: SopSenaraiSemakItem[];
}

export default function SopFieldChecklist({
  fileStem,
  sopId,
  items,
}: SopFieldChecklistProps) {
  const storageKey = `uip_sop_checklist_v1:${fileStem}`;
  const [checkedMap, setCheckedMap] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          setCheckedMap(parsed);
          return;
        }
      }
    } catch {
      // Abaikan ralat localStorage
    }
    setCheckedMap({});
  }, [storageKey]);

  const toggleItem = (id: string) => {
    setCheckedMap((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // Abaikan kuota penuh
      }
      return next;
    });
  };

  const resetAll = () => {
    setCheckedMap({});
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // Abaikan
    }
  };

  const handleCopySummary = async () => {
    const lines = [
      `SENARAI SEMAK LAPANGAN — ${sopId}`,
      `Status: ${completedCount}/${items.length} selesai`,
      "",
      ...items.map((it) => `${checkedMap[it.id] ? "[✓]" : "[ ]"} ${it.item}`),
    ];
    const ok = await copyTextSafe(lines.join("\n"));
    if (ok) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!items || items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
        Tiada item senarai semak dijana untuk SOP ini.
      </div>
    );
  }

  const completedCount = items.filter((it) => Boolean(checkedMap[it.id])).length;
  const pct = Math.round((completedCount / items.length) * 100);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-slate-50/90 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h4 className="text-sm font-bold text-slate-900">
              Senarai Semak Pelaksanaan Lapangan
            </h4>
            <p className="text-xs text-slate-500">
              Tandaan disimpan automatik pada peranti anda untuk kegunaan operasi lapangan.
            </p>
          </div>
          <div className="no-print flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopySummary}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Disalin" : "Salin Ringkasan"}
            </button>
            <button
              type="button"
              onClick={resetAll}
              disabled={completedCount === 0}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-40"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Set Semula
            </button>
          </div>
        </div>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-xs font-semibold">
            <span className="text-slate-600">
              Kemajuan: {completedCount} / {items.length} item
            </span>
            <span className={pct === 100 ? "text-emerald-700" : "text-indigo-700"}>
              {pct}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                pct === 100 ? "bg-emerald-500" : "bg-indigo-600"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>

      <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white">
        {items.map((it) => {
          const checked = Boolean(checkedMap[it.id]);
          return (
            <button
              key={it.id}
              type="button"
              onClick={() => toggleItem(it.id)}
              aria-pressed={checked}
              className={`flex w-full items-start gap-3 px-4 py-3 text-left transition ${
                checked ? "bg-emerald-50/40" : "hover:bg-slate-50"
              }`}
            >
              {checked ? (
                <CheckSquare className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
              ) : (
                <Square className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`text-sm leading-snug ${
                      checked ? "text-slate-500 line-through" : "font-medium text-slate-800"
                    }`}
                  >
                    {it.item}
                  </span>
                  {it.wajib && (
                    <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-rose-700 ring-1 ring-rose-200">
                      Wajib
                    </span>
                  )}
                </div>
                {it.rujukan && it.rujukan.length <= 120 && (
                  <p className="mt-0.5 text-xs text-slate-500">Rujukan: {it.rujukan}</p>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
