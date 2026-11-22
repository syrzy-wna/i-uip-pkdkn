"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRightCircle,
  Ban,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  Database,
  Edit3,
  FileCheck2,
  FileText,
  FileUp,
  Filter,
  Gavel,
  Loader2,
  RefreshCw,
  Save,
  Scale,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  WifiOff,
} from "lucide-react";
import {
  fetchLegalRegistry,
  fetchLegalSnapshot,
  ingestGazettePdf,
  purgeAdvisorQaCache,
  updateMasterOffence,
  verifyGazetteStatuteOrOffence,
} from "@/lib/api";
import type {
  LegalCoverageReport,
  LegalLibrarySnapshot,
  MasterOffenceRecord,
  OfficerProfile,
  StatuteRegistryRecord,
  StatuteSectionVerbatim,
  TargetOffenderCategory,
} from "@/lib/types";

const OFFLINE_CACHE_KEY = "uip_offline_legal_library_v2";

interface LegalDirectoryPanelProps {
  authToken: string | null;
  officer: OfficerProfile | null;
  isDevAdmin: boolean;
  onApplyOffenceToCase: (draftText: string, aktaCode: string, bukaIp: boolean) => void;
}

type DirectorySubTab = "offences" | "statutes" | "repealed" | "admin";

const OFFENDER_CATEGORY_LABELS: Record<TargetOffenderCategory | "SEMUA", string> = {
  SEMUA: "Semua Kategori Pelaku",
  INDIVIDU: "Individu Dewasa",
  OBD_BAWAH_18: "Orang Belum Dewasa (OBD < 18 Tahun)",
  PERTUBUHAN_PERBADANAN: "Pertubuhan Perbadanan / Syarikat (Sdn. Bhd.)",
  PENGENDALI_MAKANAN: "Pengendali Makanan",
  TUAN_PUNYA_PREMIS: "Tuan Punya / Penghuni Premis",
  PENJUAL_PENGILANG: "Penjual / Pengilang / Pengimport",
};

const CORE_STATUTE_FILE_GUIDE = [
  {
    code: "AKTA_852.pdf",
    statute_id: "AKTA_852",
    akta_code: "Akta 852",
    title: "Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
  },
  {
    code: "AKTA_852_PERINTAH_LARANGAN_2024.pdf",
    statute_id: "AKTA_852_PERINTAH_LARANGAN_2024",
    akta_code: "Akta 852",
    title: "Perintah Pengisytiharan Kawasan atau Tempat Larangan Merokok 2024 [P.U. (A) 257/2024]",
  },
  {
    code: "AKTA_852_PERATURAN_TANDA_2024.pdf",
    statute_id: "AKTA_852_PERATURAN_TANDA_2024",
    akta_code: "Akta 852",
    title: "Peraturan-Peraturan Tanda Amaran Larangan Merokok 2024 [P.U. (A) 258/2024]",
  },
  {
    code: "AKTA_852_PERATURAN_KOMPAUN_2024.pdf",
    statute_id: "AKTA_852_PERATURAN_KOMPAUN_2024",
    akta_code: "Akta 852",
    title: "Peraturan-Peraturan Pengkompaunan Kesalahan 2024 [P.U. (A) 259/2024]",
  },
  {
    code: "AKTA_852_PERATURAN_JUALAN_2024.pdf",
    statute_id: "AKTA_852_PERATURAN_JUALAN_2024",
    akta_code: "Akta 852",
    title: "Peraturan-Peraturan Kawalan Penjualan 2024 [P.U. (A) 260/2024]",
  },
  {
    code: "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024.pdf",
    statute_id: "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
    akta_code: "Akta 852",
    title: "Peraturan-Peraturan Pembungkusan dan Pelabelan 2024 [P.U. (A) 261/2024]",
  },
  {
    code: "AKTA_852_PERATURAN_PENDAFTARAN_2024.pdf",
    statute_id: "AKTA_852_PERATURAN_PENDAFTARAN_2024",
    akta_code: "Akta 852",
    title: "Peraturan-Peraturan Pendaftaran Produk Tembakau/Merokok 2024 [P.U. (A) 262/2024]",
  },
  {
    code: "AKTA_852_PERINTAH_MAKMAL_2024.pdf",
    statute_id: "AKTA_852_PERINTAH_MAKMAL_2024",
    akta_code: "Akta 852",
    title: "Perintah Makmal yang Diluluskan 2024 [P.U. (A) 263/2024]",
  },
  {
    code: "AKTA_852_PERATURAN_NOTIS_S47_2024.pdf",
    statute_id: "AKTA_852_PERATURAN_NOTIS_S47_2024",
    akta_code: "Akta 852",
    title: "Peraturan-Peraturan Notis di Bawah Seksyen 47 2024 [P.U. (A) 264/2024]",
  },
  {
    code: "AKTA_281.pdf",
    statute_id: "AKTA_281",
    akta_code: "Akta 281",
    title: "Akta Makanan 1983 [Akta 281]",
  },
  {
    code: "AKTA_281_PINDAAN_A1702_2024.pdf",
    statute_id: "AKTA_281_PINDAAN_2024",
    akta_code: "Akta 281",
    title: "Akta Makanan (Pindaan) 2024 [Akta A1702]",
  },
  {
    code: "PPKM_2009.pdf",
    statute_id: "PPKM_2009",
    akta_code: "Akta 281",
    title: "Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
  },
  {
    code: "PPM_1985.pdf",
    statute_id: "PPM_1985",
    akta_code: "Akta 281",
    title: "Peraturan-Peraturan Makanan 1985 [P.U. (A) 437/1985 — Kemaskini Ogos 2026]",
  },
  {
    code: "AKTA_154.pdf",
    statute_id: "AKTA_154",
    akta_code: "Akta 154",
    title: "Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
  },
  {
    code: "AKTA_342.pdf",
    statute_id: "AKTA_342",
    akta_code: "Akta 342",
    title: "Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
  },
  {
    code: "AKTA_342_PINDAAN_A1742_2025.pdf",
    statute_id: "AKTA_342_PINDAAN_2025",
    akta_code: "Akta 342",
    title: "Akta Pencegahan dan Pengawalan Penyakit Berjangkit (Pindaan) 2025 [Akta A1742]",
  },
  {
    code: "AKTA_342_PERATURAN_KOMPAUN_2025.pdf",
    statute_id: "AKTA_342_PERATURAN_KOMPAUN_2025",
    akta_code: "Akta 342",
    title: "Peraturan-Peraturan Pengkompaunan Kesalahan (Pindaan) 2025 [P.U. (A) 139/2025]",
  },
  {
    code: "AKTA_593.pdf",
    statute_id: "AKTA_593",
    akta_code: "Akta 593",
    title: "Kanun Tatacara Jenayah [Akta 593]",
  },
  {
    code: "AKTA_56.pdf",
    statute_id: "AKTA_56",
    akta_code: "Akta 56",
    title: "Akta Keterangan 1950 [Akta 56] (Seksyen 90A–90C)",
  },
  {
    code: "AKTA_611.pdf",
    statute_id: "AKTA_611",
    akta_code: "Akta 611",
    title: "Akta Kanak-Kanak 2001 [Akta 611] (Cetakan Semula 1 Julai 2023)",
  },
];

export default function LegalDirectoryPanel({
  authToken,
  isDevAdmin,
  onApplyOffenceToCase,
}: LegalDirectoryPanelProps) {
  const [subTab, setSubTab] = useState<DirectorySubTab>("offences");
  const [snapshot, setSnapshot] = useState<LegalLibrarySnapshot | null>(null);
  const [coverage, setCoverage] = useState<LegalCoverageReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [offlineMode, setOfflineMode] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionToast, setActionToast] = useState<string | null>(null);

  // Tapisan Direktori Kesalahan
  const [aktaFilter, setAktaFilter] = useState<string>("Semua");
  const [categoryFilter, setCategoryFilter] = useState<TargetOffenderCategory | "SEMUA">(
    "SEMUA"
  );
  const [compoundFilter, setCompoundFilter] = useState<
    "SEMUA" | "BOLEH_KOMPAUN" | "TERUS_MAHKAMAH"
  >("SEMUA");
  const [offenceSearch, setOffenceSearch] = useState<string>("");
  const [selectedOffenceId, setSelectedOffenceId] = useState<string>("");
  const [copiedCharge, setCopiedCharge] = useState<boolean>(false);

  // Tapisan Pustaka Akta Verbatim
  const [selectedStatuteId, setSelectedStatuteId] = useState<string>("AKTA_852");
  const [sectionSearch, setSectionSearch] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string>("");

  // Borang Admin: Muat Naik Warta PDF & Sunting Pengecualian
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatuteId, setUploadStatuteId] = useState<string>("AKTA_852");
  const [uploadOfficialTitle, setUploadOfficialTitle] = useState<string>("");
  const [uploadActNumberOrPu, setUploadActNumberOrPu] = useState<string>("");
  const [uploadVerified, setUploadVerified] = useState<boolean>(false);
  const [uploadingPdf, setUploadingPdf] = useState<boolean>(false);

  const [editingOffenceId, setEditingOffenceId] = useState<string | null>(null);
  const [editingExclusionsText, setEditingExclusionsText] = useState<string>("");
  const [savingOffenceEdit, setSavingOffenceEdit] = useState<boolean>(false);

  const showToast = useCallback((msg: string) => {
    setActionToast(msg);
    window.setTimeout(() => {
      setActionToast((prev) => (prev === msg ? null : prev));
    }, 4200);
  }, []);

  const loadLegalLibrary = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [snap, reg] = await Promise.all([
        fetchLegalSnapshot(authToken),
        fetchLegalRegistry(authToken),
      ]);
      setSnapshot(snap);
      setCoverage(reg);
      setOfflineMode(false);
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(OFFLINE_CACHE_KEY, JSON.stringify(snap));
        } catch {
          // Abaikan jika kuota localStorage penuh
        }
      }
      if (!selectedOffenceId && snap.master_offences_matrix.length > 0) {
        setSelectedOffenceId(snap.master_offences_matrix[0].offence_id);
      }
    } catch (err) {
      if (typeof window !== "undefined") {
        const cachedRaw = window.localStorage.getItem(OFFLINE_CACHE_KEY);
        if (cachedRaw) {
          try {
            const parsed = JSON.parse(cachedRaw) as LegalLibrarySnapshot;
            setSnapshot(parsed);
            setOfflineMode(true);
            if (!selectedOffenceId && parsed.master_offences_matrix.length > 0) {
              setSelectedOffenceId(parsed.master_offences_matrix[0].offence_id);
            }
            return;
          } catch {
            // Teruskan ke ralat
          }
        }
      }
      setErrorMsg(
        err instanceof Error
          ? `Gagal memuatkan Pustaka Akta: ${err.message}`
          : "Gagal memuatkan Pustaka Akta."
      );
    } finally {
      setLoading(false);
    }
  }, [authToken, selectedOffenceId]);

  useEffect(() => {
    void loadLegalLibrary();
  }, [loadLegalLibrary]);

  // Tapis Senarai Kesalahan (master_offences_matrix)
  const filteredOffences = useMemo(() => {
    const list = snapshot?.master_offences_matrix || [];
    const q = offenceSearch.trim().toLowerCase();
    return list.filter((off) => {
      const canonicalAct = off.canonical_akta_code || off.statute_id.replace("_", " ");
      if (aktaFilter !== "Semua") {
        if (aktaFilter === "PPKM 2009" && off.statute_id !== "PPKM_2009") return false;
        else if (aktaFilter === "PPM 1985" && off.statute_id !== "PPM_1985") return false;
        else if (
          aktaFilter !== "PPKM 2009" &&
          aktaFilter !== "PPM 1985" &&
          !canonicalAct.toLowerCase().includes(aktaFilter.toLowerCase()) &&
          !off.statute_id.toLowerCase().includes(aktaFilter.toLowerCase().replace(" ", "_"))
        ) {
          return false;
        }
      }
      if (categoryFilter !== "SEMUA" && off.target_offender !== categoryFilter) {
        return false;
      }
      if (compoundFilter === "BOLEH_KOMPAUN" && !off.compound_info?.is_compoundable) {
        return false;
      }
      if (compoundFilter === "TERUS_MAHKAMAH" && off.compound_info?.is_compoundable) {
        return false;
      }
      if (q) {
        const hay = [
          off.offence_id,
          canonicalAct,
          off.offence_section,
          off.penalty_section,
          off.offence_title,
          off.charge_sheet_template_bm,
          ...off.mandatory_elements.map((e) => `${e.description} ${e.must_prove}`),
          ...off.explicit_exclusions_and_traps,
          ...(off.read_together_with || []),
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [snapshot, aktaFilter, categoryFilter, compoundFilter, offenceSearch]);

  const activeOffence: MasterOffenceRecord | null = useMemo(() => {
    if (!filteredOffences.length) return null;
    return (
      filteredOffences.find((o) => o.offence_id === selectedOffenceId) || filteredOffences[0]
    );
  }, [filteredOffences, selectedOffenceId]);

  const linkedVerbatimForActiveOffence: StatuteSectionVerbatim[] = useMemo(() => {
    if (!activeOffence || !snapshot) return [];
    const byDocId = new Map(
      snapshot.statute_sections_verbatim.map((sec) => [sec.doc_id, sec])
    );
    const linked = (activeOffence.source_section_doc_ids || [])
      .map((id) => byDocId.get(id))
      .filter((sec): sec is StatuteSectionVerbatim => Boolean(sec));
    if (linked.length > 0) return linked;
    return snapshot.statute_sections_verbatim.filter(
      (sec) =>
        sec.statute_id === activeOffence.statute_id &&
        (activeOffence.offence_section.includes(sec.section_code) ||
          activeOffence.penalty_section.includes(sec.section_code))
    );
  }, [activeOffence, snapshot]);

  // Tapis Seksyen Verbatim untuk Tab Pustaka Akta
  const activeStatuteMeta: StatuteRegistryRecord | null = useMemo(() => {
    if (!snapshot) return null;
    return (
      snapshot.statutes_registry.find((s) => s.statute_id === selectedStatuteId) ||
      snapshot.statutes_registry[0] ||
      null
    );
  }, [snapshot, selectedStatuteId]);

  const sectionsForSelectedStatute = useMemo(() => {
    if (!snapshot || !activeStatuteMeta) return [];
    const q = sectionSearch.trim().toLowerCase();
    return snapshot.statute_sections_verbatim.filter((sec) => {
      if (sec.statute_id !== activeStatuteMeta.statute_id) return false;
      if (q) {
        const hay = [
          sec.doc_id,
          sec.section_code,
          sec.section_heading,
          sec.part_number,
          sec.part_title,
          sec.verbatim_text_bm,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [snapshot, activeStatuteMeta, sectionSearch]);

  const groupedSectionsByPart = useMemo(() => {
    const groups: Array<{
      partKey: string;
      partLabel: string;
      sections: StatuteSectionVerbatim[];
    }> = [];
    const map = new Map<string, StatuteSectionVerbatim[]>();
    const labels = new Map<string, string>();

    for (const sec of sectionsForSelectedStatute) {
      const pNum = sec.part_number || "UMUM";
      const pTitle = sec.part_title || "Peruntukan Statutori";
      const key = `${pNum}::${pTitle}`;
      if (!map.has(key)) {
        map.set(key, []);
        labels.set(key, sec.part_number ? `${sec.part_number} — ${pTitle}` : pTitle);
      }
      map.get(key)!.push(sec);
    }

    for (const [key, secs] of map.entries()) {
      groups.push({
        partKey: key,
        partLabel: labels.get(key) || key,
        sections: secs,
      });
    }
    return groups;
  }, [sectionsForSelectedStatute]);

  const activeSectionDetail: StatuteSectionVerbatim | null = useMemo(() => {
    if (!sectionsForSelectedStatute.length) return null;
    return (
      sectionsForSelectedStatute.find((s) => s.doc_id === selectedDocId) ||
      sectionsForSelectedStatute[0]
    );
  }, [sectionsForSelectedStatute, selectedDocId]);

  const handleCopyChargeTemplate = (text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedCharge(true);
    window.setTimeout(() => setCopiedCharge(false), 2000);
  };

  const handleVerifyStatute = async (statuteId: string, verified: boolean) => {
    try {
      await verifyGazetteStatuteOrOffence({
        statuteId,
        verifiedByAdmin: verified,
        authToken,
      });
      showToast(
        `Status pengesahan Warta ${statuteId} dikemas kini (${
          verified ? "DISAHKAN WARTA AGC" : "SEMAKAN DRAF"
        }).`
      );
      await loadLegalLibrary();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal mengesahkan Warta.");
    }
  };

  const handleVerifyOffence = async (offenceId: string, verified: boolean) => {
    try {
      await verifyGazetteStatuteOrOffence({
        offenceId,
        verifiedByAdmin: verified,
        authToken,
      });
      showToast(`Rekod kesalahan ${offenceId} telah disahkan Warta!`);
      await loadLegalLibrary();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal mengesahkan rekod kesalahan.");
    }
  };

  const handleSaveOffenceExclusions = async (offenceId: string) => {
    setSavingOffenceEdit(true);
    try {
      const lines = editingExclusionsText
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean);
      await updateMasterOffence(
        offenceId,
        {
          explicit_exclusions_and_traps: lines,
          verified_status: "VERIFIED_AGC",
        },
        authToken
      );
      setEditingOffenceId(null);
      showToast(`Pengecualian & Perangkap untuk ${offenceId} berjaya disimpan & disahkan!`);
      await loadLegalLibrary();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal menyimpan suntingan kesalahan.");
    } finally {
      setSavingOffenceEdit(false);
    }
  };

  const handleUploadGazettePdf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setErrorMsg("Sila pilih fail PDF atau TXT Warta Kerajaan Persekutuan (AGC) terlebih dahulu.");
      return;
    }
    setUploadingPdf(true);
    setErrorMsg(null);
    try {
      const res = await ingestGazettePdf({
        file: uploadFile,
        statuteId: uploadStatuteId,
        officialTitleBm: uploadOfficialTitle || undefined,
        actNumberOrPu: uploadActNumberOrPu || undefined,
        verifiedByAdmin: uploadVerified,
        authToken,
      });
      setUploadFile(null);
      const ing = res.legal_library_ingest;
      showToast(
        `Warta ${ing.statute_id} berjaya diindeks (${ing.sections_extracted} seksyen verbatim, ${ing.new_offences_swept} kesalahan baharu disapu, versi ${ing.statute_library_version}).`
      );
      await loadLegalLibrary();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal memproses fail Warta AGC.");
    } finally {
      setUploadingPdf(false);
    }
  };

  const handlePurgeQaCache = async () => {
    try {
      const res = await purgeAdvisorQaCache(undefined, authToken);
      showToast(
        `${res.stale_records_marked} rekod cache Koleksi Q&A lama ditandakan STALE (Versi Pustaka: ${res.statute_library_version}).`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal membersihkan cache Koleksi Q&A.");
    }
  };

  return (
    <div className="mx-auto max-w-[1600px] space-y-4">
      {/* Header Utama Direktori Kesalahan & Pustaka Akta Verbatim */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#0f2744] text-amber-300 shadow-sm">
              <Scale className="h-5 w-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-extrabold text-slate-900 sm:text-lg">
                  Direktori Kesalahan &amp; Pustaka Akta Penuh (Zero-Hallucination Legal Engine)
                </h2>
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-extrabold text-emerald-900">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" />
                  Closed-Book Verbatim AGC • {snapshot?.statute_library_version || "v2"}
                </span>
                {offlineMode && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-900">
                    <WifiOff className="h-3 w-3" /> Mod Cache Luar Talian
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-600">
                Rujukan terus teks verbatim Warta Kerajaan Persekutuan (AGC), jadual unsur mandatori setiap kesalahan, pengecualian undang-undang, dan senarai hitam peruntukan terbatal.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-700">
              <Database className="h-3.5 w-3.5 text-blue-700" />
              <span>{snapshot?.statute_sections_verbatim.length ?? 0} Seksyen Verbatim</span>
              <span>•</span>
              <span>{snapshot?.master_offences_matrix.length ?? 0} Jadual Kesalahan</span>
            </div>

            <button
              type="button"
              onClick={() => void loadLegalLibrary()}
              disabled={loading}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Segar Semula
            </button>
          </div>
        </div>

        {/* Bar Navigasi Sub-Tab */}
        <div className="mt-4 flex flex-wrap gap-1.5 border-t border-slate-200 pt-3">
          <button
            type="button"
            onClick={() => setSubTab("offences")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-extrabold transition ${
              subTab === "offences"
                ? "bg-[#0f2744] text-white shadow-sm"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <Gavel className="h-4 w-4 text-amber-300" />
            <span>1. Direktori Semua Kesalahan ({snapshot?.master_offences_matrix.length ?? 0})</span>
          </button>

          <button
            type="button"
            onClick={() => setSubTab("statutes")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-extrabold transition ${
              subTab === "statutes"
                ? "bg-[#0f2744] text-white shadow-sm"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <BookOpen className="h-4 w-4 text-sky-300" />
            <span>2. Pustaka Akta Verbatim ({snapshot?.statutes_registry.length ?? 0} Akta/Peraturan)</span>
          </button>

          <button
            type="button"
            onClick={() => setSubTab("repealed")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-extrabold transition ${
              subTab === "repealed"
                ? "bg-rose-800 text-white shadow-sm"
                : "bg-rose-50 text-rose-900 hover:bg-rose-100"
            }`}
          >
            <Ban className="h-4 w-4" />
            <span>
              3. Senarai Hitam Undang-Undang Lapuk ({snapshot?.repealed_and_blocked_provisions.length ?? 0})
            </span>
          </button>

          <button
            type="button"
            onClick={() => setSubTab("admin")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-extrabold transition ${
              subTab === "admin"
                ? "bg-indigo-700 text-white shadow-sm"
                : "bg-indigo-50 text-indigo-900 hover:bg-indigo-100"
            }`}
          >
            <FileUp className="h-4 w-4" />
            <span>
              4. Pustaka Akta &amp; Semakan Kesalahan {isDevAdmin ? "(Admin)" : "(Audit Liputan)"}
            </span>
          </button>
        </div>
      </section>

      {actionToast && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs font-bold text-emerald-950 shadow-sm">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>{actionToast}</span>
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-bold text-rose-950 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertOctagon className="h-4 w-4 shrink-0 text-rose-600" />
            <span>{errorMsg}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            className="rounded px-2 py-0.5 text-xs font-extrabold hover:bg-rose-100"
          >
            Tutup
          </button>
        </div>
      )}

      {loading && !snapshot ? (
        <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white p-12 text-xs font-bold text-slate-600">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-blue-700" />
          Memuatkan Pustaka Akta Verbatim &amp; Jadual Induk Kesalahan...
        </div>
      ) : null}

      {/* ===================================================================== */}
      {/* SUB-TAB 1: DIREKTORI SEMUA KESALAHAN (MASTER OFFENCES MATRIX)         */}
      {/* ===================================================================== */}
      {subTab === "offences" && snapshot && (
        <div className="space-y-4">
          {/* Bar Tapisan & Carian Kesalahan */}
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <div>
                <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                  1. Tapis Mengikut Akta / Peraturan
                </label>
                <select
                  aria-label="Tapis Akta Kesalahan"
                  value={aktaFilter}
                  onChange={(e) => setAktaFilter(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800"
                >
                  <option value="Semua">Semua Akta &amp; Peraturan KKM</option>
                  <option value="Akta 852">Akta 852 (Kawalan Produk Merokok 2024)</option>
                  <option value="Akta 281">Akta 281 (Akta Makanan 1983 &amp; Peraturan)</option>
                  <option value="PPKM 2009">PPKM 2009 [P.U. (A) 95/2009]</option>
                  <option value="PPM 1985">Peraturan-Peraturan Makanan 1985</option>
                  <option value="Akta 154">Akta 154 (Pemusnahan Serangga / Aedes)</option>
                  <option value="Akta 342">Akta 342 (Penyakit Berjangkit 1988)</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                  2. Kategori Pelaku / Subjek
                </label>
                <select
                  aria-label="Tapis Kategori Pelaku"
                  value={categoryFilter}
                  onChange={(e) =>
                    setCategoryFilter(e.target.value as TargetOffenderCategory | "SEMUA")
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800"
                >
                  {Object.entries(OFFENDER_CATEGORY_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                  3. Status Kompaun / Mahkamah
                </label>
                <select
                  aria-label="Tapis Status Kompaun"
                  value={compoundFilter}
                  onChange={(e) =>
                    setCompoundFilter(
                      e.target.value as "SEMUA" | "BOLEH_KOMPAUN" | "TERUS_MAHKAMAH"
                    )
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800"
                >
                  <option value="SEMUA">Semua (Kompaun &amp; Terus Mahkamah)</option>
                  <option value="BOLEH_KOMPAUN">Boleh Dikompaun Sahaja</option>
                  <option value="TERUS_MAHKAMAH">
                    Tidak Boleh Kompaun (Terus Buka IP / Mahkamah)
                  </option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                  4. Cari Seksyen / Kata Kunci
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={offenceSearch}
                    onChange={(e) => setOffenceSearch(e.target.value)}
                    placeholder="Cth: Seksyen 17, beg, tifoid, jentik-jentik..."
                    className="w-full rounded-xl border border-slate-300 bg-slate-50/60 py-2 pl-8 pr-3 text-xs font-medium text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Paparan 2 Lajur: Senarai Kesalahan Kiri + Perincian Verbatim Kanan */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Lajur Kiri: Senarai Kesalahan */}
            <div className="space-y-2 lg:col-span-5">
              <div className="flex items-center justify-between px-1 text-xs font-extrabold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <Filter className="h-3.5 w-3.5 text-blue-700" />
                  Hasil Tapisan ({filteredOffences.length} Kesalahan)
                </span>
              </div>

              <div className="max-h-[720px] space-y-2 overflow-y-auto pr-1">
                {filteredOffences.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-xs text-slate-500">
                    Tiada kesalahan ditemui untuk tapisan ini. Cuba tukar tapisan Akta atau Kategori Pelaku.
                  </div>
                ) : (
                  filteredOffences.map((off) => {
                    const isSelected = activeOffence?.offence_id === off.offence_id;
                    const isComp = Boolean(off.compound_info?.is_compoundable);
                    const actBadge = off.canonical_akta_code || off.statute_id;
                    return (
                      <button
                        key={off.offence_id}
                        type="button"
                        onClick={() => setSelectedOffenceId(off.offence_id)}
                        className={`flex w-full flex-col items-start rounded-2xl border p-3.5 text-left transition ${
                          isSelected
                            ? "border-blue-600 bg-blue-50/70 ring-1 ring-blue-600"
                            : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex w-full flex-wrap items-center justify-between gap-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className="rounded-md bg-[#0f2744] px-2 py-0.5 text-[10px] font-extrabold text-white">
                              {actBadge}
                            </span>
                            <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-700">
                              {off.offence_id}
                            </span>
                          </div>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
                              isComp
                                ? "bg-emerald-100 text-emerald-900"
                                : "bg-amber-100 text-amber-950"
                            }`}
                          >
                            {isComp ? "Boleh Kompaun" : "Terus Mahkamah (IP)"}
                          </span>
                        </div>

                        <div className="mt-2 text-xs font-extrabold text-slate-900">
                          {off.offence_title}
                        </div>

                        <div className="mt-1 text-[11px] font-semibold text-blue-900">
                          Pertuduhan: {off.offence_section}
                        </div>
                        <div className="mt-0.5 text-[11px] text-slate-600">
                          Hukuman: {off.penalty_section}
                        </div>

                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                            {off.target_offender}
                          </span>
                          {off.verified_status !== "VERIFIED_AGC" ? (
                            <span className="inline-flex items-center gap-1 rounded-full border border-yellow-300 bg-yellow-100 px-2 py-0.5 text-[10px] font-extrabold text-yellow-900">
                              <AlertTriangle className="h-3 w-3 text-yellow-700" />
                              Perlu Semakan Manual Warta AGC
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-extrabold text-emerald-900">
                              <CheckCircle2 className="h-3 w-3" /> Disahkan Warta AGC
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Lajur Kanan: Perincian Penuh Kesalahan */}
            <div className="lg:col-span-7">
              {!activeOffence ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
                  Pilih mana-mana kesalahan di sebelah kiri untuk melihat teks verbatim Warta, jadual unsur mandatori, pengecualian, dan templat pertuduhan Borang 114.
                </div>
              ) : (
                <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                  {/* Header Kesalahan & Butang Tindakan */}
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-extrabold text-white">
                          {activeOffence.canonical_akta_code || activeOffence.statute_id}
                        </span>
                        <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs font-bold text-slate-700">
                          {activeOffence.offence_id}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-extrabold ${
                            activeOffence.verified_status === "VERIFIED_AGC"
                              ? "bg-emerald-100 text-emerald-900"
                              : "border border-yellow-300 bg-yellow-100 text-yellow-900"
                          }`}
                        >
                          {activeOffence.verified_status === "VERIFIED_AGC" ? (
                            <>
                              <CheckCircle2 className="h-3.5 w-3.5" /> Disahkan Warta AGC
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="h-3.5 w-3.5 text-yellow-700" /> Perlu Semakan Manual Warta AGC
                            </>
                          )}
                        </span>
                      </div>
                      <h3 className="text-base font-extrabold text-slate-900">
                        {activeOffence.offence_title}
                      </h3>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          onApplyOffenceToCase(
                            activeOffence.charge_sheet_template_bm,
                            activeOffence.canonical_akta_code || "Akta 852",
                            true
                          )
                        }
                        className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-blue-700"
                      >
                        <FileText className="h-4 w-4" />
                        Hantar ke Bina Fail IP / Borang 114
                      </button>

                      {activeOffence.compound_info?.is_compoundable && (
                        <button
                          type="button"
                          onClick={() =>
                            onApplyOffenceToCase(
                              activeOffence.charge_sheet_template_bm,
                              activeOffence.canonical_akta_code || "Akta 852",
                              false
                            )
                          }
                          className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-emerald-700"
                        >
                          <FileCheck2 className="h-4 w-4" />
                          Isi Notis Kompaun
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 1. Ringkasan Seksyen, Denda & Kompaun */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-3.5 text-xs">
                      <div className="text-[11px] font-extrabold uppercase text-blue-900">
                        Seksyen Kesalahan &amp; Seksyen Hukuman
                      </div>
                      <div className="mt-1 font-extrabold text-slate-900">
                        Caj: {activeOffence.offence_section}
                      </div>
                      <div className="mt-1 font-bold text-indigo-900">
                        Hukuman: {activeOffence.penalty_section}
                      </div>
                      <div className="mt-1 text-slate-700">
                        {activeOffence.penalty_first_offence?.verbatim_penalty}
                      </div>
                    </div>

                    <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5 text-xs">
                      <div className="text-[11px] font-extrabold uppercase text-emerald-900">
                        Had Denda &amp; Status Kompaun
                      </div>
                      <div className="mt-1 font-extrabold text-slate-900">
                        Status:{" "}
                        {activeOffence.compound_info?.is_compoundable
                          ? "BOLEH DIKOMPAUN"
                          : "TIDAK BOLEH DIKOMPAUN (TERUS MAHKAMAH)"}
                      </div>
                      <div className="mt-1 text-slate-700">
                        <strong>Punca Kuasa Kompaun:</strong>{" "}
                        {activeOffence.compound_info?.compound_authority_section ||
                          activeOffence.compound_info?.compound_regulation_ref ||
                          "Tiada Kompaun"}
                      </div>
                      <div className="mt-1 text-slate-700">
                        <strong>Denda Maksimum:</strong>{" "}
                        {activeOffence.penalty_first_offence?.max_fine_rm
                          ? `RM ${activeOffence.penalty_first_offence.max_fine_rm.toLocaleString("en-MY")}`
                          : "-"}{" "}
                        • <strong>Kompaun:</strong>{" "}
                        {activeOffence.compound_info?.compound_amount_or_limit || "Tiada Kompaun"}
                      </div>
                    </div>
                  </div>

                  {/* 2. Teks Verbatim Warta (statute_sections_verbatim) */}
                  <div className="space-y-2 rounded-xl border border-teal-200 bg-teal-50/30 p-4">
                    <div className="flex items-center justify-between">
                      <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-teal-950">
                        <BookOpen className="h-4 w-4 text-teal-700" />
                        Teks Verbatim Warta Kerajaan Persekutuan (statute_sections_verbatim)
                      </h4>
                      <span className="rounded bg-teal-100 px-2 py-0.5 text-[10px] font-extrabold text-teal-900">
                        100% Aksara-demi-Aksara
                      </span>
                    </div>

                    {linkedVerbatimForActiveOffence.length === 0 ? (
                      <p className="text-xs text-slate-600">
                        Tiada seksyen verbatim dipautkan untuk rekod ini.
                      </p>
                    ) : (
                      <div className="space-y-2.5">
                        {linkedVerbatimForActiveOffence.map((sec) => (
                          <div
                            key={sec.doc_id}
                            className="rounded-lg border border-teal-200/80 bg-white p-3 text-xs"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-extrabold text-teal-900">
                                {sec.statute_id} — {sec.section_code}: {sec.section_heading}
                              </span>
                              <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-600">
                                {sec.doc_id}
                              </span>
                            </div>
                            <p className="mt-1.5 whitespace-pre-line leading-relaxed text-slate-800">
                              {sec.verbatim_text_bm}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 3. Jadual Unsur Mandatori (mandatory_elements) */}
                  <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/50 p-4">
                    <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-slate-900">
                      <CheckCircle2 className="h-4 w-4 text-blue-700" />
                      Unsur Mandatori Kesalahan (Wajib Dibuktikan Semuanya Sebelum Kompaun / Pertuduhan)
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 text-[11px] font-extrabold uppercase text-slate-600">
                            <th className="py-2 pr-3">Bil</th>
                            <th className="py-2 pr-3">Perihal Unsur Mandatori (Actus Reus / Subjek)</th>
                            <th className="py-2">Bukti Wajib</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200/70">
                          {activeOffence.mandatory_elements.map((el) => (
                            <tr key={el.element_no}>
                              <td className="py-2 pr-3 font-mono font-bold text-blue-900">
                                #{el.element_no}
                              </td>
                              <td className="py-2 pr-3 font-medium text-slate-800">
                                {el.description}
                              </td>
                              <td className="py-2 text-[11px] text-slate-600">
                                {el.must_prove}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* 4. Pengecualian Eksplisit & Perangkap Kesilapan (explicit_exclusions_and_traps) */}
                  <div className="space-y-2 rounded-xl border border-rose-200 border-l-4 border-l-rose-600 bg-rose-50/40 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-rose-950">
                        <ShieldAlert className="h-4 w-4 text-rose-700" />
                        Pengecualian Undang-Undang &amp; Perangkap Kesilapan PPKP
                      </h4>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingOffenceId(activeOffence.offence_id);
                          setEditingExclusionsText(
                            activeOffence.explicit_exclusions_and_traps.join("\n")
                          );
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-rose-300 bg-white px-2.5 py-1 text-[11px] font-bold text-rose-900 hover:bg-rose-100"
                      >
                        <Edit3 className="h-3 w-3" />
                        Sunting Pengecualian
                      </button>
                    </div>

                    {editingOffenceId === activeOffence.offence_id ? (
                      <div className="space-y-2 pt-1">
                        <textarea
                          rows={4}
                          value={editingExclusionsText}
                          onChange={(e) => setEditingExclusionsText(e.target.value)}
                          className="w-full rounded-xl border border-rose-300 bg-white p-2.5 text-xs text-slate-900"
                          placeholder="Satu pengecualian / perangkap setiap baris..."
                        />
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            disabled={savingOffenceEdit}
                            onClick={() =>
                              void handleSaveOffenceExclusions(activeOffence.offence_id)
                            }
                            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-700 px-3 py-1.5 text-xs font-extrabold text-white hover:bg-rose-800"
                          >
                            <Save className="h-3.5 w-3.5" />
                            {savingOffenceEdit ? "Menyimpan..." : "Simpan & Sahkan Warta"}
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingOffenceId(null)}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700"
                          >
                            Batal
                          </button>
                        </div>
                      </div>
                    ) : (
                      <ul className="space-y-1.5 text-xs text-rose-950">
                        {activeOffence.explicit_exclusions_and_traps.map((trap, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-600" />
                            <span>{trap}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* 5. Eksibit Wajib & Templat Pertuduhan Borang 114 */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 bg-white p-3.5 text-xs">
                      <h4 className="font-extrabold text-slate-900">
                        Senarai Eksibit &amp; Bukti Wajib
                      </h4>
                      <ul className="mt-2 list-disc space-y-1.5 pl-4 text-slate-700">
                        {activeOffence.mandatory_exhibits.map((ex, i) => (
                          <li key={i}>{ex}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="font-extrabold text-slate-900">
                          Templat Pertuduhan Borang 114
                        </h4>
                        <button
                          type="button"
                          onClick={() =>
                            handleCopyChargeTemplate(activeOffence.charge_sheet_template_bm)
                          }
                          className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-100"
                        >
                          {copiedCharge ? (
                            <ClipboardCheck className="h-3.5 w-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                          {copiedCharge ? "Disalin!" : "Salin"}
                        </button>
                      </div>
                      <p className="mt-2 rounded-lg border border-slate-200 bg-white p-2.5 font-mono text-[11px] leading-relaxed text-slate-800">
                        {activeOffence.charge_sheet_template_bm}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SUB-TAB 2: PUSTAKA AKTA VERBATIM (STATUTE SECTIONS VERBATIM)          */}
      {/* ===================================================================== */}
      {subTab === "statutes" && snapshot && (
        <div className="space-y-4">
          {/* Pilihan Akta & Carian Seksyen */}
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-1.5">
                {snapshot.statutes_registry.map((st) => {
                  const active = activeStatuteMeta?.statute_id === st.statute_id;
                  return (
                    <button
                      key={st.statute_id}
                      type="button"
                      onClick={() => {
                        setSelectedStatuteId(st.statute_id);
                        setSelectedDocId("");
                      }}
                      className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-extrabold transition ${
                        active
                          ? "bg-[#0f2744] text-white shadow-sm"
                          : "border border-slate-200 bg-slate-50 text-slate-800 hover:bg-slate-100"
                      }`}
                    >
                      <span>{st.act_number_or_pu || st.statute_id}</span>
                      <span
                        className={`rounded-full px-1.5 py-0.5 text-[10px] ${
                          st.total_sections_indexed === 0
                            ? "bg-rose-600 text-white"
                            : active
                              ? "bg-amber-400 text-slate-950"
                              : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {st.total_sections_indexed}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="relative w-full sm:w-72">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  value={sectionSearch}
                  onChange={(e) => setSectionSearch(e.target.value)}
                  placeholder="Cari Seksyen / Peraturan / Teks Warta..."
                  className="w-full rounded-xl border border-slate-300 bg-slate-50 py-2 pl-8 pr-3 text-xs font-medium text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none"
                />
              </div>
            </div>

            {activeStatuteMeta && (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-extrabold text-slate-900">
                    {activeStatuteMeta.official_title_bm}
                  </span>
                  <span className="text-slate-600">
                    ({activeStatuteMeta.act_number_or_pu}) • Kuat Kuasa:{" "}
                    {activeStatuteMeta.effective_date}
                  </span>
                  {activeStatuteMeta.verified_by_admin ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-900">
                      <CheckCircle2 className="h-3 w-3" /> Disahkan Warta AGC
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full border border-yellow-300 bg-yellow-100 px-2.5 py-0.5 text-[10px] font-extrabold text-yellow-900">
                      <AlertTriangle className="h-3 w-3 text-yellow-700" /> Perlu Semakan Manual Warta AGC
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 font-mono text-[11px] text-slate-600">
                  <span>SHA256: {(activeStatuteMeta.source_pdf_hash || "").slice(0, 12)}...</span>
                </div>
              </div>
            )}
          </section>

          {/* Jika Akta Belum Diindeks (total_sections_indexed === 0) */}
          {activeStatuteMeta && activeStatuteMeta.total_sections_indexed === 0 ? (
            <div className="rounded-2xl border-2 border-rose-400 bg-rose-50 p-6 text-center shadow-sm">
              <AlertOctagon className="mx-auto h-10 w-10 text-rose-700" />
              <h3 className="mt-2 text-base font-extrabold text-rose-950">
                AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA
              </h3>
              <p className="mx-auto mt-1 max-w-xl text-xs leading-relaxed text-rose-900">
                Statut <strong>{activeStatuteMeta.official_title_bm}</strong> mempunyai{" "}
                <code>total_sections_indexed == 0</code> dalam Pustaka Akta Verbatim. Sistem dilarang sama sekali meneka kandungan seksyen daripada pengetahuan am AI. Sila muat naik fail PDF Warta Kerajaan Persekutuan di tab Admin.
              </p>
              <button
                type="button"
                onClick={() => setSubTab("admin")}
                className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-rose-700 px-4 py-2 text-xs font-extrabold text-white hover:bg-rose-800"
              >
                <FileUp className="h-4 w-4" />
                Muat Naik PDF Warta Sekarang
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              {/* Lajur Kiri: Senarai Bahagian & Seksyen */}
              <div className="max-h-[680px] space-y-3 overflow-y-auto pr-1 lg:col-span-5">
                {groupedSectionsByPart.map((grp) => (
                  <div
                    key={grp.partKey}
                    className="rounded-2xl border border-slate-200 bg-white p-3 shadow-xs"
                  >
                    <div className="mb-2 border-b border-slate-100 pb-1.5 text-[11px] font-extrabold uppercase tracking-wide text-blue-900">
                      {grp.partLabel}
                    </div>
                    <div className="space-y-1.5">
                      {grp.sections.map((sec) => {
                        const isSel = activeSectionDetail?.doc_id === sec.doc_id;
                        return (
                          <button
                            key={sec.doc_id}
                            type="button"
                            onClick={() => setSelectedDocId(sec.doc_id)}
                            className={`flex w-full flex-col items-start rounded-xl border p-2.5 text-left text-xs transition ${
                              isSel
                                ? "border-blue-600 bg-blue-50/70 font-bold text-blue-950"
                                : "border-slate-100 bg-slate-50/60 text-slate-800 hover:border-blue-200 hover:bg-white"
                            }`}
                          >
                            <div className="flex w-full items-center justify-between gap-2">
                              <span className="font-extrabold text-slate-900">
                                {sec.section_code} — {sec.section_heading}
                              </span>
                              <span className="rounded bg-white px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
                                {sec.is_offence_provision
                                  ? "KESALAHAN"
                                  : sec.is_penalty_provision
                                    ? "PENALTI"
                                    : "PROSEDUR"}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Lajur Kanan: Paparan Teks Verbatim Penuh */}
              <div className="lg:col-span-7">
                {activeSectionDetail ? (
                  <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-extrabold text-white">
                            {activeSectionDetail.statute_id}
                          </span>
                          <span className="rounded bg-teal-50 px-2 py-0.5 font-mono text-xs font-bold text-teal-900">
                            {activeSectionDetail.doc_id}
                          </span>
                        </div>
                        <h3 className="mt-2 text-base font-extrabold text-slate-900">
                          {activeSectionDetail.section_code}:{" "}
                          {activeSectionDetail.section_heading}
                        </h3>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {activeSectionDetail.part_number} — {activeSectionDetail.part_title}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          handleCopyChargeTemplate(
                            `${activeSectionDetail.statute_id} — ${activeSectionDetail.section_code} (${activeSectionDetail.section_heading}):\n${activeSectionDetail.verbatim_text_bm}`
                          )
                        }
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Salin Teks Verbatim
                      </button>
                    </div>

                    <div className="rounded-xl border border-teal-200 bg-teal-50/25 p-4">
                      <div className="mb-2 text-[11px] font-extrabold uppercase tracking-wide text-teal-900">
                        Teks Verbatim Warta Kerajaan Persekutuan (Bahasa Melayu)
                      </div>
                      <p className="whitespace-pre-line text-sm leading-relaxed text-slate-900">
                        {activeSectionDetail.verbatim_text_bm}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
                    Pilih mana-mana seksyen di sebelah kiri untuk membaca teks verbatim Warta.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* SUB-TAB 3: SENARAI HITAM UNDANG-UNDANG LAPUK / TERBATAL               */}
      {/* ===================================================================== */}
      {subTab === "repealed" && snapshot && (
        <section className="space-y-3 rounded-2xl border border-rose-200 bg-white p-4 shadow-sm sm:p-6">
          <div className="flex items-start gap-3 border-b border-rose-100 pb-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-800">
              <Ban className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-rose-950 sm:text-base">
                Senarai Hitam Undang-Undang Terbatal / Lapuk (repealed_and_blocked_provisions)
              </h3>
              <p className="text-xs text-slate-600">
                Pengawal Petikan Deterministik (<code>validateLegalOutput</code>) menyekat mana-mana output AI, Notis Kompaun, atau Borang 114 yang memetik peruntukan di bawah.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {snapshot.repealed_and_blocked_provisions.map((rep) => (
              <div
                key={rep.provision_id}
                className="rounded-2xl border border-rose-200 border-l-4 border-l-rose-600 bg-rose-50/35 p-4 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded bg-rose-700 px-2 py-0.5 font-mono text-[10px] font-extrabold text-white">
                    DISEKAT • {rep.provision_id}
                  </span>
                  <span className="font-bold text-rose-900">Status: {rep.status}</span>
                </div>
                <h4 className="mt-2 text-sm font-extrabold text-slate-900">
                  {rep.repealed_statute_or_section}
                </h4>
                <p className="mt-1.5 leading-relaxed text-slate-800">
                  <strong>Amaran Sistem:</strong> {rep.warning_message_bm}
                </p>
                {rep.replacement_section && (
                  <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50/70 p-2.5 text-emerald-950">
                    <strong>Peruntukan Gantian Berkuat Kuasa:</strong> {rep.replacement_section}
                  </div>
                )}
                {rep.key_differences_note && (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-amber-950">
                    <strong>Perbezaan Kritikal Unsur Kesalahan:</strong> {rep.key_differences_note}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ===================================================================== */}
      {/* SUB-TAB 4: ADMIN PANEL — PUSTAKA AKTA & SEMAKAN KESALAHAN (FASA 2 & 4)*/}
      {/* ===================================================================== */}
      {subTab === "admin" && (
        <div className="space-y-4">
          {/* 1. Papan Pemuka Audit Liputan Akta (Coverage Audit Dashboard) */}
          <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 sm:text-base">
                  Papan Pemuka Audit Liputan Pustaka Akta (statutes_registry)
                </h3>
                <p className="text-xs text-slate-600">
                  Semak bilangan seksyen verbatim yang diindeks berbanding dokumen Warta, status pengesahan Admin (&ldquo;Sahkan Warta&rdquo;), dan versi Pustaka Akta.
                </p>
              </div>

              <button
                type="button"
                onClick={() => void handlePurgeQaCache()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2 text-xs font-extrabold text-rose-900 hover:bg-rose-100"
              >
                <Trash2 className="h-3.5 w-3.5 text-rose-700" />
                Bersihkan Cache Koleksi Q&amp;A Lama (STALE)
              </button>
            </div>

            {coverage && coverage.unverified_statutes.length > 0 && (
              <div className="flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3.5 py-2.5 text-xs font-bold text-amber-950">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700" />
                <span>
                  Amaran Liputan: Statut berikut belum disahkan sepenuhnya oleh Admin:{" "}
                  {coverage.unverified_statutes.join(", ")}
                </span>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-extrabold uppercase text-slate-600">
                    <th className="p-2.5">Kod Statut</th>
                    <th className="p-2.5">Tajuk Rasmi &amp; Warta</th>
                    <th className="p-2.5">Kuat Kuasa</th>
                    <th className="p-2.5">Seksyen Diindeks</th>
                    <th className="p-2.5">Kesalahan</th>
                    <th className="p-2.5">Status Warta</th>
                    <th className="p-2.5">Tindakan Admin</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {(coverage?.statutes_registry || snapshot?.statutes_registry || []).map((st) => {
                    const isUnindexed = st.total_sections_indexed === 0;
                    return (
                      <tr
                        key={st.statute_id}
                        className={isUnindexed ? "bg-rose-50/60" : "hover:bg-slate-50/80"}
                      >
                        <td className="p-2.5 font-mono font-extrabold text-slate-900">
                          {st.statute_id}
                          <div className="text-[10px] font-semibold text-blue-800">
                            {st.canonical_akta_code}
                          </div>
                        </td>
                        <td className="p-2.5">
                          <div className="font-bold text-slate-900">{st.official_title_bm}</div>
                          <div className="text-[11px] text-slate-500">
                            {st.act_number_or_pu} • SHA256:{" "}
                            {(st.source_pdf_hash || "").slice(0, 10)}...
                          </div>
                        </td>
                        <td className="p-2.5 font-semibold text-slate-700">
                          {st.effective_date}
                        </td>
                        <td className="p-2.5">
                          {isUnindexed ? (
                            <span className="rounded bg-rose-700 px-2 py-0.5 text-[10px] font-extrabold text-white">
                              0 Seksyen (BELUM DIINDEKS)
                            </span>
                          ) : (
                            <span className="font-extrabold text-emerald-900">
                              {st.total_sections_indexed} /{" "}
                              {st.total_sections_in_pdf || st.total_sections_indexed} Seksyen (100%)
                            </span>
                          )}
                        </td>
                        <td className="p-2.5 font-bold text-slate-800">
                          {st.total_offences_indexed ?? "-"}
                        </td>
                        <td className="p-2.5">
                          {st.verified_by_admin ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-900">
                              <CheckCircle2 className="h-3 w-3" /> Disahkan Warta AGC
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border border-yellow-300 bg-yellow-100 px-2.5 py-0.5 text-[10px] font-extrabold text-yellow-900">
                              <AlertTriangle className="h-3 w-3 text-yellow-700" /> Perlu Semakan Manual Warta AGC
                            </span>
                          )}
                        </td>
                        <td className="p-2.5">
                          <button
                            type="button"
                            onClick={() =>
                              void handleVerifyStatute(st.statute_id, !st.verified_by_admin)
                            }
                            className={`rounded-lg px-2.5 py-1 text-[11px] font-extrabold transition ${
                              st.verified_by_admin
                                ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                                : "bg-emerald-600 text-white hover:bg-emerald-700"
                            }`}
                          >
                            {st.verified_by_admin ? "Nyah-Sahkan" : "Sahkan Warta"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* 2. Borang Muat Naik PDF Warta Kerajaan Persekutuan (AGC) & Panduan Penamaan Fail */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <form
              onSubmit={handleUploadGazettePdf}
              className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:col-span-7"
            >
              <div className="flex items-center gap-2 border-b border-slate-200 pb-2.5">
                <FileUp className="h-5 w-5 text-indigo-700" />
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900">
                    Muat Naik &amp; Indeks Fail PDF / Teks Warta Rasmi AGC (lom.agc.gov.my)
                  </h4>
                  <p className="text-xs text-slate-500">
                    Penghurai deterministik akan memetakan setiap Bahagian, Seksyen &amp; Jadual ke dalam <code>statute_sections_verbatim</code> serta menanda cache Q&amp;A lama sebagai <code>STALE</code>.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                    Kod Statut (statute_id)
                  </label>
                  <select
                    value={uploadStatuteId}
                    onChange={(e) => {
                      const val = e.target.value;
                      setUploadStatuteId(val);
                      const matched = CORE_STATUTE_FILE_GUIDE.find((g) => g.statute_id === val);
                      if (matched) {
                        setUploadOfficialTitle(matched.title);
                        setUploadActNumberOrPu(matched.akta_code);
                      }
                    }}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-900"
                  >
                    {CORE_STATUTE_FILE_GUIDE.map((g) => (
                      <option key={g.statute_id} value={g.statute_id}>
                        {g.statute_id} ({g.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                    Nombor Akta / Rujukan P.U. (A)
                  </label>
                  <input
                    type="text"
                    value={uploadActNumberOrPu}
                    onChange={(e) => setUploadActNumberOrPu(e.target.value)}
                    placeholder="Cth: Akta 852 / P.U. (A) 259/2024"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                  Tajuk Rasmi Akta / Peraturan (Bahasa Melayu)
                </label>
                <input
                  type="text"
                  value={uploadOfficialTitle}
                  onChange={(e) => setUploadOfficialTitle(e.target.value)}
                  placeholder="Cth: Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]"
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-extrabold uppercase text-slate-600">
                  Pilih Fail PDF / TXT Warta Kerajaan Persekutuan
                </label>
                <input
                  type="file"
                  accept=".pdf,.txt"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full rounded-xl border border-dashed border-indigo-300 bg-indigo-50/40 p-2.5 text-xs font-semibold text-slate-800"
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <label className="inline-flex items-center gap-2 text-xs font-bold text-slate-700">
                  <input
                    type="checkbox"
                    checked={uploadVerified}
                    onChange={(e) => setUploadVerified(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                  />
                  <span>Terus Tandakan &ldquo;Sahkan Warta&rdquo; Selepas Diindeks</span>
                </label>

                <button
                  type="submit"
                  disabled={uploadingPdf || !uploadFile}
                  className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-indigo-700 px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-indigo-800 disabled:opacity-50"
                >
                  {uploadingPdf ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileUp className="h-4 w-4" />
                  )}
                  {uploadingPdf ? "Sedang Menghurai Warta..." : "Muat Naik & Indeks Warta AGC"}
                </button>
              </div>
            </form>

            {/* Panduan Penamaan Fail Warta Rasmi */}
            <div className="space-y-2.5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:col-span-5">
              <h4 className="text-sm font-extrabold text-slate-900">
                Panduan Penamaan Fail PDF Warta AGC (data/akta/)
              </h4>
              <p className="text-xs leading-relaxed text-slate-600">
                Letakkan fail PDF rasmi daripada Portal Jabatan Peguam Negara (
                <code>lom.agc.gov.my</code>) di dalam direktori <code>data/akta/</code> atau muat naik terus di sebelah kiri:
              </p>
              <div className="space-y-1.5 text-xs">
                {CORE_STATUTE_FILE_GUIDE.map((item) => (
                  <div
                    key={item.code}
                    className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5"
                  >
                    <span className="font-mono font-extrabold text-indigo-900">{item.code}</span>
                    <span className="text-right text-[11px] text-slate-600">{item.title}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 3. Semakan Kesalahan Draf (DRAFT_PENDING_REVIEW -> Sahkan Warta) */}
          {snapshot && (
            <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <h4 className="text-sm font-extrabold text-slate-900">
                Senarai Semakan Kesalahan &amp; Pengesahan Warta ({snapshot.master_offences_matrix.length} Kesalahan)
              </h4>
              <div className="max-h-[360px] overflow-y-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-extrabold uppercase text-slate-600">
                      <th className="p-2">ID Kesalahan</th>
                      <th className="p-2">Seksyen Pertuduhan &amp; Hukuman</th>
                      <th className="p-2">Tajuk Kesalahan</th>
                      <th className="p-2">Status Semakan</th>
                      <th className="p-2">Tindakan</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {snapshot.master_offences_matrix.map((off) => (
                      <tr key={off.offence_id} className="hover:bg-slate-50">
                        <td className="p-2 font-mono font-bold text-slate-900">
                          {off.offence_id}
                        </td>
                        <td className="p-2">
                          <div className="font-bold text-blue-900">{off.offence_section}</div>
                          <div className="text-[11px] text-slate-500">{off.penalty_section}</div>
                        </td>
                        <td className="p-2 font-medium text-slate-800">{off.offence_title}</td>
                        <td className="p-2">
                          {off.verified_status === "VERIFIED_AGC" ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-900">
                              <CheckCircle2 className="h-3 w-3" /> Disahkan Warta AGC
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border border-yellow-300 bg-yellow-100 px-2.5 py-0.5 text-[10px] font-extrabold text-yellow-900">
                              <AlertTriangle className="h-3 w-3 text-yellow-700" /> Perlu Semakan Manual Warta AGC
                            </span>
                          )}
                        </td>
                        <td className="p-2">
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedOffenceId(off.offence_id);
                                setSubTab("offences");
                              }}
                              className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-100"
                            >
                              Lihat
                            </button>
                            {off.verified_status !== "VERIFIED_AGC" && (
                              <button
                                type="button"
                                onClick={() => void handleVerifyOffence(off.offence_id, true)}
                                className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-1 text-[11px] font-extrabold text-white hover:bg-emerald-700"
                              >
                                <ArrowRightCircle className="h-3 w-3" />
                                Sahkan Warta
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
