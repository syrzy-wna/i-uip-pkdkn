"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  WifiOff,
  X,
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

export interface CompoundPrefillMeta {
  seksyen?: string;
  kuasaKompaun?: string;
  amaun?: string;
  tempoh?: string;
  kesalahanRingkas?: string;
}

interface LegalDirectoryPanelProps {
  authToken: string | null;
  officer: OfficerProfile | null;
  isDevAdmin: boolean;
  onApplyOffenceToCase: (
    draftText: string,
    aktaCode: string,
    bukaIp: boolean,
    compoundMeta?: CompoundPrefillMeta
  ) => void;
}

type DirectorySubTab = "offences" | "statutes" | "repealed" | "admin";

const OFFENDER_CATEGORY_LABELS: Record<TargetOffenderCategory | "SEMUA", string> = {
  SEMUA: "Semua Kategori Pelaku",
  INDIVIDU: "Individu",
  OBD_BAWAH_18: "Bawah 18 Tahun (OBD)",
  PERTUBUHAN_PERBADANAN: "Syarikat",
  PENGENDALI_MAKANAN: "Pengendali Makanan",
  TUAN_PUNYA_PREMIS: "Pemilik Premis",
  PENJUAL_PENGILANG: "Penjual / Pengilang",
};

function formatOffenderLabel(raw?: string | null): string {
  if (!raw) return "Individu";
  const key = raw.trim().toUpperCase() as TargetOffenderCategory | "SEMUA";
  return OFFENDER_CATEGORY_LABELS[key] || raw.replace(/_/g, " ");
}

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
  const selectedOffenceIdRef = useRef<string>("");
  useEffect(() => {
    selectedOffenceIdRef.current = selectedOffenceId;
  }, [selectedOffenceId]);
  const [copiedCharge, setCopiedCharge] = useState<boolean>(false);
  const [showMobileFilters, setShowMobileFilters] = useState<boolean>(false);
  const [mobileOffenceDrawerOpen, setMobileOffenceDrawerOpen] = useState<boolean>(false);
  const [mobileSectionDrawerOpen, setMobileSectionDrawerOpen] = useState<boolean>(false);

  // Tapisan Pustaka Akta Verbatim
  const [selectedStatuteId, setSelectedStatuteId] = useState<string>("AKTA_852");
  const [sectionSearch, setSectionSearch] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string>("");

  useEffect(() => {
    if (!isDevAdmin && subTab === "admin") {
      setSubTab("offences");
    }
  }, [isDevAdmin, subTab]);

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
      if (!selectedOffenceIdRef.current && snap.master_offences_matrix.length > 0) {
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
            if (!selectedOffenceIdRef.current && parsed.master_offences_matrix.length > 0) {
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
  }, [authToken]);

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
      const pTitle = sec.part_title || "Peruntukan Akta";
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
        `Warta ${ing.statute_id} berjaya diindeks (${ing.sections_extracted} seksyen penuh, ${ing.new_offences_swept} kesalahan baharu dikesan, versi ${ing.statute_library_version}).`
      );
      await loadLegalLibrary();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal memproses fail Warta rasmi.");
    } finally {
      setUploadingPdf(false);
    }
  };

  const handlePurgeQaCache = async () => {
    try {
      const res = await purgeAdvisorQaCache(undefined, authToken);
      showToast(
        `${res.stale_records_marked} jawapan terdahulu lama telah disegarkan (Versi Pustaka: ${res.statute_library_version}).`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal membersihkan cache Koleksi Q&A.");
    }
  };

  const activeFilterCount =
    (aktaFilter !== "Semua" ? 1 : 0) +
    (categoryFilter !== "SEMUA" ? 1 : 0) +
    (compoundFilter !== "SEMUA" ? 1 : 0);

  const unverifiedOffencesCount = useMemo(
    () =>
      (snapshot?.master_offences_matrix || []).filter(
        (o) => o.verified_status !== "VERIFIED_AGC"
      ).length,
    [snapshot]
  );

  const renderOffenceDetailContent = (off: MasterOffenceRecord) => {
    const isComp = Boolean(off.compound_info?.is_compoundable);
    return (
      <div className="space-y-4">
        {/* Header Kesalahan & Butang Tindakan */}
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-extrabold text-white">
                {off.canonical_akta_code || off.statute_id}
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-extrabold ${
                  isComp
                    ? "bg-emerald-100 text-emerald-900"
                    : "bg-amber-100 text-amber-950"
                }`}
              >
                {isComp ? "Boleh Kompaun" : "Terus Mahkamah"}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-slate-700">
                {formatOffenderLabel(off.target_offender)}
              </span>
              {isDevAdmin && (
                <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-600">
                  {off.offence_id}
                </span>
              )}
            </div>
            <h3 className="text-base font-extrabold text-slate-900">{off.offence_title}</h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setMobileOffenceDrawerOpen(false);
                onApplyOffenceToCase(
                  off.charge_sheet_template_bm,
                  off.canonical_akta_code || "Akta 852",
                  true
                );
              }}
              className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-blue-700"
            >
              <FileText className="h-4 w-4" />
              Buka di Editor Fail IP
            </button>

            {isComp && (
              <button
                type="button"
                onClick={() => {
                  if (off.verified_status !== "VERIFIED_AGC") {
                    const proceed = window.confirm(
                      `Sila semak semula seksyen (${off.offence_section}) dan had kompaun ini dengan Warta rasmi sebelum keluarkan notis.\n\nTeruskan isi ke Borang Notis Kompaun?`
                    );
                    if (!proceed) return;
                  }
                  const aktaCode = off.canonical_akta_code || "Akta 852";
                  const rawLimit = off.compound_info?.compound_amount_or_limit || "";
                  const amtMatch = rawLimit.match(/RM\s*[\d,]+(?:\.\d{2})?/i);
                  setMobileOffenceDrawerOpen(false);
                  onApplyOffenceToCase(
                    off.charge_sheet_template_bm,
                    aktaCode,
                    false,
                    {
                      seksyen: `${off.offence_section} ${aktaCode}`.trim(),
                      kuasaKompaun: off.compound_info?.compound_authority_section || "",
                      amaun: amtMatch ? amtMatch[0].toUpperCase() : aktaCode === "Akta 154" ? "RM 500.00" : "RM 250.00",
                      tempoh:
                        aktaCode === "Akta 852"
                          ? "30 hari dari tarikh tawaran kompaun"
                          : "14 hari dari tarikh serahan notis",
                      kesalahanRingkas: off.offence_title || off.charge_sheet_template_bm,
                    }
                  );
                }}
                className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
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
              Seksyen Kesalahan &amp; Hukuman
            </div>
            <div className="mt-1 font-extrabold text-slate-900">
              Seksyen Kesalahan: {off.offence_section}
            </div>
            <div className="mt-1 font-bold text-indigo-900">
              Hukuman: {off.penalty_section}
            </div>
            <div className="mt-1 text-slate-700">
              {off.penalty_first_offence?.verbatim_penalty}
            </div>
          </div>

          <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5 text-xs">
            <div className="text-[11px] font-extrabold uppercase text-emerald-900">
              Had Denda &amp; Status Kompaun
            </div>
            <div className="mt-1 font-extrabold text-slate-900">
              {isComp ? "Boleh Kompaun" : "Terus Mahkamah (Buka IP)"}
            </div>
            <div className="mt-1 text-slate-700">
              <strong>Punca Kuasa Kompaun:</strong>{" "}
              {off.compound_info?.compound_authority_section ||
                off.compound_info?.compound_regulation_ref ||
                "Tiada Kompaun"}
            </div>
            <div className="mt-1 text-slate-700">
              <strong>Denda Maksimum:</strong>{" "}
              {off.penalty_first_offence?.max_fine_rm
                ? `RM ${off.penalty_first_offence.max_fine_rm.toLocaleString("en-MY")}`
                : "-"}{" "}
              • <strong>Kompaun:</strong>{" "}
              {off.compound_info?.compound_amount_or_limit || "Tiada Kompaun"}
            </div>
          </div>
        </div>

        {/* 2. Perkara Wajib Dibuktikan */}
        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/50 p-4">
          <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-slate-900">
            <CheckCircle2 className="h-4 w-4 text-blue-700" />
            Perkara Wajib Dibuktikan
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-[11px] font-extrabold uppercase text-slate-600">
                  <th className="py-2 pr-3">Bil</th>
                  <th className="py-2 pr-3">Perkara Wajib Dibuktikan</th>
                  <th className="py-2">Bukti Di Lokasi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70">
                {off.mandatory_elements.map((el) => (
                  <tr key={el.element_no}>
                    <td className="py-2 pr-3 font-mono font-bold text-blue-900">
                      {el.element_no}
                    </td>
                    <td className="py-2 pr-3 font-medium text-slate-800">{el.description}</td>
                    <td className="py-2 text-[11px] text-slate-600">{el.must_prove}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 3. Elak Kesilapan Biasa PPKP */}
        <div className="space-y-2 rounded-xl border border-amber-200 border-l-4 border-l-amber-500 bg-amber-50/40 p-4">
          <div className="flex items-center justify-between gap-2">
            <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-amber-950">
              <AlertTriangle className="h-4 w-4 text-amber-700" />
              Elak Kesilapan Biasa PPKP &amp; Pengecualian
            </h4>
            {isDevAdmin && (
              <button
                type="button"
                onClick={() => {
                  setEditingOffenceId(off.offence_id);
                  setEditingExclusionsText(off.explicit_exclusions_and_traps.join("\n"));
                }}
                className="inline-flex items-center gap-1 rounded-lg border border-amber-300 bg-white px-2.5 py-1 text-[11px] font-bold text-amber-950 hover:bg-amber-100"
              >
                <Edit3 className="h-3 w-3" />
                Sunting
              </button>
            )}
          </div>

          {isDevAdmin && editingOffenceId === off.offence_id ? (
            <div className="space-y-2 pt-1">
              <textarea
                rows={4}
                value={editingExclusionsText}
                onChange={(e) => setEditingExclusionsText(e.target.value)}
                className="w-full rounded-xl border border-amber-300 bg-white p-2.5 text-xs text-slate-900"
                placeholder="Satu pengecualian / perangkap setiap baris..."
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={savingOffenceEdit}
                  onClick={() => void handleSaveOffenceExclusions(off.offence_id)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-700 px-3 py-1.5 text-xs font-extrabold text-white hover:bg-amber-800"
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
            <ul className="space-y-1.5 text-xs text-amber-950">
              {off.explicit_exclusions_and_traps.map((trap, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                  <span>{trap}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 4. Barang Bukti Wajib & Draf Pertuduhan Borang 114 */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-3.5 text-xs">
            <h4 className="font-extrabold text-slate-900">Barang Bukti &amp; Borang Wajib</h4>
            <ul className="mt-2 list-disc space-y-1.5 pl-4 text-slate-700">
              {off.mandatory_exhibits.map((ex, i) => (
                <li key={i}>{ex}</li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs">
            <div className="flex items-center justify-between gap-2">
              <h4 className="font-extrabold text-slate-900">Draf Pertuduhan (Borang 114)</h4>
              <button
                type="button"
                onClick={() => handleCopyChargeTemplate(off.charge_sheet_template_bm)}
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
            <p className="mt-2 rounded-lg border border-slate-200 bg-white p-2.5 text-[11px] leading-relaxed text-slate-800">
              {off.charge_sheet_template_bm}
            </p>
          </div>
        </div>

        {/* 5. Teks Asal Akta */}
        <div className="space-y-2 rounded-xl border border-teal-200 bg-teal-50/30 p-4">
          <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-teal-950">
            <BookOpen className="h-4 w-4 text-teal-700" />
            Teks Asal Akta (Warta Kerajaan)
          </h4>

          {linkedVerbatimForActiveOffence.length === 0 ? (
            <p className="text-xs text-slate-600">Tiada petikan seksyen dipautkan untuk rekod ini.</p>
          ) : (
            <div className="space-y-2.5">
              {linkedVerbatimForActiveOffence.map((sec) => (
                <div
                  key={sec.doc_id}
                  className="rounded-lg border border-teal-200/80 bg-white p-3 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-extrabold text-teal-900">
                      Seksyen {sec.section_code} — {sec.section_heading}
                    </span>
                    {isDevAdmin && (
                      <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-600">
                        {sec.doc_id}
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 whitespace-pre-line leading-relaxed text-slate-800">
                    {sec.verbatim_text_bm}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="mx-auto max-w-[1600px] space-y-4">
      {/* Header Utama Direktori Akta & Kesalahan */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#0f2744] text-amber-300 shadow-sm">
              <Scale className="h-5 w-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-extrabold text-slate-900 sm:text-lg">
                  Direktori Akta &amp; Kesalahan
                </h2>
                {isDevAdmin && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-900">
                    <ShieldCheck className="h-3 w-3 text-emerald-700" />
                    {snapshot?.statute_library_version || "v2.5"}
                  </span>
                )}
                {offlineMode && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-900">
                    <WifiOff className="h-3 w-3" /> Mod Luar Talian
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-slate-600">
                Rujukan pantas senarai kesalahan, had kompaun, perkara wajib dibuktikan dan teks asal akta KKM.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-700 sm:flex">
              <Database className="h-3.5 w-3.5 text-blue-700" />
              <span>{snapshot?.master_offences_matrix.length ?? 0} Kesalahan</span>
              <span>•</span>
              <span>{snapshot?.statute_sections_verbatim.length ?? 0} Seksyen</span>
            </div>

            <button
              type="button"
              onClick={() => void loadLegalLibrary()}
              disabled={loading}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Muat Semula
            </button>
          </div>
        </div>

        {/* Bar Navigasi Sub-Tab Ringkas (Tab Admin Warta HANYA untuk Admin) */}
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
            <span>Senarai Kesalahan ({snapshot?.master_offences_matrix.length ?? 0})</span>
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
            <span>Teks Penuh Akta ({snapshot?.statutes_registry.length ?? 0})</span>
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
              Akta Dimansuhkan ({snapshot?.repealed_and_blocked_provisions.length ?? 0})
            </span>
          </button>

          {isDevAdmin && (
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
              <span>Admin Warta</span>
            </button>
          )}
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
          Memuatkan Direktori Akta &amp; Kesalahan...
        </div>
      ) : null}

      {/* ===================================================================== */}
      {/* SUB-TAB 1: SENARAI KESALAHAN                                          */}
      {/* ===================================================================== */}
      {subTab === "offences" && snapshot && (
        <div className="space-y-4">
          {/* Bar Carian + Butang Tapis (Mesra Telefon & Desktop) */}
          <section className="rounded-2xl border border-slate-200 bg-white p-3.5 shadow-sm sm:p-4">
            {/* Baris Utama: Carian + Butang Tapis pada telefon */}
            <div className="flex items-center gap-2 md:hidden">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={offenceSearch}
                  onChange={(e) => setOffenceSearch(e.target.value)}
                  placeholder="Cari seksyen, kesalahan atau kata kunci..."
                  className="w-full rounded-xl border border-slate-300 bg-slate-50/70 py-2.5 pl-9 pr-3 text-sm text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={() => setShowMobileFilters((v) => !v)}
                className={`inline-flex min-h-[42px] shrink-0 items-center gap-1.5 rounded-xl border px-3.5 py-2 text-xs font-extrabold transition ${
                  showMobileFilters || activeFilterCount > 0
                    ? "border-[#0f2744] bg-[#0f2744] text-white"
                    : "border-slate-300 bg-white text-slate-700"
                }`}
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                <span>Tapis</span>
                {activeFilterCount > 0 && (
                  <span className="rounded-full bg-amber-400 px-1.5 py-0.5 text-[10px] font-extrabold text-slate-950">
                    {activeFilterCount}
                  </span>
                )}
              </button>
            </div>

            {/* Penapis Lanjutan (Boleh buka/tutup di telefon; sentiasa kelihatan di desktop) */}
            <div
              className={`${
                showMobileFilters ? "mt-3 grid" : "hidden md:grid"
              } grid-cols-1 gap-3 md:grid-cols-4`}
            >
              <div>
                <label className="mb-1 block text-[11px] font-bold text-slate-600">
                  Akta / Peraturan
                </label>
                <select
                  aria-label="Tapis Akta Kesalahan"
                  value={aktaFilter}
                  onChange={(e) => setAktaFilter(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800"
                >
                  <option value="Semua">Semua Akta KKM</option>
                  <option value="Akta 852">Akta 852 (Merokok / Vape)</option>
                  <option value="Akta 281">Akta 281 (Makanan)</option>
                  <option value="PPKM 2009">PPKM 2009 (Kebersihan Makanan)</option>
                  <option value="PPM 1985">PPM 1985 (Peraturan Makanan)</option>
                  <option value="Akta 154">Akta 154 (Aedes / Vektor)</option>
                  <option value="Akta 342">Akta 342 (Penyakit Berjangkit)</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] font-bold text-slate-600">
                  Kategori Pelaku
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
                <label className="mb-1 block text-[11px] font-bold text-slate-600">
                  Status Kompaun
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
                  <option value="SEMUA">Semua Status</option>
                  <option value="BOLEH_KOMPAUN">Boleh Kompaun</option>
                  <option value="TERUS_MAHKAMAH">Terus Mahkamah (IP)</option>
                </select>
              </div>

              <div className="hidden md:block">
                <label className="mb-1 block text-[11px] font-bold text-slate-600">
                  Carian Pantas
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={offenceSearch}
                    onChange={(e) => setOffenceSearch(e.target.value)}
                    placeholder="Cth: Seksyen 17, tifoid, jentik..."
                    className="w-full rounded-xl border border-slate-300 bg-slate-50/60 py-2 pl-8 pr-3 text-xs font-medium text-slate-900 focus:border-blue-600 focus:bg-white focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Paparan 2 Lajur (Desktop) + Modal/Drawer (Telefon) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Lajur Kiri: Senarai Kesalahan (Maksimum 2 Lencana Setiap Kad) */}
            <div className="space-y-2 lg:col-span-5">
              <div className="flex items-center justify-between px-1 text-xs font-bold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <Filter className="h-3.5 w-3.5 text-[#0f2744]" />
                  {filteredOffences.length} Kesalahan Ditemui
                </span>
                <span className="text-xs font-medium text-slate-500 lg:hidden">
                  Tekan mana-mana kesalahan untuk lihat butiran
                </span>
              </div>

              <div className="max-h-[720px] space-y-2 overflow-y-auto pr-1">
                {filteredOffences.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-xs text-slate-500">
                    Tiada kesalahan ditemui untuk tapisan ini. Cuba ubah carian atau penapis.
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
                        onClick={() => {
                          setSelectedOffenceId(off.offence_id);
                          setMobileOffenceDrawerOpen(true);
                        }}
                        className={`flex w-full flex-col items-start rounded-2xl border p-3.5 text-left transition ${
                          isSelected
                            ? "border-blue-600 bg-blue-50/70 ring-1 ring-blue-600"
                            : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50"
                        }`}
                      >
                        {/* MAKSIMUM 2 LENCANA SAHAJA: Akta & Seksyen di kiri + Status Kompaun di kanan */}
                        <div className="flex w-full items-center justify-between gap-2">
                          <span className="truncate rounded-md bg-[#0f2744] px-2 py-0.5 text-[11px] font-extrabold text-white">
                            {actBadge} · {off.offence_section}
                          </span>
                          <span
                            className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-extrabold ${
                              isComp
                                ? "bg-emerald-100 text-emerald-900"
                                : "bg-amber-100 text-amber-950"
                            }`}
                          >
                            {isComp ? "Boleh Kompaun" : "Terus Mahkamah"}
                          </span>
                        </div>

                        <div className="mt-2 text-xs font-extrabold leading-snug text-slate-900 sm:text-[13px]">
                          {off.offence_title}
                        </div>

                        <div className="mt-1.5 flex w-full flex-wrap items-center justify-between gap-1 text-[11px] text-slate-600">
                          <span>Pelaku: {formatOffenderLabel(off.target_offender)}</span>
                          <span className="font-semibold text-slate-700">
                            Hukuman: {off.penalty_section}
                          </span>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Lajur Kanan (Desktop sahaja): Perincian Penuh Kesalahan */}
            <div className="hidden lg:col-span-7 lg:block">
              {!activeOffence ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
                  Pilih mana-mana kesalahan di sebelah kiri untuk melihat perkara wajib dibuktikan, draf pertuduhan dan teks asal akta.
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  {renderOffenceDetailContent(activeOffence)}
                </div>
              )}
            </div>
          </div>

          {/* Modal / Drawer Perincian Kesalahan Untuk Telefon & Tablet (< lg) */}
          {mobileOffenceDrawerOpen && activeOffence && (
            <div
              onClick={(e) => {
                if (e.target === e.currentTarget) setMobileOffenceDrawerOpen(false);
              }}
              className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 backdrop-blur-[1px] lg:hidden"
            >
              <div className="flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="min-w-0 pr-2">
                    <div className="text-[11px] font-extrabold uppercase tracking-wide text-blue-900">
                      {activeOffence.canonical_akta_code || activeOffence.statute_id} ·{" "}
                      {activeOffence.offence_section}
                    </div>
                    <div className="truncate text-xs font-bold text-slate-800">
                      Perincian Kesalahan
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMobileOffenceDrawerOpen(false)}
                    aria-label="Tutup perincian kesalahan"
                    className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="overflow-y-auto p-4">
                  {renderOffenceDetailContent(activeOffence)}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* SUB-TAB 2: TEKS PENUH AKTA                                            */}
      {/* ===================================================================== */}
      {subTab === "statutes" && snapshot && (
        <div className="space-y-4">
          {/* Pilihan Akta (Dropdown Bersih) & Carian Seksyen */}
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-12">
              <div className="sm:col-span-7">
                <label className="mb-1 block text-xs font-bold text-slate-700">
                  Pilih Akta / Peraturan Rasmi ({snapshot.statutes_registry.length})
                </label>
                <select
                  value={activeStatuteMeta?.statute_id || ""}
                  onChange={(e) => {
                    setSelectedStatuteId(e.target.value);
                    setSelectedDocId("");
                  }}
                  className="min-h-[44px] w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-900 focus:border-[#0f2744] focus:outline-none sm:text-sm"
                >
                  {snapshot.statutes_registry.map((st) => (
                    <option key={st.statute_id} value={st.statute_id}>
                      {st.act_number_or_pu || st.statute_id} — {st.official_title_bm} ({st.total_sections_indexed} seksyen)
                    </option>
                  ))}
                </select>
              </div>

              <div className="sm:col-span-5">
                <label className="mb-1 block text-xs font-bold text-slate-700">
                  Cari Seksyen atau Perkataan
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={sectionSearch}
                    onChange={(e) => setSectionSearch(e.target.value)}
                    placeholder="cth: Seksyen 17, sitaan, tifoid..."
                    className="min-h-[44px] w-full rounded-xl border border-slate-300 bg-slate-50 py-2 pl-9 pr-3 text-base font-medium text-slate-900 focus:border-[#0f2744] focus:bg-white focus:outline-none sm:text-sm"
                  />
                </div>
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
                </div>
                {isDevAdmin && (
                  <div className="font-mono text-[11px] text-slate-500">
                    SHA256: {(activeStatuteMeta.source_pdf_hash || "").slice(0, 12)}...
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Jika Akta Belum Diindeks */}
          {activeStatuteMeta && activeStatuteMeta.total_sections_indexed === 0 ? (
            <div className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-center shadow-sm">
              <AlertOctagon className="mx-auto h-9 w-9 text-amber-700" />
              <h3 className="mt-2 text-base font-extrabold text-slate-900">
                Teks Warta Belum Dimuat Naik
              </h3>
              <p className="mx-auto mt-1 max-w-xl text-xs leading-relaxed text-slate-700">
                Fail PDF Warta rasmi bagi <strong>{activeStatuteMeta.official_title_bm}</strong> belum dimuat naik ke dalam sistem.
              </p>
              {isDevAdmin && (
                <button
                  type="button"
                  onClick={() => setSubTab("admin")}
                  className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-indigo-700 px-4 py-2 text-xs font-extrabold text-white hover:bg-indigo-800"
                >
                  <FileUp className="h-4 w-4" />
                  Muat Naik PDF Warta (Admin)
                </button>
              )}
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
                            onClick={() => {
                              setSelectedDocId(sec.doc_id);
                              setMobileSectionDrawerOpen(true);
                            }}
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
                              <span className="shrink-0 rounded bg-white px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                                {sec.is_offence_provision
                                  ? "Kesalahan"
                                  : sec.is_penalty_provision
                                    ? "Hukuman"
                                    : "Prosedur"}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Lajur Kanan (Desktop sahaja): Paparan Teks Penuh Seksyen */}
              <div className="hidden lg:col-span-7 lg:block">
                {activeSectionDetail ? (
                  <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="rounded-md bg-[#0f2744] px-2.5 py-0.5 text-xs font-extrabold text-white">
                            {activeStatuteMeta?.act_number_or_pu || activeSectionDetail.statute_id}
                          </span>
                          {isDevAdmin && (
                            <span className="rounded bg-teal-50 px-2 py-0.5 font-mono text-[10px] font-bold text-teal-900">
                              {activeSectionDetail.doc_id}
                            </span>
                          )}
                        </div>
                        <h3 className="mt-2 text-base font-extrabold text-slate-900">
                          Seksyen {activeSectionDetail.section_code}:{" "}
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
                            `${activeStatuteMeta?.act_number_or_pu || activeSectionDetail.statute_id} — Seksyen ${activeSectionDetail.section_code} (${activeSectionDetail.section_heading}):\n${activeSectionDetail.verbatim_text_bm}`
                          )
                        }
                        className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Salin Teks
                      </button>
                    </div>

                    <div className="rounded-xl border border-teal-200 bg-teal-50/25 p-4">
                      <div className="mb-2 text-[11px] font-extrabold uppercase tracking-wide text-teal-900">
                        Teks Asal Warta Kerajaan
                      </div>
                      <p className="whitespace-pre-line text-sm leading-relaxed text-slate-900">
                        {activeSectionDetail.verbatim_text_bm}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
                    Pilih mana-mana seksyen di sebelah kiri untuk membaca teks asal akta.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Modal / Drawer Teks Seksyen Untuk Telefon & Tablet (< lg) */}
          {mobileSectionDrawerOpen && activeSectionDetail && (
            <div
              onClick={(e) => {
                if (e.target === e.currentTarget) setMobileSectionDrawerOpen(false);
              }}
              className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 backdrop-blur-[1px] lg:hidden"
            >
              <div className="flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="min-w-0 pr-2">
                    <div className="text-[11px] font-extrabold text-blue-900">
                      {activeStatuteMeta?.act_number_or_pu || activeSectionDetail.statute_id}
                    </div>
                    <div className="truncate text-xs font-extrabold text-slate-900">
                      Seksyen {activeSectionDetail.section_code} — {activeSectionDetail.section_heading}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMobileSectionDrawerOpen(false)}
                    aria-label="Tutup teks seksyen"
                    className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="space-y-3 overflow-y-auto p-4">
                  <div className="rounded-xl border border-teal-200 bg-teal-50/25 p-4">
                    <p className="whitespace-pre-line text-sm leading-relaxed text-slate-900">
                      {activeSectionDetail.verbatim_text_bm}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      handleCopyChargeTemplate(
                        `${activeStatuteMeta?.act_number_or_pu || activeSectionDetail.statute_id} — Seksyen ${activeSectionDetail.section_code}:\n${activeSectionDetail.verbatim_text_bm}`
                      )
                    }
                    className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white py-2.5 text-xs font-bold text-slate-800 hover:bg-slate-50"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Salin Teks Asal Seksyen
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* SUB-TAB 3: AKTA DIMANSUHKAN                                           */}
      {/* ===================================================================== */}
      {subTab === "repealed" && snapshot && (
        <section className="space-y-3 rounded-2xl border border-rose-200 bg-white p-4 shadow-sm sm:p-6">
          <div className="flex items-start gap-3 border-b border-rose-100 pb-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-800">
              <Ban className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-rose-950 sm:text-base">
                Senarai Akta &amp; Peraturan Yang Telah Dimansuhkan
              </h3>
              <p className="text-xs text-slate-600">
                Elakkan memetik mana-mana peruntukan lapuk di bawah dalam Notis Kompaun atau Borang 114.
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
                  <span className="rounded-full bg-rose-700 px-2.5 py-0.5 text-[10px] font-extrabold text-white">
                    {rep.status === "DIMANSUHKAN"
                      ? "Dimansuhkan"
                      : rep.status === "TAMAT_TEMPOH"
                        ? "Tamat Tempoh"
                        : "Tidak Sah Digunakan"}
                  </span>
                  {isDevAdmin && (
                    <span className="font-mono text-[10px] font-bold text-rose-900">
                      {rep.provision_id}
                    </span>
                  )}
                </div>
                <h4 className="mt-2 text-sm font-extrabold text-slate-900">
                  {rep.repealed_statute_or_section}
                </h4>
                <p className="mt-1.5 leading-relaxed text-slate-800">
                  {rep.warning_message_bm}
                </p>
                {rep.replacement_section && (
                  <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50/70 p-2.5 text-emerald-950">
                    <strong>Guna Seksyen Ini Sebagai Ganti:</strong> {rep.replacement_section}
                  </div>
                )}
                {rep.key_differences_note && (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-amber-950">
                    <strong>Perbezaan Penting:</strong> {rep.key_differences_note}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ===================================================================== */}
      {/* SUB-TAB 4: ADMIN WARTA (DIPAPARKAN KEPADA AKAUN ADMIN SAHAJA)         */}
      {/* ===================================================================== */}
      {isDevAdmin && subTab === "admin" && (
        <div className="space-y-4">
          {/* 1. Papan Pemuka Audit Liputan Akta (Coverage Audit Dashboard) */}
          <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900 sm:text-base">
                  Semakan Liputan Pustaka Akta
                </h3>
                <p className="text-xs text-slate-600">
                  Semak bilangan seksyen penuh yang diindeks daripada Warta rasmi, status pengesahan pentadbir dan versi pustaka akta.
                </p>
              </div>

              <button
                type="button"
                onClick={() => void handlePurgeQaCache()}
                className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2 text-xs font-extrabold text-rose-900 hover:bg-rose-100"
              >
                <Trash2 className="h-3.5 w-3.5 text-rose-700" />
                Segarkan Jawapan Terdahulu Lama
              </button>
            </div>

            {coverage && coverage.unverified_statutes.length > 0 && (
              <div className="flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3.5 py-2.5 text-xs font-bold text-amber-950">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700" />
                <span>
                  Nota Semakan: Statut berikut belum disahkan oleh pentadbir:{" "}
                  {coverage.unverified_statutes.join(", ")}
                </span>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs font-extrabold uppercase text-slate-600">
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
                          <div className="text-xs font-semibold text-[#0f2744]">
                            {st.canonical_akta_code}
                          </div>
                        </td>
                        <td className="p-2.5">
                          <div className="font-bold text-slate-900">{st.official_title_bm}</div>
                          <div className="text-xs text-slate-500">
                            {st.act_number_or_pu} • SHA256:{" "}
                            {(st.source_pdf_hash || "").slice(0, 10)}...
                          </div>
                        </td>
                        <td className="p-2.5 font-semibold text-slate-700">
                          {st.effective_date}
                        </td>
                        <td className="p-2.5">
                          {isUnindexed ? (
                            <span className="rounded bg-rose-700 px-2 py-0.5 text-xs font-extrabold text-white">
                              0 Seksyen (Belum Diindeks)
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
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-extrabold text-emerald-900">
                              <CheckCircle2 className="h-3 w-3" /> Disahkan Warta
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border border-yellow-300 bg-yellow-100 px-2.5 py-0.5 text-xs font-extrabold text-yellow-900">
                              <AlertTriangle className="h-3 w-3 text-yellow-700" /> Perlu Semakan Warta
                            </span>
                          )}
                        </td>
                        <td className="p-2.5">
                          <button
                            type="button"
                            onClick={() =>
                              void handleVerifyStatute(st.statute_id, !st.verified_by_admin)
                            }
                            className={`min-h-[36px] rounded-lg px-3 py-1 text-xs font-extrabold transition ${
                              st.verified_by_admin
                                ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                                : "bg-emerald-600 text-white hover:bg-emerald-700"
                            }`}
                          >
                            {st.verified_by_admin ? "Batal Pengesahan" : "Sahkan Warta"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* 2. Borang Muat Naik PDF Warta Kerajaan Persekutuan */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <form
              onSubmit={handleUploadGazettePdf}
              className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:col-span-7"
            >
              <div className="flex items-center gap-2 border-b border-slate-200 pb-2.5">
                <FileUp className="h-5 w-5 text-[#0f2744]" />
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900">
                    Muat Naik &amp; Indeks Fail PDF Warta Kerajaan Rasmi
                  </h4>
                  <p className="text-xs text-slate-600">
                    Sistem akan membaca dan menyusun setiap Bahagian, Seksyen &amp; Jadual secara automatik serta menyegarkan jawapan terdahulu lama.
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
