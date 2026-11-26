"use client";

import React, { useState, useEffect } from "react";
import {
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  GitBranch,
  AlertTriangle,
  ExternalLink,
  BookOpen,
} from "lucide-react";
import type { SopFasaKerja } from "@/lib/types";

interface SopStepTimelineProps {
  fasaKerja: SopFasaKerja[];
  highlightedStepNo?: string | null;
  onJumpToLampiran?: (lampiranKod: string) => void;
  onOpenSop?: (sopCode: string) => void;
}

const ROLE_BADGE_MAP: Record<string, string> = {
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
  PSPP: "bg-lime-100 text-lime-800 border-lime-200",
  PDRM: "bg-slate-200 text-slate-800 border-slate-300",
};

function badgeForRole(role: string): string {
  const key = role.toUpperCase().split(/[/,\s]+/)[0];
  return ROLE_BADGE_MAP[key] || "bg-slate-100 text-slate-700 border-slate-200";
}

export default function SopStepTimeline({
  fasaKerja,
  highlightedStepNo,
  onJumpToLampiran,
  onOpenSop,
}: SopStepTimelineProps) {
  const [openPhases, setOpenPhases] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const initial: Record<string, boolean> = {};
    for (const ph of fasaKerja) {
      initial[ph.fasa_id] = true;
    }
    setOpenPhases(initial);
  }, [fasaKerja]);

  useEffect(() => {
    if (!highlightedStepNo) return;
    // Pastikan fasa yang mengandungi langkah tersebut dibuka dan skrol ke elemen langkah
    const targetPhase = fasaKerja.find((ph) =>
      ph.langkah.some((st) => st.no === highlightedStepNo)
    );
    if (targetPhase) {
      setOpenPhases((prev) => ({ ...prev, [targetPhase.fasa_id]: true }));
    }
    const timer = window.setTimeout(() => {
      const el = document.getElementById(`sop-step-${highlightedStepNo}`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
    return () => window.clearTimeout(timer);
  }, [highlightedStepNo, fasaKerja]);

  if (!fasaKerja || fasaKerja.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
        Tiada langkah berstruktur ditemui. Sila rujuk tab <strong>Teks Penuh Asal</strong>.
      </div>
    );
  }

  const allOpen = fasaKerja.every((ph) => openPhases[ph.fasa_id] !== false);
  const toggleAll = () => {
    const nextVal = !allOpen;
    const updated: Record<string, boolean> = {};
    for (const ph of fasaKerja) {
      updated[ph.fasa_id] = nextVal;
    }
    setOpenPhases(updated);
  };

  return (
    <div className="space-y-4">
      {fasaKerja.length > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500">
            {fasaKerja.length} Fasa Pelaksanaan
          </span>
          <button
            type="button"
            onClick={toggleAll}
            className="no-print text-xs font-semibold text-indigo-700 hover:text-indigo-900 hover:underline"
          >
            {allOpen ? "Tutup Semua Fasa" : "Buka Semua Fasa"}
          </button>
        </div>
      )}

      {fasaKerja.map((phase) => {
        const isOpen = openPhases[phase.fasa_id] !== false;
        return (
          <section
            key={phase.fasa_id}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
          >
            <button
              type="button"
              onClick={() =>
                setOpenPhases((prev) => ({ ...prev, [phase.fasa_id]: !isOpen }))
              }
              aria-expanded={isOpen}
              className="flex w-full items-center justify-between gap-3 bg-slate-50/90 px-4 py-3 text-left transition hover:bg-slate-100/80"
            >
              <div className="flex items-center gap-2.5">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 text-indigo-600" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-slate-500" />
                )}
                <h4 className="text-sm font-bold text-slate-900">{phase.tajuk_fasa}</h4>
              </div>
              <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[11px] font-bold text-indigo-700">
                {phase.langkah.length} Langkah
              </span>
            </button>

            {isOpen && (
              <div className="divide-y divide-slate-100 p-4">
                {phase.langkah.map((step, sIdx) => {
                  const isHighlighted = highlightedStepNo === step.no;
                  const cleanRoles = (step.anggota || []).filter(
                    (r) => r && r.length <= 24
                  );
                  return (
                    <div
                      key={`${phase.fasa_id}-${step.no}-${sIdx}`}
                      id={`sop-step-${step.no}`}
                      className={`sop-step-card relative py-3.5 first:pt-1 last:pb-1 transition ${
                        isHighlighted
                          ? "rounded-xl bg-indigo-50/70 px-3 ring-2 ring-indigo-400"
                          : ""
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex flex-col items-center">
                          <span className="inline-flex h-7 min-w-[28px] items-center justify-center rounded-full bg-indigo-600 px-2 text-xs font-bold text-white shadow-sm">
                            {step.no}
                          </span>
                          {sIdx < phase.langkah.length - 1 && (
                            <span className="mt-1.5 h-full min-h-[16px] w-0.5 bg-slate-200" />
                          )}
                        </div>

                        <div className="min-w-0 flex-1 space-y-2">
                          {/* Role badges + SLA + PDF Page */}
                          <div className="flex flex-wrap items-center gap-1.5">
                            {cleanRoles.map((role, rIdx) => (
                              <span
                                key={`${step.no}-role-${rIdx}`}
                                className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-bold ${badgeForRole(
                                  role
                                )}`}
                              >
                                {role}
                              </span>
                            ))}
                            {step.sla && (
                              <span className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                                <Clock className="h-3 w-3" />
                                {step.sla}
                              </span>
                            )}
                            {step.muka_surat_pdf && (
                              <span className="ml-auto text-[11px] font-medium text-slate-400">
                                m/s PDF {step.muka_surat_pdf}
                              </span>
                            )}
                          </div>

                          {/* Tindakan bullets / paragraphs */}
                          {step.tindakan.length <= 1 ? (
                            <p className="text-sm leading-relaxed text-slate-800">
                              {step.tindakan[0] || step.tajuk}
                            </p>
                          ) : (
                            <ul className="list-disc space-y-1 pl-4 text-sm leading-relaxed text-slate-800">
                              {step.tindakan.map((act, aIdx) => (
                                <li key={`${step.no}-act-${aIdx}`}>{act}</li>
                              ))}
                            </ul>
                          )}

                          {/* Decision branch note */}
                          {step.keputusan && (
                            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2 text-xs text-amber-950">
                              <GitBranch className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700" />
                              <div>
                                <span className="font-bold">Cabang Keputusan: </span>
                                {step.keputusan}
                              </div>
                            </div>
                          )}

                          {/* Inline [NOTA PINDAAN] override */}
                          {step.amaran_pindaan && (
                            <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-900">
                              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-600" />
                              <span>{step.amaran_pindaan}</span>
                            </div>
                          )}

                          {/* References, Lampiran pills, Cross-SOP pills */}
                          {(step.rujukan_lampiran.length > 0 ||
                            step.rujukan_sop.length > 0 ||
                            step.rujukan.length > 0) && (
                            <div className="flex flex-wrap items-center gap-1.5 pt-1">
                              {step.rujukan_lampiran.map((lamp) => (
                                <button
                                  key={`${step.no}-lp-${lamp}`}
                                  type="button"
                                  onClick={() => onJumpToLampiran?.(lamp)}
                                  className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 hover:bg-emerald-100"
                                >
                                  <FileText className="h-3 w-3" />
                                  {lamp}
                                </button>
                              ))}
                              {step.rujukan_sop.map((sopCode) => (
                                <button
                                  key={`${step.no}-sop-${sopCode}`}
                                  type="button"
                                  onClick={() => onOpenSop?.(sopCode)}
                                  className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  {sopCode}
                                </button>
                              ))}
                              {step.rujukan
                                .filter((r) => r && r.length <= 120)
                                .slice(0, 3)
                                .map((ref, rfIdx) => (
                                  <span
                                    key={`${step.no}-ref-${rfIdx}`}
                                    className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600"
                                  >
                                    <BookOpen className="h-3 w-3 text-slate-400" />
                                    {ref}
                                  </span>
                                ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
