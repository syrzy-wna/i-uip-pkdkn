"use client";

import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckSquare,
  Clock,
  Copy,
  ExternalLink,
  FileText,
  GitBranch,
  Info,
  ListChecks,
  MessageSquare,
  Printer,
  Scale,
  ShieldAlert,
  Users,
} from "lucide-react";
import type { ActiveSopDetail } from "@/lib/types";
import { copyTextSafe } from "@/lib/uiHelpers";
import RichLegalText from "@/components/RichLegalText";
import SopStepTimeline from "./SopStepTimeline";
import SopFlowchart from "./SopFlowchart";
import SopFieldChecklist from "./SopFieldChecklist";

interface SopInteractiveViewerProps {
  detail: ActiveSopDetail;
  onOpenSop?: (sopCode: string) => void;
  onAskExpertWithSop?: (promptText: string) => void;
}

type ViewerTab = "langkah" | "carta" | "semak" | "borang" | "teks";

export default function SopInteractiveViewer({
  detail,
  onOpenSop,
  onAskExpertWithSop,
}: SopInteractiveViewerProps) {
  const [activeTab, setActiveTab] = useState<ViewerTab>("langkah");
  const [highlightedStep, setHighlightedStep] = useState<string | null>(null);
  const [highlightedLampiran, setHighlightedLampiran] = useState<string | null>(null);
  const [showRawMd, setShowRawMd] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);

  const structured = detail.structured;

  useEffect(() => {
    setActiveTab("langkah");
    setHighlightedStep(null);
    setHighlightedLampiran(null);
    setShowRawMd(false);
  }, [detail.file_stem]);

  const totalSteps = (structured?.fasa_kerja || []).reduce(
    (sum, ph) => sum + (ph.langkah?.length || 0),
    0
  );
  const totalLampiran = (structured?.lampiran || []).length || (detail.borang_lampiran || []).length;
  const totalChecklist = (structured?.senarai_semak || []).length;
  const notaPindaan = structured?.nota_pindaan || [];
  const tempohSla = structured?.tempoh_sla || [];
  const anggota = (structured?.anggota_terlibat || []).filter(
    (a) => a.kod && a.kod.length <= 16
  );

  const handleJumpToStep = (stepNo: string) => {
    setActiveTab("langkah");
    setHighlightedStep(stepNo);
  };

  const handleJumpToLampiran = (lampiranKod: string) => {
    setActiveTab("borang");
    setHighlightedLampiran(lampiranKod.toLowerCase());
  };

  const handleCopySummary = async () => {
    const lines = [
      `${detail.sop_id} — ${detail.tajuk}`,
      `Akta: ${detail.akta} | Kuat Kuasa: ${detail.tarikh_kuat_kuasa || "2024"}`,
      "",
      `Tujuan: ${structured?.tujuan || detail.ringkasan}`,
      ...(notaPindaan.length > 0
        ? ["", "NOTA PINDAAN:", ...notaPindaan.map((n) => `- ${n.tajuk}: ${n.butiran}`)]
        : []),
      ...(tempohSla.length > 0
        ? ["", "TEMPOH SLA:", ...tempohSla.map((t) => `- ${t.label}: ${t.tempoh}`)]
        : []),
    ];
    const ok = await copyTextSafe(lines.join("\n"));
    if (ok) {
      setCopiedSummary(true);
      window.setTimeout(() => setCopiedSummary(false), 2000);
    }
  };

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  const tabs: Array<{ id: ViewerTab; label: string; badge?: number; icon: React.ReactNode }> = [
    {
      id: "langkah",
      label: "Ringkasan & Langkah",
      badge: totalSteps || undefined,
      icon: <ListChecks className="h-3.5 w-3.5" />,
    },
    {
      id: "carta",
      label: "Carta Alir",
      icon: <GitBranch className="h-3.5 w-3.5" />,
    },
    {
      id: "semak",
      label: "Senarai Semak",
      badge: totalChecklist || undefined,
      icon: <CheckSquare className="h-3.5 w-3.5" />,
    },
    {
      id: "borang",
      label: "Borang & Singkatan",
      badge: totalLampiran || undefined,
      icon: <FileText className="h-3.5 w-3.5" />,
    },
    {
      id: "teks",
      label: "Teks Penuh Asal",
      icon: <BookOpen className="h-3.5 w-3.5" />,
    },
  ];

  return (
    <div className="sop-print-area space-y-4">
      {/* Header Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="inline-flex items-center rounded-md bg-indigo-600 px-2.5 py-0.5 font-mono text-xs font-bold text-white">
                {detail.sop_id}
              </span>
              <span className="inline-flex items-center rounded-md border border-slate-200 bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                {detail.akta}
              </span>
              {detail.tarikh_kuat_kuasa && (
                <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
                  Kuat Kuasa: {detail.tarikh_kuat_kuasa}
                </span>
              )}
              {detail.muka_surat_pdf && (
                <span className="inline-flex items-center rounded-md bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500 ring-1 ring-slate-200">
                  PDF m/s {detail.muka_surat_pdf}
                </span>
              )}
            </div>

            <h3 className="text-base font-bold leading-snug text-slate-900 sm:text-lg">
              {detail.tajuk}
            </h3>

            {(structured?.tujuan || detail.ringkasan) && (
              <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
                {structured?.tujuan || detail.ringkasan}
              </p>
            )}
          </div>

          <div className="no-print flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={handleCopySummary}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              {copiedSummary ? (
                <Check className="h-3.5 w-3.5 text-emerald-600" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
              {copiedSummary ? "Disalin" : "Salin"}
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <Printer className="h-3.5 w-3.5" />
              Cetak
            </button>
            {onAskExpertWithSop && (
              <button
                type="button"
                onClick={() =>
                  onAskExpertWithSop(
                    `Terangkan langkah pelaksanaan lapangan, punca kuasa dan borang wajib bagi ${detail.sop_id} (${detail.tajuk}).`
                  )
                }
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                Tanya Pakar
              </button>
            )}
          </div>
        </div>

        {/* Pinned [NOTA PINDAAN] & Konflik Kod Alerts */}
        {(notaPindaan.length > 0 || detail.amaran_konflik_kod) && (
          <div className="mt-4 space-y-2">
            {notaPindaan.map((np, idx) => {
              const isCrit = np.tahap === "KRITIKAL";
              const isWarn = np.tahap === "AMARAN";
              return (
                <div
                  key={`np-${idx}`}
                  className={`rounded-xl border px-3.5 py-2.5 text-xs leading-relaxed ${
                    isCrit
                      ? "border-rose-300 bg-rose-50 text-rose-950"
                      : isWarn
                      ? "border-amber-300 bg-amber-50 text-amber-950"
                      : "border-sky-200 bg-sky-50 text-sky-950"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {isCrit ? (
                      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                    ) : isWarn ? (
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    ) : (
                      <Info className="mt-0.5 h-4 w-4 shrink-0 text-sky-600" />
                    )}
                    <div className="space-y-0.5">
                      <div className="font-bold">{np.tajuk}</div>
                      <p>{np.butiran}</p>
                      {np.gantian_statut && (
                        <div className="pt-0.5 text-[11px] font-semibold opacity-90">
                          Rujukan Statut Mengatasi: {np.gantian_statut}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {detail.amaran_konflik_kod && (
              <div className="flex items-start gap-2 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-2 text-xs text-sky-900">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-sky-600" />
                <span>{detail.amaran_konflik_kod}</span>
              </div>
            )}
          </div>
        )}

        {/* At-a-Glance Strip: Punca Kuasa, SLA, Anggota */}
        {(structured?.punca_kuasa?.length || tempohSla.length > 0 || anggota.length > 0) ? (
          <div className="mt-4 grid gap-2.5 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                <Scale className="h-3.5 w-3.5 text-indigo-600" />
                Punca Kuasa Utama
              </div>
              <div className="space-y-1 text-xs text-slate-800">
                {(structured?.punca_kuasa || detail.seksyen_kunci || [])
                  .slice(0, 3)
                  .map((pk, idx) => (
                    <div key={`pk-${idx}`} className="font-medium leading-snug">
                      • {pk}
                    </div>
                  ))}
                {!(structured?.punca_kuasa?.length || detail.seksyen_kunci?.length) && (
                  <span className="text-slate-500">{detail.akta}</span>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                <Clock className="h-3.5 w-3.5 text-amber-600" />
                Tempoh / SLA Penting
              </div>
              <div className="space-y-1 text-xs text-slate-800">
                {tempohSla.length > 0 ? (
                  tempohSla.slice(0, 3).map((t, idx) => (
                    <div key={`sla-${idx}`} className="leading-snug">
                      <span className="font-bold text-amber-900">{t.tempoh}</span>{" "}
                      <span className="text-slate-600">— {t.label}</span>
                    </div>
                  ))
                ) : (
                  <span className="text-slate-500">Tiada had tempoh statutori khusus dinyatakan.</span>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                <Users className="h-3.5 w-3.5 text-emerald-600" />
                Anggota Terlibat
              </div>
              <div className="flex flex-wrap gap-1">
                {anggota.length > 0 ? (
                  anggota.slice(0, 8).map((a) => (
                    <span
                      key={a.kod}
                      title={a.jawatan}
                      className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-700"
                    >
                      {a.kod}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-500">Pegawai Diberi Kuasa (PDK / PPKP)</span>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* 5-Tab Bar */}
      <div
        role="tablist"
        aria-label="Paparan Kandungan SOP"
        className="no-print flex gap-1.5 overflow-x-auto rounded-xl border border-slate-200 bg-slate-100/80 p-1.5 no-scrollbar"
      >
        {tabs.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                active
                  ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200"
                  : "text-slate-600 hover:bg-white/60 hover:text-slate-900"
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`rounded-full px-1.5 py-0.2 text-[10px] font-bold ${
                    active ? "bg-indigo-100 text-indigo-800" : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div role="tabpanel" className="min-h-[260px]">
        {activeTab === "langkah" && (
          <div className="space-y-4">
            {structured ? (
              <>
                <SopStepTimeline
                  fasaKerja={structured.fasa_kerja || []}
                  highlightedStepNo={highlightedStep}
                  onJumpToLampiran={handleJumpToLampiran}
                  onOpenSop={onOpenSop}
                />

                {(structured.undang_undang_berkaitan || []).length > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                    <h4 className="mb-2.5 text-xs font-bold uppercase tracking-wide text-slate-600">
                      Undang-Undang &amp; Peraturan Berkaitan
                    </h4>
                    <div className="space-y-2">
                      {structured.undang_undang_berkaitan.map((uu, idx) => (
                        <div
                          key={`uu-${idx}`}
                          className={`flex flex-wrap items-start justify-between gap-2 rounded-lg border px-3 py-2 text-xs ${
                            uu.status === "DIMANSUHKAN"
                              ? "border-rose-200 bg-rose-50/70 text-rose-900"
                              : "border-slate-200 bg-slate-50/70 text-slate-800"
                          }`}
                        >
                          <div className="min-w-0 flex-1">
                            <span className={uu.status === "DIMANSUHKAN" ? "line-through" : "font-medium"}>
                              {uu.akta}
                            </span>
                            {uu.nota && (
                              <p className="mt-0.5 text-[11px] font-semibold text-rose-700">
                                {uu.nota}
                              </p>
                            )}
                          </div>
                          <span
                            className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                              uu.status === "DIMANSUHKAN"
                                ? "bg-rose-200 text-rose-900"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {uu.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(structured.nota_audit_kualiti || []).length > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                    <span className="font-bold text-slate-700">Nota Audit Kualiti SOP: </span>
                    {structured.nota_audit_kualiti.join(" ")}
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <RichLegalText
                  text={detail.cleaned_markdown || detail.markdown_content}
                  onOpenSop={onOpenSop}
                />
              </div>
            )}
          </div>
        )}

        {activeTab === "carta" && (
          <SopFlowchart
            cartaAlir={structured?.carta_alir || { nodes: [], edges: [] }}
            onSelectStep={handleJumpToStep}
            onOpenSop={onOpenSop}
          />
        )}

        {activeTab === "semak" && (
          <SopFieldChecklist
            fileStem={detail.file_stem}
            sopId={detail.sop_id}
            items={structured?.senarai_semak || []}
          />
        )}

        {activeTab === "borang" && (
          <div className="space-y-4">
            {/* Borang & Lampiran */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h4 className="mb-3 text-sm font-bold text-slate-900">
                Senarai Borang &amp; Lampiran ({totalLampiran})
              </h4>
              {structured?.lampiran && structured.lampiran.length > 0 ? (
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {structured.lampiran.map((lp, idx) => {
                    const isMatch =
                      highlightedLampiran &&
                      lp.kod.toLowerCase().includes(highlightedLampiran);
                    const isRepealed = lp.status === "DIMANSUHKAN";
                    return (
                      <div
                        key={`lp-${idx}`}
                        className={`rounded-xl border p-3 text-xs transition ${
                          isRepealed
                            ? "border-rose-200 bg-rose-50/70"
                            : isMatch
                            ? "border-emerald-400 bg-emerald-50 ring-2 ring-emerald-300"
                            : "border-slate-200 bg-slate-50/60"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs font-bold text-indigo-800">
                            {lp.kod}
                          </span>
                          <div className="flex items-center gap-1">
                            {lp.status_ekstrak === "imej_raster_borang" && (
                              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900">
                                Templat Imej
                              </span>
                            )}
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                isRepealed
                                  ? "bg-rose-200 text-rose-900"
                                  : "bg-emerald-100 text-emerald-800"
                              }`}
                            >
                              {lp.status}
                            </span>
                          </div>
                        </div>
                        <p className="mt-1 font-medium text-slate-800">{lp.tajuk}</p>
                        {lp.nota && (
                          <p className="mt-1 text-[11px] font-semibold text-rose-700">
                            {lp.nota}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (detail.borang_lampiran || []).length > 0 ? (
                <ul className="space-y-1.5 text-xs text-slate-700">
                  {detail.borang_lampiran.map((b, idx) => (
                    <li
                      key={`bl-${idx}`}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
                    >
                      {b}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">
                  Tiada borang atau lampiran khusus disenaraikan dalam SOP ini.
                </p>
              )}
            </div>

            {/* Rujukan Silang SOP */}
            {(structured?.rujukan_silang_resolved || []).length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h4 className="mb-2.5 text-sm font-bold text-slate-900">
                  SOP Rujukan Silang Berkaitan
                </h4>
                <div className="flex flex-wrap gap-2">
                  {structured!.rujukan_silang_resolved.map((rs) => (
                    <button
                      key={rs.file_stem}
                      type="button"
                      onClick={() => onOpenSop?.(rs.file_stem)}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2 text-left text-xs font-semibold text-indigo-800 transition hover:bg-indigo-100"
                    >
                      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                      <span>
                        <span className="font-mono font-bold">{rs.file_stem}</span> — {rs.tajuk}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Glosari Singkatan */}
            {(structured?.singkatan || []).length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h4 className="mb-3 text-sm font-bold text-slate-900">
                  Glosari Singkatan Rasmi ({structured!.singkatan.length})
                </h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-xs">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="w-32 px-3 py-2 text-left font-bold text-slate-700">
                          Singkatan
                        </th>
                        <th className="px-3 py-2 text-left font-bold text-slate-700">
                          Maksud Rasmi
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {structured!.singkatan.map((sg) => (
                        <tr key={sg.kod} className="hover:bg-slate-50/70">
                          <td className="px-3 py-2 font-mono font-bold text-indigo-800">
                            {sg.kod}
                          </td>
                          <td className="px-3 py-2 text-slate-700">{sg.maksud}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "teks" && (
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="no-print mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Teks penuh diekstrak daripada dokumen PDF rasmi KKM
              </span>
              <button
                type="button"
                onClick={() => setShowRawMd((prev) => !prev)}
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                {showRawMd ? "Paparan Terformat" : "Paparan Markdown Mentah"}
              </button>
            </div>
            {showRawMd ? (
              <pre className="max-h-[65vh] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 font-mono text-xs leading-relaxed text-slate-700">
                {detail.cleaned_markdown || detail.markdown_content}
              </pre>
            ) : (
              <div className="max-h-[68vh] overflow-y-auto pr-1">
                <RichLegalText
                  text={detail.cleaned_markdown || detail.markdown_content}
                  onOpenSop={onOpenSop}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
