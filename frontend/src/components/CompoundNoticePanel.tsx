"use client";

import React, { useRef, useState } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Download,
  FileUp,
  FolderOpen,
  Loader2,
  Save,
  Sparkles,
  XCircle,
} from "lucide-react";
import { checkCompoundNotice, downloadDocx } from "@/lib/api";
import type { CompoundCheckResult, NotisKompaunData } from "@/lib/types";

interface CompoundNoticePanelProps {
  notice: NotisKompaunData;
  onChangeNotice: (updated: NotisKompaunData) => void;
  onClearNotice: () => void;
  onAutoFillFromCase: () => void;
  onExtractFileForCompound: (file: File) => Promise<void>;
  onOpenCases?: () => void;
  autoFillLoading: boolean;
  activeCaseTitle?: string;
  hasCaseSource?: boolean;
  savingCase?: boolean;
  onSaveNotice?: () => void;
  onDownloaded?: (filename: string) => void;
}

const INPUT_CLASS =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 shadow-sm transition hover:border-blue-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm";

export default function CompoundNoticePanel({
  notice,
  onChangeNotice,
  onClearNotice,
  onAutoFillFromCase,
  onExtractFileForCompound,
  onOpenCases,
  autoFillLoading,
  activeCaseTitle,
  hasCaseSource = false,
  savingCase = false,
  onSaveNotice,
  onDownloaded,
}: CompoundNoticePanelProps) {
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

  const icDigits = (notice.no_kp || "").replace(/\D/g, "");
  const numericAmount = parseFloat((notice.amaun_kompaun_rm || "").replace(/[^0-9.]/g, "") || "0");
  const isAkta154OverLimit =
    /154|aedes|spbp/i.test(notice.peruntukan_undang || "") && numericAmount > 500;
  const needsWitness = notice.status_serahan === "enggan_tandatangan";

  const handleFileChosen = async (file: File | null) => {
    if (!file) return;
    setScanningFile(true);
    setErrorMsg(null);
    setDownloadOkMsg(null);
    try {
      await onExtractFileForCompound(file);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal membaca fail/foto untuk borang kompaun.");
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
    setExporting(true);
    setErrorMsg(null);
    setDownloadOkMsg(null);
    try {
      const fname = await downloadDocx("notis_kompaun", { notis_kompaun: notice });
      setDownloadOkMsg(
        `Fail ${fname} telah dimuat turun — semak folder Muat Turun / Files peranti anda.`
      );
      if (onDownloaded) onDownloaded(fname);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal muat turun notis .docx.");
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
    <div className="mx-auto max-w-4xl space-y-4">
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

      {/* Kad Utama Borang Kompaun (1 Skrin Fokus) */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        {/* Bar Atas Konteks & Auto-Isi */}
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div>
            <h2 className="text-base font-extrabold text-slate-900">
              Notis Kompaun Rasmi (S.32B / S.47 / S.25)
            </h2>
            <p className="mt-0.5 text-xs text-slate-600">
              {activeCaseTitle ? (
                <>
                  Kes Aktif: <strong className="text-slate-900">{activeCaseTitle}</strong>
                </>
              ) : (
                "Isi ruangan bertanda (*) atau imbas foto SSM / notis untuk isi secara automatik."
              )}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={scanningFile}
              onClick={() => cameraInputRef.current?.click()}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-900 hover:bg-blue-100 disabled:opacity-60 sm:hidden"
            >
              {scanningFile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              Kamera
            </button>

            <button
              type="button"
              disabled={scanningFile}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
            >
              {scanningFile ? (
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              ) : (
                <FileUp className="h-4 w-4 text-blue-700" />
              )}
              {scanningFile ? "Sedang Membaca..." : "Imbas Foto / SSM"}
            </button>

            {hasCaseSource ? (
              <button
                type="button"
                disabled={autoFillLoading}
                onClick={onAutoFillFromCase}
                className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-amber-50 px-3 py-2 text-xs font-bold text-amber-950 ring-1 ring-amber-300 hover:bg-amber-100 disabled:opacity-60"
              >
                {autoFillLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 text-amber-600" />
                )}
                Tarik Dari Kes Aktif
              </button>
            ) : (
              onOpenCases && (
                <button
                  type="button"
                  onClick={onOpenCases}
                  className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  <FolderOpen className="h-4 w-4 text-amber-600" />
                  Pilih Kes
                </button>
              )
            )}

            <button
              type="button"
              onClick={() => {
                onClearNotice();
                setCheckResult(null);
                setDownloadOkMsg(null);
              }}
              className="px-2 py-1 text-xs font-semibold text-slate-500 hover:text-rose-700 hover:underline"
            >
              Kosongkan
            </button>
          </div>
        </div>

        {/* 3 Bahagian Borang Terus Dengan Pemisah Garis Halus (Tanpa Kotak Bertindan) */}
        <div className="divide-y divide-slate-200 px-4 sm:px-6">
          {/* Bahagian 1 */}
          <div className="py-4 space-y-3">
            <h3 className="text-xs font-extrabold uppercase tracking-wide text-[#0f2744]">
              1. Maklumat Penerima (OKS) &amp; Premis
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Nama Penuh Penerima (Ikut MyKad) <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.nama_penerima}
                  onChange={(e) => updateField("nama_penerima", e.target.value)}
                  placeholder="Nama penuh seperti MyKad"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <div className="flex items-center justify-between gap-1">
                  <label className="text-xs font-semibold text-slate-700">
                    No. Kad Pengenalan (12 Digit) <span className="text-rose-600">*</span>
                  </label>
                  {icDigits.length > 0 && (
                    <span
                      className={`text-[11px] font-bold ${
                        icDigits.length === 12 ? "text-emerald-700" : "text-rose-600"
                      }`}
                    >
                      {icDigits.length}/12 digit
                    </span>
                  )}
                </div>
                <input
                  type="text"
                  inputMode="numeric"
                  value={notice.no_kp}
                  onChange={(e) => updateField("no_kp", e.target.value)}
                  placeholder="cth: 890415-10-5321"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Tarikh &amp; Masa Kesalahan <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.tarikh_masa || ""}
                  onChange={(e) => updateField("tarikh_masa", e.target.value)}
                  placeholder="cth: 14 Oktober 2026, 10.45 pagi"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  No. Rujukan Notis <span className="font-normal text-slate-400">(Pilihan)</span>
                </label>
                <input
                  type="text"
                  value={notice.no_notis}
                  onChange={(e) => updateField("no_notis", e.target.value)}
                  placeholder="cth: KKM/KOM/852/2026/001"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Nama Premis / Syarikat <span className="font-normal text-slate-400">(Pilihan)</span>
                </label>
                <input
                  type="text"
                  value={notice.nama_premis}
                  onChange={(e) => updateField("nama_premis", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  No. Daftar SSM <span className="font-normal text-slate-400">(Pilihan)</span>
                </label>
                <input
                  type="text"
                  value={notice.no_ssm || ""}
                  onChange={(e) => updateField("no_ssm", e.target.value)}
                  placeholder="cth: 202101034892 (1435192-K)"
                  className={INPUT_CLASS}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">
                  Alamat Lengkap Tempat Kejadian <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.alamat_kejadian || ""}
                  onChange={(e) => updateField("alamat_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
            </div>
          </div>

          {/* Bahagian 2 */}
          <div className="py-4 space-y-3">
            <h3 className="text-xs font-extrabold uppercase tracking-wide text-[#0f2744]">
              2. Kesalahan, Amaun &amp; Tempoh Bayaran
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Peruntukan Kesalahan (Akta &amp; Seksyen) <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={notice.peruntukan_undang}
                  onChange={(e) => updateField("peruntukan_undang", e.target.value)}
                  placeholder="cth: Seksyen 10(1) Akta 852"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Peruntukan Kuasa Mengkompaun{" "}
                  <span className="font-normal text-slate-400">(Pilihan)</span>
                </label>
                <input
                  type="text"
                  value={notice.peruntukan_kompaun || ""}
                  onChange={(e) => updateField("peruntukan_kompaun", e.target.value)}
                  placeholder="cth: Seksyen 48 Akta 852 / S.25 Akta 154"
                  className={INPUT_CLASS}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">
                  Butiran Kesalahan Ditemui PPKP <span className="text-rose-600">*</span>
                </label>
                <textarea
                  rows={3}
                  value={notice.kesalahan_ringkas}
                  onChange={(e) => updateField("kesalahan_ringkas", e.target.value)}
                  placeholder="Nyatakan perbuatan kesalahan yang dilihat di tempat pemeriksaan..."
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <label className="text-xs font-semibold text-slate-700">
                    Amaun Kompaun (RM) <span className="text-rose-600">*</span>
                  </label>
                  <div className="flex gap-1">
                    {["RM 250.00", "RM 500.00"].map((amt) => (
                      <button
                        key={amt}
                        type="button"
                        onClick={() => updateField("amaun_kompaun_rm", amt)}
                        className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700 hover:bg-blue-100 hover:text-blue-900"
                      >
                        {amt}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="text"
                  inputMode="decimal"
                  value={notice.amaun_kompaun_rm}
                  onChange={(e) => updateField("amaun_kompaun_rm", e.target.value)}
                  placeholder="cth: RM 250.00"
                  className={INPUT_CLASS}
                />
                {isAkta154OverLimit && (
                  <p className="mt-1 text-xs font-bold text-rose-700">
                    Amaran: Had maksimum kompaun Akta 154 ialah RM 500.00 (Seksyen 25)!
                  </p>
                )}
              </div>

              <div>
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <label className="text-xs font-semibold text-slate-700">
                    Tempoh Bayaran <span className="text-rose-600">*</span>
                  </label>
                  <div className="flex gap-1">
                    {[
                      { label: "14 hari (154/281)", val: "14 hari dari tarikh serahan notis" },
                      { label: "30 hari (852)", val: "30 hari dari tarikh tawaran kompaun" },
                    ].map((opt) => (
                      <button
                        key={opt.label}
                        type="button"
                        onClick={() => updateField("tempoh_bayaran", opt.val)}
                        className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700 hover:bg-blue-100 hover:text-blue-900"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="text"
                  value={notice.tempoh_bayaran}
                  onChange={(e) => updateField("tempoh_bayaran", e.target.value)}
                  placeholder="30 hari (Akta 852) / 14 hari (Akta 154 & 281)"
                  className={INPUT_CLASS}
                />
              </div>
            </div>
          </div>

          {/* Bahagian 3 */}
          <div className="py-4 space-y-3">
            <h3 className="text-xs font-extrabold uppercase tracking-wide text-[#0f2744]">
              3. Pegawai Pengeluar &amp; Status Serahan
            </h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
                  <option value="tandatangan_terima">OKT Tandatangan Terima di Premis</option>
                  <option value="enggan_tandatangan">OKT Enggan Tandatangan (Perlu Saksi PPKP &amp; Pos AR)</option>
                </select>
              </div>

              {needsWitness && (
                <div>
                  <label className="text-xs font-bold text-amber-900">
                    Nama PPKP Saksi (Wajib Kerana Enggan Tandatangan){" "}
                    <span className="text-rose-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={notice.saksi_ppkp || ""}
                    onChange={(e) => updateField("saksi_ppkp", e.target.value)}
                    placeholder="Masukkan nama & gred PPKP saksi"
                    className="mt-1 w-full rounded-lg border-2 border-amber-400 bg-white px-3 py-2 text-base text-slate-900 focus:border-blue-600 focus:outline-none sm:text-sm"
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bar Tindakan Jelas (1 Butang Utama + 2 Sekunder) */}
        <div className="flex flex-col gap-2 border-t border-slate-200 bg-slate-50/70 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={checking}
              onClick={handleCheck}
              className="inline-flex min-h-[42px] flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100 disabled:opacity-60 sm:flex-none"
            >
              {checking ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ClipboardCheck className="h-4 w-4 text-blue-700" />
              )}
              Semak 10 Perkara Wajib
            </button>

            {onSaveNotice && (
              <button
                type="button"
                disabled={savingCase}
                onClick={onSaveNotice}
                className="inline-flex min-h-[42px] flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100 disabled:opacity-60 sm:flex-none"
              >
                {savingCase ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 text-emerald-700" />
                )}
                Simpan ke Akaun PKD
              </button>
            )}
          </div>

          <button
            type="button"
            disabled={exporting}
            onClick={handleDownload}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4 text-amber-300" />
            )}
            Muat Turun Notis Word (.docx)
          </button>
        </div>
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

      {/* Keputusan Semakan: Isu GAGAL/SEMAK di atas, LULUS dilipat */}
      {checkResult && (
        <section
          ref={resultRef}
          className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
            <div>
              <div className="text-xs font-semibold text-slate-500">Keputusan Semakan Notis</div>
              <div className="text-base font-extrabold text-slate-900">
                {checkResult.score_percent}% — {checkResult.readiness_status}
              </div>
            </div>
            <div className="flex gap-2 text-xs font-bold">
              <span className="rounded-lg bg-rose-50 px-2.5 py-1 text-rose-800">
                Gagal: {checkResult.counts.GAGAL}
              </span>
              <span className="rounded-lg bg-amber-50 px-2.5 py-1 text-amber-800">
                Semak: {checkResult.counts.SEMAK}
              </span>
              <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-emerald-800">
                Lulus: {checkResult.counts.LULUS}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-3 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-bold text-blue-950">Cadangan Ayat Kesalahan Statutori:</div>
              <button
                type="button"
                onClick={() => updateField("kesalahan_ringkas", checkResult.suggested_offense_text)}
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
              >
                Guna Ayat Ini
              </button>
            </div>
            <p className="mt-1.5 leading-relaxed text-slate-700">
              {checkResult.suggested_offense_text}
            </p>
          </div>

          {issueChecks.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-extrabold text-rose-900">
                Perkara Perlu Dibetulkan ({issueChecks.length})
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {issueChecks.map((item) => (
                  <div
                    key={item.code}
                    className={`flex items-start gap-2 rounded-xl border p-3 text-xs ${
                      item.status === "GAGAL"
                        ? "border-rose-200 bg-rose-50/70"
                        : "border-amber-200 bg-amber-50/70"
                    }`}
                  >
                    {item.status === "GAGAL" ? (
                      <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    )}
                    <div>
                      <div className="font-bold text-slate-900">
                        {item.code}: {item.label}
                      </div>
                      <div className="mt-0.5 text-xs text-slate-700">{item.note}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {passedChecks.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowPassedItems((v) => !v)}
                className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 hover:underline"
              >
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Lihat {passedChecks.length} perkara yang telah lulus</span>
                {showPassedItems ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showPassedItems && (
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {passedChecks.map((item) => (
                    <div
                      key={item.code}
                      className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50/30 p-2.5 text-xs"
                    >
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                      <div>
                        <div className="font-bold text-slate-900">
                          {item.code}: {item.label}
                        </div>
                        <div className="text-xs text-slate-600">{item.note}</div>
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
