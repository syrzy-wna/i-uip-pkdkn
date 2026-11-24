"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Camera,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Clock,
  Download,
  FileUp,
  FolderOpen,
  Loader2,
  Save,
  Sparkles,
  UserCheck,
  XCircle,
} from "lucide-react";
import { checkCompoundNotice, downloadDocx } from "@/lib/api";
import { formatDateTimeNowMalay } from "@/lib/uiHelpers";
import type { CompoundCheckResult, NotisKompaunData } from "@/lib/types";

interface CompoundNoticePanelProps {
  notice: NotisKompaunData;
  onChangeNotice: (updated: NotisKompaunData) => void;
  onClearNotice: () => void;
  onAutoFillFromCase: () => void;
  onExtractFileForCompound: (file: File) => Promise<void>;
  onOpenCases?: () => void;
  onOpenProfile?: () => void;
  missingKadKuasa?: boolean;
  autoFillLoading: boolean;
  activeCaseTitle?: string;
  hasCaseSource?: boolean;
  savingCase?: boolean;
  onSaveNotice?: () => void;
  onDownloaded?: (filename: string) => void;
  autoCheckNonce?: number;
  onAutoCheckConsumed?: () => void;
}

const INPUT_CLASS =
  "mt-1 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-900 transition hover:border-slate-400 focus:border-[#0f2744] focus:outline-none focus:ring-2 focus:ring-slate-200 sm:text-sm";

const COMMON_OFFENCE_PRESETS: Array<{
  label: string;
  peruntukan_undang: string;
  peruntukan_kompaun: string;
  amaun_kompaun_rm: string;
  tempoh_bayaran: string;
  kesalahan_ringkas: string;
}> = [
  {
    label: "Merokok Restoran (S.16(2))",
    peruntukan_undang: "Seksyen 16(2) Akta 852",
    peruntukan_kompaun: "Seksyen 48 Akta 852 [P.U. (A) 259/2024]",
    amaun_kompaun_rm: "RM 250.00",
    tempoh_bayaran: "30 hari dari tarikh tawaran kompaun",
    kesalahan_ringkas:
      "Menghisap produk merokok di tempat makan yang diisytiharkan sebagai kawasan larangan merokok.",
  },
  {
    label: "Tiada Tanda Larangan (S.18(1))",
    peruntukan_undang: "Seksyen 18(1)(a) Akta 852",
    peruntukan_kompaun: "Seksyen 48 Akta 852 [P.U. (A) 259/2024]",
    amaun_kompaun_rm: "RM 250.00",
    tempoh_bayaran: "30 hari dari tarikh tawaran kompaun",
    kesalahan_ringkas:
      "Gagal mempamerkan tanda amaran larangan merokok mengikut spesifikasi ditetapkan di premis makanan.",
  },
  {
    label: "Tiada Tifoid (P.31)",
    peruntukan_undang: "Peraturan 31(1) PPKM 2009 [P.U. (A) 95/2009]",
    peruntukan_kompaun: "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983",
    amaun_kompaun_rm: "RM 250.00",
    tempoh_bayaran: "14 hari dari tarikh serahan notis",
    kesalahan_ringkas:
      "Gagal mendapatkan suntikan vaksin antitifoid yang sah semasa mengendalikan makanan di premis makanan.",
  },
  {
    label: "Tiada LPM (P.30)",
    peruntukan_undang: "Peraturan 30(1) PPKM 2009 [P.U. (A) 95/2009]",
    peruntukan_kompaun: "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983",
    amaun_kompaun_rm: "RM 250.00",
    tempoh_bayaran: "14 hari dari tarikh serahan notis",
    kesalahan_ringkas:
      "Gagal menjalani Kursus Latihan Pengendali Makanan (LPM) di Sekolah Latihan Pengendali Makanan yang diiktiraf KKM.",
  },
  {
    label: "Premis Kotor (P.11)",
    peruntukan_undang: "Peraturan 11(1) PPKM 2009 [P.U. (A) 95/2009]",
    peruntukan_kompaun: "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983",
    amaun_kompaun_rm: "RM 500.00",
    tempoh_bayaran: "14 hari dari tarikh serahan notis",
    kesalahan_ringkas:
      "Gagal memastikan premis makanan bersih, kemas dan bebas daripada kekotoran serta kehadiran perosak.",
  },
  {
    label: "Pembiakan Aedes (S.13)",
    peruntukan_undang: "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154",
    peruntukan_kompaun: "Seksyen 25 Akta 154 (Maksimum RM500)",
    amaun_kompaun_rm: "RM 500.00",
    tempoh_bayaran: "14 hari dari tarikh serahan notis",
    kesalahan_ringkas:
      "Membiarkan pembiakan larva nyamuk Aedes di dalam bekas takungan air di kawasan premis.",
  },
];

export default function CompoundNoticePanel({
  notice,
  onChangeNotice,
  onClearNotice,
  onAutoFillFromCase,
  onExtractFileForCompound,
  onOpenCases,
  onOpenProfile,
  missingKadKuasa = false,
  autoFillLoading,
  activeCaseTitle,
  hasCaseSource = false,
  savingCase = false,
  onSaveNotice,
  onDownloaded,
  autoCheckNonce = 0,
  onAutoCheckConsumed,
}: CompoundNoticePanelProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [showOptionalPremise, setShowOptionalPremise] = useState(
    Boolean(notice.no_notis || notice.nama_premis || notice.no_ssm)
  );
  const [showOptionalAuthority, setShowOptionalAuthority] = useState(false);
  const [checkResult, setCheckResult] = useState<CompoundCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [scanningFile, setScanningFile] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [downloadOkMsg, setDownloadOkMsg] = useState<string | null>(null);
  const [showPassedItems, setShowPassedItems] = useState(false);
  const resultRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  const updateField = (field: keyof NotisKompaunData, value: string) => {
    onChangeNotice({
      ...notice,
      [field]: value,
    });
  };

  const applyPresetOffence = (preset: (typeof COMMON_OFFENCE_PRESETS)[number]) => {
    onChangeNotice({
      ...notice,
      peruntukan_undang: preset.peruntukan_undang,
      peruntukan_kompaun: preset.peruntukan_kompaun,
      amaun_kompaun_rm: preset.amaun_kompaun_rm,
      tempoh_bayaran: preset.tempoh_bayaran,
      kesalahan_ringkas: preset.kesalahan_ringkas,
    });
    setCheckResult(null);
    setErrorMsg(null);
  };

  const handleLoadDemoSample = async () => {
    const hasExisting = Boolean(
      (notice.nama_penerima || "").trim() ||
        (notice.no_kp || "").trim() ||
        (notice.kesalahan_ringkas || "").trim()
    );
    if (
      hasExisting &&
      !window.confirm(
        "Muatkan contoh notis kompaun ini? Data borang semasa yang belum disimpan akan diganti."
      )
    ) {
      return;
    }
    const sampleNotice: NotisKompaunData = {
      ...notice,
      no_notis: "KKM/UIP/KOM/154/2026/018",
      nama_penerima: "Ahmad Zaki bin Mohamad",
      no_kp: "840615-11-5123",
      nama_premis: "Kedai Serbaneka Harmoni",
      no_ssm: "202101034892",
      alamat_kejadian: "Lot 14, Jalan Harmoni 2, Taman Sejahtera, Malaysia",
      tarikh_masa: "18 November 2026, jam 10.15 pagi",
      peruntukan_undang: "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154",
      peruntukan_kompaun: "Seksyen 25 Akta 154 (Maksimum RM500)",
      kesalahan_ringkas:
        "Membiarkan pembiakan jentik-jentik nyamuk Aedes di dalam 2 baldi takungan air di bahagian belakang premis.",
      amaun_kompaun_rm: "RM 1000.00",
      tempoh_bayaran: "14 hari dari tarikh serahan notis",
      pegawai_pengeluar: notice.pegawai_pengeluar || "PPKP Mohd Amirul bin Hassan",
      no_kad_kuasa: notice.no_kad_kuasa || "KKM-UIP-2026-088",
      status_serahan: "tandatangan_terima",
      saksi_ppkp: "",
    };
    onChangeNotice(sampleNotice);
    setShowOptionalPremise(true);
    setStep(3);
    setChecking(true);
    setErrorMsg(null);
    try {
      const res = await checkCompoundNotice(sampleNotice);
      setCheckResult(res);
      setShowPassedItems(false);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal menyemak contoh notis kompaun.");
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    if (autoCheckNonce > 0) {
      onAutoCheckConsumed?.();
      setStep(3);
      setChecking(true);
      setErrorMsg(null);
      checkCompoundNotice(notice)
        .then((res) => {
          setCheckResult(res);
          setShowPassedItems(res.counts.GAGAL === 0 && res.counts.SEMAK === 0);
        })
        .catch((err) => {
          setErrorMsg(err instanceof Error ? err.message : "Gagal menyemak notis kompaun.");
        })
        .finally(() => setChecking(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoCheckNonce]);

  const icDigits = (notice.no_kp || "").replace(/\D/g, "");
  const numericAmount = parseFloat((notice.amaun_kompaun_rm || "").replace(/[^0-9.]/g, "") || "0");
  const isAkta154OverLimit =
    /154|aedes|spbp/i.test(notice.peruntukan_undang || "") && numericAmount > 500;
  const needsWitness = notice.status_serahan === "enggan_tandatangan";

  // Meter kelengkapan masa nyata (8 perkara teras)
  const readinessStats = useMemo(() => {
    const missing: string[] = [];
    if (!(notice.nama_penerima || "").trim()) missing.push("Nama OKS");
    if (!(notice.no_kp || "").trim()) missing.push("No. K/P / Pasport");
    if (!(notice.tarikh_masa || "").trim()) missing.push("Tarikh & Masa");
    if (!(notice.alamat_kejadian || "").trim()) missing.push("Alamat");
    if (!(notice.peruntukan_undang || "").trim()) missing.push("Seksyen");
    if ((notice.kesalahan_ringkas || "").trim().length < 15) missing.push("Butiran Kesalahan");
    if (!(notice.amaun_kompaun_rm || "").trim()) missing.push("Amaun RM");
    if (!(notice.tempoh_bayaran || "").trim()) missing.push("Tempoh Bayaran");
    return {
      completed: 8 - missing.length,
      total: 8,
      missing,
    };
  }, [notice]);

  const handleFileChosen = async (file: File | null) => {
    if (!file) return;
    const lowerName = file.name.toLowerCase();
    if (!/\.(pdf|docx|txt|png|jpe?g|webp)$/.test(lowerName) && !file.type.startsWith("image/")) {
      setErrorMsg("Jenis fail tidak disokong. Sila pilih foto, PDF, Word (.docx) atau teks (.txt).");
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setErrorMsg("Fail terlalu besar. Saiz maksimum yang dibenarkan ialah 15 MB.");
      return;
    }
    setScanningFile(true);
    setErrorMsg(null);
    setDownloadOkMsg(null);
    try {
      await onExtractFileForCompound(file);
      setShowOptionalPremise(true);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal membaca foto atau fail ini.");
    } finally {
      setScanningFile(false);
    }
  };

  const handleCheck = async () => {
    setChecking(true);
    setErrorMsg(null);
    try {
      const res = await checkCompoundNotice(notice);
      setCheckResult(res);
      setShowPassedItems(res.counts.GAGAL === 0 && res.counts.SEMAK === 0);
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal menyemak notis kompaun.");
    } finally {
      setChecking(false);
    }
  };

  const handleDownload = async () => {
    if (checkResult && checkResult.counts.GAGAL > 0) {
      const proceed = window.confirm(
        `Notis ini masih mempunyai ${checkResult.counts.GAGAL} perkara tidak lulus yang boleh menjejaskan kesahihan kompaun. Teruskan muat turun fail Word?`
      );
      if (!proceed) return;
    } else if (!checkResult && readinessStats.missing.length > 0) {
      const proceed = window.confirm(
        `Borang ini belum disemak dan masih mempunyai ${readinessStats.missing.length} ruangan asas belum diisi (${readinessStats.missing.join(", ")}). Teruskan muat turun fail Word?`
      );
      if (!proceed) return;
    }
    setExporting(true);
    setErrorMsg(null);
    setDownloadOkMsg(null);
    try {
      const fname = await downloadDocx("notis_kompaun", { notis_kompaun: notice });
      setDownloadOkMsg(
        `Fail ${fname} telah dimuat turun — semak ruang Muat Turun pada peranti anda.`
      );
      if (onDownloaded) onDownloaded(fname);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal memuat turun notis Word.");
    } finally {
      setExporting(false);
    }
  };

  const issueChecks = checkResult
    ? checkResult.checks.filter((item) => item.status !== "LULUS")
    : [];
  const passedChecks = checkResult
    ? checkResult.checks.filter((item) => item.status === "LULUS")
    : [];

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.docx,image/*"
        className="hidden"
        onChange={(e) => {
          handleFileChosen(e.target.files?.[0] || null);
          e.target.value = "";
        }}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          handleFileChosen(e.target.files?.[0] || null);
          e.target.value = "";
        }}
      />

      {/* Tip Kontekstual Profil (Hanya Jika Belum Simpan No. Kad Kuasa) */}
      {missingKadKuasa && onOpenProfile && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-950">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 shrink-0 text-amber-700" />
            <span>
              Simpan <strong>No. Kad Kuasa</strong> sekali sahaja dalam profil supaya setiap Notis Kompaun diisi secara automatik.
            </span>
          </div>
          <button
            type="button"
            onClick={onOpenProfile}
            className="inline-flex min-h-[44px] items-center rounded-lg px-2 font-bold text-[#0f2744] hover:bg-amber-100 hover:underline"
          >
            Lengkapkan Profil →
          </button>
        </div>
      )}

      {/* Kad Hero Pantas: Imbas Foto SSM & Pilihan Kesalahan Lazim */}
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-extrabold text-slate-900 sm:text-lg">
              Notis Kompaun Rasmi
            </h2>
            <p className="mt-0.5 text-xs text-slate-600 sm:text-sm">
              {activeCaseTitle ? (
                <>
                  Fail aktif: <strong className="text-slate-900">{activeCaseTitle}</strong>
                </>
              ) : (
                "Ambil atau muat naik foto Sijil SSM, atau pilih kesalahan lazim di bawah untuk mengisi borang dengan pantas."
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              const hasInput = Boolean(
                (notice.nama_penerima || "").trim() ||
                  (notice.kesalahan_ringkas || "").trim() ||
                  (notice.no_kp || "").trim()
              );
              if (
                hasInput &&
                !window.confirm("Kosongkan semua maklumat pada borang Notis Kompaun ini?")
              ) {
                return;
              }
              onClearNotice();
              setCheckResult(null);
              setDownloadOkMsg(null);
              setStep(1);
            }}
            className="inline-flex min-h-[44px] items-center rounded-lg px-3 text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-rose-700"
          >
            Kosongkan
          </button>
        </div>

        {/* Kad Tindakan Hero: Imbas SSM / Kamera / Contoh */}
        <div className="space-y-2.5 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
          <div className="text-xs font-bold text-slate-800">
            Jimat Masa: Baca Butiran Automatik daripada Foto SSM atau Kes Sedia Ada
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={scanningFile}
              onClick={() => cameraInputRef.current?.click()}
              className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {scanningFile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              {scanningFile ? "Sedang membaca foto..." : "Ambil Foto SSM"}
            </button>

            <button
              type="button"
              disabled={scanningFile}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex min-h-[44px] items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100 disabled:opacity-60"
            >
              <FileUp className="h-4 w-4 text-[#0f2744]" />
              Muat Naik Foto / PDF
            </button>

            {hasCaseSource ? (
              <button
                type="button"
                disabled={autoFillLoading}
                onClick={onAutoFillFromCase}
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100 disabled:opacity-60"
              >
                {autoFillLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-amber-600" />}
                Isi Automatik daripada Kes
              </button>
            ) : (
              onOpenCases && (
                <button
                  type="button"
                  onClick={onOpenCases}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100"
                >
                  <FolderOpen className="h-4 w-4 text-slate-600" />
                  Pilih Fail Kes
                </button>
              )
            )}

            <button
              type="button"
              disabled={checking}
              onClick={() => void handleLoadDemoSample()}
              className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-[#0f2744] hover:bg-slate-100 disabled:opacity-60"
            >
              {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-amber-600" />}
              Cuba Contoh (Lihat Amaran Had RM500)
            </button>
          </div>
        </div>

        {/* Meter Semakan Pantas Masa Nyata */}
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-bold text-slate-900">
              Kelengkapan Asas: {readinessStats.completed}/{readinessStats.total}
            </span>
            {readinessStats.missing.length > 0 ? (
              <span className="text-slate-600">
                • Belum diisi: {readinessStats.missing.slice(0, 3).join(", ")}
                {readinessStats.missing.length > 3 ? ` (+${readinessStats.missing.length - 3})` : ""}
              </span>
            ) : (
              <span className="font-semibold text-emerald-700">• Semua ruangan asas lengkap</span>
            )}
          </div>
          <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-[#0f2744] transition-all"
              style={{ width: `${Math.round((readinessStats.completed / readinessStats.total) * 100)}%` }}
            />
          </div>
        </div>

        {/* Bar 3 Langkah Stepper (Boleh Klik Terus) */}
        <div className="grid grid-cols-3 gap-2 pt-1">
          {[
            { num: 1 as const, label: "1. Penerima & Tempat", shortLabel: "1. Penerima" },
            { num: 2 as const, label: "2. Kesalahan & Amaun", shortLabel: "2. Kesalahan" },
            { num: 3 as const, label: "3. Semak & Muat Turun", shortLabel: "3. Semak" },
          ].map((s) => {
            const active = step === s.num;
            return (
              <button
                key={s.num}
                type="button"
                onClick={() => setStep(s.num)}
                className={`min-h-[44px] rounded-xl border px-2.5 py-2 text-xs font-bold transition ${
                  active
                    ? "border-[#0f2744] bg-[#0f2744] text-white shadow-sm"
                    : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
              >
                <span className="hidden sm:inline">{s.label}</span>
                <span className="sm:hidden">{s.shortLabel}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* KANDUNGAN MENGIKUT LANGKAH (1 KAD RATA, MAKSIMUM 4–5 MEDAN) */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 space-y-5">
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">
                Langkah 1: Maklumat Penerima Notis (OKS) &amp; Lokasi
              </h3>
              <p className="mt-0.5 text-xs text-slate-600">
                Isi 4 ruangan wajib di bawah. Maklumat premis/SSM boleh ditambah jika perlu.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Nama Penuh Penerima Notis (OKS) <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.nama_penerima}
                  onChange={(e) => updateField("nama_penerima", e.target.value)}
                  placeholder="Nama penuh seperti MyKad / Pasport"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <div className="flex items-center justify-between gap-1">
                  <label className="text-xs font-semibold text-slate-700">
                    No. K/P (12 Digit) / Pasport / SSM <span className="text-rose-600">*</span>
                  </label>
                  {icDigits.length > 0 && !/[a-zA-Z]/.test(notice.no_kp || "") && (
                    <span
                      className={`text-xs font-bold ${
                        icDigits.length === 12 ? "text-emerald-700" : "text-rose-600"
                      }`}
                    >
                      {icDigits.length}/12
                    </span>
                  )}
                </div>
                <input
                  type="text"
                  inputMode="text"
                  value={notice.no_kp}
                  onChange={(e) => updateField("no_kp", e.target.value)}
                  placeholder="cth: 890415-10-5321 atau A12345678"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-xs font-semibold text-slate-700">
                    Tarikh &amp; Masa Kesalahan <span className="text-rose-600">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => updateField("tarikh_masa", formatDateTimeNowMalay(true))}
                    className="inline-flex min-h-[32px] items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-[#0f2744] hover:bg-slate-200"
                  >
                    <Clock className="h-3 w-3" />
                    Sekarang
                  </button>
                </div>
                <input
                  type="text"
                  value={notice.tarikh_masa || ""}
                  onChange={(e) => updateField("tarikh_masa", e.target.value)}
                  placeholder="cth: 18 November 2026, 10.30 pagi"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Alamat Tempat Kejadian <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.alamat_kejadian || ""}
                  onChange={(e) => updateField("alamat_kejadian", e.target.value)}
                  placeholder="Alamat penuh lokasi pemeriksaan"
                  className={INPUT_CLASS}
                />
              </div>
            </div>

            <div className="border-t border-slate-200 pt-3">
              <button
                type="button"
                onClick={() => setShowOptionalPremise((v) => !v)}
                className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-[#0f2744] hover:underline"
              >
                {showOptionalPremise ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                <span>Butiran Premis, No. SSM &amp; No. Siri Notis (Pilihan)</span>
              </button>

              {showOptionalPremise && (
                <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-700">No. Siri Notis</label>
                    <input
                      type="text"
                      value={notice.no_notis}
                      onChange={(e) => updateField("no_notis", e.target.value)}
                      placeholder="cth: KKM/KOM/852/2026/001"
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">Nama Premis / Syarikat</label>
                    <input
                      type="text"
                      value={notice.nama_premis}
                      onChange={(e) => updateField("nama_premis", e.target.value)}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">No. Daftar SSM</label>
                    <input
                      type="text"
                      value={notice.no_ssm || ""}
                      onChange={(e) => updateField("no_ssm", e.target.value)}
                      placeholder="cth: 202101034892"
                      className={INPUT_CLASS}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end border-t border-slate-200 pt-4">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white hover:bg-slate-800 sm:w-auto"
              >
                Seterusnya: Kesalahan &amp; Amaun <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">
                Langkah 2: Kesalahan, Amaun &amp; Tempoh Bayaran
              </h3>
              <p className="mt-0.5 text-xs text-slate-600">
                Pilih satu kesalahan lazim di bawah untuk mengisi seksyen, amaun &amp; tempoh bayaran secara automatik, atau taip sendiri.
              </p>
            </div>

            {/* Cip 1-Klik Kesalahan Lazim */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-slate-700">Pilihan Pantas Kesalahan Lazim:</div>
              <div className="flex flex-wrap gap-2">
                {COMMON_OFFENCE_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => applyPresetOffence(preset)}
                    className="min-h-[44px] rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-800 transition hover:border-[#0f2744] hover:bg-slate-100"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Seksyen Kesalahan (Akta &amp; Seksyen) <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.peruntukan_undang}
                  onChange={(e) => updateField("peruntukan_undang", e.target.value)}
                  placeholder="cth: Seksyen 16(2) Akta 852 / Peraturan 31(1) PPKM 2009"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Butiran Kesalahan Ditemui PPKP <span className="text-rose-600">*</span>
                </label>
                <textarea
                  rows={3}
                  value={notice.kesalahan_ringkas}
                  onChange={(e) => updateField("kesalahan_ringkas", e.target.value)}
                  placeholder="Nyatakan kesalahan yang ditemui semasa pemeriksaan..."
                  className={INPUT_CLASS}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-slate-700">
                    Amaun Kompaun (RM) <span className="text-rose-600">*</span>
                  </label>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={notice.amaun_kompaun_rm}
                    onChange={(e) => updateField("amaun_kompaun_rm", e.target.value)}
                    placeholder="cth: RM 250.00"
                    className={INPUT_CLASS}
                  />
                  <div className="mt-2 flex flex-wrap gap-2">
                    {["RM 250.00", "RM 500.00"].map((amt) => (
                      <button
                        key={amt}
                        type="button"
                        onClick={() => updateField("amaun_kompaun_rm", amt)}
                        className="min-h-[44px] rounded-xl border border-slate-300 bg-slate-50 px-3.5 text-xs font-bold text-slate-800 hover:bg-slate-100"
                      >
                        {amt}
                      </button>
                    ))}
                  </div>
                  {isAkta154OverLimit && (
                    <p className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-xs font-bold text-rose-800">
                      Amaran: Had maksimum kompaun Akta 154 ialah RM 500.00 (Seksyen 25).
                    </p>
                  )}
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700">
                    Tempoh Bayaran <span className="text-rose-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={notice.tempoh_bayaran}
                    onChange={(e) => updateField("tempoh_bayaran", e.target.value)}
                    placeholder="30 hari (Akta 852) / 14 hari (Akta 154 & 281)"
                    className={INPUT_CLASS}
                  />
                  <div className="mt-2 flex flex-wrap gap-2">
                    {[
                      { label: "14 hari (Akta 154 / 281)", val: "14 hari dari tarikh serahan notis" },
                      { label: "30 hari (Akta 852)", val: "30 hari dari tarikh tawaran kompaun" },
                    ].map((opt) => (
                      <button
                        key={opt.label}
                        type="button"
                        onClick={() => updateField("tempoh_bayaran", opt.val)}
                        className="min-h-[44px] rounded-xl border border-slate-300 bg-slate-50 px-3.5 text-xs font-bold text-slate-800 hover:bg-slate-100"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-2">
                <button
                  type="button"
                  onClick={() => setShowOptionalAuthority((v) => !v)}
                  className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-slate-900"
                >
                  {showOptionalAuthority ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  <span>Peruntukan Kuasa Mengkompaun (Diisi Automatik / Pilihan)</span>
                </button>
                {showOptionalAuthority && (
                  <div className="mt-2">
                    <input
                      type="text"
                      value={notice.peruntukan_kompaun || ""}
                      onChange={(e) => updateField("peruntukan_kompaun", e.target.value)}
                      placeholder="cth: Seksyen 48 Akta 852 / Seksyen 25 Akta 154"
                      className={INPUT_CLASS}
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-4">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
              >
                <ArrowLeft className="h-4 w-4" /> Kembali
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep(3);
                  void handleCheck();
                }}
                className="inline-flex min-h-[46px] items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white hover:bg-slate-800"
              >
                Semak 10 Perkara &amp; Sedia Muat Turun <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">
                Langkah 3: Pegawai Pengeluar, Semakan &amp; Muat Turun Word
              </h3>
              <p className="mt-0.5 text-xs text-slate-600">
                Pastikan butiran pegawai dan keputusan semakan 10 perkara adalah sah sebelum dicetak.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Nama PPKP Pengeluar Notis <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.pegawai_pengeluar || ""}
                  onChange={(e) => updateField("pegawai_pengeluar", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  No. Kad Kuasa KKM <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.no_kad_kuasa || ""}
                  onChange={(e) => updateField("no_kad_kuasa", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>

              <div className={needsWitness ? "" : "sm:col-span-2"}>
                <label className="text-xs font-semibold text-slate-700">Status Serahan Notis</label>
                <select
                  value={notice.status_serahan || "tandatangan_terima"}
                  onChange={(e) => updateField("status_serahan", e.target.value)}
                  className={INPUT_CLASS}
                >
                  <option value="tandatangan_terima">Penerima (OKS) Tandatangan Terima</option>
                  <option value="enggan_tandatangan">Penerima Enggan Tandatangan (Perlu Saksi PPKP &amp; Pos Berdaftar Kad AR)</option>
                </select>
              </div>

              {needsWitness && (
                <div>
                  <label className="text-xs font-bold text-amber-900">
                    Nama PPKP Saksi (Wajib) <span className="text-rose-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={notice.saksi_ppkp || ""}
                    onChange={(e) => updateField("saksi_ppkp", e.target.value)}
                    placeholder="Nama & gred PPKP saksi"
                    className="mt-1 w-full rounded-xl border-2 border-amber-400 bg-white px-3.5 py-2.5 text-base text-slate-900 focus:border-[#0f2744] focus:outline-none sm:text-sm"
                  />
                </div>
              )}
            </div>

            {/* Bar Tindakan Utama */}
            <div className="flex flex-col gap-2.5 border-t border-slate-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  <ArrowLeft className="h-4 w-4" /> Sunting Kesalahan
                </button>

                <button
                  type="button"
                  disabled={checking}
                  onClick={handleCheck}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
                >
                  {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4 text-[#0f2744]" />}
                  Semak Semula (10 Perkara)
                </button>

                {onSaveNotice && (
                  <button
                    type="button"
                    disabled={savingCase}
                    onClick={onSaveNotice}
                    className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
                  >
                    {savingCase ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4 text-emerald-700" />}
                    Simpan Kes
                  </button>
                )}
              </div>

              <button
                type="button"
                disabled={exporting}
                onClick={handleDownload}
                className="inline-flex min-h-[46px] items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60"
              >
                {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Muat Turun Word (.docx)
              </button>
            </div>
          </div>
        )}
      </section>

      {errorMsg && (
        <div className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-800">
          {errorMsg}
        </div>
      )}

      {downloadOkMsg && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-xs font-bold text-emerald-900">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>{downloadOkMsg}</span>
        </div>
      )}

      {/* Keputusan Semakan 10 Perkara */}
      {checkResult && (
        <section
          ref={resultRef}
          className="scroll-mt-20 space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
            <div>
              <div className="text-xs font-semibold text-slate-500">Keputusan Semakan Notis</div>
              <div className="text-base font-extrabold text-slate-900">
                {checkResult.score_percent}% — {checkResult.readiness_status}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-bold">
              {checkResult.counts.GAGAL > 0 && (
                <span className="rounded-full bg-rose-100 px-3 py-1 text-rose-800">
                  Gagal: {checkResult.counts.GAGAL}
                </span>
              )}
              {checkResult.counts.SEMAK > 0 && (
                <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-900">
                  Semak: {checkResult.counts.SEMAK}
                </span>
              )}
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800">
                Lulus: {checkResult.counts.LULUS}
              </span>
            </div>
          </div>

          {issueChecks.length > 0 && (
            <div className="space-y-2.5">
              <div className="text-xs font-extrabold text-rose-900">
                Perkara Perlu Dibetulkan ({issueChecks.length})
              </div>
              <div className="divide-y divide-slate-200 rounded-xl border border-slate-200">
                {issueChecks.map((item) => (
                  <div
                    key={item.code}
                    className={`flex items-start justify-between gap-3 p-3.5 text-xs ${
                      item.status === "GAGAL" ? "bg-rose-50/40" : "bg-amber-50/40"
                    }`}
                  >
                    <div className="flex min-w-0 flex-1 items-start gap-2.5">
                      {item.status === "GAGAL" ? (
                        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                      ) : (
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                      )}
                      <div className="min-w-0 flex-1 break-words">
                        <div className="text-sm font-bold text-slate-900">{item.label}</div>
                        <div className="mt-0.5 text-xs leading-relaxed text-slate-700">{item.note}</div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (item.code === "K03" || item.code === "K04") {
                          setStep(1);
                          setShowOptionalPremise(true);
                        } else if (["K01", "K02", "K05"].includes(item.code)) {
                          setStep(1);
                        } else if (["K06", "K07", "K08"].includes(item.code)) {
                          setStep(2);
                        } else if (item.code === "K09") {
                          if ((notice.pegawai_pengeluar || "").trim() && (notice.no_kad_kuasa || "").trim()) {
                            setStep(1);
                            setShowOptionalPremise(true);
                          } else {
                            setStep(3);
                          }
                        } else {
                          setStep(3);
                        }
                        if (typeof window !== "undefined") {
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }
                      }}
                      className="inline-flex min-h-[44px] shrink-0 items-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-[#0f2744] hover:bg-slate-50"
                    >
                      Baiki
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-bold text-slate-900">Cadangan Ayat Rasmi Butiran Kesalahan:</div>
              <button
                type="button"
                disabled={notice.kesalahan_ringkas.trim() === checkResult.suggested_offense_text.trim()}
                onClick={() => {
                  const suggested = (checkResult.suggested_offense_text || "").trim();
                  if (!suggested) return;
                  setErrorMsg(null);
                  updateField("kesalahan_ringkas", suggested);
                }}
                className="min-h-[44px] rounded-lg bg-[#0f2744] px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {notice.kesalahan_ringkas.trim() === checkResult.suggested_offense_text.trim()
                  ? "Ayat Sudah Digunakan"
                  : "Guna Ayat Ini"}
              </button>
            </div>
            <p className="mt-2 break-words text-sm leading-relaxed text-slate-700">
              {checkResult.suggested_offense_text}
            </p>
          </div>

          {passedChecks.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowPassedItems((v) => !v)}
                className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-emerald-800 hover:underline"
              >
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Lihat {passedChecks.length} perkara yang telah lulus</span>
                {showPassedItems ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showPassedItems && (
                <div className="mt-2 divide-y divide-slate-100 rounded-xl border border-slate-200">
                  {passedChecks.map((item) => (
                    <div key={item.code} className="flex items-start gap-2.5 p-3 text-xs">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                      <div className="min-w-0 flex-1 break-words">
                        <div className="font-bold text-slate-900">{item.label}</div>
                        <div className="text-slate-600">{item.note}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
