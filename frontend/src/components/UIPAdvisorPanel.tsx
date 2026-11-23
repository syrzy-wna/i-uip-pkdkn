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
  fetchLegalSnapshot,
} from "@/lib/api";
import { validateLegalOutput } from "@/lib/legalValidator";
import type {
  AdvisorAnsweredItem,
  AdvisorAnsweredListResponse,
  AdvisorConsultResult,
  AdvisorScenarioItem,
  LegalLibrarySnapshot,
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
];

const CORE_ACT_CODES = ["Akta 852", "Akta 281", "Akta 154", "Akta 342"] as const;
const SECONDARY_ACT_CODES = [
  "Akta 593",
  "Akta 56",
  "Akta Lain / Rujukan Silang",
] as const;

function getActBadgeStyle(aktaCode: string): {
  badge: string;
  headerBg: string;
  pillActive: string;
} {
  switch (aktaCode) {
    case "Akta 852":
      return {
        badge: "bg-indigo-700 text-white",
        headerBg: "border-indigo-200 bg-indigo-50/70",
        pillActive: "bg-indigo-700 text-white border-indigo-700",
      };
    case "Akta 281":
      return {
        badge: "bg-amber-700 text-white",
        headerBg: "border-amber-200 bg-amber-50/70",
        pillActive: "bg-amber-700 text-white border-amber-700",
      };
    case "Akta 154":
      return {
        badge: "bg-emerald-700 text-white",
        headerBg: "border-emerald-200 bg-emerald-50/70",
        pillActive: "bg-emerald-700 text-white border-emerald-700",
      };
    case "Akta 342":
      return {
        badge: "bg-rose-700 text-white",
        headerBg: "border-rose-200 bg-rose-50/70",
        pillActive: "bg-rose-700 text-white border-rose-700",
      };
    default:
      return {
        badge: "bg-slate-700 text-white",
        headerBg: "border-slate-200 bg-slate-100/80",
        pillActive: "bg-slate-800 text-white border-slate-800",
      };
  }
}

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
  initialWorkspaceTab = "ask",
  workspaceTabNonce = 0,
  onApplyToCaseBuilder,
}: UIPAdvisorPanelProps) {
  const [workspaceTab, setWorkspaceTab] = useState<PakarWorkspaceTab>(initialWorkspaceTab);
  const [question, setQuestion] = useState("");
  const [aktaFilter, setAktaFilter] = useState<string>("Semua");
  const [scenarios, setScenarios] = useState<AdvisorScenarioItem[]>([]);
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
  const [answeredActFilter, setAnsweredActFilter] = useState<string>("Semua");
  const [answeredSearch, setAnsweredSearch] = useState("");
  const [selectedAnsweredId, setSelectedAnsweredId] = useState<string | null>(null);
  const [expandedActGroups, setExpandedActGroups] = useState<Record<string, boolean>>({});
  const [legalSnapshot, setLegalSnapshot] = useState<LegalLibrarySnapshot | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);
  const answeredSectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setWorkspaceTab(initialWorkspaceTab);
  }, [initialWorkspaceTab, workspaceTabNonce]);

  useEffect(() => {
    fetchAdvisorScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]));
  }, []);

  useEffect(() => {
    fetchLegalSnapshot(authToken)
      .then((snap) => {
        setLegalSnapshot(snap);
        if (typeof window !== "undefined") {
          try {
            window.localStorage.setItem("uip_offline_legal_library_v2", JSON.stringify(snap));
          } catch {
            // Abaikan jika kuota penuh
          }
        }
      })
      .catch(() => {
        if (typeof window !== "undefined") {
          const raw = window.localStorage.getItem("uip_offline_legal_library_v2");
          if (raw) {
            try {
              setLegalSnapshot(JSON.parse(raw) as LegalLibrarySnapshot);
            } catch {
              // Abaikan
            }
          }
        }
      });
  }, [authToken]);

  const loadAnsweredQuestions = useCallback(async () => {
    setAnsweredLoading(true);
    try {
      const data = await fetchAdvisorAnsweredQuestions({ authToken, limit: 150 });
      setAnsweredData(data);
    } catch {
      // Abaikan jika senarai soalan dijawab gagal dimuat sementara
    } finally {
      setAnsweredLoading(false);
    }
  }, [authToken]);

  useEffect(() => {
    void loadAnsweredQuestions();
  }, [loadAnsweredQuestions]);

  const handleConsult = async (
    customQuestion?: string,
    scenarioId?: string,
    forceAi = false
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

    try {
      const res = await consultUipAdvisor({
        question: q || "Rujuk contoh situasi ini",
        aktaHint: aktaFilter,
        scenarioId,
        useAi: forceAi,
        authToken,
        officerProfile: officer,
      });
      setResult(res);
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
      setQuestion(initialQuestion.trim());
      setWorkspaceTab("ask");
      void handleConsult(initialQuestion.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestionNonce]);

  const handleSelectAnsweredItem = (item: AdvisorAnsweredItem) => {
    setQuestion(item.question);
    setSelectedAnsweredId(item.id);
    setError(null);
    setCopiedSummary(false);
    setShowLibrary(false);
    setShowNoOffenceStatutes(false);
    setWorkspaceTab("ask");
    if (item.answer) {
      setResult(item.answer);
      setCheckedSop({});
      setResultTab("evidence");
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 90);
      return;
    }
    void handleConsult(item.question);
  };

  const handleCopySummary = () => {
    if (!result) return;
    const isNoOff =
      result.status_kesalahan === "TIADA_KESALAHAN" ||
      (!result.status_kesalahan &&
        (result.keputusan_tindakan.toUpperCase().includes("TIADA KESALAHAN") ||
          result.keputusan_tindakan.toUpperCase().includes("BUKAN KESALAHAN")));

    if (isNoOff) {
      const steps =
        result.langkah_susulan_ppkp && result.langkah_susulan_ppkp.length > 0
          ? result.langkah_susulan_ppkp
          : result.sop_lapangan;
      const text = [
        `${result.tajuk_nasihat} (${result.akta_disyorkan})`,
        `KEPUTUSAN: ${result.ringkasan_keputusan || result.keputusan_tindakan}`,
        `SEBAB TIDAK MENYALAHI UNDANG-UNDANG:\n${result.sebab_tidak_menyalahi || result.alasan_keputusan}`,
        steps.length
          ? `LANGKAH SUSULAN PPKP:\n${steps.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
          : "",
      ]
        .filter(Boolean)
        .join("\n\n");
      navigator.clipboard?.writeText(text);
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2000);
      return;
    }

    const primary = result.cadangan_pertuduhan[0];
    const punca = result.punca_kuasa;
    const text = [
      `RUJUKAN UIP KKM: ${result.tajuk_nasihat} (${result.akta_disyorkan})`,
      `SEKSYEN KESALAHAN: ${punca?.seksyen_kesalahan || primary?.seksyen_kesalahan || result.akta_disyorkan}`,
      `HUKUMAN: ${punca?.seksyen_hukuman || primary?.seksyen_hukuman || "-"} (${punca?.had_hukuman || primary?.hukuman_maksimum || "-"})`,
      `TINDAKAN SEGERA: ${result.ringkasan_keputusan || result.keputusan_tindakan}`,
      `LANGKAH LAPANGAN:\n${result.sop_lapangan.map((s, i) => `${i + 1}. ${s}`).join("\n")}`,
      `BARANG BUKTI WAJIB:\n${result.eksibit_wajib.map((e) => `- ${e}`).join("\n")}`,
    ]
      .filter(Boolean)
      .join("\n\n");
    navigator.clipboard?.writeText(text);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
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

  const activeValidation: LegalValidationResult | null = useMemo(() => {
    if (!result) return null;
    if (legalSnapshot) {
      const clientCheck = validateLegalOutput(result, legalSnapshot, question);
      if (!clientCheck.passed) return clientCheck;
    }
    return result.legal_validation || (legalSnapshot ? validateLegalOutput(result, legalSnapshot, question) : null);
  }, [result, legalSnapshot, question]);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      {/* BAR 3 TAB BERSIH: GABUNGAN TANYA SITUASI + SENARAI KESALAHAN & AKTA + SOALAN TERDAHULU */}
      <div className="flex gap-1.5 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm no-scrollbar">
        {[
          { id: "ask" as PakarWorkspaceTab, label: "Tanya Situasi", icon: MessageSquareQuote },
          { id: "directory" as PakarWorkspaceTab, label: "Senarai Kesalahan & Teks Akta", icon: Database },
          {
            id: "history" as PakarWorkspaceTab,
            label: `Soalan Terdahulu (${answeredData?.total_questions ?? 0})`,
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
              className={`inline-flex min-h-[42px] shrink-0 flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2 text-xs font-extrabold transition ${
                active
                  ? "bg-[#0f2744] text-white shadow-sm"
                  : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="whitespace-nowrap">{tab.label}</span>
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
              Tak pasti seksyen atau tindakan di lokasi?
            </h2>
            <p className="mt-0.5 text-xs text-slate-600 sm:text-sm">
              Taip sahaja apa yang anda jumpa untuk semak seksyen tepat, kompaun atau buka IP, dan langkah SOP.
            </p>
          </div>

          <select
            aria-label="Tapis Akta KKM"
            value={aktaFilter}
            onChange={(e) => setAktaFilter(e.target.value)}
            className="min-h-[42px] w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-800 sm:w-auto sm:text-sm"
          >
            <option value="Semua">Semua Akta KKM</option>
            <option value="Akta 852">Akta 852 (Merokok/Vape)</option>
            <option value="Akta 281">Akta 281 &amp; PPKM 2009</option>
            <option value="Akta 154">Akta 154 (Aedes)</option>
            <option value="Akta 342">Akta 342 (Tibi/Berjangkit)</option>
          </select>
        </div>

        <div className="mt-3 space-y-3">
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                handleConsult();
              }
            }}
            placeholder="Contoh: Ada pelajar hisap vape di tandas sekolah, atau kedai pamer vape terbuka di kaunter..."
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
                    handleConsult(chip);
                  }}
                  className="min-h-[38px] rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[#0f2744] hover:bg-slate-100 hover:text-slate-900"
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
                className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                <BookOpen className="h-4 w-4 text-[#0f2744]" />
                <span>Contoh Situasi ({filteredScenarios.length})</span>
                {showLibrary ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
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
                {deepLoading ? "AI sedang menyemak..." : "Semakan Mendalam dengan AI"}
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
            <div className="mb-2.5 text-xs font-bold text-slate-700">
              Pilih satu situasi untuk terus lihat seksyen &amp; SOP:
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {filteredScenarios.map((sc) => {
                const selected = result?.scenario_id === sc.id;
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
                      <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[11px] font-bold text-white">
                        {sc.akta_utama}
                      </span>
                      <span
                        className={`text-[11px] font-bold ${
                          sc.sesuai_buka_ip ? "text-amber-800" : "text-emerald-700"
                        }`}
                      >
                        {sc.sesuai_buka_ip ? "Buka IP" : "Kompaun"}
                      </span>
                    </div>
                    <span className="mt-1.5 text-xs font-bold text-slate-900">{sc.tajuk}</span>
                  </button>
                );
              })}
            </div>
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
                ? "Sedang menjalankan Semakan Mendalam dengan AI..."
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

        const punca = result.punca_kuasa || {
          akta: result.akta_disyorkan,
          seksyen_kesalahan: primaryCharge?.seksyen_kesalahan || result.akta_disyorkan,
          seksyen_hukuman: primaryCharge?.seksyen_hukuman || "-",
          had_hukuman: primaryCharge?.hukuman_maksimum || "-",
          status_kompaun:
            primaryCharge?.boleh_kompaun ||
            (result.sesuai_buka_ip ? "Terus Mahkamah (Buka IP)" : "Boleh Kompaun"),
          boleh_kompaun_flag: !result.sesuai_buka_ip,
          kuasa_penguatkuasaan: "",
          peringatan_akta_611: null,
        };

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

        return (
          <section
            ref={resultRef}
            className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
          >
            {/* Bar Atas: Tag Ringkas + Butang Salin / Tindakan */}
            <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-200 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-bold text-white">
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
                {isDevAdmin && activeValidation && activeValidation.passed && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-900">
                    <ShieldCheck className="h-3 w-3 text-emerald-700" />
                    {result.statute_library_version || activeValidation.statute_library_version}
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopySummary}
                  className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  {copiedSummary ? (
                    <ClipboardCheck className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  {copiedSummary ? "Disalin!" : "Salin Ringkasan"}
                </button>

                {!isNoOffence && (!activeValidation || activeValidation.passed) && !result.unindexed_statute && (
                  <button
                    type="button"
                    onClick={() => {
                      const amtMatch = (punca.status_kompaun || "").match(/RM\s*[\d,]+(?:\.\d{2})?/i);
                      onApplyToCaseBuilder(
                        result.draf_teks_kes_cadangan,
                        result.akta_disyorkan,
                        result.sesuai_buka_ip,
                        result.sesuai_buka_ip
                          ? undefined
                          : {
                              seksyen: punca.seksyen_kesalahan || primaryCharge?.seksyen_kesalahan || "",
                              kuasaKompaun:
                                result.akta_disyorkan === "Akta 852"
                                  ? "Seksyen 48 Akta 852 [P.U. (A) 259/2024]"
                                  : result.akta_disyorkan === "Akta 154"
                                    ? "Seksyen 25 Akta 154"
                                    : result.akta_disyorkan === "Akta 342"
                                      ? "Seksyen 25 Akta 342 [P.U. (A) 139/2025]"
                                      : "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983",
                              amaun: amtMatch
                                ? amtMatch[0].toUpperCase()
                                : result.akta_disyorkan === "Akta 154"
                                  ? "RM 500.00"
                                  : "RM 250.00",
                              tempoh:
                                result.akta_disyorkan === "Akta 852"
                                  ? "30 hari dari tarikh tawaran kompaun"
                                  : "14 hari dari tarikh serahan notis",
                              kesalahanRingkas:
                                primaryCharge?.perihal || result.tajuk_nasihat || question.trim(),
                            }
                      );
                    }}
                    className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                  >
                    <ArrowRightCircle className="h-4 w-4" />
                    {result.sesuai_buka_ip
                      ? "Bina Draf Fail IP →"
                      : "Isi Notis Kompaun →"}
                  </button>
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
                  onClick={() => handleConsult(undefined, undefined, true)}
                  className="inline-flex min-h-[36px] shrink-0 items-center gap-1 rounded-lg border border-teal-300 bg-white px-3 py-1.5 text-xs font-bold text-teal-900 hover:bg-teal-100 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5 text-[#0f2744]" />
                  {deepLoading ? "AI sedang menyemak..." : "Semak Baharu Dengan AI"}
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
                  className="inline-flex min-h-[36px] shrink-0 items-center gap-1 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {deepLoading ? "AI sedang menyemak..." : "Cuba Semula AI"}
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

                  {result.element_evaluations && result.element_evaluations.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-sky-200/70 pt-3">
                      <div className="text-[11px] font-extrabold uppercase tracking-wide text-slate-700">
                        Perkara Wajib Dibuktikan (Punca Penolakan)
                      </div>
                      {result.element_evaluations.map((ev) => (
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
                              Unsur Tidak Dipenuhi
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
                                        ? "bg-emerald-100 text-emerald-900"
                                        : "bg-amber-100 text-amber-900"
                                  }`}
                                >
                                  {el.status === "TIDAK TERPENUHI"
                                    ? "TIDAK DIPENUHI"
                                    : el.status === "TERPENUHI"
                                      ? "DIPENUHI"
                                      : el.status || "PERLU BUKTI TAMBAHAN"}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 3. Langkah & Tindakan Susulan PPKP (Jika Perlu) */}
                {followUpSteps.length > 0 && (
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
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
                  </div>
                )}

                {/* 4. Rujukan Teks Asal Akta (Akordion Kemas) */}
                {result.statutory_citations.length > 0 && (
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/40">
                    <button
                      type="button"
                      onClick={() => setShowNoOffenceStatutes((v) => !v)}
                      className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-xs font-extrabold text-slate-900 hover:bg-slate-100/70"
                    >
                      <span className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-teal-700" />
                        Rujukan Teks Asal Akta ({result.statutory_citations.length} Seksyen — untuk semakan / rujukan pengadu)
                      </span>
                      {showNoOffenceStatutes ? (
                        <ChevronUp className="h-4 w-4 text-slate-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-slate-500" />
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
                    className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl border border-[#0f2744]/25 bg-slate-50 px-3.5 py-1.5 text-xs font-bold text-[#0f2744] transition hover:bg-slate-100 disabled:opacity-50"
                  >
                    {deepLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                    )}
                    {deepLoading
                      ? "AI sedang menyemak mendalam..."
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

                {/* 2. CADANGAN TINDAKAN SEGERA */}
                <div
                  className={`rounded-2xl border border-slate-200 border-l-4 p-4 ${
                    result.sesuai_buka_ip
                      ? "border-l-amber-500 bg-amber-50/40"
                      : "border-l-emerald-600 bg-emerald-50/40"
                  }`}
                >
                  <div className="text-xs font-extrabold uppercase tracking-wide text-slate-700">
                    2. Cadangan Tindakan Segera
                  </div>
                  <div className="mt-1 text-sm font-extrabold text-slate-900">
                    {result.ringkasan_keputusan || result.keputusan_tindakan}
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-700 sm:text-sm">
                    {result.alasan_keputusan}
                  </p>
                </div>

                {/* 3. LANGKAH PERLU DIAMBIL (SOP LAPANGAN — SENARAI SEMAK INTERAKTIF) */}
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-slate-900">
                      <ClipboardList className="h-4 w-4 text-emerald-700" />
                      3. Langkah Perlu Diambil di Lokasi (Boleh Tanda Siap)
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
                            className={`flex cursor-pointer items-start gap-3 rounded-xl border p-2.5 transition ${
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
                          className={`min-h-[40px] shrink-0 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
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
                      className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl border border-[#0f2744]/25 bg-slate-50 px-3 py-1.5 text-xs font-bold text-[#0f2744] transition hover:bg-slate-100 disabled:opacity-50"
                    >
                      {deepLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                      )}
                      {deepLoading
                        ? "AI sedang menyemak mendalam..."
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
                            Elak Kesilapan Biasa PPKP
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

                      {result.element_evaluations && result.element_evaluations.length > 0 && (
                        <div className="space-y-2.5">
                          <h4 className="text-xs font-extrabold uppercase tracking-wide text-slate-700">
                            Perkara Wajib Dibuktikan
                          </h4>
                          {result.element_evaluations.map((ev) => (
                            <div
                              key={ev.offence_id}
                              className="overflow-x-auto rounded-xl border border-slate-200"
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
                                    ? "Unsur Tidak Dipenuhi"
                                    : ev.all_elements_satisfied
                                      ? "Fakta Asas Dipenuhi"
                                      : "Sahkan Bukti Di Lokasi"}
                                </span>
                              </div>
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
                                            ? "DIPENUHI"
                                            : el.status === "TIDAK TERPENUHI"
                                              ? "TIDAK DIPENUHI"
                                              : el.status || "PERLU BUKTI TAMBAHAN"}
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
                  Soalan yang pernah ditanya pegawai lain, disusun ikut Akta. Jawapan sedia ada terus dipaparkan jika situasi hampir sama.
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
              className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${answeredLoading ? "animate-spin" : ""}`} />
              <span className="ml-1.5 hidden sm:inline">Muat Semula</span>
            </button>
          </div>
        </div>

        {/* Carian & Tapisan Mengikut Akta */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={answeredSearch}
              onChange={(e) => setAnsweredSearch(e.target.value)}
              placeholder="Cari soalan terdahulu, seksyen atau keputusan..."
              className="min-h-[44px] w-full rounded-xl border border-slate-300 bg-slate-50/50 py-2 pl-9 pr-9 text-base text-slate-900 placeholder:text-slate-400 focus:border-[#0f2744] focus:bg-white focus:outline-none sm:text-sm"
            />
            {answeredSearch && (
              <button
                type="button"
                onClick={() => setAnsweredSearch("")}
                aria-label="Kosongkan carian"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setAnsweredActFilter("Semua")}
              className={`inline-flex min-h-[38px] items-center gap-1.5 rounded-full border px-3.5 py-1 text-xs font-bold transition ${
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
                  className={`inline-flex min-h-[38px] items-center gap-1.5 rounded-full border px-3.5 py-1 text-xs font-bold transition ${
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
              Setiap soalan yang disemak di tab Tanya Situasi akan disimpan di sini untuk rujukan pegawai lain.
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
              className="min-h-[38px] rounded-xl border border-slate-300 bg-white px-4 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-100"
            >
              Tunjuk Semua Semula
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
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <span className="shrink-0 rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-extrabold text-white">
                        {group.akta_code}
                      </span>
                      <span className="truncate text-xs font-bold text-slate-900">
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
                    <div className="border-t border-slate-200 bg-slate-50 px-3.5 py-2.5 text-center">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedActGroups((prev) => ({
                            ...prev,
                            [group.akta_code]: !prev[group.akta_code],
                          }))
                        }
                        className="inline-flex min-h-[36px] items-center gap-1 text-xs font-bold text-[#0f2744] hover:underline"
                      >
                        {isExpanded ? (
                          <>
                            Sembunyikan senarai {group.akta_code} <ChevronUp className="h-4 w-4" />
                          </>
                        ) : (
                          <>
                            Tunjuk {hiddenCount} lagi soalan {group.akta_code}{" "}
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
