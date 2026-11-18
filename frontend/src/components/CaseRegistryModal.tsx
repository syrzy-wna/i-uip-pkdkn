"use client";

import React, { useState } from "react";
import { FolderOpen, Loader2, Plus, Trash2, X } from "lucide-react";
import { deleteCaseRecord, saveCaseRecord } from "@/lib/api";
import type { IPCaseRecord, WorkflowMode } from "@/lib/types";

interface CaseRegistryModalProps {
  open: boolean;
  onClose: () => void;
  cases: IPCaseRecord[];
  activeCaseId: string;
  onSelectCase: (rec: IPCaseRecord) => void;
  onCasesUpdated: (nextCases: IPCaseRecord[]) => void;
}

export default function CaseRegistryModal({
  open,
  onClose,
  cases,
  activeCaseId,
  onSelectCase,
  onCasesUpdated,
}: CaseRegistryModalProps) {
  const [mode, setMode] = useState<"list" | "new">("list");
  const [saving, setSaving] = useState(false);

  const [noIp, setNoIp] = useState("PKD/UIP/852/2026/");
  const [akta, setAkta] = useState("Akta 852");
  const [daerah, setDaerah] = useState("Petaling, Selangor");
  const [tarikh, setTarikh] = useState("");
  const [masa, setMasa] = useState("");
  const [namaPremis, setNamaPremis] = useState("");
  const [noSsm, setNoSsm] = useState("");
  const [alamat, setAlamat] = useState("");
  const [namaOkt, setNamaOkt] = useState("");
  const [noKpOkt, setNoKpOkt] = useState("");
  const [pegawaiIo, setPegawaiIo] = useState("");
  const [kadKuasa, setKadKuasa] = useState("");
  const [kesalahan, setKesalahan] = useState("");

  if (!open) return null;

  const handleCreateNew = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const formattedText = `KERTAS SIASATAN UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)
NO. IP: ${noIp}
DAERAH: ${daerah}
AKTA: ${akta}

1. BUTIRAN PEMERIKSAAN
Tarikh Kejadian: ${tarikh || "Sila isi tarikh"}
Masa Kejadian: ${masa || "Sila isi masa"}
Nama Premis: ${namaPremis || "Sila isi nama premis"}
No. SSM: ${noSsm || "-"}
Alamat Kejadian: ${alamat || "Sila isi alamat lengkap"}
Nama Suspek (OKT): ${namaOkt || "Sila isi nama penuh ikut MyKad"}
No. K/P: ${noKpOkt || "Sila isi 12 digit MyKad"}
Pegawai Penyiasat (IO): ${pegawaiIo || "PPKP"} (No. Kad Kuasa: ${kadKuasa || "-"})

2. RINGKASAN KESALAHAN
Kesalahan: ${kesalahan || "Sila nyatakan butiran kesalahan yang ditemui semasa pemeriksaan."}
`;
      const created = await saveCaseRecord({
        no_ip: noIp,
        tajuk_kes: `${noIp} — ${namaPremis || namaOkt || "Kes Baharu PKD"}`,
        akta_utama: akta,
        workflow: "audit_ip" as WorkflowMode,
        badge: "Kes Baharu",
        nama_okt: namaOkt,
        no_kp_okt: noKpOkt,
        nama_premis: namaPremis,
        no_ssm: noSsm,
        alamat_kejadian: alamat,
        tarikh_kejadian: tarikh,
        masa_kejadian: masa,
        pegawai_io: pegawaiIo,
        no_kad_kuasa: kadKuasa,
        status_kes: "DALAM SIASATAN",
        case_text: formattedText,
      });
      onCasesUpdated([created, ...cases]);
      onSelectCase(created);
      setMode("list");
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await deleteCaseRecord(id);
    onCasesUpdated(cases.filter((c) => c.id !== id));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[88vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-[#0f2744]" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Daftar Kes Kertas Siasatan (IP) PKD — Pangkalan Data SQLite
              </h2>
              <p className="text-[11px] text-slate-500">
                Semua kes IP, hasil semakan Pra-TPR dan draf disimpan kekal di PC anda.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMode(mode === "list" ? "new" : "list")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
            >
              <Plus className="h-3.5 w-3.5" />
              {mode === "list" ? "Daftar Kes IP Baharu" : "Lihat Senarai Kes"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="mt-4 flex-1 overflow-y-auto pr-1">
          {mode === "list" ? (
            <div className="space-y-2">
              {cases.map((c) => {
                const isActive = c.id === activeCaseId;
                return (
                  <div
                    key={c.id}
                    className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3 transition ${
                      isActive ? "border-blue-600 bg-blue-50/70" : "border-slate-200 bg-slate-50/40"
                    }`}
                  >
                    <div
                      className="flex-1 cursor-pointer"
                      onClick={() => {
                        onSelectCase(c);
                        onClose();
                      }}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[10px] font-bold text-white">
                          {c.akta_utama}
                        </span>
                        <span className="text-xs font-bold text-slate-900">{c.tajuk_kes}</span>
                        <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                          {c.status_kes}
                        </span>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-600">
                        OKT: <strong>{c.nama_okt || "-"}</strong> ({c.no_kp_okt || "-"}) • Premis:{" "}
                        <strong>{c.nama_premis || "-"}</strong> • Skor: {c.skor_audit || 0}%
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          onSelectCase(c);
                          onClose();
                        }}
                        className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-300 hover:bg-blue-50"
                      >
                        Buka Kes
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(c.id)}
                        className="rounded-lg bg-rose-50 p-1.5 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                        title="Padam kes"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <form onSubmit={handleCreateNew} className="grid grid-cols-1 gap-2.5 text-xs sm:grid-cols-2">
              <div>
                <label className="font-semibold text-slate-600">No. Fail IP PKD</label>
                <input
                  required
                  type="text"
                  value={noIp}
                  onChange={(e) => setNoIp(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-600">Akta Utama</label>
                <select
                  value={akta}
                  onChange={(e) => setAkta(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5"
                >
                  <option value="Akta 852">Akta 852 (Produk Merokok &amp; Vape)</option>
                  <option value="Akta 281">Akta Makanan 1983 &amp; PPKM 2009</option>
                  <option value="Akta 154">Akta 154 (Aedes / Serangga Pembawa Penyakit)</option>
                  <option value="Akta 342">Akta 342 (Penyakit Berjangkit)</option>
                </select>
              </div>
              <div>
                <label className="font-semibold text-slate-600">Daerah / Negeri</label>
                <input
                  type="text"
                  value={daerah}
                  onChange={(e) => setDaerah(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-slate-600">Tarikh Kejadian</label>
                  <input
                    type="text"
                    placeholder="cth: 18 November 2026"
                    value={tarikh}
                    onChange={(e) => setTarikh(e.target.value)}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-600">Masa</label>
                  <input
                    type="text"
                    placeholder="cth: 10.15 pagi"
                    value={masa}
                    onChange={(e) => setMasa(e.target.value)}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1.5"
                  />
                </div>
              </div>
              <div>
                <label className="font-semibold text-slate-600">Nama Premis / Syarikat</label>
                <input
                  type="text"
                  value={namaPremis}
                  onChange={(e) => setNamaPremis(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-600">No. Pendaftaran SSM</label>
                <input
                  type="text"
                  value={noSsm}
                  onChange={(e) => setNoSsm(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="font-semibold text-slate-600">Alamat Lengkap Tempat Kejadian</label>
                <input
                  type="text"
                  value={alamat}
                  onChange={(e) => setAlamat(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-600">Nama Penuh OKT / Pemilik (MyKad)</label>
                <input
                  type="text"
                  value={namaOkt}
                  onChange={(e) => setNamaOkt(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-600">No. Kad Pengenalan (12 Digit)</label>
                <input
                  type="text"
                  placeholder="XXXXXX-XX-XXXX"
                  value={noKpOkt}
                  onChange={(e) => setNoKpOkt(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-600">Nama Pegawai Penyiasat (IO)</label>
                <input
                  type="text"
                  value={pegawaiIo}
                  onChange={(e) => setPegawaiIo(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-600">No. Kad Kuasa KKM</label>
                <input
                  type="text"
                  value={kadKuasa}
                  onChange={(e) => setKadKuasa(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="font-semibold text-slate-600">Ringkasan Fakta Kesalahan Lapangan</label>
                <textarea
                  rows={3}
                  value={kesalahan}
                  onChange={(e) => setKesalahan(e.target.value)}
                  className="mt-0.5 w-full rounded border border-slate-300 p-2"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
                <button
                  type="button"
                  onClick={() => setMode("list")}
                  className="rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 font-bold text-white hover:bg-slate-800"
                >
                  {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Daftar &amp; Simpan Kes IP
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
