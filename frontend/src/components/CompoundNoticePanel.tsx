"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Download,
  Eraser,
  Loader2,
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
}

export default function CompoundNoticePanel({
  notice,
  onChangeNotice,
  onClearNotice,
  onAutoFillFromCase,
  autoFillLoading,
}: CompoundNoticePanelProps) {
  const [checkResult, setCheckResult] = useState<CompoundCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const updateField = (field: keyof NotisKompaunData, value: string) => {
    onChangeNotice({
      ...notice,
      [field]: value,
    });
  };

  const handleCheck = async () => {
    setChecking(true);
    setErrorMsg(null);
    try {
      const res = await checkCompoundNotice(notice);
      setCheckResult(res);
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
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50/70 p-3">
        <div>
          <h3 className="text-xs font-bold text-amber-950">
            Semakan Notis Kompaun / Notis S.32B &amp; S.47 (Sifar Kecacatan Teknikal)
          </h3>
          <p className="text-[11px] text-amber-900">
            Menyemak kesahihan 12 digit MyKad, ketepatan seksyen, had maksimum kompaun Akta (cth: RM500 Akta 154) &amp; tempoh bayaran sebelum cetakan.
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => {
              onClearNotice();
              setCheckResult(null);
            }}
            className="inline-flex items-center gap-1 rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50"
          >
            <Eraser className="h-3.5 w-3.5" />
            Kosongkan Borang
          </button>
          <button
            type="button"
            disabled={autoFillLoading}
            onClick={onAutoFillFromCase}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#0f2744] px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {autoFillLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5 text-amber-300" />
            )}
            Tarik Data Dari Kes Aktif
          </button>
        </div>
      </div>

      {/* Borang Notis Kompaun */}
      <div className="grid grid-cols-1 gap-2.5 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-2">
        <div>
          <label className="text-[11px] font-semibold text-slate-600">No. Rujukan Notis</label>
          <input
            type="text"
            value={notice.no_notis}
            onChange={(e) => updateField("no_notis", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">Tarikh &amp; Masa Kesalahan</label>
          <input
            type="text"
            value={notice.tarikh_masa || ""}
            onChange={(e) => updateField("tarikh_masa", e.target.value)}
            placeholder="cth: 14 Oktober 2026, 10.45 pagi"
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">Nama Penuh Penerima / OKT (Ikut MyKad)</label>
          <input
            type="text"
            value={notice.nama_penerima}
            onChange={(e) => updateField("nama_penerima", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">No. Kad Pengenalan (12 Digit)</label>
          <input
            type="text"
            value={notice.no_kp}
            onChange={(e) => updateField("no_kp", e.target.value)}
            placeholder="cth: 890415-10-5321"
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">Nama Premis / Syarikat</label>
          <input
            type="text"
            value={notice.nama_premis}
            onChange={(e) => updateField("nama_premis", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">No. Daftar SSM (jika syarikat/kedai)</label>
          <input
            type="text"
            value={notice.no_ssm || ""}
            onChange={(e) => updateField("no_ssm", e.target.value)}
            placeholder="cth: 202101034892 (1435192-K)"
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div className="sm:col-span-2">
          <label className="text-[11px] font-semibold text-slate-600">Alamat Lengkap Tempat Kejadian</label>
          <input
            type="text"
            value={notice.alamat_kejadian || ""}
            onChange={(e) => updateField("alamat_kejadian", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">Peruntukan Kesalahan (Akta &amp; Seksyen)</label>
          <input
            type="text"
            value={notice.peruntukan_undang}
            onChange={(e) => updateField("peruntukan_undang", e.target.value)}
            placeholder="cth: Seksyen 10(1) Akta 852 & Peraturan 6 P.U.(A) 260/2024"
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">Peruntukan Kompaun</label>
          <input
            type="text"
            value={notice.peruntukan_kompaun || ""}
            onChange={(e) => updateField("peruntukan_kompaun", e.target.value)}
            placeholder="cth: Seksyen 48 Akta 852 / Seksyen 33 Akta 281"
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div className="sm:col-span-2">
          <label className="text-[11px] font-semibold text-slate-600">
            Butiran Kesalahan (Fakta yang dilihat oleh PPKP di premis)
          </label>
          <textarea
            rows={3}
            value={notice.kesalahan_ringkas}
            onChange={(e) => updateField("kesalahan_ringkas", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 p-2 text-xs"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">Amaun Kompaun (RM)</label>
          <input
            type="text"
            value={notice.amaun_kompaun_rm}
            onChange={(e) => updateField("amaun_kompaun_rm", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">Tempoh Bayaran (30 hari Akta 852 / 14 hari Akta 154&amp;281)</label>
          <input
            type="text"
            value={notice.tempoh_bayaran}
            onChange={(e) => updateField("tempoh_bayaran", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">Nama PPKP Pengeluar Notis</label>
          <input
            type="text"
            value={notice.pegawai_pengeluar || ""}
            onChange={(e) => updateField("pegawai_pengeluar", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">No. Kad Kuasa KKM</label>
          <input
            type="text"
            value={notice.no_kad_kuasa || ""}
            onChange={(e) => updateField("no_kad_kuasa", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">Status Serahan Notis</label>
          <select
            value={notice.status_serahan || "tandatangan_terima"}
            onChange={(e) => updateField("status_serahan", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
          >
            <option value="tandatangan_terima">OKT Tandatangan Terima di Premis</option>
            <option value="enggan_tandatangan">OKT Enggan Tandatangan (Perlu Saksi PPKP &amp; Pos AR)</option>
          </select>
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">Nama PPKP Saksi (jika OKT enggan terima)</label>
          <input
            type="text"
            value={notice.saksi_ppkp || ""}
            onChange={(e) => updateField("saksi_ppkp", e.target.value)}
            placeholder="Isi jika OKT enggan tandatangan"
            className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
          />
        </div>
      </div>

      {/* Butang Semak & Muat Turun */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={checking}
          onClick={handleCheck}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-700 px-4 py-2.5 text-xs font-bold text-white hover:bg-blue-800 disabled:opacity-60"
        >
          {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />}
          Semak 10 Perkara Wajib Notis
        </button>

        <button
          type="button"
          disabled={exporting}
          onClick={handleDownload}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-amber-700 disabled:opacity-60"
        >
          {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Muat Turun Notis (.docx)
        </button>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 p-2 text-xs text-rose-800">
          {errorMsg}
        </div>
      )}

      {/* Keputusan Semakan */}
      {checkResult && (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
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
                className="rounded bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-700 hover:bg-blue-100"
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
                className={`flex items-start gap-2 rounded-lg border p-2 text-xs ${
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
