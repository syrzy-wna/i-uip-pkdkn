"use client";

import React from "react";
import { ArrowDown, GitBranch, PlayCircle, CheckCircle2, ExternalLink } from "lucide-react";
import type { SopCartaAlir } from "@/lib/types";

interface SopFlowchartProps {
  cartaAlir: SopCartaAlir;
  onSelectStep?: (stepNo: string) => void;
  onOpenSop?: (sopCode: string) => void;
}

const ROLE_COLORS: Record<string, string> = {
  PPKP: "bg-sky-100 text-sky-800 border-sky-200",
  PKP: "bg-indigo-100 text-indigo-800 border-indigo-200",
  KPPKP: "bg-indigo-100 text-indigo-800 border-indigo-200",
  PPKPK: "bg-indigo-100 text-indigo-800 border-indigo-200",
  PKD: "bg-purple-100 text-purple-800 border-purple-200",
  IO: "bg-teal-100 text-teal-800 border-teal-200",
  RO: "bg-cyan-100 text-cyan-800 border-cyan-200",
  PO: "bg-violet-100 text-violet-800 border-violet-200",
  TPR: "bg-rose-100 text-rose-800 border-rose-200",
  PDK: "bg-blue-100 text-blue-800 border-blue-200",
  PKA: "bg-emerald-100 text-emerald-800 border-emerald-200",
  PKAK: "bg-emerald-100 text-emerald-800 border-emerald-200",
  PDRM: "bg-slate-200 text-slate-800 border-slate-300",
};

function getRoleStyle(role?: string | null): string {
  if (!role) return "bg-slate-100 text-slate-700 border-slate-200";
  const key = role.toUpperCase().split(/[/,\s]+/)[0];
  return ROLE_COLORS[key] || "bg-slate-100 text-slate-700 border-slate-200";
}

export default function SopFlowchart({
  cartaAlir,
  onSelectStep,
  onOpenSop,
}: SopFlowchartProps) {
  const nodes = cartaAlir?.nodes || [];
  const edges = cartaAlir?.edges || [];

  if (nodes.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
        Carta alir visual belum dijana untuk SOP ini. Rujuk tab <strong>Ringkasan &amp; Langkah</strong>.
      </div>
    );
  }

  const edgeByFrom = new Map<string, string[]>();
  for (const e of edges) {
    if (!e.label) continue;
    const list = edgeByFrom.get(e.from) || [];
    list.push(e.label);
    edgeByFrom.set(e.from, list);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-2.5 text-xs text-slate-600">
        <span>
          Klik mana-mana kotak langkah untuk terus melompat ke butiran penuh tindakan dalam tab{" "}
          <strong className="text-slate-800">Ringkasan &amp; Langkah</strong>.
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800">
            Mula / Tamat
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 font-medium text-slate-700 ring-1 ring-slate-200">
            Langkah Proses
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-900">
            Titik Keputusan
          </span>
        </div>
      </div>

      <div className="mx-auto flex max-w-2xl flex-col items-center py-2">
        {nodes.map((node, idx) => {
          const isStart = node.type === "start";
          const isEnd = node.type === "end";
          const isDecision = node.type === "decision";
          const edgeLabels = edgeByFrom.get(node.id) || [];
          const clickable = Boolean(node.step_ref && onSelectStep);

          return (
            <React.Fragment key={node.id}>
              {isStart || isEnd ? (
                <div
                  className={`sop-print-break-avoid inline-flex items-center gap-2 rounded-full border px-5 py-2 text-xs font-bold shadow-sm ${
                    isStart
                      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                      : "border-indigo-300 bg-indigo-50 text-indigo-900"
                  }`}
                >
                  {isStart ? (
                    <PlayCircle className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-indigo-600" />
                  )}
                  <span>{node.label}</span>
                </div>
              ) : (
                <div
                  role={clickable ? "button" : undefined}
                  tabIndex={clickable ? 0 : undefined}
                  onClick={() => clickable && node.step_ref && onSelectStep?.(node.step_ref)}
                  onKeyDown={(e) => {
                    if (clickable && node.step_ref && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault();
                      onSelectStep?.(node.step_ref);
                    }
                  }}
                  className={`sop-print-break-avoid w-full rounded-xl border p-3.5 shadow-sm transition ${
                    isDecision
                      ? "border-amber-300 bg-amber-50/70 hover:border-amber-400"
                      : "border-slate-200 bg-white hover:border-indigo-300"
                  } ${clickable ? "cursor-pointer hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500" : ""}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      {isDecision ? (
                        <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-amber-200/80 text-amber-900">
                          <GitBranch className="h-3.5 w-3.5" />
                        </span>
                      ) : (
                        <span className="mt-0.5 inline-flex h-6 min-w-[24px] shrink-0 items-center justify-center rounded-full bg-indigo-600 px-1.5 text-[11px] font-bold text-white">
                          {node.step_ref || idx}
                        </span>
                      )}
                      <div>
                        {isDecision && (
                          <div className="mb-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-800">
                            Titik Keputusan / Syarat
                          </div>
                        )}
                        <p className="text-sm font-medium leading-snug text-slate-800">
                          {node.label}
                        </p>
                      </div>
                    </div>

                    {node.role && (
                      <span
                        className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-bold ${getRoleStyle(
                          node.role
                        )}`}
                      >
                        {node.role}
                      </span>
                    )}
                  </div>

                  {node.sop_ref && onOpenSop && (
                    <div className="mt-2 flex items-center justify-end">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenSop(node.sop_ref as string);
                        }}
                        className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Buka {node.sop_ref}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {idx < nodes.length - 1 && (
                <div className="flex flex-col items-center py-1 text-slate-400">
                  <div className="h-3 w-px bg-slate-300" />
                  {edgeLabels.length > 0 && (
                    <span className="my-0.5 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
                      {edgeLabels.join(" / ")}
                    </span>
                  )}
                  <ArrowDown className="h-3.5 w-3.5" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
