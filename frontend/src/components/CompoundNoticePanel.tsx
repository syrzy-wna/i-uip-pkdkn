"use client";

import React, { useRef, useState } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ClipboardCheck,
  Download,
  Eraser,
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
  autoFillLoading: boolean;
  activeCaseTitle?: string;
  savingCase?: boolean;
  onSaveNotice?: () => void;
  onSwitchToInput?: () => void;
}

const INPUT_CLASS =
  "mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base text-slate-900 shadow-sm transition hover:border-blue-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:py-1.5 sm:text-xs";

export default function CompoundNoticePanel({
  notice,
  onChangeNotice,
  onClearNotice,
  onAutoFillFromCase,
  autoFillLoading,
  activeCaseTitle,
  savingCase = false,
  onSaveNotice,
  onSwitchToInput,
}: CompoundNoticePanelProps) {
  const [checkResult, setCheckResult] = useState<CompoundCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);

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

  const handleCheck = async () => {
    setChecking(true);
    setErrorMsg(null);
    try {
      const res = await checkCompoundNotice(notice);
      setCheckResult(res);
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
    try {
      await downloadDocx("notis_kompaun", { notis_kompaun: notice });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal muat turun notis .docx.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Bar Konteks & 3 Cara Mula */}
      <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3.5 space-y-2.5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-xs font-extrabold text-amber-950 sm:text-sm">
              Semak &amp; Cetak Notis Kompaun (S.32B / S.47 / S.25)
            </h3>
            <p className="text-[11px] text-amber-900">
              {activeCaseTitle ? (
                <>
                  Kes Aktif: <strong>{activeCaseTitle}</strong>
                </>
              ) : (
                "Isi borang di bawah secara manual atau tarik butiran daripada kes / gambar SSM."
              )}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={autoFillLoading}
            onClick={onAutoFillFromCase}
            className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {autoFillLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5 text-amber-300" />
            )}
            Tarik Data Dari Kes Aktif
          </button>

          {onSwitchToInput && (
            <button
              type="button"
              onClick={onSwitchToInput}
              className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-50"
            >
              <Camera className="h-3.5 w-3.5" />
              Imbas Foto Notis / SSM
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              onClearNotice();
              setCheckResult(null);
            }}
            className="inline-flex min-h-[38px] items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Eraser className="h-3.5 w-3.5" />
            Kosongkan
          </button>
        </div>
      </div>

      {/* Kumpulan 1: Penerima & Premis */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 space-y-2.5">
        <h4 className="text-xs font-extrabold text-[#0f2744]">
          1. Maklumat Penerima (OKS) &amp; Premis
        </h4>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <div>
            <label className="text-[11px] font-semibold text-slate-700">No. Rujukan Notis</label>
            <input
              type="text"
              value={notice.no_notis}
              onChange={(e) => updateField("no_notis", e.target.value)}
              placeholder="cth: KKM/KOM/852/2026/001"
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700">
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
            <label className="text-[11px] font-semibold text-slate-700">
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
              <label className="text-[11px] font-semibold text-slate-700">
                No. Kad Pengenalan (12 Digit) <span className="text-rose-600">*</span>
              </label>
              {icDigits.length > 0 && (
                <span
                  className={`text-[10px] font-bold ${
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
            <label className="text-[11px] font-semibold text-slate-700">Nama Premis / Syarikat</label>
            <input
              type="text"
              value={notice.nama_premis}
              onChange={(e) => updateField("nama_premis", e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700">No. Daftar SSM (jika ada)</label>
            <input
              type="text"
              value={notice.no_ssm || ""}
              onChange={(e) => updateField("no_ssm", e.target.value)}
              placeholder="cth: 202101034892 (1435192-K)"
              className={INPUT_CLASS}
            />
          </div>

          <div className="sm:col-span-2">
            <label className="text-[11px] font-semibold text-slate-700">
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

      {/* Kumpulan 2: Butiran Kesalahan & Amaun Kompaun */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 space-y-2.5">
        <h4 className="text-xs font-extrabold text-[#0f2744]">
          2. Peruntukan Undang-Undang, Fakta Kesalahan &amp; Amaun
        </h4>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <div>
            <label className="text-[11px] font-semibold text-slate-700">
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
            <label className="text-[11px] font-semibold text-slate-700">Peruntukan Kuasa Mengkompaun</label>
            <input
              type="text"
              value={notice.peruntukan_kompaun || ""}
              onChange={(e) => updateField("peruntukan_kompaun", e.target.value)}
              placeholder="cth: Seksyen 48 Akta 852 / S.25 Akta 154"
              className={INPUT_CLASS}
            />
          </div>

          <div className="sm:col-span-2">
            <label className="text-[11px] font-semibold text-slate-700">
              Butiran Kesalahan Ditemui PPKP <span className="text-rose-600">*</span>
            </label>
            <textarea
              rows={3}
              value={notice.kesalahan_ringkas}
              onChange={(e) => updateField("kesalahan_ringkas", e.target.value)}
              className={INPUT_CLASS}
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-700">
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
            {isAkta154OverLimit && (
              <p className="mt-1 text-[11px] font-bold text-rose-700">
                Amaran: Had maksimum kompaun Akta 154 ialah RM 500.00 (Seksyen 25)!
              </p>
            )}
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-700">
              Tempoh Bayaran <span className="text-rose-600">*</span>
            </label>
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

      {/* Kumpulan 3: Pegawai Pengeluar & Serahan */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 space-y-2.5">
        <h4 className="text-xs font-extrabold text-[#0f2744]">
          3. Maklumat Pegawai Pengeluar &amp; Status Serahan
        </h4>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <div>
            <label className="text-[11px] font-semibold text-slate-700">
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
            <label className="text-[11px] font-semibold text-slate-700">
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
            <label className="text-[11px] font-semibold text-slate-700">Status Serahan Notis</label>
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
              <label className="text-[11px] font-bold text-amber-900">
                Nama PPKP Saksi (Wajib Kerana OKT Enggan Tandatangan) <span className="text-rose-600">*</span>
              </label>
              <input
                type="text"
                value={notice.saksi_ppkp || ""}
                onChange={(e) => updateField("saksi_ppkp", e.target.value)}
                placeholder="Masukkan nama & gred PPKP saksi"
                className="mt-0.5 w-full rounded-lg border-2 border-amber-400 bg-white px-2.5 py-2 text-base text-slate-900 focus:border-blue-600 focus:outline-none sm:py-1.5 sm:text-xs"
              />
            </div>
          )}
        </div>
      </div>

      {/* Butang Tindakan Bernombor Jelas */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <button
          type="button"
          disabled={checking}
          onClick={handleCheck}
          className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-blue-700 px-3 py-2.5 text-xs font-extrabold text-white shadow-sm hover:bg-blue-800 disabled:opacity-60"
        >
          {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />}
          1. Semak 10 Perkara Wajib
        </button>

        {onSaveNotice && (
          <button
            type="button"
            disabled={savingCase}
            onClick={onSaveNotice}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2.5 text-xs font-extrabold text-emerald-900 hover:bg-emerald-100 disabled:opacity-60"
          >
            {savingCase ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            2. Simpan ke Kes
          </button>
        )}

        <button
          type="button"
          disabled={exporting}
          onClick={handleDownload}
          className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-amber-600 px-3 py-2.5 text-xs font-extrabold text-white shadow-sm hover:bg-amber-700 disabled:opacity-60"
        >
          {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          3. Muat Turun Notis (.docx)
        </button>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 p-2.5 text-xs font-semibold text-rose-800">
          {errorMsg}
        </div>
      )}

      {/* Keputusan Semakan */}
      {checkResult && (
        <div ref={resultRef} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[11px] font-semibold text-slate-500">Status Notis Kompaun</div>
              <div className="text-sm font-extrabold text-slate-900">
                {checkResult.score_percent}% — {checkResult.readiness_status}
              </div>
            </div>
            <div className="flex gap-1.5 text-[11px] font-bold">
              <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">
                LULUS: {checkResult.counts.LULUS}
              </span>
              <span className="rounded bg-amber-100 px-2 py-1 text-amber-800">
                SEMAK: {checkResult.counts.SEMAK}
              </span>
              <span className="rounded bg-rose-100 px-2 py-1 text-rose-800">
                GAGAL: {checkResult.counts.GAGAL}
              </span>
            </div>
          </div>

          <div className="rounded-lg border border-blue-200 bg-white p-2.5 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-bold text-blue-900">Cadangan Ayat Kesalahan Notis Kompaun:</div>
              <button
                type="button"
                onClick={() => updateField("kesalahan_ringkas", checkResult.suggested_offense_text)}
                className="rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-blue-700"
              >
                Guna Ayat Cadangan Ini
              </button>
            </div>
            <p className="mt-1 leading-relaxed text-slate-700">{checkResult.suggested_offense_text}</p>
          </div>

          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {checkResult.checks.map((item) => (
              <div
                key={item.code}
                className={`flex items-start gap-2 rounded-lg border p-2.5 text-xs ${
                  item.status === "LULUS"
                    ? "border-emerald-200 bg-white"
                    : item.status === "GAGAL"
                      ? "border-rose-200 bg-rose-50"
                      : "border-amber-200 bg-amber-50"
                }`}
              >
                {item.status === "LULUS" ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                ) : item.status === "GAGAL" ? (
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                ) : (
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                )}
                <div>
                  <div className="font-bold text-slate-900">
                    {item.code}: {item.label}
                  </div>
                  <div className="text-[11px] text-slate-600">{item.note}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
