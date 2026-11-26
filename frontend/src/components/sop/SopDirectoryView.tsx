"use client";

import React, { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  FileText,
  Filter,
  ListChecks,
  Loader2,
  RefreshCw,
  Search,
  ShieldAlert,
  X,
} from "lucide-react";
import type { ActiveSopDetail, ActiveSopSummary, PekelilingRujukanItem } from "@/lib/types";
import { fetchActiveSopDetail, fetchActiveSops } from "@/lib/api";
import { useLockBodyScroll, useModalFocusTrap } from "@/lib/uiHelpers";
import SopInteractiveViewer from "./SopInteractiveViewer";
import { getCachedSopDetail, setCachedSopDetail } from "./SopQuickModal";

interface SopDirectoryViewProps {
  authToken?: string | null;
  initialSopCode?: string | null;
  onAskExpertWithSop?: (promptText: string) => void;
}

const AKTA_CHIPS = [
  { key: "Semua", label: "Semua SOP" },
  { key: "Akta 852", label: "Akta 852 (Merokok)" },
  { key: "Akta 281", label: "Akta 281 (Makanan)" },
  { key: "Akta 154", label: "Akta 154 (APSPP)" },
  { key: "Akta 342", label: "Akta 342 (APPPB)" },
  { key: "UMUM", label: "SOP Umum / KTJ" },
];

export default function SopDirectoryView({
  authToken,
  initialSopCode,
  onAskExpertWithSop,
}: SopDirectoryViewProps) {
  const [sops, setSops] = useState<ActiveSopSummary[]>([]);
  const [totalCorpus, setTotalCorpus] = useState<number>(0);
  const [quarantinedCount, setQuarantinedCount] = useState<number>(5);
  const [pekelilingList, setPekelilingList] = useState<PekelilingRujukanItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const deferredQuery = useDeferredValue(searchQuery);
  const [aktaFilter, setAktaFilter] = useState("Semua");
  const [onlyWithAmendment, setOnlyWithAmendment] = useState(false);

  const [selectedStem, setSelectedStem] = useState<string | null>(initialSopCode || null);
  const [selectedDetail, setSelectedDetail] = useState<ActiveSopDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  const mobileDrawerRef = useRef<HTMLDivElement | null>(null);
  useLockBodyScroll(mobileDrawerOpen);
  useModalFocusTrap(mobileDrawerRef, mobileDrawerOpen, () => setMobileDrawerOpen(false));

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setListError(null);
    try {
      const res = await fetchActiveSops({
        q: deferredQuery.trim() || undefined,
        akta: aktaFilter !== "Semua" ? aktaFilter : undefined,
        ada_pindaan: onlyWithAmendment ? true : undefined,
        authToken,
      });
      const items = res.items || res.sops || [];
      setSops(items);
      setTotalCorpus(res.total_active_corpus ?? res.total ?? items.length);
      setQuarantinedCount(res.quarantined_deprecated_blocked ?? 5);
      setPekelilingList(res.pekeliling_rujukan || []);

      setSelectedStem((prev) => {
        if (prev && items.some((it) => it.file_stem.toUpperCase() === prev.toUpperCase())) {
          return prev;
        }
        return items.length > 0 ? items[0].file_stem : null;
      });
    } catch (err: unknown) {
      setListError(
        err instanceof Error
          ? err.message
          : "Gagal memuatkan senarai SOP KKM aktif. Sila cuba semula."
      );
    } finally {
      setLoadingList(false);
    }
  }, [deferredQuery, aktaFilter, onlyWithAmendment, authToken]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (initialSopCode) {
      setSelectedStem(initialSopCode);
    }
  }, [initialSopCode]);

  const loadDetail = useCallback(
    async (stem: string, bypassCache = false) => {
      const clean = stem.trim().split(/\s+/)[0].toUpperCase();
      if (!clean) return;
      if (!bypassCache) {
        const cached = getCachedSopDetail(clean);
        if (cached) {
          setSelectedDetail(cached);
          setDetailError(null);
          setLoadingDetail(false);
          return;
        }
      }
      setLoadingDetail(true);
      setDetailError(null);
      try {
        const detail = await fetchActiveSopDetail(clean, authToken);
        setCachedSopDetail(detail.file_stem || clean, detail);
        setSelectedDetail(detail);
      } catch (err: unknown) {
        setSelectedDetail(null);
        setDetailError(
          err instanceof Error
            ? err.message
            : "Gagal memuatkan butiran SOP ini. Sila cuba semula."
        );
      } finally {
        setLoadingDetail(false);
      }
    },
    [authToken]
  );

  useEffect(() => {
    if (!selectedStem) {
      setSelectedDetail(null);
      return;
    }
    void loadDetail(selectedStem);
  }, [selectedStem, loadDetail]);

  const handleSelectSop = (stem: string, openMobile = true) => {
    setSelectedStem(stem);
    if (openMobile && typeof window !== "undefined" && window.innerWidth < 1024) {
      setMobileDrawerOpen(true);
    }
  };

  const showPekelilingCard = useMemo(
    () =>
      pekelilingList.length > 0 &&
      (aktaFilter === "Semua" || aktaFilter === "Akta 852"),
    [pekelilingList, aktaFilter]
  );

  return (
    <div className="space-y-4">
      {/* Top Banner & Search Controls */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
              <BookOpen className="h-4 w-4 text-indigo-600" />
              Direktori Visual SOP Penguatkuasaan KKM 2024
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              {totalCorpus || sops.length} SOP aktif berstruktur (langkah demi langkah, carta alir,
              senarai semak lapangan &amp; borang) · {quarantinedCount} SOP PPKHT 2004 mansuh
              dikuarantin.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-bold text-emerald-800">
            Statut &gt; SOP Aktif
          </span>
        </div>

        {/* Search + Amendment Filter */}
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari kod SOP, tajuk, langkah, borang, seksyen (cth: S.47, sitaan, BWC, 18(1)(d))..."
              className="w-full rounded-xl border border-slate-300 bg-slate-50/50 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
          </div>
          <button
            type="button"
            onClick={() => setOnlyWithAmendment((v) => !v)}
            aria-pressed={onlyWithAmendment}
            className={`inline-flex shrink-0 items-center justify-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition ${
              onlyWithAmendment
                ? "border-amber-400 bg-amber-50 text-amber-900"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            <Filter className="h-3.5 w-3.5" />
            Ada [NOTA PINDAAN]
          </button>
        </div>

        {/* Act Filter Chips */}
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-0.5 no-scrollbar">
          {AKTA_CHIPS.map((chip) => {
            const active = aktaFilter === chip.key;
            return (
              <button
                key={chip.key}
                type="button"
                onClick={() => setAktaFilter(chip.key)}
                className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold transition ${
                  active
                    ? "border-indigo-600 bg-indigo-600 text-white shadow-sm"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-white"
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Supplementary Warning Card for Pekeliling KPK Bil 18/2024 (#09) */}
      {showPekelilingCard &&
        pekelilingList.map((pek) => (
          <div
            key={pek.kod}
            className="rounded-xl border border-amber-300 bg-amber-50/90 p-3.5 text-xs text-amber-950"
          >
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold">
                    {pek.kod} ({pek.no_rujukan} · {pek.tarikh})
                  </span>
                  <span className="rounded-full bg-amber-200/80 px-2 py-0.5 text-[10px] font-bold text-amber-950">
                    Amaran Imbasan Tidak Lengkap
                  </span>
                </div>
                <p className="leading-relaxed">{pek.amaran_ketidaklengkapan}</p>
              </div>
            </div>
          </div>
        ))}

      {/* List Error Banner */}
      {listError && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-900">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0 text-rose-600" />
            <span className="font-semibold">{listError}</span>
          </div>
          <button
            type="button"
            onClick={() => void loadList()}
            className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-rose-700"
          >
            <RefreshCw className="h-3 w-3" />
            Cuba Semula
          </button>
        </div>
      )}

      {/* Master-Detail Split Layout */}
      <div className="grid gap-4 lg:grid-cols-12">
        {/* Left Master List */}
        <div className="space-y-2 lg:col-span-4 xl:col-span-4">
          <div className="flex items-center justify-between px-1 text-xs font-semibold text-slate-500">
            <span>Menunjukkan {sops.length} SOP aktif</span>
            {loadingList && <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />}
          </div>

          <div className="max-h-[72vh] space-y-2 overflow-y-auto pr-1">
            {!loadingList && sops.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-xs text-slate-500">
                Tiada SOP aktif sepadan dengan tapisan anda. Cuba kata kunci lain atau pilih{" "}
                <strong>Semua SOP</strong>.
              </div>
            ) : (
              sops.map((item) => {
                const isSelected =
                  selectedStem?.toUpperCase() === item.file_stem.toUpperCase();
                return (
                  <button
                    key={item.file_stem}
                    type="button"
                    onClick={() => handleSelectSop(item.file_stem, true)}
                    className={`w-full rounded-xl border p-3 text-left transition ${
                      isSelected
                        ? "border-indigo-500 bg-indigo-50/70 shadow-sm ring-1 ring-indigo-300"
                        : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-slate-50/60"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-1.5">
                      <span className="font-mono text-xs font-bold text-indigo-700">
                        {item.file_stem}
                      </span>
                      <div className="flex items-center gap-1">
                        {item.has_nota_pindaan && (
                          <span
                            className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                              item.nota_pindaan_tahap === "KRITIKAL"
                                ? "bg-rose-100 text-rose-800"
                                : "bg-amber-100 text-amber-900"
                            }`}
                          >
                            Nota Pindaan
                          </span>
                        )}
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                          {item.akta.split(" ")[0]} {item.akta.split(" ")[1] || ""}
                        </span>
                      </div>
                    </div>

                    <h4 className="mt-1 line-clamp-2 text-xs font-bold leading-snug text-slate-900">
                      {item.tajuk}
                    </h4>

                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                      {typeof item.bil_langkah === "number" && item.bil_langkah > 0 && (
                        <span className="inline-flex items-center gap-1">
                          <ListChecks className="h-3 w-3 text-indigo-500" />
                          {item.bil_langkah} langkah
                        </span>
                      )}
                      {typeof item.bil_lampiran === "number" && item.bil_lampiran > 0 && (
                        <span className="inline-flex items-center gap-1">
                          <FileText className="h-3 w-3 text-emerald-600" />
                          {item.bil_lampiran} lampiran
                        </span>
                      )}
                    </div>

                    {item.match_snippet && (
                      <p className="mt-1.5 line-clamp-2 rounded bg-amber-50/80 px-2 py-1 text-[11px] text-amber-950">
                        {item.match_snippet}
                      </p>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Detail Viewer (Desktop) */}
        <div className="hidden lg:col-span-8 lg:block xl:col-span-8">
          {loadingDetail ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white py-24 text-slate-500">
              <Loader2 className="h-7 w-7 animate-spin text-indigo-600" />
              <p className="text-sm font-medium">Memuatkan paparan visual SOP...</p>
            </div>
          ) : detailError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
              <p className="text-sm font-semibold text-rose-900">{detailError}</p>
              {selectedStem && (
                <button
                  type="button"
                  onClick={() => void loadDetail(selectedStem, true)}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Cuba Semula
                </button>
              )}
            </div>
          ) : selectedDetail ? (
            <SopInteractiveViewer
              detail={selectedDetail}
              onOpenSop={(code) => handleSelectSop(code, false)}
              onAskExpertWithSop={onAskExpertWithSop}
            />
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-500">
              Pilih mana-mana SOP di sebelah kiri untuk memaparkan langkah visual, carta alir,
              senarai semak lapangan dan borang wajib.
            </div>
          )}
        </div>
      </div>

      {/* Mobile Full-Height Bottom-Sheet Drawer (< lg) */}
      {mobileDrawerOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-slate-900/55 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileDrawerOpen(false)}
          role="presentation"
        >
          <div
            ref={mobileDrawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Paparan Butiran SOP"
            tabIndex={-1}
            onClick={(e) => e.stopPropagation()}
            className="flex h-[92vh] w-full flex-col overflow-hidden rounded-t-2xl bg-slate-50 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
              <span className="font-mono text-xs font-bold text-indigo-700">
                {selectedDetail?.sop_id || selectedStem}
              </span>
              <button
                type="button"
                onClick={() => setMobileDrawerOpen(false)}
                aria-label="Tutup paparan SOP"
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3.5">
              {loadingDetail ? (
                <div className="flex flex-col items-center justify-center gap-2 py-16 text-slate-500">
                  <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
                  <span className="text-xs">Memuatkan SOP...</span>
                </div>
              ) : detailError ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-center text-xs text-rose-900">
                  <p className="font-semibold">{detailError}</p>
                  {selectedStem && (
                    <button
                      type="button"
                      onClick={() => void loadDetail(selectedStem, true)}
                      className="mt-2 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white"
                    >
                      Cuba Semula
                    </button>
                  )}
                </div>
              ) : selectedDetail ? (
                <SopInteractiveViewer
                  detail={selectedDetail}
                  onOpenSop={(code) => handleSelectSop(code, true)}
                  onAskExpertWithSop={
                    onAskExpertWithSop
                      ? (prompt) => {
                          setMobileDrawerOpen(false);
                          onAskExpertWithSop(prompt);
                        }
                      : undefined
                  }
                />
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
