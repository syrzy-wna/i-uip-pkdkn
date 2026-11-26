"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Archive,
  ArrowLeft,
  Check,
  Cloud,
  Copy,
  Database,
  Download,
  Eye,
  EyeOff,
  FileArchive,
  FileCode2,
  FileEdit,
  FileText,
  HardDrive,
  Loader2,
  Lock,
  MessageSquare,
  Paperclip,
  RefreshCw,
  Scale,
  Search,
  ShieldCheck,
  UserCheck,
  X,
} from "lucide-react";
import {
  downloadDevVaultFile,
  exportDevVaultBundle,
  fetchDevVaultFilePreviewUrl,
  fetchDevVaultRecordDetail,
  fetchDevVaultRecords,
  retryDevVaultS3Sync,
} from "@/lib/api";
import { copyTextSafe } from "@/lib/uiHelpers";
import type {
  DevVaultCategory,
  DevVaultExportMode,
  DevVaultListResponse,
  DevVaultRecordDetail,
} from "@/lib/types";

interface DevVaultTabProps {
  authToken?: string | null;
  developerEmail?: string;
  initialUserFilter?: string;
  onClearInitialUserFilter?: () => void;
  refreshSignal?: number;
}

const CATEGORY_TABS: Array<{
  id: DevVaultCategory;
  label: string;
  badgeClass: string;
}> = [
  { id: "ALL", label: "Semua Rekod", badgeClass: "bg-slate-100 text-slate-800 border-slate-200" },
  {
    id: "USER_REGISTER",
    label: "Pengguna Didaftar",
    badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-200",
  },
  {
    id: "ADVISOR_QA",
    label: "Soalan Pakar",
    badgeClass: "bg-indigo-100 text-indigo-800 border-indigo-200",
  },
  {
    id: "AUDIT_IP",
    label: "Dokumen Audit IP",
    badgeClass: "bg-amber-100 text-amber-800 border-amber-200",
  },
  {
    id: "OCR_EVIDENCE",
    label: "Bukti OCR",
    badgeClass: "bg-rose-100 text-rose-800 border-rose-200",
  },
  {
    id: "DRAFT_COMPOUND",
    label: "Draf & Kompaun",
    badgeClass: "bg-purple-100 text-purple-800 border-purple-200",
  },
];

function formatBytes(bytes?: number | null): string {
  const n = Number(bytes || 0);
  if (!n || n <= 0) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function renderHighlightedTokens(text: string): React.ReactNode {
  if (!text) return null;
  const parts = text.split(/(\[[A-Z_]+_\d+\])/g);
  return parts.map((part, i) => {
    if (/^\[[A-Z_]+_\d+\]$/.test(part)) {
      return (
        <span
          key={i}
          className="mx-0.5 inline-block rounded bg-amber-200 px-1 py-0.5 font-mono text-[11px] font-bold text-amber-950 ring-1 ring-amber-400"
        >
          {part}
        </span>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

function getCategoryStyle(category: string): string {
  const found = CATEGORY_TABS.find((c) => c.id === category);
  return found ? found.badgeClass : "bg-slate-100 text-slate-700 border-slate-200";
}

function getCategoryIcon(category: string) {
  switch (category) {
    case "USER_REGISTER":
      return UserCheck;
    case "ADVISOR_QA":
      return MessageSquare;
    case "AUDIT_IP":
      return Scale;
    case "OCR_EVIDENCE":
      return Eye;
    case "DRAFT_COMPOUND":
      return FileEdit;
    default:
      return Archive;
  }
}

export default function DevVaultTab({
  authToken,
  developerEmail,
  initialUserFilter = "",
  onClearInitialUserFilter,
  refreshSignal = 0,
}: DevVaultTabProps) {
  const [category, setCategory] = useState<DevVaultCategory>("ALL");
  const [searchInput, setSearchInput] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [userFilter, setUserFilter] = useState(initialUserFilter);
  const [hasFileOnly, setHasFileOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const [listData, setListData] = useState<DevVaultListResponse | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, DevVaultRecordDetail>>({});
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [showRawPii, setShowRawPii] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<"content" | "json" | "metadata">("content");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const [exportingMode, setExportingMode] = useState<DevVaultExportMode | null>(null);
  const [downloadingFile, setDownloadingFile] = useState(false);
  const [syncingS3, setSyncingS3] = useState(false);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    setUserFilter(initialUserFilter);
    setOffset(0);
  }, [initialUserFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQ(searchInput);
      setOffset(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        window.URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const res = await fetchDevVaultRecords({
        category,
        q: debouncedQ,
        userEmail: userFilter,
        hasFile: hasFileOnly,
        limit,
        offset,
        authToken,
      });
      setListData(res);
      setSelectedId((prev) => {
        if (prev && res.items.some((item) => item.id === prev)) return prev;
        return res.items[0]?.id || null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuatkan Arkib & Bucket Dev.");
    } finally {
      setLoadingList(false);
    }
  }, [category, debouncedQ, userFilter, hasFileOnly, limit, offset, authToken]);

  useEffect(() => {
    loadList();
  }, [loadList, refreshSignal]);

  const detailCacheRef = React.useRef(detailCache);
  detailCacheRef.current = detailCache;

  const loadDetail = useCallback(
    async (recordId: string) => {
      setPreviewUrl((prev) => {
        if (prev) window.URL.revokeObjectURL(prev);
        return null;
      });
      if (detailCacheRef.current[recordId]) return;
      setLoadingDetail(true);
      try {
        const detail = await fetchDevVaultRecordDetail(recordId, authToken);
        setDetailCache((prev) => ({ ...prev, [recordId]: detail }));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Gagal memuatkan butiran rekod arkib.");
      } finally {
        setLoadingDetail(false);
      }
    },
    [authToken]
  );

  useEffect(() => {
    if (selectedId) {
      loadDetail(selectedId);
    }
  }, [selectedId, loadDetail]);

  const activeDetail = selectedId ? detailCache[selectedId] || null : null;

  const handleCopyText = async (key: string, text: string) => {
    const ok = await copyTextSafe(text);
    if (ok) {
      setCopiedId(key);
      window.setTimeout(() => setCopiedId(null), 1600);
    }
  };

  const handleDownloadAttachment = async (kind: "attachment" | "json") => {
    if (!activeDetail) return;
    setDownloadingFile(true);
    setError(null);
    try {
      const fallback =
        kind === "json"
          ? `${activeDetail.id}_dossier.json`
          : activeDetail.file_attachment?.original_filename || `${activeDetail.id}.bin`;
      await downloadDevVaultFile(activeDetail.id, fallback, kind, authToken);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuat turun fail asal.");
    } finally {
      setDownloadingFile(false);
    }
  };

  const handlePreviewImage = async () => {
    if (!activeDetail) return;
    setLoadingPreview(true);
    setError(null);
    try {
      const { objectUrl } = await fetchDevVaultFilePreviewUrl(activeDetail.id, authToken);
      setPreviewUrl((prev) => {
        if (prev) window.URL.revokeObjectURL(prev);
        return objectUrl;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuatkan pratonton imej.");
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleExport = async (mode: DevVaultExportMode) => {
    setExportingMode(mode);
    setError(null);
    setActionMsg(null);
    try {
      await exportDevVaultBundle({
        mode,
        format: "zip",
        category,
        q: debouncedQ,
        userEmail: userFilter,
        includeFiles: true,
        authToken,
      });
      setActionMsg(
        mode === "redacted"
          ? "Pakej ZIP Versi PDPA Disamarkan berjaya dieksport."
          : "Pakej ZIP Lengkap berjaya dieksport."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengeksport pakej dokumentasi.");
    } finally {
      setExportingMode(null);
    }
  };

  const handleRetryS3Sync = async () => {
    setSyncingS3(true);
    setError(null);
    setActionMsg(null);
    try {
      const res = await retryDevVaultS3Sync(authToken);
      setActionMsg(res.message);
      await loadList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menyelaraskan ke Bucket S3/Neon.");
    } finally {
      setSyncingS3(false);
    }
  };

  const health = listData?.storage_health;
  const counts = listData?.category_counts;
  const isImageAttachment = Boolean(
    activeDetail?.file_attachment?.content_type?.toLowerCase().startsWith("image/")
  );

  return (
    <div className="space-y-3.5">
      {/* A. Bar Status Kesihatan Bucket & Eksport 1-Klik */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#0f2744] px-2.5 py-1 text-[11px] font-bold text-amber-200">
              <Lock className="h-3 w-3" />
              Bucket Eksklusif Dev • {developerEmail || listData?.developer || "Pentadbir Sistem"}
            </span>

            {health && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold ${
                  health.is_cloud_bucket
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-amber-200 bg-amber-50 text-amber-900"
                }`}
              >
                {health.is_cloud_bucket ? (
                  <Cloud className="h-3.5 w-3.5 text-emerald-600" />
                ) : (
                  <Database className="h-3.5 w-3.5 text-amber-700" />
                )}
                {health.backend_label}
              </span>
            )}

            {health && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-700">
                <HardDrive className="h-3 w-3 text-slate-500" />
                {health.total_records} rekod • {health.total_files} fail •{" "}
                {formatBytes(health.total_bytes)}
              </span>
            )}
          </div>

          <div className="text-[11px] text-slate-600">
            {health?.is_cloud_bucket ? (
              <span>
                Bucket Persendirian: <code className="font-mono font-bold">{health.bucket_name}</code>{" "}
                ({health.bucket_region}) • Semua pengguna didaftar, soalan &amp; dokumen analisis disalin automatik.
              </span>
            ) : (
              <span>
                Disimpan kekal dalam enjin <strong>{health?.db_engine === "postgresql" ? "PostgreSQL Neon" : "SQLite"}</strong>{" "}
                {health?.local_vault_path ? (
                  <>
                    &amp; arkib tempatan <code className="font-mono">{health.local_vault_path}</code>
                  </>
                ) : null}
                .{" "}
                {health?.is_ephemeral_warning &&
                  "Syor: sambungkan DATABASE_URL / Neon Bucket dev-vault untuk storan awan kekal."}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {health?.is_cloud_bucket && (health.unsynced_count || 0) > 0 && (
            <button
              type="button"
              onClick={handleRetryS3Sync}
              disabled={syncingS3}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-900 hover:bg-blue-100 disabled:opacity-60 sm:min-h-0"
            >
              {syncingS3 ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              Selaraskan {health.unsynced_count} ke Bucket S3
            </button>
          )}

          <button
            type="button"
            onClick={() => handleExport("redacted")}
            disabled={exportingMode !== null}
            title="Selamat untuk dokumentasi & penambahbaikan model (PII disamarkan)"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-900 hover:bg-emerald-100 disabled:opacity-60 sm:min-h-0"
          >
            {exportingMode === "redacted" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5" />
            )}
            Eksport PDPA Disamarkan (.zip)
          </button>

          <button
            type="button"
            onClick={() => handleExport("full")}
            disabled={exportingMode !== null}
            title="Mengandungi profil penuh, teks asal & lampiran fail asal"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60 sm:min-h-0"
          >
            {exportingMode === "full" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileArchive className="h-3.5 w-3.5" />
            )}
            Eksport Pakej Lengkap (.zip)
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
          {error}
        </div>
      )}

      {actionMsg && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">
          {actionMsg}
        </div>
      )}

      {/* B. Penapis Kategori & Carian Pantas */}
      <div className="flex flex-col gap-2.5 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex flex-wrap gap-1.5">
          {CATEGORY_TABS.map((item) => {
            const active = category === item.id;
            const cnt = counts ? counts[item.id] ?? 0 : 0;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setCategory(item.id);
                  setOffset(0);
                }}
                className={`inline-flex min-h-[38px] items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold transition sm:min-h-0 ${
                  active
                    ? "bg-[#0f2744] text-white shadow-sm"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                <span>{item.label}</span>
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] ${
                    active ? "bg-white/20 text-white" : "bg-white text-slate-700"
                  }`}
                >
                  {cnt}
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2 flex-1">
            <div className="relative flex-1 min-w-[220px] max-w-md">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Cari e-mel pegawai, soalan, nama fail PDF/OCR atau teks..."
                className="min-h-[44px] w-full rounded-lg border border-slate-300 pl-8 pr-10 py-1.5 text-base focus:border-blue-500 focus:outline-none sm:min-h-[36px] sm:text-xs"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => setSearchInput("")}
                  aria-label="Kosongkan carian"
                  className="absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                setHasFileOnly((v) => !v);
                setOffset(0);
              }}
              className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-bold transition sm:min-h-[36px] ${
                hasFileOnly
                  ? "border-blue-500 bg-blue-50 text-blue-900"
                  : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              <Paperclip className="h-3.5 w-3.5" />
              Ada Fail Lampiran Sahaja
            </button>

            {userFilter && (
              <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-1 text-[11px] font-bold text-indigo-900">
                Pegawai: {userFilter}
                <button
                  type="button"
                  onClick={() => {
                    setUserFilter("");
                    onClearInitialUserFilter?.();
                    setOffset(0);
                  }}
                  aria-label="Buang penapis pegawai"
                  className="ml-0.5 rounded-full p-0.5 hover:bg-indigo-200"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={loadList}
            disabled={loadingList}
            className="inline-flex min-h-[44px] items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 sm:min-h-[36px]"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingList ? "animate-spin" : ""}`} />
            Muat Semula
          </button>
        </div>
      </div>

      {/* C. Paparan Master-Detail Split */}
      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-12">
        {/* Panel Kiri: Senarai Rekod Arkib */}
        <div
          className={`${
            selectedId ? "hidden lg:flex" : "flex"
          } flex-col overflow-hidden rounded-xl border border-slate-200 bg-white lg:col-span-5 lg:h-[52vh]`}
        >
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {loadingList && !listData ? (
              <div className="flex items-center justify-center gap-2 py-12 text-xs text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Memuatkan senarai arkib...
              </div>
            ) : (listData?.items.length || 0) === 0 ? (
              <div className="px-4 py-12 text-center text-xs text-slate-500">
                Tiada rekod arkib sepadan dengan penapis semasa.
              </div>
            ) : (
              listData?.items.map((item) => {
                const isSelected = selectedId === item.id;
                const CatIcon = getCategoryIcon(item.category);
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    className={`w-full text-left px-3.5 py-2.5 transition hover:bg-slate-50 ${
                      isSelected
                        ? "bg-blue-50/75 border-l-4 border-l-[#0f2744]"
                        : "border-l-4 border-l-transparent"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span
                          className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-bold ${getCategoryStyle(
                            item.category
                          )}`}
                        >
                          <CatIcon className="h-2.5 w-2.5" />
                          {item.action_type}
                        </span>
                        {item.akta_utama && (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                            {item.akta_utama}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 whitespace-nowrap">
                        {item.created_at}
                      </span>
                    </div>

                    <div className="mt-1 line-clamp-2 text-xs font-bold text-slate-900">
                      {item.title}
                    </div>

                    {item.preview_text && (
                      <div className="mt-0.5 line-clamp-1 text-[11px] text-slate-500">
                        {item.preview_text}
                      </div>
                    )}

                    <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500">
                      <span className="truncate max-w-[240px]">
                        {item.user_name || "Pegawai"} • {item.user_email}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {item.has_file && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-amber-100 px-1.5 py-0.5 font-bold text-amber-900">
                            <Paperclip className="h-2.5 w-2.5" />
                            {formatBytes(item.file_size_bytes)}
                          </span>
                        )}
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[9px] text-slate-600">
                          {item.storage_backend === "s3_neon" ? "S3 Bucket" : "Vault DB"}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Paginasi Bawah */}
          {listData && (
            <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-3 py-2 text-[11px] text-slate-600">
              <span>
                {listData.total_matching === 0
                  ? "0 rekod"
                  : `${offset + 1}–${Math.min(offset + listData.items.length, listData.total_matching)} daripada ${listData.total_matching}`}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={offset === 0 || loadingList}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  className="min-h-[36px] rounded border border-slate-300 bg-white px-2.5 py-1 font-semibold hover:bg-slate-100 disabled:opacity-40 sm:min-h-0 sm:px-2 sm:py-0.5"
                >
                  Sebelumnya
                </button>
                <button
                  type="button"
                  disabled={offset + limit >= listData.total_matching || loadingList}
                  onClick={() => setOffset(offset + limit)}
                  className="min-h-[36px] rounded border border-slate-300 bg-white px-2.5 py-1 font-semibold hover:bg-slate-100 disabled:opacity-40 sm:min-h-0 sm:px-2 sm:py-0.5"
                >
                  Seterusnya
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Panel Kanan: Pemeriksa Rekod Terperinci */}
        <div
          className={`${
            selectedId ? "flex" : "hidden lg:flex"
          } flex-col overflow-hidden rounded-xl border border-slate-200 bg-white lg:col-span-7 lg:h-[52vh]`}
        >
          {!selectedId ? (
            <div className="flex flex-1 flex-col items-center justify-center p-8 text-center text-xs text-slate-500">
              <Archive className="mb-2 h-8 w-8 text-slate-300" />
              Pilih mana-mana rekod di sebelah kiri untuk melihat soalan penuh, fail dimuat naik, atau data pengguna.
            </div>
          ) : loadingDetail && !activeDetail ? (
            <div className="flex flex-1 items-center justify-center gap-2 text-xs text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Memuatkan butiran rekod...
            </div>
          ) : activeDetail ? (
            <div className="flex flex-1 flex-col overflow-y-auto">
              {/* Header Pemeriksa Sticky */}
              <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 p-3.5 backdrop-blur-sm space-y-2.5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => setSelectedId(null)}
                        className="inline-flex min-h-[38px] items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700 lg:hidden"
                      >
                        <ArrowLeft className="h-3.5 w-3.5" /> Senarai
                      </button>
                      <span
                        className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-bold ${getCategoryStyle(
                          activeDetail.category
                        )}`}
                      >
                        {activeDetail.action_type}
                      </span>
                      <span className="font-mono text-[10px] text-slate-500">
                        {activeDetail.id}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        • {activeDetail.created_at}
                      </span>
                    </div>
                    <h4 className="text-xs sm:text-sm font-extrabold text-slate-900">
                      {activeDetail.title}
                    </h4>
                    <div className="text-[11px] text-slate-600">
                      <strong>{activeDetail.user_name || "Pegawai"}</strong> ({activeDetail.user_email}) •{" "}
                      {activeDetail.district_pkd} • Enjin:{" "}
                      <code className="font-mono">{activeDetail.model_used || "-"}</code>
                    </div>
                  </div>

                  {/* Toggle PDPA Disamarkan vs Teks Asal */}
                  <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-[11px] font-bold">
                    <button
                      type="button"
                      onClick={() => setShowRawPii(false)}
                      className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 transition ${
                        !showRawPii
                          ? "bg-emerald-600 text-white shadow-sm"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      <EyeOff className="h-3 w-3" />
                      PDPA Disamarkan ({activeDetail.pdpa_entities_masked})
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowRawPii(true)}
                      className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 transition ${
                        showRawPii
                          ? "bg-amber-600 text-white shadow-sm"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      <Eye className="h-3 w-3" />
                      Teks Asal (Dev)
                    </button>
                  </div>
                </div>

                {/* Sub-Tab Pemeriksa */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex gap-1">
                    {[
                      { id: "content", label: "Kandungan & Analisis", icon: FileText },
                      { id: "json", label: "Struktur JSON", icon: FileCode2 },
                      { id: "metadata", label: "Storan & Bucket", icon: Database },
                    ].map((sub) => {
                      const SIcon = sub.icon;
                      const active = inspectorTab === sub.id;
                      return (
                        <button
                          key={sub.id}
                          type="button"
                          onClick={() => setInspectorTab(sub.id as typeof inspectorTab)}
                          className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-bold ${
                            active
                              ? "bg-[#0f2744] text-white"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                          }`}
                        >
                          <SIcon className="h-3 w-3" />
                          {sub.label}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    type="button"
                    onClick={() => handleDownloadAttachment("json")}
                    disabled={downloadingFile}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    <Download className="h-3 w-3" />
                    Muat Turun Dossier JSON
                  </button>
                </div>
              </div>

              {/* Isi Kandungan Pemeriksa */}
              <div className="space-y-3 p-4 text-xs">
                {/* Kad Lampiran Fail Asal */}
                {activeDetail.file_attachment && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-1.5 font-extrabold text-slate-900">
                          <Paperclip className="h-3.5 w-3.5 text-amber-700" />
                          {activeDetail.file_attachment.original_filename}
                        </div>
                        <div className="mt-0.5 text-[11px] text-slate-600">
                          {activeDetail.file_attachment.content_type} •{" "}
                          {formatBytes(activeDetail.file_attachment.size_bytes)} • SHA-256:{" "}
                          <code className="font-mono">
                            {activeDetail.file_attachment.sha256.slice(0, 16)}...
                          </code>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5">
                        {isImageAttachment && activeDetail.file_attachment.is_available && (
                          <button
                            type="button"
                            onClick={handlePreviewImage}
                            disabled={loadingPreview}
                            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[11px] font-bold text-slate-800 hover:bg-slate-50"
                          >
                            {loadingPreview ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Eye className="h-3 w-3" />
                            )}
                            Pratonton Imej
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => handleDownloadAttachment("attachment")}
                          disabled={downloadingFile || !activeDetail.file_attachment.is_available}
                          className="inline-flex items-center gap-1 rounded-lg bg-[#0f2744] px-2.5 py-1.5 text-[11px] font-bold text-white hover:bg-slate-800 disabled:opacity-50"
                        >
                          {downloadingFile ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Download className="h-3 w-3" />
                          )}
                          Muat Turun Fail Asal
                        </button>
                      </div>
                    </div>

                    {previewUrl && (
                      <div className="rounded-lg border border-slate-200 bg-white p-2">
                        <img
                          src={previewUrl}
                          alt={activeDetail.file_attachment.original_filename}
                          className="max-h-64 w-auto rounded object-contain mx-auto"
                        />
                      </div>
                    )}
                  </div>
                )}

                {inspectorTab === "content" && (
                  <div className="space-y-3">
                    {/* Profil Pegawai jika Kategori USER_REGISTER */}
                    {activeDetail.category === "USER_REGISTER" && activeDetail.user_snapshot && (
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3">
                        <div className="mb-2 text-[11px] font-extrabold uppercase text-emerald-900">
                          Butiran Rekod Pendaftaran / Profil Pegawai
                        </div>
                        <dl className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 text-[11px]">
                          <div>
                            <dt className="text-slate-500">Nama Penuh</dt>
                            <dd className="font-bold text-slate-900">
                              {activeDetail.user_snapshot.full_name || "-"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500">E-mel Rasmi</dt>
                            <dd className="font-bold text-slate-900">
                              {activeDetail.user_snapshot.email || "-"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500">Jawatan &amp; Gred SSPA</dt>
                            <dd className="font-semibold text-slate-800">
                              {activeDetail.user_snapshot.designation || "-"} (Gred{" "}
                              {activeDetail.user_snapshot.grade || "-"})
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500">No. Kad Kuasa KKM</dt>
                            <dd className="font-mono font-semibold text-slate-800">
                              {activeDetail.user_snapshot.kkm_authority_card_no || "-"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500">Pejabat Kesihatan / JKN</dt>
                            <dd className="font-semibold text-slate-800">
                              {activeDetail.user_snapshot.district_pkd || "-"} (
                              {activeDetail.user_snapshot.state_jkn || "-"})
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500">No. K/P Pegawai</dt>
                            <dd className="font-mono text-slate-800">
                              {showRawPii
                                ? activeDetail.user_snapshot.ic_number || "-"
                                : activeDetail.user_snapshot.ic_number
                                ? `${activeDetail.user_snapshot.ic_number.slice(0, 6)}-**-**${activeDetail.user_snapshot.ic_number.slice(-2)}`
                                : "-"}
                            </dd>
                          </div>
                        </dl>
                      </div>
                    )}

                    {/* Input / Soalan / Teks Dokumen */}
                    {(activeDetail.raw_input_text || activeDetail.redacted_input_text) && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                        <div className="mb-1.5 flex items-center justify-between">
                          <span className="text-[11px] font-extrabold uppercase text-slate-700">
                            {activeDetail.category === "ADVISOR_QA"
                              ? "Soalan / Input Pengguna"
                              : "Teks Input / Kandungan Dokumen Diekstrak"}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              handleCopyText(
                                "input",
                                showRawPii
                                  ? activeDetail.raw_input_text
                                  : activeDetail.redacted_input_text
                              )
                            }
                            className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 text-[10px] font-bold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-100"
                          >
                            {copiedId === "input" ? (
                              <Check className="h-3 w-3 text-emerald-600" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                            Salin
                          </button>
                        </div>
                        <div className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-2.5 text-xs leading-relaxed text-slate-800 ring-1 ring-slate-200">
                          {showRawPii
                            ? activeDetail.raw_input_text
                            : renderHighlightedTokens(activeDetail.redacted_input_text)}
                        </div>
                      </div>
                    )}

                    {/* Jawapan / Rumusan Analisis */}
                    {(activeDetail.raw_response_text || activeDetail.redacted_response_text) && (
                      <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-3">
                        <div className="mb-1.5 text-[11px] font-extrabold uppercase text-indigo-900">
                          Jawapan AI / Ringkasan Keputusan Analisis
                        </div>
                        <div className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-2.5 text-xs leading-relaxed text-slate-800 ring-1 ring-indigo-100">
                          {showRawPii
                            ? activeDetail.raw_response_text
                            : renderHighlightedTokens(activeDetail.redacted_response_text)}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {inspectorTab === "json" && (
                  <div className="rounded-xl border border-slate-200 bg-slate-900 p-3 text-slate-100">
                    <div className="mb-2 flex items-center justify-between text-[11px]">
                      <span className="font-bold text-amber-300">
                        {showRawPii
                          ? "JSON Penuh (Teks Asal — Dev Sahaja)"
                          : "JSON Versi PDPA Disamarkan"}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          handleCopyText(
                            "json",
                            JSON.stringify(
                              showRawPii
                                ? activeDetail.analysis_json
                                : activeDetail.redacted_analysis_json,
                              null,
                              2
                            )
                          )
                        }
                        className="inline-flex items-center gap-1 rounded bg-white/10 px-2 py-0.5 text-[10px] font-bold text-white hover:bg-white/20"
                      >
                        {copiedId === "json" ? (
                          <Check className="h-3 w-3 text-emerald-300" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                        Salin JSON
                      </button>
                    </div>
                    <pre className="max-h-80 overflow-auto text-[11px] font-mono leading-relaxed text-emerald-200">
                      {JSON.stringify(
                        showRawPii
                          ? activeDetail.analysis_json
                          : activeDetail.redacted_analysis_json,
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}

                {inspectorTab === "metadata" && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-[11px] space-y-2">
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <div>
                        <span className="text-slate-500">Enjin Storan:</span>{" "}
                        <strong className="font-mono text-slate-900">
                          {activeDetail.storage_backend}
                        </strong>
                      </div>
                      <div>
                        <span className="text-slate-500">Status Penyelarasan:</span>{" "}
                        <strong className="font-mono text-slate-900">
                          {activeDetail.storage_metadata.sync_status || "-"}
                        </strong>
                      </div>
                      <div>
                        <span className="text-slate-500">Nama Bucket S3:</span>{" "}
                        <strong className="font-mono text-slate-900">
                          {activeDetail.storage_metadata.bucket_name || "(DB + Local Vault)"}
                        </strong>
                      </div>
                      <div>
                        <span className="text-slate-500">Laluan Endpoint Sumber:</span>{" "}
                        <strong className="font-mono text-slate-900">
                          {activeDetail.storage_metadata.source_endpoint || "-"}
                        </strong>
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-500">Kunci Objek Bucket / Fail:</span>
                      <div className="mt-0.5 rounded bg-white px-2 py-1 font-mono text-[10px] text-slate-800 ring-1 ring-slate-200 break-all">
                        {activeDetail.storage_metadata.object_key || "-"}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-500">SHA-256 Rekod JSON:</span>
                      <div className="mt-0.5 rounded bg-white px-2 py-1 font-mono text-[10px] text-slate-800 ring-1 ring-slate-200 break-all">
                        {activeDetail.storage_metadata.payload_sha256 || "-"}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
