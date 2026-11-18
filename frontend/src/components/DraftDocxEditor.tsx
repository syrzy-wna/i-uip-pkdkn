"use client";

import React, { useState } from "react";
import {
  BookCheck,
  Download,
  FileCheck2,
  FileText,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { downloadDocx } from "@/lib/api";
import type { DraftGenerationResponse, MinitEntry } from "@/lib/types";

interface DraftDocxEditorProps {
  draft: DraftGenerationResponse | null;
  onChangeDraft: (updated: DraftGenerationResponse) => void;
}

export default function DraftDocxEditor({
  draft,
  onChangeDraft,
}: DraftDocxEditorProps) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  if (!draft) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-10 text-center">
        <FileText className="mb-3 h-10 w-10 text-slate-400" />
        <h3 className="text-sm font-bold text-slate-700">
          Editor Penuh Fail Kertas Siasatan (IP) &amp; Dokumen Rasmi .docx
        </h3>
        <p className="mt-1 max-w-md text-xs text-slate-500">
          Tekan <strong>Jana Fail IP &amp; Borang 114</strong> di sebelah kiri
          untuk membina Kulit IP, Indeks A–H, Minit 1–4, Borang 143, Borang 114 Mahkamah,
          Fakta Kes, Senarai Saksi, Barang Kes, Sijil 90A, Rakaman S.112 &amp; Diari Siasatan.
        </p>
      </div>
    );
  }

  const handleExport = async (
    docType:
      | "borang_114"
      | "saman_111"
      | "diari_siasatan"
      | "rakaman_112"
      | "pakej_ip"
      | "notis_kompaun"
  ) => {
    setExporting(docType);
    setExportError(null);
    try {
      await downloadDocx(docType, draft as unknown as Record<string, unknown>);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Gagal muat turun fail .docx");
    } finally {
      setExporting(null);
    }
  };

  const updateBorang114 = (
    field: keyof DraftGenerationResponse["borang_114"],
    value: string
  ) => {
    onChangeDraft({
      ...draft,
      borang_114: {
        ...draft.borang_114,
        [field]: value,
      },
    });
  };

  const minitList: MinitEntry[] = Array.isArray(draft.minit_ip)
    ? draft.minit_ip
    : [
        {
          bil: "Minit 1",
          tarikh: "-",
          daripada: "IO",
          kepada: "UIP / TPR",
          kandungan: String(draft.minit_ip || ""),
        },
      ];

  const addDiariRow = () => {
    const nextBil = String(draft.diari_siasatan.length + 1);
    onChangeDraft({
      ...draft,
      diari_siasatan: [
        ...draft.diari_siasatan,
        {
          bil: nextBil,
          tarikh: "Tarikh tindakan",
          masa: "Masa",
          butiran_tindakan: "Catatan tindakan susulan IO...",
          pegawai: draft.sijil_90a.nama_pegawai || "PPKP / IO",
        },
      ],
    });
  };

  const addSaksiRow = () => {
    const nextBil = `SP${draft.senarai_saksi.length + 1}`;
    onChangeDraft({
      ...draft,
      senarai_saksi: [
        ...draft.senarai_saksi,
        {
          bil: nextBil,
          nama: "",
          no_kp: "",
          jawatan_peranan: "Saksi Pendakwaan",
          alamat_hubungan: "",
        },
      ],
    });
  };

  const addEksibitRow = () => {
    const nextTanda = `P${draft.senarai_eksibit.length + 1}`;
    onChangeDraft({
      ...draft,
      senarai_eksibit: [
        ...draft.senarai_eksibit,
        {
          tanda: nextTanda,
          perihal: "",
          no_lak_seal: "-",
          lokasi_simpanan: "Stor Eksibit PKD",
        },
      ],
    });
  };

  return (
    <div className="space-y-4">
      {/* Bar Muat Turun Fail Word (.docx) */}
      <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-xs font-bold text-blue-950">
              Muat Turun Dokumen Rasmi Mahkamah Majistret &amp; UIP KKM (.docx)
            </h3>
            <p className="text-[11px] text-blue-800">
              Format rasmi perundangan (Borang 114 tulen, Kulit IP, Indeks A–H, Minit 1–4, Borang 143, Sijil 90A &amp; S.112).
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("borang_114")}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-[#0f2744] px-2 py-2 text-[11px] font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {exporting === "borang_114" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 text-amber-300" />
            )}
            Borang 114
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("diari_siasatan")}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-blue-700 px-2 py-2 text-[11px] font-bold text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {exporting === "diari_siasatan" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Diari Siasatan
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("rakaman_112")}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-700 px-2 py-2 text-[11px] font-bold text-white hover:bg-indigo-800 disabled:opacity-60"
          >
            {exporting === "rakaman_112" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Rakaman S.112
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("pakej_ip")}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-700 px-2 py-2 text-[11px] font-bold text-white hover:bg-emerald-800 disabled:opacity-60"
          >
            {exporting === "pakej_ip" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileCheck2 className="h-3.5 w-3.5" />
            )}
            Pakej IP Penuh
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("notis_kompaun")}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-amber-600 px-2 py-2 text-[11px] font-bold text-white hover:bg-amber-700 disabled:opacity-60"
          >
            {exporting === "notis_kompaun" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Notis Kompaun
          </button>
        </div>

        {exportError && (
          <p className="mt-2 text-xs font-semibold text-rose-700">{exportError}</p>
        )}
      </div>

      {/* 1. Kertas Minit Siasatan (Minit 1-4) */}
      <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
        <h4 className="text-xs font-bold text-slate-900">
          1. Kertas Minit Siasatan (Minit 1 – Minit 4)
        </h4>
        {minitList.map((m, idx) => (
          <div key={idx} className="rounded border border-slate-200 bg-slate-50/50 p-2 text-xs">
            <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[11px] font-bold text-slate-700">
              <span>{m.bil} ({m.daripada} → {m.kepada})</span>
              <span>Tarikh: {m.tarikh}</span>
            </div>
            <textarea
              rows={2}
              value={m.kandungan}
              onChange={(e) => {
                const next = [...minitList];
                next[idx] = { ...next[idx], kandungan: e.target.value };
                onChangeDraft({ ...draft, minit_ip: next });
              }}
              className="w-full rounded border border-slate-300 bg-white p-1.5 text-xs"
            />
          </div>
        ))}
      </div>

      {/* 2. Editor Lengkap Borang 114 */}
      <div className="space-y-2.5 rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
          <h4 className="text-xs font-bold text-slate-900">
            2. Kertas Pertuduhan Rasmi (Borang Mahkamah 114 — Seksyen 152-154 KTJ)
          </h4>
          <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
            {draft.akta_utama}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Mahkamah</label>
            <input
              type="text"
              value={draft.borang_114.mahkamah}
              onChange={(e) => updateBorang114("mahkamah", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">No. Kes / No. IP</label>
            <input
              type="text"
              value={draft.borang_114.no_kes}
              onChange={(e) => updateBorang114("no_kes", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Nama OKS / Tertuduh</label>
            <input
              type="text"
              value={draft.borang_114.nama_tertuduh}
              onChange={(e) => updateBorang114("nama_tertuduh", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">No. Kad Pengenalan</label>
            <input
              type="text"
              value={draft.borang_114.no_kp_tertuduh}
              onChange={(e) => updateBorang114("no_kp_tertuduh", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Umur / Jantina</label>
            <input
              type="text"
              value={draft.borang_114.umur_jantina || ""}
              onChange={(e) => updateBorang114("umur_jantina", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Pekerjaan / Jawatan</label>
            <input
              type="text"
              value={draft.borang_114.pekerjaan || ""}
              onChange={(e) => updateBorang114("pekerjaan", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-[11px] font-semibold text-slate-600">Alamat OKS</label>
            <input
              type="text"
              value={draft.borang_114.alamat_tertuduh}
              onChange={(e) => updateBorang114("alamat_tertuduh", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Tarikh Kejadian</label>
            <input
              type="text"
              value={draft.borang_114.tarikh_kejadian}
              onChange={(e) => updateBorang114("tarikh_kejadian", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Masa Kejadian</label>
            <input
              type="text"
              value={draft.borang_114.masa_kejadian}
              onChange={(e) => updateBorang114("masa_kejadian", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-[11px] font-semibold text-slate-600">Tempat Kejadian</label>
            <input
              type="text"
              value={draft.borang_114.tempat_kejadian}
              onChange={(e) => updateBorang114("tempat_kejadian", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Seksyen Kesalahan</label>
            <input
              type="text"
              value={draft.borang_114.akta_dan_seksyen}
              onChange={(e) => updateBorang114("akta_dan_seksyen", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Seksyen Hukuman</label>
            <input
              type="text"
              value={draft.borang_114.seksyen_hukuman}
              onChange={(e) => updateBorang114("seksyen_hukuman", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-[11px] font-semibold text-slate-600">Hukuman Statutori Maksimum</label>
            <input
              type="text"
              value={draft.borang_114.hukuman_maksimum || ""}
              onChange={(e) => updateBorang114("hukuman_maksimum", e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
        </div>

        <div>
          <label className="text-[11px] font-semibold text-slate-600">
            Teks Pertuduhan Rasmi Borang 114
          </label>
          <textarea
            rows={4}
            value={draft.borang_114.teks_pertuduhan}
            onChange={(e) => updateBorang114("teks_pertuduhan", e.target.value)}
            className="mt-0.5 w-full rounded border border-slate-300 bg-slate-50/50 p-2 text-xs leading-relaxed"
          />
        </div>
      </div>

      {/* 3. Fakta Kes & 4. Sijil Seksyen 90A(2) */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <h4 className="mb-1.5 text-xs font-bold text-slate-900">
            3. Fakta Kes Ringkas
          </h4>
          <textarea
            rows={9}
            value={draft.fakta_kes}
            onChange={(e) => onChangeDraft({ ...draft, fakta_kes: e.target.value })}
            className="w-full rounded border border-slate-300 bg-slate-50/50 p-2 text-xs leading-relaxed"
          />
        </div>

        <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
          <h4 className="text-xs font-bold text-slate-900">
            4. Sijil Seksyen 90A(2) Akta Keterangan 1950
          </h4>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Nama Pegawai</label>
              <input
                type="text"
                value={draft.sijil_90a.nama_pegawai}
                onChange={(e) =>
                  onChangeDraft({
                    ...draft,
                    sijil_90a: { ...draft.sijil_90a, nama_pegawai: e.target.value },
                  })
                }
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Jawatan</label>
              <input
                type="text"
                value={draft.sijil_90a.jawatan}
                onChange={(e) =>
                  onChangeDraft({
                    ...draft,
                    sijil_90a: { ...draft.sijil_90a, jawatan: e.target.value },
                  })
                }
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
              />
            </div>
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Kamera / Peranti Input</label>
            <input
              type="text"
              value={draft.sijil_90a.peranti_kamera || ""}
              onChange={(e) =>
                onChangeDraft({
                  ...draft,
                  sijil_90a: { ...draft.sijil_90a, peranti_kamera: e.target.value },
                })
              }
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Komputer &amp; Pencetak Pejabat</label>
            <input
              type="text"
              value={draft.sijil_90a.perihal_komputer}
              onChange={(e) =>
                onChangeDraft({
                  ...draft,
                  sijil_90a: { ...draft.sijil_90a, perihal_komputer: e.target.value },
                })
              }
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-slate-600">Senarai Dokumen Digital / Foto</label>
            <textarea
              rows={2}
              value={draft.sijil_90a.senarai_dokumen_digital}
              onChange={(e) =>
                onChangeDraft({
                  ...draft,
                  sijil_90a: {
                    ...draft.sijil_90a,
                    senarai_dokumen_digital: e.target.value,
                  },
                })
              }
              className="mt-0.5 w-full rounded border border-slate-300 p-1.5 text-xs"
            />
          </div>
        </div>
      </div>

      {/* 5. Jadual Dinamik Senarai Saksi & 6. Senarai Barang Kes (Eksibit) */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900">5. Senarai Saksi Pendakwaan (SP)</h4>
            <button
              type="button"
              onClick={addSaksiRow}
              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
            >
              <Plus className="h-3 w-3" /> Tambah Saksi
            </button>
          </div>
          <div className="space-y-1.5">
            {draft.senarai_saksi.map((s, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-1 rounded border border-slate-200 bg-slate-50/50 p-1.5 text-[11px]">
                <input
                  type="text"
                  value={s.bil}
                  onChange={(e) => {
                    const next = [...draft.senarai_saksi];
                    next[idx] = { ...next[idx], bil: e.target.value };
                    onChangeDraft({ ...draft, senarai_saksi: next });
                  }}
                  className="col-span-2 rounded border border-slate-300 bg-white px-1.5 py-1 font-bold"
                />
                <input
                  type="text"
                  placeholder="Nama Saksi"
                  value={s.nama}
                  onChange={(e) => {
                    const next = [...draft.senarai_saksi];
                    next[idx] = { ...next[idx], nama: e.target.value };
                    onChangeDraft({ ...draft, senarai_saksi: next });
                  }}
                  className="col-span-5 rounded border border-slate-300 bg-white px-1.5 py-1"
                />
                <input
                  type="text"
                  placeholder="Peranan"
                  value={s.jawatan_peranan}
                  onChange={(e) => {
                    const next = [...draft.senarai_saksi];
                    next[idx] = { ...next[idx], jawatan_peranan: e.target.value };
                    onChangeDraft({ ...draft, senarai_saksi: next });
                  }}
                  className="col-span-4 rounded border border-slate-300 bg-white px-1.5 py-1"
                />
                <button
                  type="button"
                  onClick={() => {
                    onChangeDraft({
                      ...draft,
                      senarai_saksi: draft.senarai_saksi.filter((_, i) => i !== idx),
                    });
                  }}
                  className="col-span-1 flex items-center justify-center text-rose-600 hover:text-rose-800"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900">6. Senarai Barang Kes / Eksibit (P)</h4>
            <button
              type="button"
              onClick={addEksibitRow}
              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
            >
              <Plus className="h-3 w-3" /> Tambah Eksibit
            </button>
          </div>
          <div className="space-y-1.5">
            {draft.senarai_eksibit.map((ex, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-1 rounded border border-slate-200 bg-slate-50/50 p-1.5 text-[11px]">
                <input
                  type="text"
                  value={ex.tanda}
                  onChange={(e) => {
                    const next = [...draft.senarai_eksibit];
                    next[idx] = { ...next[idx], tanda: e.target.value };
                    onChangeDraft({ ...draft, senarai_eksibit: next });
                  }}
                  className="col-span-2 rounded border border-slate-300 bg-white px-1.5 py-1 font-bold"
                />
                <input
                  type="text"
                  placeholder="Perihal Barang Kes"
                  value={ex.perihal}
                  onChange={(e) => {
                    const next = [...draft.senarai_eksibit];
                    next[idx] = { ...next[idx], perihal: e.target.value };
                    onChangeDraft({ ...draft, senarai_eksibit: next });
                  }}
                  className="col-span-6 rounded border border-slate-300 bg-white px-1.5 py-1"
                />
                <input
                  type="text"
                  placeholder="No. Lak"
                  value={ex.no_lak_seal || "-"}
                  onChange={(e) => {
                    const next = [...draft.senarai_eksibit];
                    next[idx] = { ...next[idx], no_lak_seal: e.target.value };
                    onChangeDraft({ ...draft, senarai_eksibit: next });
                  }}
                  className="col-span-3 rounded border border-slate-300 bg-white px-1.5 py-1"
                />
                <button
                  type="button"
                  onClick={() => {
                    onChangeDraft({
                      ...draft,
                      senarai_eksibit: draft.senarai_eksibit.filter((_, i) => i !== idx),
                    });
                  }}
                  className="col-span-1 flex items-center justify-center text-rose-600 hover:text-rose-800"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 7. Rakaman Percakapan S.112 KTJ */}
      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <h4 className="mb-1.5 text-xs font-bold text-slate-900">
          7. Draf Rakaman Percakapan Seksyen 112 KTJ (Patuh Subseksyen 112(2)-(5))
        </h4>
        <textarea
          rows={8}
          value={draft.rakaman_112 || ""}
          onChange={(e) => onChangeDraft({ ...draft, rakaman_112: e.target.value })}
          className="w-full rounded border border-slate-300 bg-slate-50/50 p-2 font-mono text-xs leading-relaxed"
        />
      </div>

      {/* 8. Diari Siasatan */}
      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-900">
            8. Diari Siasatan (DS — Seksyen 119 KTJ)
          </h4>
          <button
            type="button"
            onClick={addDiariRow}
            className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
          >
            <Plus className="h-3 w-3" /> Tambah Baris DS
          </button>
        </div>

        <div className="space-y-2">
          {draft.diari_siasatan.map((row, idx) => (
            <div
              key={`${row.bil}-${idx}`}
              className="grid grid-cols-1 gap-1.5 rounded border border-slate-200 bg-slate-50/50 p-2 sm:grid-cols-12"
            >
              <input
                type="text"
                value={row.bil}
                onChange={(e) => {
                  const next = [...draft.diari_siasatan];
                  next[idx] = { ...next[idx], bil: e.target.value };
                  onChangeDraft({ ...draft, diari_siasatan: next });
                }}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-bold sm:col-span-1"
              />
              <input
                type="text"
                value={row.tarikh || row.tarikh_masa || ""}
                onChange={(e) => {
                  const next = [...draft.diari_siasatan];
                  next[idx] = { ...next[idx], tarikh: e.target.value };
                  onChangeDraft({ ...draft, diari_siasatan: next });
                }}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] sm:col-span-2"
              />
              <input
                type="text"
                value={row.masa || ""}
                placeholder="Masa"
                onChange={(e) => {
                  const next = [...draft.diari_siasatan];
                  next[idx] = { ...next[idx], masa: e.target.value };
                  onChangeDraft({ ...draft, diari_siasatan: next });
                }}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] sm:col-span-2"
              />
              <input
                type="text"
                value={row.butiran_tindakan}
                onChange={(e) => {
                  const next = [...draft.diari_siasatan];
                  next[idx] = { ...next[idx], butiran_tindakan: e.target.value };
                  onChangeDraft({ ...draft, diari_siasatan: next });
                }}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] sm:col-span-6"
              />
              <button
                type="button"
                onClick={() => {
                  onChangeDraft({
                    ...draft,
                    diari_siasatan: draft.diari_siasatan.filter((_, i) => i !== idx),
                  });
                }}
                className="flex items-center justify-center rounded bg-rose-50 p-1 text-rose-600 hover:bg-rose-100 sm:col-span-1"
                title="Padam baris"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* 9. Jadual Kronologi Kes */}
      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-900">
            9. Kronologi Kes (Susunan Tarikh Klinikal &amp; Siasatan)
          </h4>
          <button
            type="button"
            onClick={() => {
              const current = draft.kronologi_kes || [];
              onChangeDraft({
                ...draft,
                kronologi_kes: [
                  ...current,
                  { tarikh: "Tarikh baharu", peristiwa: "Catatan peristiwa atau tindakan susulan..." },
                ],
              });
            }}
            className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
          >
            <Plus className="h-3 w-3" /> Tambah Kronologi
          </button>
        </div>
        <div className="space-y-1.5">
          {(draft.kronologi_kes || []).map((item, idx) => (
            <div
              key={idx}
              className="grid grid-cols-1 gap-1.5 rounded border border-slate-200 bg-slate-50/50 p-2 sm:grid-cols-12"
            >
              <input
                type="text"
                placeholder="Tarikh"
                value={item.tarikh}
                onChange={(e) => {
                  const next = [...(draft.kronologi_kes || [])];
                  next[idx] = { ...next[idx], tarikh: e.target.value };
                  onChangeDraft({ ...draft, kronologi_kes: next });
                }}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-semibold sm:col-span-3"
              />
              <input
                type="text"
                placeholder="Peristiwa"
                value={item.peristiwa}
                onChange={(e) => {
                  const next = [...(draft.kronologi_kes || [])];
                  next[idx] = { ...next[idx], peristiwa: e.target.value };
                  onChangeDraft({ ...draft, kronologi_kes: next });
                }}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px] sm:col-span-8"
              />
              <button
                type="button"
                onClick={() => {
                  onChangeDraft({
                    ...draft,
                    kronologi_kes: (draft.kronologi_kes || []).filter((_, i) => i !== idx),
                  });
                }}
                className="flex items-center justify-center rounded bg-rose-50 p-1 text-rose-600 hover:bg-rose-100 sm:col-span-1"
                title="Padam baris"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* 10. Kertas Cadangan Pegawai Penyiasat (IO) */}
      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <h4 className="mb-1.5 text-xs font-bold text-slate-900">
          10. Kertas Cadangan Pegawai Penyiasat (IO)
        </h4>
        <textarea
          rows={5}
          value={draft.kertas_cadangan_io || ""}
          onChange={(e) => onChangeDraft({ ...draft, kertas_cadangan_io: e.target.value })}
          className="w-full rounded border border-slate-300 bg-slate-50/50 p-2 text-xs leading-relaxed"
        />
      </div>

      {/* 11. Saman (Mahkamah 111 - Pin. 1/85) & Pemberatan Hukuman */}
      <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-xs font-bold text-slate-900">
            11. Saman (Mahkamah 111 - Pin. 1/85) &amp; Hujahan Pemberatan Hukuman
          </h4>
          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("saman_111")}
            className="inline-flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-slate-900 disabled:opacity-60"
          >
            {exporting === "saman_111" ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Download className="h-3 w-3 text-amber-300" />
            )}
            Muat Turun Saman 111 (.docx)
          </button>
        </div>

        {draft.saman_111 && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Mahkamah Majistret</label>
              <input
                type="text"
                value={draft.saman_111.mahkamah || ""}
                onChange={(e) =>
                  onChangeDraft({
                    ...draft,
                    saman_111: { ...draft.saman_111, mahkamah: e.target.value },
                  })
                }
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Tarikh Hadir Mahkamah</label>
              <input
                type="text"
                value={draft.saman_111.tarikh_hadir || ""}
                onChange={(e) =>
                  onChangeDraft({
                    ...draft,
                    saman_111: { ...draft.saman_111, tarikh_hadir: e.target.value },
                  })
                }
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Masa Hadir</label>
              <input
                type="text"
                value={draft.saman_111.masa_hadir || ""}
                onChange={(e) =>
                  onChangeDraft({
                    ...draft,
                    saman_111: { ...draft.saman_111, masa_hadir: e.target.value },
                  })
                }
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs"
              />
            </div>
          </div>
        )}

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-700">
              Poin Pemberatan Hukuman (Dibaca Pegawai Pendakwa Selepas OKT Mengaku Salah / Sabit):
            </span>
            <button
              type="button"
              onClick={() =>
                onChangeDraft({
                  ...draft,
                  pemberatan_hukuman: [
                    ...(draft.pemberatan_hukuman || []),
                    "Faktor pemberatan tambahan kepentingan kesihatan awam...",
                  ],
                })
              }
              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
            >
              <Plus className="h-3 w-3" /> Tambah Poin
            </button>
          </div>
          <div className="space-y-1.5">
            {(draft.pemberatan_hukuman || []).map((pt, idx) => (
              <div key={idx} className="flex items-start gap-1.5">
                <span className="mt-1.5 w-5 text-center text-[11px] font-bold text-slate-600">
                  {idx + 1}.
                </span>
                <input
                  type="text"
                  value={pt}
                  onChange={(e) => {
                    const next = [...(draft.pemberatan_hukuman || [])];
                    next[idx] = e.target.value;
                    onChangeDraft({ ...draft, pemberatan_hukuman: next });
                  }}
                  className="flex-1 rounded border border-slate-300 bg-slate-50/50 px-2 py-1 text-xs"
                />
                <button
                  type="button"
                  onClick={() =>
                    onChangeDraft({
                      ...draft,
                      pemberatan_hukuman: (draft.pemberatan_hukuman || []).filter((_, i) => i !== idx),
                    })
                  }
                  className="mt-0.5 rounded bg-rose-50 p-1 text-rose-600 hover:bg-rose-100"
                  title="Padam poin"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Petikan Akta Sebenar */}
      {draft.statutory_citations.length > 0 && (
        <div className="rounded-lg border border-teal-200 bg-teal-50/50 p-3">
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-teal-900">
            <BookCheck className="h-4 w-4 text-teal-700" />
            <span>Teks Akta Sebenar Yang Dirujuk</span>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {draft.statutory_citations.slice(0, 2).map((cit, i) => (
              <div
                key={i}
                className="rounded border border-teal-200 bg-white p-2 text-[11px] text-slate-700"
              >
                <div className="font-bold text-teal-800">
                  {cit.akta_code} — {cit.section}
                </div>
                <p className="mt-1 line-clamp-4">{cit.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
