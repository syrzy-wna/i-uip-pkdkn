"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRightCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  ClipboardList,
  Clock,
  Copy,
  Database,
  Gavel,
  History,
  Loader2,
  MessageSquareQuote,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import LegalDirectoryPanel, { type CompoundPrefillMeta } from "@/components/LegalDirectoryPanel";
import {
  consultUipAdvisor,
  fetchAdvisorAnsweredQuestions,
  fetchAdvisorScenarios,
} from "@/lib/api";
import {
  CORE_ACT_CODES,
  CORE_KKM_ACTS,
  SECONDARY_ACT_CODES,
  SUPPORT_LEGAL_ACTS,
  getActBadgeStyle,
  isCompoundableKkmAct,
  isPdrmReferralAct,
} from "@/lib/actMeta";
import { validateLegalOutput } from "@/lib/legalValidator";
import { copyTextSafe, extractRecommendedCompoundRm } from "@/lib/uiHelpers";
import type {
  AdvisorAnsweredItem,
  AdvisorAnsweredListResponse,
  AdvisorConsultResult,
  AdvisorScenarioItem,
  LegalValidationResult,
  OfficerProfile,
} from "@/lib/types";

export type PakarWorkspaceTab = "ask" | "directory" | "history";

interface UIPAdvisorPanelProps {
  aktaUtama: string;
  authToken: string | null;
  officer: OfficerProfile | null;
  isDevAdmin?: boolean;
  initialQuestion?: string | null;
  initialQuestionNonce?: number;
  onInitialQuestionConsumed?: () => void;
  initialWorkspaceTab?: PakarWorkspaceTab;
  workspaceTabNonce?: number;
  onApplyToCaseBuilder: (
    draftText: string,
    aktaDisyorkan: string,
    bukaIp: boolean,
    compoundMeta?: CompoundPrefillMeta
  ) => void;
}

type AdvisorResultTab = "evidence" | "charges" | "statutes";

const QUICK_CHIPS = [
  "Pelajar hisap vape dalam tandas sekolah",
  "Pelajar bawa vape dalam beg sekolah",
  "Restoran kotor & pekerja tiada tifoid",
  "Kedai pamer vape terbuka di kaunter",
  "Pemilik kedai vape halang & ugut PPKP (Akta 574)",
  "Kiraan 10 hari bersih sijil juruanalisis (Akta 388)",
];

function formatShortTimestamp(raw: string): string {
  const clean = (raw || "").trim();
  if (!clean) return "";
  const m = clean.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2})/);
  if (!m) return clean;
  const months = [
    "Jan",
    "Feb",
    "Mac",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Ogs",
    "Sep",
    "Okt",
    "Nov",
    "Dis",
  ];
  const monthIdx = Number(m[2]) - 1;
  const mon = months[monthIdx] || m[2];
  return `${Number(m[3])} ${mon}, ${m[4]}`;
}

export default function UIPAdvisorPanel({
  authToken,
  officer,
  isDevAdmin = false,
  initialQuestion = null,
  initialQuestionNonce = 0,
  onInitialQuestionConsumed,
  initialWorkspaceTab = "ask",
  workspaceTabNonce = 0,
  onApplyToCaseBuilder,
}: UIPAdvisorPanelProps) {
  const [workspaceTab, setWorkspaceTab] = useState<PakarWorkspaceTab>(initialWorkspaceTab);
  const [question, setQuestion] = useState("");
  const [aktaFilter, setAktaFilter] = useState<string>("Semua");
  const [scenarios, setScenarios] = useState<AdvisorScenarioItem[]>([]);
  const [scenariosError, setScenariosError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [deepLoading, setDeepLoading] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdvisorConsultResult | null>(null);
  const [checkedSop, setCheckedSop] = useState<Record<number, boolean>>({});
  const [showLibrary, setShowLibrary] = useState(false);
  const [resultTab, setResultTab] = useState<AdvisorResultTab>("evidence");
  const [showNoOffenceStatutes, setShowNoOffenceStatutes] = useState(false);
  const [answeredData, setAnsweredData] = useState<AdvisorAnsweredListResponse | null>(null);
  const [answeredLoading, setAnsweredLoading] = useState(false);
  const [answeredError, setAnsweredError] = useState<string | null>(null);
  const [answeredActFilter, setAnsweredActFilter] = useState<string>("Semua");
  const [answeredSearch, setAnsweredSearch] = useState("");
  const [selectedAnsweredId, setSelectedAnsweredId] = useState<string | null>(null);
  const [expandedActGroups, setExpandedActGroups] = useState<Record<string, boolean>>({});
  const [lastSubmittedQuestion, setLastSubmittedQuestion] = useState<string>("");
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; content: string }>
  >([]);
  const resultRef = useRef<HTMLDivElement | null>(null);
  const answeredSectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setWorkspaceTab(initialWorkspaceTab);
  }, [initialWorkspaceTab, workspaceTabNonce]);

  const loadScenarios = useCallback(async () => {
    setScenariosError(null);
    try {
      const list = await fetchAdvisorScenarios();
      setScenarios(list);
    } catch {
      setScenarios([]);
      setScenariosError("Senarai contoh situasi gagal dimuatkan buat masa ini.");
    }
  }, []);

  useEffect(() => {
    void loadScenarios();
  }, [loadScenarios]);

  const loadAnsweredQuestions = useCallback(async () => {
    setAnsweredLoading(true);
    setAnsweredError(null);
    try {
      const data = await fetchAdvisorAnsweredQuestions({ authToken, limit: 150 });
      setAnsweredData(data);
    } catch {
      setAnsweredError("Senarai soalan terdahulu gagal dimuatkan. Sila cuba semula.");
    } finally {
      setAnsweredLoading(false);
    }
  }, [authToken]);

  useEffect(() => {
    void loadAnsweredQuestions();
  }, [loadAnsweredQuestions]);

  const handleResetConversation = () => {
    setQuestion("");
    setLastSubmittedQuestion("");
    setConversationHistory([]);
    setResult(null);
    setError(null);
    setSelectedAnsweredId(null);
    setCheckedSop({});
    setShowNoOffenceStatutes(false);
  };

  const handleConsult = async (
    customQuestion?: string,
    scenarioId?: string,
    forceAi = false,
    resetThread = false
  ) => {
    const q = (customQuestion ?? question).trim();
    if (!q && !scenarioId) {
      setError("Sila taip situasi yang ditemui atau pilih daripada Contoh Situasi.");
      return;
    }
    if (forceAi) {
      setDeepLoading(true);
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 40);
    } else {
      setLoading(true);
    }
    setError(null);
    setCopiedSummary(false);
    setWorkspaceTab("ask");

    const effectiveQ = q || "Rujuk contoh situasi ini";
    const historyToSend = resetThread || scenarioId ? [] : conversationHistory.slice(-6);

    try {
      const res = await consultUipAdvisor({
        question: effectiveQ,
        aktaHint: aktaFilter,
        scenarioId,
        useAi: forceAi,
        authToken,
        officerProfile: officer,
        conversationHistory: historyToSend,
      });
      setResult(res);
      setLastSubmittedQuestion(effectiveQ);
      const assistantSummary = `${res.akta_disyorkan} — ${res.tajuk_nasihat}: ${
        res.ringkasan_keputusan || res.keputusan_tindakan
      }`;
      setConversationHistory((prev) => {
        const base = resetThread || scenarioId ? [] : prev.slice(-4);
        return [
          ...base,
          { role: "user", content: effectiveQ },
          { role: "assistant", content: assistantSummary },
        ];
      });
      setCheckedSop({});
      setResultTab("evidence");
      setShowNoOffenceStatutes(false);
      setShowLibrary(false);
      setSelectedAnsweredId(res.matched_collection_id || null);
      void loadAnsweredQuestions();
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 90);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mendapatkan nasihat pakar UIP.");
    } finally {
      setLoading(false);
      setDeepLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuestionNonce > 0 && initialQuestion && initialQuestion.trim()) {
      const qClean = initialQuestion.trim();
      setQuestion(qClean);
      setWorkspaceTab("ask");
      onInitialQuestionConsumed?.();
      void handleConsult(qClean, undefined, false, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestionNonce]);

  const handleSelectAnsweredItem = (item: AdvisorAnsweredItem) => {
    setQuestion(item.question);
    setLastSubmittedQuestion(item.question);
    setSelectedAnsweredId(item.id);
    setError(null);
    setCopiedSummary(false);
    setShowLibrary(false);
    setShowNoOffenceStatutes(false);
    setWorkspaceTab("ask");
    if (item.answer) {
      setResult(item.answer);
      setConversationHistory([
        { role: "user", content: item.question },
        {
          role: "assistant",
          content: `${item.answer.akta_disyorkan} — ${item.answer.tajuk_nasihat}: ${
            item.answer.ringkasan_keputusan || item.answer.keputusan_tindakan
          }`,
        },
      ]);
      setCheckedSop({});
      setResultTab("evidence");
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 90);
      return;
    }
    void handleConsult(item.question, undefined, false, true);
  };

  const handleCopySummary = async () => {
    if (!result) return;
    const isNoOff =
      result.status_kesalahan === "TIADA_KESALAHAN" ||
      (!result.status_kesalahan &&
        (result.keputusan_tindakan.toUpperCase().includes("TIADA KESALAHAN") ||
          result.keputusan_tindakan.toUpperCase().includes("BUKAN KESALAHAN")));

    const sopSummaryLine =
      result.sop_references && result.sop_references.length > 0
        ? `RUJUKAN SOP KKM 2024:\n${result.sop_references
            .map(
              (s) =>
                `- ${s.sop_id}: ${s.tajuk}${s.muka_surat_pdf ? ` (PDF m.s. ${s.muka_surat_pdf})` : ""}`
            )
            .join("\n")}`
        : "";

    if (isNoOff) {
      const steps =
        result.langkah_susulan_ppkp && result.langkah_susulan_ppkp.length > 0
          ? result.langkah_susulan_ppkp
          : result.sop_lapangan;
      const text = [
        `${result.tajuk_nasihat} (${result.akta_disyorkan})`,
        `KEPUTUSAN: ${result.ringkasan_keputusan || result.keputusan_tindakan}`,
        `SEBAB TIDAK MENYALAHI UNDANG-UNDANG:\n${result.sebab_tidak_menyalahi || result.alasan_keputusan}`,
        result.nota_pindaan ? `${result.nota_pindaan}` : "",
        steps.length
          ? `LANGKAH SUSULAN PPKP:\n${steps.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
          : "",
        sopSummaryLine,
      ]
        .filter(Boolean)
        .join("\n\n");
      const ok = await copyTextSafe(text);
      if (ok) {
        setCopiedSummary(true);
        setTimeout(() => setCopiedSummary(false), 2000);
      }
      return;
    }

    const primary = result.cadangan_pertuduhan[0];
    const punca = result.punca_kuasa;
    const text = [
      `RUJUKAN UIP KKM: ${result.tajuk_nasihat} (${result.akta_disyorkan})`,
      `SEKSYEN KESALAHAN: ${punca?.seksyen_kesalahan || primary?.seksyen_kesalahan || result.akta_disyorkan}`,
      `HUKUMAN: ${punca?.seksyen_hukuman || primary?.seksyen_hukuman || "-"} (${punca?.had_hukuman || primary?.hukuman_maksimum || "-"})`,
      `CADANGAN TINDAKAN: ${result.ringkasan_keputusan || result.keputusan_tindakan}`,
      result.nota_pindaan ? `${result.nota_pindaan}` : "",
      `LANGKAH DI LOKASI:\n${result.sop_lapangan.map((s, i) => `${i + 1}. ${s}`).join("\n")}`,
      sopSummaryLine,
      `BARANG BUKTI WAJIB:\n${result.eksibit_wajib.map((e) => `- ${e}`).join("\n")}`,
    ]
      .filter(Boolean)
      .join("\n\n");
    const ok = await copyTextSafe(text);
    if (ok) {
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2000);
    }
  };

  const filteredScenarios =
    aktaFilter === "Semua"
      ? scenarios
      : scenarios.filter((s) => s.akta_utama === aktaFilter);

  const visibleActFilterCodes = useMemo(() => {
    const counts = answeredData?.act_counts || {};
    const extra = SECONDARY_ACT_CODES.filter((code) => (counts[code] || 0) > 0);
    return [...CORE_ACT_CODES, ...extra];
  }, [answeredData]);

  const filteredAnsweredGroups = useMemo(() => {
    const groups = answeredData?.groups || [];
    const qLow = answeredSearch.trim().toLowerCase();
    return groups
      .filter(
        (grp) => answeredActFilter === "Semua" || grp.akta_code === answeredActFilter
      )
      .map((grp) => {
        if (!qLow) return grp;
        const matchedItems = grp.items.filter((item) => {
          const hay = [
            item.question,
            item.tajuk_nasihat,
            item.keputusan_tindakan,
            item.seksyen_utama,
            item.akta_group,
            item.akta_disyorkan,
          ]
            .join(" ")
            .toLowerCase();
          return hay.includes(qLow);
        });
        return { ...grp, count: matchedItems.length, items: matchedItems };
      })
      .filter((grp) => grp.items.length > 0);
  }, [answeredData, answeredActFilter, answeredSearch]);

  const activeActsCount = useMemo(() => {
    const counts = answeredData?.act_counts || {};
    return Object.values(counts).filter((c) => c > 0).length;
  }, [answeredData]);

  const primaryCharge = result?.cadangan_pertuduhan?.[0];

  // Utamakan keputusan validasi rasmi backend (2,334 seksyen verbatim AGC + 22 SOP KKM 2024)
  // dan kunci terhadap lastSubmittedQuestion supaya menaip soalan baharu tidak memicu amaran palsu!
  const activeValidation: LegalValidationResult | null = useMemo(() => {
    if (!result) return null;
    if (result.legal_validation && typeof result.legal_validation === "object") {
      return result.legal_validation;
    }
    return validateLegalOutput(result, null, lastSubmittedQuestion);
  }, [result, lastSubmittedQuestion]);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      {/* BAR 3 TAB BERSIH: GABUNGAN TANYA SITUASI + SENARAI KESALAHAN & AKTA + SOALAN TERDAHULU */}
      <div className="flex gap-1.5 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm no-scrollbar">
        {[
          {
            id: "ask" as PakarWorkspaceTab,
            label: "Tanya Situasi",
            shortLabel: "Tanya Situasi",
            icon: MessageSquareQuote,
          },
          {
            id: "directory" as PakarWorkspaceTab,
            label: "Senarai Kesalahan & Teks Akta",
            shortLabel: "Rujukan Akta",
            icon: Database,
          },
          {
            id: "history" as PakarWorkspaceTab,
            label: `Soalan Terdahulu (${answeredData?.total_questions ?? 0})`,
            shortLabel: `Terdahulu (${answeredData?.total_questions ?? 0})`,
            icon: History,
          },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = workspaceTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setWorkspaceTab(tab.id)}
              className={`inline-flex min-h-[44px] shrink-0 flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-extrabold transition sm:gap-2 sm:px-4 ${
                active
                  ? "bg-[#0f2744] text-white shadow-sm"
                  : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="hidden whitespace-nowrap sm:inline">{tab.label}</span>
              <span className="whitespace-nowrap sm:hidden">{tab.shortLabel}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 2: SENARAI KESALAHAN & TEKS PENUH AKTA */}
      {workspaceTab === "directory" && (
        <LegalDirectoryPanel
          authToken={authToken}
          officer={officer}
          isDevAdmin={isDevAdmin}
          onApplyOffenceToCase={onApplyToCaseBuilder}
        />
      )}

      {/* TAB 1: TANYA SITUASI DI LOKASI */}
      {workspaceTab === "ask" && (
        <>
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-extrabold text-slate-900">
              Kurang pasti seksyen atau tindakan di lokasi?
            </h2>
            <p className="mt-0.5 text-xs text-slate-600 sm:text-sm">
              Taip sahaja apa yang anda temui untuk menyemak seksyen yang tepat, sama ada kompaun atau buka Fail IP, serta langkah SOP.
            </p>
          </div>

          <select
            aria-label="Tapis Akta KKM"
            value={aktaFilter}
            onChange={(e) => setAktaFilter(e.target.value)}
            className="min-h-[44px] w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-800 sm:w-auto sm:text-sm"
          >
            <option value="Semua">Semua Akta (KKM + Rujukan Silang)</option>
            <optgroup label="Akta Teras KKM">
              {CORE_KKM_ACTS.map((act) => (
                <option key={act.value} value={act.value}>
                  {act.shortLabel}
                </option>
              ))}
            </optgroup>
            <optgroup label="Akta Prosedur, Jenayah & Rujukan Silang">
              {SUPPORT_LEGAL_ACTS.map((act) => (
                <option key={act.value} value={act.value}>
                  {act.shortLabel}
                </option>
              ))}
            </optgroup>
          </select>
        </div>

        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200/80 bg-slate-50/70 px-3 py-2 text-[11px] text-slate-600">
            <span>
              <strong className="text-[#0f2744]">Panduan soalan tepat:</strong> Nyatakan{" "}
              <span className="font-semibold text-slate-800">Siapa pelaku</span> +{" "}
              <span className="font-semibold text-slate-800">Perbuatan/Peninggalan</span> +{" "}
              <span className="font-semibold text-slate-800">Lokasi/Premis</span> +{" "}
              <span className="font-semibold text-slate-800">Alasan/Bukti</span>.
            </span>
            {conversationHistory.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[10px] font-bold text-indigo-900">
                Konteks Susulan Aktif ({Math.ceil(conversationHistory.length / 2)} pusingan)
              </span>
            )}
          </div>

          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                handleConsult();
              }
            }}
            placeholder="Contoh: Ada pelajar hisap vape di tandas sekolah, pemilik kedai halang PPKP (Akta 574), atau kiraan 10 hari bersih (Akta 388)..."
            className="w-full rounded-xl border border-slate-300 bg-slate-50/40 p-3.5 text-base leading-relaxed text-slate-900 transition focus:border-[#0f2744] focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-200 sm:text-sm"
          />

          {/* Cip Pantas Pendek (Dilipat automatik sebaik jawapan muncul supaya skrin tenang) */}
          {!result && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Contoh pantas:</span>
              {QUICK_CHIPS.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => {
                    setQuestion(chip);
                    handleConsult(chip, undefined, false, true);
                  }}
                  className="min-h-[44px] rounded-full border border-slate-200 bg-slate-50 px-3.5 py-2 text-xs font-semibold text-slate-700 transition hover:border-[#0f2744] hover:bg-slate-100 hover:text-slate-900 sm:min-h-[38px] sm:py-1.5"
                >
                  {chip}
                </button>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-2 pt-1 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setShowLibrary((v) => !v)}
                className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                <BookOpen className="h-4 w-4 text-[#0f2744]" />
                <span>Contoh Situasi ({filteredScenarios.length})</span>
                {showLibrary ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {(result || question.trim() || conversationHistory.length > 0) && (
                <button
                  type="button"
                  onClick={handleResetConversation}
                  className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                >
                  <X className="h-3.5 w-3.5" />
                  <span>Soalan Baharu</span>
                </button>
              )}
            </div>

            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <button
                type="button"
                disabled={loading || deepLoading}
                onClick={() => handleConsult(undefined, undefined, false)}
                className="inline-flex min-h-[46px] items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-60"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {loading ? "Sedang menyemak..." : "Semak Kes Ini"}
              </button>

              <button
                type="button"
                disabled={loading || deepLoading}
                onClick={() => handleConsult(undefined, undefined, true)}
                className="inline-flex min-h-[46px] items-center justify-center gap-2 rounded-xl border border-[#0f2744]/30 bg-slate-50 px-5 py-2.5 text-sm font-extrabold text-[#0f2744] shadow-sm transition hover:border-[#0f2744] hover:bg-slate-100 disabled:opacity-60"
              >
                {deepLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
                ) : (
                  <Sparkles className="h-4 w-4 text-amber-600" />
                )}
                {deepLoading ? "AI sedang membuat semakan mendalam..." : "Semakan Mendalam dengan AI"}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-800">
              {error}
            </div>
          )}
        </div>

        {/* Contoh Situasi Boleh Lipat */}
        {showLibrary && (
          <div className="mt-4 border-t border-slate-200 pt-4">
            {scenariosError ? (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-900">
                <span>{scenariosError}</span>
                <button
                  type="button"
                  onClick={() => void loadScenarios()}
                  className="inline-flex min-h-[40px] items-center gap-1 rounded-lg border border-rose-300 bg-white px-3 text-xs font-bold text-rose-900 hover:bg-rose-100"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Cuba Semula
                </button>
              </div>
            ) : (
              <>
                <div className="mb-2.5 text-xs font-bold text-slate-700">
                  Pilih satu situasi untuk terus lihat seksyen &amp; SOP:
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredScenarios.map((sc) => {
                    const selected = result?.scenario_id === sc.id;
                    const actStyle = getActBadgeStyle(sc.akta_utama);
                    const scIsComp = !sc.sesuai_buka_ip && isCompoundableKkmAct(sc.akta_utama);
                    const scIsPdrm = isPdrmReferralAct(sc.akta_utama);
                    const actionTag = scIsPdrm
                      ? "Rujuk PDRM / TPR"
                      : sc.sesuai_buka_ip
                        ? "Buka IP / Mahkamah"
                        : scIsComp
                          ? "Kompaun"
                          : "Panduan Akta";
                    const actionColor = scIsPdrm
                      ? "text-red-800"
                      : sc.sesuai_buka_ip
                        ? "text-amber-800"
                        : scIsComp
                          ? "text-emerald-700"
                          : "text-slate-700";
                    return (
                      <button
                        key={sc.id}
                        type="button"
                        onClick={() => {
                          setQuestion(sc.tajuk);
                          handleConsult(sc.tajuk, sc.id);
                        }}
                        className={`flex flex-col items-start rounded-xl border p-3 text-left transition ${
                          selected
                            ? "border-indigo-500 bg-indigo-50/70 ring-1 ring-indigo-500"
                            : "border-slate-200 bg-slate-50/50 hover:border-indigo-300 hover:bg-indigo-50/30"
                        }`}
                      >
                        <div className="flex w-full items-center justify-between gap-2">
                          <span className={`rounded px-2 py-0.5 text-[11px] font-bold ${actStyle.badge}`}>
                            {sc.akta_utama}
                          </span>
                          <span className={`text-[11px] font-bold ${actionColor}`}>
                            {actionTag}
                          </span>
                        </div>
                        <span className="mt-1.5 text-xs font-bold text-slate-900">{sc.tajuk}</span>
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        )}
      </section>

      {/* Penunjuk Jelas Semasa Semakan Berjalan */}
      {(loading || deepLoading) && (
        <div className="flex items-center gap-3 rounded-2xl border border-[#0f2744]/20 bg-white px-4 py-3.5 text-xs text-slate-800 shadow-sm">
          <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[#0f2744]" />
          <div>
            <div className="font-extrabold text-[#0f2744]">
              {deepLoading
                ? "AI sedang membuat semakan mendalam..."
                : "Sedang menyemak seksyen undang-undang & SOP..."}
            </div>
            <p className="mt-0.5 text-slate-600">
              {deepLoading
                ? "AI sedang meneliti teks penuh akta Warta, pengecualian Jadual dan huraian kes anda."
                : "Mencari peruntukan akta yang tepat daripada pustaka undang-undang rasmi."}
            </p>
          </div>
        </div>
      )}

      {/* 2. KEPUTUSAN 2-CABANG YANG TEGAS (TIADA_KESALAHAN vs ADA_KESALAHAN) */}
      {result && (() => {
        const isNoOffence =
          result.status_kesalahan === "TIADA_KESALAHAN" ||
          (!result.status_kesalahan &&
            (result.keputusan_tindakan.toUpperCase().includes("TIADA KESALAHAN") ||
              result.keputusan_tindakan.toUpperCase().includes("BUKAN KESALAHAN")));

        const showValidationAlert = Boolean(activeValidation && !activeValidation.passed);
        const showQaBanner =
          !showValidationAlert &&
          Boolean(result.from_qa_collection && result.matched_collection_question);
        const showFallbackBanner =
          !showValidationAlert &&
          !showQaBanner &&
          Boolean(result.ai_attempted && result.ai_succeeded === false && result.fallback_reason);

        const actCanCompound = isCompoundableKkmAct(result.akta_disyorkan);
        const punca = result.punca_kuasa || {
          akta: result.akta_disyorkan,
          seksyen_kesalahan: primaryCharge?.seksyen_kesalahan || result.akta_disyorkan,
          seksyen_hukuman: primaryCharge?.seksyen_hukuman || "-",
          had_hukuman: primaryCharge?.hukuman_maksimum || "-",
          status_kompaun:
            primaryCharge?.boleh_kompaun ||
            (!actCanCompound
              ? "Tidak Boleh Kompaun (Rujuk PDRM / Panduan Akta)"
              : result.sesuai_buka_ip
                ? "Terus Mahkamah (Buka IP)"
                : "Boleh Kompaun"),
          boleh_kompaun_flag: actCanCompound && !result.sesuai_buka_ip,
          kuasa_penguatkuasaan: "",
          peringatan_akta_611: null,
        };
        const canOfferCompoundCta =
          actCanCompound &&
          !result.sesuai_buka_ip &&
          Boolean(punca.boleh_kompaun_flag);

        const followUpSteps =
          result.langkah_susulan_ppkp && result.langkah_susulan_ppkp.length > 0
            ? result.langkah_susulan_ppkp
            : result.sop_lapangan;

        const cleanEngineLabel = result.from_qa_collection
          ? "Jawapan Soalan Serupa"
          : result.ai_succeeded
            ? isDevAdmin
              ? result.engine_used
              : "Bantuan AI"
            : isDevAdmin
              ? result.engine_used || "Panduan Akta Rasmi"
              : "Panduan Akta Rasmi";

        const rawElementEvals = Array.isArray(result.element_evaluations)
          ? result.element_evaluations
          : [];

        const visibleNoOffenceEvals = rawElementEvals.filter((ev) => {
          const els = Array.isArray(ev.element_evaluations) ? ev.element_evaluations : [];
          const hasUnmet =
            Boolean(ev.action_blocked) ||
            els.some((el) => el.status === "TIDAK TERPENUHI");
          return hasUnmet;
        });

        const activeChargeBlob = [
          punca.seksyen_kesalahan || "",
          ...(result.cadangan_pertuduhan || []).map((c) => c.seksyen_kesalahan || ""),
        ]
          .join(" ")
          .toLowerCase();
        const activeSecNums = new Set(
          (activeChargeBlob.match(/\b\d+[a-z]?(?:\(\d+\))?/gi) || []).map((s) =>
            s.toLowerCase().replace(/\(\d+\)$/, "")
          )
        );
        const visibleOffenceEvals = rawElementEvals.filter((ev) => {
          if (activeSecNums.size === 0) return true;
          const evSec = String(ev.offence_section || "").toLowerCase();
          const evNums = (evSec.match(/\b\d+[a-z]?(?:\(\d+\))?/gi) || []).map((s) =>
            s.toLowerCase().replace(/\(\d+\)$/, "")
          );
          return evNums.length === 0 || evNums.some((n) => activeSecNums.has(n));
        });

        const buildCompoundMeta = (): CompoundPrefillMeta => {
          const sec = punca.seksyen_kesalahan || primaryCharge?.seksyen_kesalahan || "";
          const recomAmt = extractRecommendedCompoundRm(
            `${sec} ${result.akta_disyorkan}`,
            punca.status_kompaun || primaryCharge?.boleh_kompaun || ""
          );
          const kuasa =
            result.akta_disyorkan === "Akta 852"
              ? "Seksyen 48 Akta 852 [P.U. (A) 259/2024]"
              : result.akta_disyorkan === "Akta 281"
                ? "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983"
                : result.akta_disyorkan === "Akta 154"
                  ? "Seksyen 25 Akta 154 (Maksimum RM500)"
                  : result.akta_disyorkan === "Akta 342"
                    ? "Seksyen 25 Akta 342 [P.U. (A) 139/2025]"
                    : "";
          return {
            seksyen: sec,
            kuasaKompaun: kuasa,
            amaun: kuasa ? recomAmt : "",
            tempoh:
              result.akta_disyorkan === "Akta 852"
                ? "30 hari dari tarikh tawaran kompaun"
                : kuasa
                  ? "14 hari dari tarikh serahan notis"
                  : "",
            kesalahanRingkas:
              primaryCharge?.perihal || result.tajuk_nasihat || question.trim(),
          };
        };

        const resultActBadgeStyle = getActBadgeStyle(result.akta_disyorkan);

        return (
          <section
            ref={resultRef}
            className="scroll-mt-20 space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
          >
            {/* Bar Atas: Tag Ringkas + Butang Salin / Tindakan */}
            <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-200 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-md px-2.5 py-0.5 text-xs font-bold ${resultActBadgeStyle.badge}`}>
                  {result.akta_disyorkan}
                </span>
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-bold ${
                    result.from_qa_collection
                      ? "border-teal-300 bg-teal-50 text-teal-900"
                      : result.ai_succeeded
                        ? "border-slate-300 bg-slate-100 text-slate-800"
                        : "border-slate-200 bg-slate-50 text-slate-700"
                  }`}
                >
                  {result.from_qa_collection ? (
                    <History className="h-3.5 w-3.5" />
                  ) : result.ai_succeeded ? (
                    <Sparkles className="h-3.5 w-3.5" />
                  ) : (
                    <Zap className="h-3.5 w-3.5 text-emerald-700" />
                  )}
                  {cleanEngineLabel}
                </span>
                {activeValidation && activeValidation.passed && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-900">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" />
                    <span>Disahkan Teks Akta AGC &amp; SOP 2024</span>
                    {isDevAdmin && (
                      <span className="ml-1 font-mono text-[10px] text-emerald-700">
                        ({result.statute_library_version || activeValidation.statute_library_version})
                      </span>
                    )}
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleCopySummary()}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  {copiedSummary ? (
                    <ClipboardCheck className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  {copiedSummary ? "Disalin!" : "Salin Ringkasan"}
                </button>

                {!isNoOffence && (!activeValidation || activeValidation.passed) && !result.unindexed_statute && (
                  <>
                    {canOfferCompoundCta && (
                      <button
                        type="button"
                        onClick={() =>
                          onApplyToCaseBuilder(
                            result.draf_teks_kes_cadangan,
                            result.akta_disyorkan,
                            true
                          )
                        }
                        className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-[#0f2744]/30 bg-white px-3.5 py-2 text-xs font-bold text-[#0f2744] hover:bg-slate-50"
                      >
                        Buka Fail IP
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() =>
                        onApplyToCaseBuilder(
                          result.draf_teks_kes_cadangan,
                          result.akta_disyorkan,
                          !canOfferCompoundCta,
                          canOfferCompoundCta ? buildCompoundMeta() : undefined
                        )
                      }
                      className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                    >
                      <ArrowRightCircle className="h-4 w-4" />
                      {canOfferCompoundCta
                        ? "Isi Notis Kompaun →"
                        : "Muat ke Fail IP (Langkah 1) →"}
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* MAKSIMUM 1 BANNER STATUS SAHAJA DI BAHAGIAN ATAS */}
            {showValidationAlert && activeValidation && (
              <div className="rounded-xl border border-rose-300 bg-rose-50 p-3.5 text-xs text-rose-950">
                <div className="flex items-start gap-2.5">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" />
                  <div className="space-y-1">
                    <div className="font-extrabold text-rose-900">
                      Semakan Akta Memerlukan Perhatian
                    </div>
                    <ul className="list-disc space-y-0.5 pl-4 font-medium text-rose-900">
                      {[
                        ...(activeValidation.invalid_citations || []),
                        ...(activeValidation.repealed_hits || []).map((r) => r.warning_message_bm),
                        ...(activeValidation.penalty_mismatches || []),
                        ...(activeValidation.unfulfilled_element_errors || []),
                      ].map((errItem, idx) => (
                        <li key={idx}>{errItem}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {showQaBanner && (
              <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-teal-200 bg-teal-50/70 px-3.5 py-2.5 text-xs text-teal-950">
                <div className="flex min-w-0 flex-1 items-start gap-2">
                  <History className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
                  <div className="min-w-0">
                    <span className="font-bold">Jawapan daripada soalan terdahulu yang serupa:</span>{" "}
                    <span className="text-teal-900">&ldquo;{result.matched_collection_question}&rdquo;</span>
                  </div>
                </div>
                <button
                  type="button"
                  disabled={loading || deepLoading}
                  onClick={() => {
                    const typed = question.trim();
                    handleConsult(
                      typed ? undefined : result.matched_collection_question || result.tajuk_nasihat,
                      undefined,
                      true
                    );
                  }}
                  className="inline-flex min-h-[44px] shrink-0 items-center gap-1 rounded-lg border border-teal-300 bg-white px-3 py-1.5 text-xs font-bold text-teal-900 hover:bg-teal-100 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5 text-[#0f2744]" />
                  {deepLoading ? "AI sedang membuat semakan mendalam..." : "Semak Semula dengan AI"}
                </button>
              </div>
            )}

            {showFallbackBanner && (
              <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-950">
                <div className="flex min-w-0 flex-1 items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                  <div>
                    <span className="font-bold">Dipaparkan daripada Panduan Rasmi (bantuan AI tidak tersedia buat sementara):</span>{" "}
                    {result.fallback_reason}
                  </div>
                </div>
                <button
                  type="button"
                  disabled={loading || deepLoading}
                  onClick={() => {
                    const typed = question.trim();
                    handleConsult(
                      typed ? undefined : result.tajuk_nasihat,
                      typed ? undefined : result.scenario_id,
                      true
                    );
                  }}
                  className="inline-flex min-h-[44px] shrink-0 items-center gap-1 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {deepLoading ? "AI sedang membuat semakan mendalam..." : "Cuba Semula AI"}
                </button>
              </div>
            )}

            {/* ================================================================= */}
            {/* CABANG A: TIADA_KESALAHAN (Susunan Bersih Warna Ambar/Biru)       */}
            {/* ================================================================= */}
            {isNoOffence ? (
              <div className="space-y-4">
                {/* 1. Kad Keputusan Utama (Warna Ambar/Biru Bersih — BUKAN kotak ralat merah) */}
                <div className="rounded-2xl border border-amber-300 bg-gradient-to-br from-amber-50/90 via-white to-sky-50/70 p-4 sm:p-5">
                  <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-extrabold text-amber-950">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-700" />
                    Keputusan Semakan Undang-Undang
                  </div>
                  <h3 className="mt-2 text-base font-extrabold tracking-tight text-slate-900 sm:text-lg">
                    {result.tajuk_nasihat.toUpperCase().startsWith("TIADA KESALAHAN") ||
                    result.tajuk_nasihat.toUpperCase().startsWith("AKTA BELUM DIINDEKS")
                      ? result.tajuk_nasihat
                      : `TIADA KESALAHAN DI BAWAH ${result.akta_disyorkan.toUpperCase()}`}
                  </h3>
                  <p className="mt-1.5 text-sm font-bold leading-snug text-slate-800">
                    {result.ringkasan_keputusan || result.keputusan_tindakan}
                  </p>
                </div>

                {/* 2. Sebab Tidak Menyalahi Undang-Undang */}
                <div className="rounded-2xl border border-sky-200 bg-sky-50/40 p-4">
                  <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-sky-950">
                    <BookOpen className="h-4 w-4 text-sky-700" />
                    Sebab Tidak Menyalahi Undang-Undang
                  </h4>
                  <p className="mt-2 text-xs leading-relaxed text-slate-800 sm:text-[13px]">
                    {result.sebab_tidak_menyalahi || result.alasan_keputusan}
                  </p>

                  {visibleNoOffenceEvals.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-sky-200/70 pt-3">
                      <div className="text-[11px] font-extrabold uppercase tracking-wide text-slate-700">
                        Perkara Wajib Dibuktikan (Sebab Tiada Kesalahan)
                      </div>
                      {visibleNoOffenceEvals.map((ev) => (
                        <div key={ev.offence_id} className="space-y-1.5 rounded-xl border border-slate-200 bg-white p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                            <span className="font-extrabold text-slate-900">
                              {ev.offence_section || result.akta_disyorkan}
                              {isDevAdmin ? (
                                <span className="ml-1.5 font-mono text-[10px] font-semibold text-slate-500">
                                  ({ev.offence_id})
                                </span>
                              ) : null}
                            </span>
                            <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-extrabold text-amber-950">
                              Syarat Tidak Dipenuhi
                            </span>
                          </div>
                          <ul className="space-y-1.5 text-xs">
                            {ev.element_evaluations.map((el) => (
                              <li key={el.element_no} className="flex flex-wrap items-start justify-between gap-2 border-t border-slate-100 pt-1.5">
                                <div className="min-w-0 flex-1">
                                  <span className="font-semibold text-slate-800">
                                    {el.element_no}. {el.description}
                                  </span>
                                  {el.notes && (
                                    <p className="mt-0.5 text-[11px] text-slate-600">{el.notes}</p>
                                  )}
                                </div>
                                <span
                                  className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
                                    el.status === "TIDAK TERPENUHI"
                                      ? "bg-rose-100 text-rose-900"
                                      : el.status === "TERPENUHI"
                                        ? "bg-slate-100 text-slate-700"
                                        : "bg-amber-100 text-amber-900"
                                  }`}
                                >
                                  {el.status === "TIDAK TERPENUHI"
                                    ? "Syarat Tidak Dipenuhi"
                                    : el.status === "TERPENUHI"
                                      ? "Fakta Asas"
                                      : el.status || "Perlu Bukti Tambahan"}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 3. Langkah & Tindakan Susulan PPKP (Jika Perlu) + Rujukan SOP KKM 2024 & [NOTA PINDAAN] */}
                {(followUpSteps.length > 0 ||
                  result.nota_pindaan ||
                  (result.repealed_warnings && result.repealed_warnings.length > 0) ||
                  (result.sop_references && result.sop_references.length > 0) ||
                  result.jawapan_4_lapisan_sop) && (
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    {followUpSteps.length > 0 && (
                      <>
                        <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-slate-900">
                          <ClipboardList className="h-4 w-4 text-indigo-700" />
                          Langkah &amp; Tindakan Susulan PPKP (Jika Perlu)
                        </h4>
                        <ol className="mt-2.5 space-y-2.5 text-xs leading-relaxed text-slate-700 sm:text-[13px]">
                          {followUpSteps.map((step, idx) => (
                            <li key={idx} className="flex items-start gap-2.5">
                              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#0f2744] text-[11px] font-extrabold text-white">
                                {idx + 1}
                              </span>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ol>
                      </>
                    )}

                    {(result.nota_pindaan ||
                      (result.repealed_warnings && result.repealed_warnings.length > 0) ||
                      (result.sop_references && result.sop_references.length > 0) ||
                      result.jawapan_4_lapisan_sop) && (
                      <div className="mt-3.5 space-y-2.5 border-t border-slate-200 pt-3">
                        {result.nota_pindaan && (
                          <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-950">
                            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                            <span>{result.nota_pindaan}</span>
                          </div>
                        )}

                        {result.repealed_warnings && result.repealed_warnings.length > 0 && (
                          <div className="space-y-1.5">
                            {result.repealed_warnings.map((rw, rIdx) => (
                              <div
                                key={rw.provision_id || rIdx}
                                className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50/70 px-3 py-2 text-xs text-rose-950"
                              >
                                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" />
                                <div>
                                  <span className="font-extrabold">{rw.warning_message_bm}</span>
                                  {rw.key_differences_note && (
                                    <span className="ml-1 text-rose-900">({rw.key_differences_note})</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {result.sop_references && result.sop_references.length > 0 && (
                          <div className="space-y-1.5">
                            <div className="text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
                              Rujukan Rasmi SOP KKM (Pindaan 15 Feb 2024)
                            </div>
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                              {result.sop_references.map((sop) => (
                                <div
                                  key={sop.sop_id}
                                  className="rounded-xl border border-indigo-200/80 bg-indigo-50/40 px-3 py-2 text-xs"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-1.5">
                                    <span className="font-extrabold text-indigo-950">
                                      {sop.sop_id}
                                    </span>
                                    {sop.muka_surat_pdf && (
                                      <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-indigo-900 ring-1 ring-indigo-200">
                                        PDF m.s. {sop.muka_surat_pdf}
                                      </span>
                                    )}
                                  </div>
                                  <div className="mt-0.5 font-medium text-slate-700">
                                    {sop.tajuk}
                                  </div>
                                  {sop.lampiran_ringkas && sop.lampiran_ringkas.length > 0 && (
                                    <div className="mt-1 text-[11px] text-slate-600">
                                      <span className="font-bold text-slate-800">Borang/Lampiran:</span>{" "}
                                      {sop.lampiran_ringkas.join(", ")}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {result.jawapan_4_lapisan_sop && (
                          <details className="rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-xs">
                            <summary className="cursor-pointer font-extrabold text-[#0f2744]">
                              Lihat Ringkasan Lengkap 4 Lapisan Bukti SOP (Penilaian, Punca Kuasa, Langkah &amp; Lampiran)
                            </summary>
                            <div className="mt-2 whitespace-pre-wrap leading-relaxed text-slate-700">
                              {result.jawapan_4_lapisan_sop}
                            </div>
                          </details>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 4. Rujukan Teks Asal Akta (Akordion Kemas) */}
                {result.statutory_citations.length > 0 && (
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/40">
                    <button
                      type="button"
                      onClick={() => setShowNoOffenceStatutes((v) => !v)}
                      className="flex min-h-[44px] w-full items-center justify-between gap-2 px-4 py-3 text-left text-xs font-extrabold text-slate-900 hover:bg-slate-100/70"
                    >
                      <span className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 shrink-0 text-teal-700" />
                        Rujukan Teks Asal Akta ({result.statutory_citations.length} Seksyen — untuk semakan / rujukan pengadu)
                      </span>
                      {showNoOffenceStatutes ? (
                        <ChevronUp className="h-4 w-4 shrink-0 text-slate-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 shrink-0 text-slate-500" />
                      )}
                    </button>

                    {showNoOffenceStatutes && (
                      <div className="space-y-2.5 border-t border-slate-200 bg-white p-4">
                        {result.statutory_citations.map((cit, i) => (
                          <div
                            key={i}
                            className="rounded-xl border border-teal-200 bg-teal-50/25 p-3.5 text-xs text-slate-800"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="font-extrabold text-teal-900">
                                {cit.section.toLowerCase().includes(cit.akta_code.toLowerCase())
                                  ? cit.section
                                  : `${cit.akta_code} — ${cit.section}`}
                              </div>
                              {isDevAdmin && cit.doc_id && (
                                <span className="rounded bg-white px-2 py-0.5 font-mono text-[10px] font-bold text-slate-600 ring-1 ring-slate-200">
                                  {cit.doc_id}
                                </span>
                              )}
                            </div>
                            <p className="mt-1.5 whitespace-pre-line leading-relaxed">{cit.text}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    disabled={loading || deepLoading}
                    onClick={() => {
                      const typed = question.trim();
                      handleConsult(
                        typed ? undefined : result.tajuk_nasihat,
                        typed ? undefined : result.scenario_id,
                        true
                      );
                    }}
                    className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-[#0f2744]/25 bg-slate-50 px-3.5 py-2 text-xs font-bold text-[#0f2744] transition hover:bg-slate-100 disabled:opacity-50"
                  >
                    {deepLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                    )}
                    {deepLoading
                      ? "AI sedang membuat semakan mendalam..."
                      : "Jalankan Semakan Mendalam dengan AI"}
                  </button>
                </div>
              </div>
            ) : (
              /* ================================================================= */
              /* CABANG B: ADA_KESALAHAN (Turutan Kerja Lapangan PPKP)             */
              /* ================================================================= */
              <div className="space-y-4">
                <h3 className="text-base font-extrabold text-slate-900 sm:text-lg">
                  {result.tajuk_nasihat}
                </h3>

                {/* 1. PUNCA KUASA (Teratas & Jelas) */}
                <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-[#0f2744]">
                      <Gavel className="h-4 w-4 text-[#0f2744]" />
                      1. Punca Kuasa
                    </div>
                    <span
                      className={`rounded-full px-3 py-0.5 text-xs font-extrabold ${
                        punca.boleh_kompaun_flag
                          ? "bg-emerald-100 text-emerald-900"
                          : "bg-amber-100 text-amber-950"
                      }`}
                    >
                      {punca.boleh_kompaun_flag ? "Boleh Kompaun" : "Terus Mahkamah"}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-3 text-xs sm:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                      <div className="text-xs font-semibold text-slate-500">Seksyen Kesalahan</div>
                      <div className="mt-0.5 text-sm font-extrabold text-[#0f2744]">
                        {punca.seksyen_kesalahan}
                      </div>
                      <div className="mt-1.5 text-xs text-slate-600">
                        <span className="font-semibold">Seksyen Hukuman:</span> {punca.seksyen_hukuman}
                      </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                      <div className="text-xs font-semibold text-slate-500">Had Denda / Penjara &amp; Kompaun</div>
                      <div className="mt-0.5 text-sm font-bold text-slate-900">{punca.had_hukuman}</div>
                      <div className="mt-1.5 text-xs font-semibold text-emerald-800">
                        {punca.status_kompaun}
                      </div>
                    </div>
                  </div>

                  {punca.kuasa_penguatkuasaan && (
                    <div className="mt-2.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-700">
                      <span className="font-bold text-slate-900">Kuasa Penguatkuasaan: </span>
                      {punca.kuasa_penguatkuasaan}
                    </div>
                  )}

                  {punca.peringatan_akta_611 && (
                    <div className="mt-2.5 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-950">
                      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                      <span>{punca.peringatan_akta_611}</span>
                    </div>
                  )}
                </div>

                {/* 2. CADANGAN TINDAKAN */}
                <div
                  className={`rounded-2xl border border-slate-200 border-l-4 p-4 ${
                    result.sesuai_buka_ip
                      ? "border-l-amber-500 bg-amber-50/40"
                      : "border-l-emerald-600 bg-emerald-50/40"
                  }`}
                >
                  <div className="text-xs font-extrabold uppercase tracking-wide text-slate-700">
                    2. Cadangan Tindakan
                  </div>
                  <div className="mt-1 text-sm font-extrabold text-slate-900">
                    {result.ringkasan_keputusan || result.keputusan_tindakan}
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-700 sm:text-sm">
                    {result.alasan_keputusan}
                  </p>
                </div>

                {/* 3. LANGKAH TINDAKAN DI LOKASI (SENARAI SEMAK INTERAKTIF) */}
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-slate-900">
                      <ClipboardList className="h-4 w-4 text-emerald-700" />
                      3. Langkah Tindakan di Lokasi (Tandakan jika selesai)
                    </h4>
                    <span className="text-xs font-semibold text-slate-500">
                      {Object.values(checkedSop).filter(Boolean).length}/{result.sop_lapangan.length} selesai
                    </span>
                  </div>
                  <ol className="mt-3 space-y-2 text-xs leading-relaxed text-slate-700 sm:text-sm">
                    {result.sop_lapangan.map((step, i) => {
                      const done = Boolean(checkedSop[i]);
                      return (
                        <li key={i}>
                          <label
                            className={`flex min-h-[44px] cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                              done
                                ? "border-emerald-200 bg-emerald-50/40 text-slate-500 line-through"
                                : "border-slate-200 bg-slate-50/40 hover:bg-slate-50"
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={done}
                              onChange={() =>
                                setCheckedSop((prev) => ({ ...prev, [i]: !prev[i] }))
                              }
                              className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-[#0f2744]"
                            />
                            <span>
                              <strong className="mr-1 text-[#0f2744] no-underline">{i + 1}.</strong>
                              {step}
                            </span>
                          </label>
                        </li>
                      );
                    })}
                  </ol>

                  {/* Rujukan SOP KKM Pindaan 2024 & [NOTA PINDAAN] (Otak SOP Dual Knowledge Store) */}
                  {(result.nota_pindaan ||
                    (result.repealed_warnings && result.repealed_warnings.length > 0) ||
                    (result.sop_references && result.sop_references.length > 0) ||
                    result.jawapan_4_lapisan_sop) && (
                    <div className="mt-3.5 space-y-2.5 border-t border-slate-200 pt-3">
                      {result.nota_pindaan && (
                        <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-950">
                          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                          <span>{result.nota_pindaan}</span>
                        </div>
                      )}

                      {result.repealed_warnings && result.repealed_warnings.length > 0 && (
                        <div className="space-y-1.5">
                          {result.repealed_warnings.map((rw, rIdx) => (
                            <div
                              key={rw.provision_id || rIdx}
                              className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50/70 px-3 py-2 text-xs text-rose-950"
                            >
                              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" />
                              <div>
                                <span className="font-extrabold">{rw.warning_message_bm}</span>
                                {rw.key_differences_note && (
                                  <span className="ml-1 text-rose-900">({rw.key_differences_note})</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {result.sop_references && result.sop_references.length > 0 && (
                        <div className="space-y-1.5">
                          <div className="text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
                            Rujukan Rasmi SOP KKM (Pindaan 15 Feb 2024)
                          </div>
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {result.sop_references.map((sop) => (
                              <div
                                key={sop.sop_id}
                                className="rounded-xl border border-indigo-200/80 bg-indigo-50/40 px-3 py-2 text-xs"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-1.5">
                                  <span className="font-extrabold text-indigo-950">
                                    {sop.sop_id}
                                  </span>
                                  {sop.muka_surat_pdf && (
                                    <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-indigo-900 ring-1 ring-indigo-200">
                                      PDF m.s. {sop.muka_surat_pdf}
                                    </span>
                                  )}
                                </div>
                                <div className="mt-0.5 font-medium text-slate-700">
                                  {sop.tajuk}
                                </div>
                                {sop.lampiran_ringkas && sop.lampiran_ringkas.length > 0 && (
                                  <div className="mt-1 text-[11px] text-slate-600">
                                    <span className="font-bold text-slate-800">Borang/Lampiran:</span>{" "}
                                    {sop.lampiran_ringkas.join(", ")}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.jawapan_4_lapisan_sop && (
                        <details className="rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-xs">
                          <summary className="cursor-pointer font-extrabold text-[#0f2744]">
                            Lihat Ringkasan Lengkap 4 Lapisan Bukti SOP (Penilaian, Punca Kuasa, Langkah &amp; Lampiran)
                          </summary>
                          <div className="mt-2 whitespace-pre-wrap leading-relaxed text-slate-700">
                            {result.jawapan_4_lapisan_sop}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                </div>

                {/* 4. TAB TAMBAHAN YANG KEMAS DI BAWAH SOP */}
                <div className="space-y-3 pt-1">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
                    <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
                      {[
                        {
                          id: "evidence" as AdvisorResultTab,
                          label: "Bukti & Syarat Kes",
                        },
                        {
                          id: "charges" as AdvisorResultTab,
                          label: `Draf Pertuduhan (${result.cadangan_pertuduhan.length})`,
                        },
                        {
                          id: "statutes" as AdvisorResultTab,
                          label: `Teks Asal Akta (${result.statutory_citations.length})`,
                        },
                      ].map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setResultTab(t.id)}
                          className={`min-h-[44px] shrink-0 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                            resultTab === t.id
                              ? "bg-[#0f2744] text-white"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    <button
                      type="button"
                      disabled={loading || deepLoading}
                      onClick={() => {
                        const typed = question.trim();
                        handleConsult(
                          typed ? undefined : result.tajuk_nasihat,
                          typed ? undefined : result.scenario_id,
                          true
                        );
                      }}
                      className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-[#0f2744]/25 bg-slate-50 px-3.5 py-2 text-xs font-bold text-[#0f2744] transition hover:bg-slate-100 disabled:opacity-50"
                    >
                      {deepLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                      )}
                      {deepLoading
                        ? "AI sedang membuat semakan mendalam..."
                        : "Semakan Mendalam dengan AI"}
                    </button>
                  </div>

                  {/* TAB 1: BARANG BUKTI & PERKARA WAJIB BUKTIKAN + ELAK KESILAPAN BIASA */}
                  {resultTab === "evidence" && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-3.5">
                          <h4 className="mb-2 flex items-center gap-1.5 text-xs font-extrabold text-slate-900">
                            <CheckCircle2 className="h-4 w-4 text-teal-700" />
                            Senarai Barang Bukti &amp; Borang Wajib
                          </h4>
                          <ul className="list-disc space-y-1.5 pl-5 text-xs leading-relaxed text-slate-700">
                            {result.eksibit_wajib.map((ex, i) => (
                              <li key={i}>{ex}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="rounded-xl border border-amber-200 border-l-4 border-l-amber-500 bg-amber-50/40 p-3.5">
                          <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-extrabold text-amber-950">
                            <AlertTriangle className="h-4 w-4 text-amber-700" />
                            Elak Kesilapan Lazim PPKP
                          </h4>
                          <ul className="space-y-1.5 text-xs text-amber-950">
                            {result.perangkap_kesilapan.map((trap, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                                <span>{trap}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {visibleOffenceEvals.length > 0 && (
                        <div className="space-y-2.5">
                          <h4 className="text-xs font-extrabold uppercase tracking-wide text-slate-700">
                            Perkara Wajib Dibuktikan
                          </h4>
                          {visibleOffenceEvals.map((ev) => (
                            <div
                              key={ev.offence_id}
                              className="overflow-hidden rounded-xl border border-slate-200"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs">
                                <span className="font-extrabold text-slate-900">
                                  {ev.offence_section || result.akta_disyorkan}
                                  {isDevAdmin ? (
                                    <span className="ml-1.5 font-mono text-[10px] font-semibold text-slate-500">
                                      ({ev.offence_id})
                                    </span>
                                  ) : null}
                                </span>
                                <span
                                  className={`rounded-full px-2.5 py-0.5 text-[10px] font-extrabold ${
                                    ev.action_blocked
                                      ? "bg-rose-100 text-rose-900"
                                      : ev.all_elements_satisfied
                                        ? "bg-emerald-100 text-emerald-900"
                                        : "bg-amber-100 text-amber-900"
                                  }`}
                                >
                                  {ev.action_blocked
                                    ? "Syarat Tidak Dipenuhi"
                                    : ev.all_elements_satisfied
                                      ? "Fakta Asas Dipenuhi"
                                      : "Sahkan Bukti Di Lokasi"}
                                </span>
                              </div>

                              {/* Paparan Kad Telefon (<640px) */}
                              <div className="divide-y divide-slate-200 bg-white sm:hidden">
                                {ev.element_evaluations.map((el) => (
                                  <div key={el.element_no} className="space-y-1.5 p-3 text-xs">
                                    <div className="flex items-start justify-between gap-2">
                                      <span className="font-bold text-slate-900">
                                        {el.element_no}. {el.description}
                                      </span>
                                      <span
                                        className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
                                          el.status === "TERPENUHI"
                                            ? "bg-emerald-100 text-emerald-900"
                                            : el.status === "TIDAK TERPENUHI"
                                              ? "bg-rose-100 text-rose-900"
                                              : "bg-amber-100 text-amber-900"
                                        }`}
                                      >
                                        {el.status === "TERPENUHI"
                                          ? "Dipenuhi"
                                          : el.status === "TIDAK TERPENUHI"
                                            ? "Syarat Tidak Dipenuhi"
                                            : el.status || "Perlu Bukti Tambahan"}
                                      </span>
                                    </div>
                                    {(el.notes || el.must_prove) && (
                                      <p className="text-[11px] leading-relaxed text-slate-600">
                                        {el.notes || el.must_prove}
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>

                              {/* Paparan Jadual Desktop (>=640px) */}
                              <div className="hidden overflow-x-auto sm:block">
                                <table className="w-full border-collapse text-left text-xs">
                                  <thead>
                                    <tr className="border-b border-slate-200 bg-white text-[11px] font-extrabold uppercase text-slate-600">
                                      <th className="p-2.5">Bil</th>
                                      <th className="p-2.5">Perkara Wajib Dibuktikan</th>
                                      <th className="p-2.5">Status</th>
                                      <th className="p-2.5">Catatan Bukti</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-200">
                                    {ev.element_evaluations.map((el) => (
                                      <tr key={el.element_no} className="hover:bg-slate-50/60">
                                        <td className="p-2.5 font-mono font-bold text-slate-900">
                                          {el.element_no}
                                        </td>
                                        <td className="p-2.5 font-medium text-slate-800">
                                          {el.description}
                                        </td>
                                        <td className="p-2.5">
                                          <span
                                            className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-extrabold ${
                                              el.status === "TERPENUHI"
                                                ? "bg-emerald-100 text-emerald-900"
                                                : el.status === "TIDAK TERPENUHI"
                                                  ? "bg-rose-100 text-rose-900"
                                                  : "bg-amber-100 text-amber-900"
                                            }`}
                                          >
                                            {el.status === "TERPENUHI"
                                              ? "Dipenuhi"
                                              : el.status === "TIDAK TERPENUHI"
                                                ? "Syarat Tidak Dipenuhi"
                                                : el.status || "Perlu Bukti Tambahan"}
                                          </span>
                                        </td>
                                        <td className="p-2.5 text-slate-600">
                                          {el.notes || el.must_prove}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 2: DRAF PERTUDUHAN */}
                  {resultTab === "charges" && (
                    <div className="space-y-3">
                      {result.cadangan_pertuduhan.map((c, idx) => (
                        <div
                          key={idx}
                          className="rounded-xl border border-slate-200 bg-slate-50/40 p-3.5 text-xs"
                        >
                          <div className="flex items-center gap-2 font-extrabold text-slate-900">
                            <Gavel className="h-4 w-4 text-blue-700" />
                            <span>{c.perihal}</span>
                          </div>
                          <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                            <div>
                              <span className="font-semibold text-slate-500">Seksyen Kesalahan: </span>
                              <span className="font-bold text-blue-900">{c.seksyen_kesalahan}</span>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-500">Seksyen Hukuman: </span>
                              <span className="font-bold text-indigo-900">{c.seksyen_hukuman}</span>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-500">Had Hukuman: </span>
                              <span className="text-slate-800">{c.hukuman_maksimum}</span>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-500">Status Kompaun: </span>
                              <span className="font-bold text-emerald-800">{c.boleh_kompaun}</span>
                            </div>
                          </div>
                        </div>
                      ))}

                      {result.templat_ringkas && (
                        <div className="rounded-xl border border-slate-200 bg-white p-3.5 text-xs">
                          <div className="font-extrabold text-slate-900">
                            Rangka Ringkas Pertuduhan / Borang 114
                          </div>
                          <p className="mt-1.5 leading-relaxed text-slate-700">
                            {result.templat_ringkas}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 3: TEKS ASAL AKTA */}
                  {resultTab === "statutes" && (
                    <div className="space-y-2.5">
                      {result.statutory_citations.length === 0 ? (
                        <p className="text-xs text-slate-500">
                          Tiada petikan akta tambahan dilampirkan untuk pertanyaan ini.
                        </p>
                      ) : (
                        result.statutory_citations.map((cit, i) => (
                          <div
                            key={i}
                            className="rounded-xl border border-teal-200 bg-teal-50/25 p-3.5 text-xs text-slate-800"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="font-extrabold text-teal-900">
                                {cit.section.toLowerCase().includes(cit.akta_code.toLowerCase())
                                  ? cit.section
                                  : `${cit.akta_code} — ${cit.section}`}
                              </div>
                              {isDevAdmin && cit.doc_id && (
                                <span className="rounded bg-white px-2 py-0.5 font-mono text-[10px] font-bold text-slate-600 ring-1 ring-slate-200">
                                  {cit.doc_id}
                                </span>
                              )}
                            </div>
                            <p className="mt-1.5 whitespace-pre-line leading-relaxed">{cit.text}</p>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="border-t border-slate-100 pt-2.5 text-[11px] leading-relaxed text-slate-500">
              <strong className="text-slate-700">Nota Rujukan Rasmi:</strong> Panduan ini berasaskan teks Warta Kerajaan Persekutuan (AGC) &amp; 22 SOP Penguatkuasaan KKM Pindaan 2024 (Hierarki Statut &gt; SOP). Keputusan muktamad pendakwaan tertakluk kepada semakan UIP JKN dan Izin Mendakwa Timbalan Pendakwa Raya.
            </div>
          </section>
        );
      })()}
        </>
      )}

      {/* TAB 3: SOALAN TERDAHULU (TERASING DARIPADA KOTAK JAWAPAN SUPAYA SKRIN TENANG) */}
      {workspaceTab === "history" && (
      <section
        ref={answeredSectionRef}
        className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-[#0f2744]">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-900">
                Soalan Terdahulu (Mengikut Akta)
              </h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
                <span>
                  Soalan yang pernah ditanya pegawai lain, disusun mengikut Akta. Jawapan sedia ada terus dipaparkan jika situasi hampir sama.
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" /> Data Sulit Dilindungi
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-extrabold text-slate-800">
              {answeredData?.total_questions ?? 0} Soalan · {activeActsCount} Akta
            </span>
            <button
              type="button"
              onClick={() => void loadAnsweredQuestions()}
              disabled={answeredLoading}
              title="Muat semula senarai soalan"
              aria-label="Muat semula senarai soalan"
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${answeredLoading ? "animate-spin" : ""}`} />
              <span className="ml-1.5 hidden sm:inline">Muat Semula</span>
            </button>
          </div>
        </div>

        {answeredError && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-900">
            <span>{answeredError}</span>
            <button
              type="button"
              onClick={() => void loadAnsweredQuestions()}
              className="inline-flex min-h-[40px] items-center gap-1 rounded-lg border border-rose-300 bg-white px-3 text-xs font-bold text-rose-900 hover:bg-rose-100"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Cuba Semula
            </button>
          </div>
        )}

        {/* Carian & Tapisan Mengikut Akta */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={answeredSearch}
              onChange={(e) => setAnsweredSearch(e.target.value)}
              placeholder="Cari soalan terdahulu, seksyen atau keputusan..."
              className="min-h-[44px] w-full rounded-xl border border-slate-300 bg-slate-50/50 py-2 pl-9 pr-11 text-base text-slate-900 placeholder:text-slate-400 focus:border-[#0f2744] focus:bg-white focus:outline-none sm:text-sm"
            />
            {answeredSearch && (
              <button
                type="button"
                onClick={() => setAnsweredSearch("")}
                aria-label="Kosongkan carian"
                className="absolute right-1 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-200 hover:text-slate-700"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="no-scrollbar flex flex-nowrap items-center gap-1.5 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0">
            <button
              type="button"
              onClick={() => setAnsweredActFilter("Semua")}
              className={`inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-bold transition sm:min-h-[38px] sm:py-1 ${
                answeredActFilter === "Semua"
                  ? "border-[#0f2744] bg-[#0f2744] text-white"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              <span>Semua Akta</span>
              <span
                className={`rounded-full px-1.5 py-0.5 text-xs font-extrabold ${
                  answeredActFilter === "Semua"
                    ? "bg-white/20 text-white"
                    : "bg-slate-200 text-slate-800"
                }`}
              >
                {answeredData?.total_questions ?? 0}
              </span>
            </button>

            {visibleActFilterCodes.map((code) => {
              const count = answeredData?.act_counts?.[code] ?? 0;
              const active = answeredActFilter === code;
              const st = getActBadgeStyle(code);
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => setAnsweredActFilter(code)}
                  className={`inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-bold transition sm:min-h-[38px] sm:py-1 ${
                    active
                      ? st.pillActive
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span>{code}</span>
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-xs font-extrabold ${
                      active ? "bg-white/20 text-white" : "bg-slate-200 text-slate-800"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Senarai Soalan Dikelompok Mengikut Akta */}
        {answeredLoading && !answeredData ? (
          <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50/50 py-8 text-xs font-semibold text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin text-[#0f2744]" />
            Sedang memuatkan soalan terdahulu...
          </div>
        ) : !answeredData || answeredData.total_questions === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 px-4 py-8 text-center">
            <p className="text-sm font-bold text-slate-700">
              Belum ada soalan terdahulu direkodkan setakat ini.
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Setiap soalan yang disemak di ruangan Tanya Situasi akan disimpan di sini untuk rujukan pegawai lain.
            </p>
          </div>
        ) : filteredAnsweredGroups.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-7 text-center">
            <p className="text-sm font-bold text-slate-700">
              Tiada soalan direkodkan bagi tapisan ini.
            </p>
            <button
              type="button"
              onClick={() => {
                setAnsweredActFilter("Semua");
                setAnsweredSearch("");
              }}
              className="min-h-[44px] rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100"
            >
              Papar Semua Semula
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAnsweredGroups.map((group) => {
              const isExpanded = Boolean(expandedActGroups[group.akta_code]);
              const shownItems = isExpanded ? group.items : group.items.slice(0, 6);
              const hiddenCount = group.items.length - shownItems.length;

              return (
                <div
                  key={group.akta_code}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-white"
                >
                  <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
                    <div className="flex min-w-0 flex-1 items-center gap-2">
                      <span className="shrink-0 rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-extrabold text-white">
                        {group.akta_code}
                      </span>
                      <span className="min-w-0 truncate text-xs font-bold text-slate-900">
                        {group.akta_title}
                      </span>
                    </div>
                    <span className="shrink-0 rounded-full bg-white px-2.5 py-0.5 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                      {group.items.length} soalan
                    </span>
                  </div>

                  <div className="divide-y divide-slate-200">
                    {shownItems.map((item) => {
                      const isSelected = selectedAnsweredId === item.id;
                      const tsLabel = formatShortTimestamp(item.last_asked_at);
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => handleSelectAnsweredItem(item)}
                          className={`flex w-full flex-col gap-1.5 p-4 text-left transition ${
                            isSelected
                              ? "bg-slate-50"
                              : "bg-white hover:bg-slate-50/70"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span
                                className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                                  item.sesuai_buka_ip
                                    ? "bg-amber-100 text-amber-900"
                                    : "bg-emerald-100 text-emerald-800"
                                }`}
                              >
                                {item.sesuai_buka_ip ? "Buka IP" : "Kompaun / Rujukan"}
                              </span>
                              {item.ask_count > 1 && (
                                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                                  Ditanya {item.ask_count} kali
                                </span>
                              )}
                            </div>

                            {tsLabel && (
                              <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                                <Clock className="h-3.5 w-3.5" />
                                {tsLabel}
                              </span>
                            )}
                          </div>

                          <p className="text-sm font-bold leading-snug text-slate-900">
                            &ldquo;{item.question}&rdquo;
                          </p>

                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                            <span>
                              {item.seksyen_utama ? `${item.seksyen_utama} • ` : ""}
                              {item.keputusan_tindakan}
                            </span>
                            <span className="font-bold text-[#0f2744]">
                              Lihat jawapan →
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {group.items.length > 6 && (
                    <div className="border-t border-slate-200 bg-slate-50 px-3.5 py-2 text-center">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedActGroups((prev) => ({
                            ...prev,
                            [group.akta_code]: !prev[group.akta_code],
                          }))
                        }
                        className="inline-flex min-h-[44px] items-center gap-1 px-3 text-xs font-bold text-[#0f2744] hover:underline"
                      >
                        {isExpanded ? (
                          <>
                            Sembunyikan senarai {group.akta_code} <ChevronUp className="h-4 w-4" />
                          </>
                        ) : (
                          <>
                            Papar {hiddenCount} lagi soalan {group.akta_code}{" "}
                            <ChevronDown className="h-4 w-4" />
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
      )}
    </div>
  );
}
