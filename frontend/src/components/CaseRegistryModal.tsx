"use client";

import React, { useEffect, useMemo, useState } from "react";
import { FolderOpen, Loader2, Plus, Search, Trash2, X } from "lucide-react";
import { deleteCaseRecord, saveCaseRecord } from "@/lib/api";
import type { IPCaseRecord, OfficerProfile, WorkflowMode } from "@/lib/types";

interface CaseRegistryModalProps {
  open: boolean;
  onClose: () => void;
  cases: IPCaseRecord[];
  activeCaseId: string;
  onSelectCase: (rec: IPCaseRecord) => void;
  onCasesUpdated: (nextCases: IPCaseRecord[]) => void;
  initialMode?: "list" | "new";
  officer?: OfficerProfile | null;
}

const INPUT_CLASS =
  "mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:py-1.5 sm:text-xs";

export default function CaseRegistryModal({
  open,
  onClose,
  cases,
  activeCaseId,
  onSelectCase,
  onCasesUpdated,
  initialMode = "list",
  officer = null,
}: CaseRegistryModalProps) {
  const [mode, setMode] = useState<"list" | "new">(initialMode);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [aktaFilter, setAktaFilter] = useState("SEMUA");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const currentYear = new Date().getFullYear();
  const [noIp, setNoIp] = useState(`PKD-KN/UIP/852/${currentYear}/`);
  const [akta, setAkta] = useState("Akta 852");
  const [daerah, setDaerah] = useState("Kuala Nerus, Terengganu");
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

  useEffect(() => {
    if (!open) return;
    setMode(initialMode);
    setErrorMsg(null);
    setConfirmDeleteId(null);
    if (officer) {
      setPegawaiIo((prev) => prev || officer.full_name || "");
      setKadKuasa((prev) => prev || officer.kkm_authority_card_no || "");
      if (officer.district_pkd && officer.district_pkd.includes("Kuala Nerus")) {
        setDaerah("Kuala Nerus, Terengganu");
      }
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, initialMode, officer, onClose]);

  const handleAktaChange = (nextAkta: string) => {
    setAkta(nextAkta);
    const num = nextAkta.replace(/\D/g, "") || "852";
    setNoIp((prev) => prev.replace(/^PKD-KN\/UIP\/\d+\//, `PKD-KN/UIP/${num}/`));
  };

  const filteredCases = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return cases.filter((c) => {
      if (aktaFilter !== "SEMUA" && c.akta_utama !== aktaFilter) return false;
      if (!q) return true;
      return (
        c.tajuk_kes.toLowerCase().includes(q) ||
        (c.no_ip || "").toLowerCase().includes(q) ||
        (c.nama_okt || "").toLowerCase().includes(q) ||
        (c.nama_premis || "").toLowerCase().includes(q)
      );
    });
  }, [cases, searchQuery, aktaFilter]);

  if (!open) return null;

  const handleCreateNew = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMsg(null);
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
      // Kosongkan borang supaya pendaftaran kes seterusnya bersih
      setNoIp(`PKD-KN/UIP/${akta.replace(/\D/g, "") || "852"}/${currentYear}/`);
      setTarikh("");
      setMasa("");
      setNamaPremis("");
      setNoSsm("");
      setAlamat("");
      setNamaOkt("");
      setNoKpOkt("");
      setKesalahan("");
      setMode("list");
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal mendaftar kes baharu.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setErrorMsg(null);
    try {
      await deleteCaseRecord(id);
      onCasesUpdated(cases.filter((c) => c.id !== id));
      setConfirmDeleteId(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal memadam kes.");
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Daftar Fail Kertas Siasatan PKD"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/65 p-0 backdrop-blur-sm sm:items-center sm:p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-white p-4 shadow-2xl sm:rounded-2xl sm:p-5"
      >
        <div className="flex flex-col gap-2.5 border-b border-slate-100 pb-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 shrink-0 text-[#0f2744]" />
              <div>
                <h2 className="text-sm font-extrabold text-slate-900">
                  Daftar Fail Kertas Siasatan (IP) PKD Kuala Nerus
                </h2>
                <p className="text-[11px] text-slate-600">
                  Semua kes, keputusan semakan Pra-TPR &amp; draf dokumen disimpan dalam akaun anda.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup daftar kes"
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 sm:hidden"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMode(mode === "list" ? "new" : "list")}
              className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 sm:flex-none"
            >
              <Plus className="h-3.5 w-3.5" />
              {mode === "list" ? "Daftar Kes IP Baharu" : "Lihat Senarai Kes"}
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup daftar kes"
              className="hidden min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 sm:inline-flex"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-3 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
            {errorMsg}
          </div>
        )}

        <div className="mt-3 flex-1 overflow-y-auto pr-1">
          {mode === "list" ? (
            <div className="space-y-3">
              {/* Bar Carian & Penapis Akta */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative flex-1 min-w-[180px]">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Cari No. IP, nama OKT atau premis..."
                    className="w-full rounded-lg border border-slate-300 pl-8 pr-3 py-1.5 text-base focus:border-blue-500 focus:outline-none sm:text-xs"
                  />
                </div>
                <select
                  value={aktaFilter}
                  onChange={(e) => setAktaFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-base font-semibold text-slate-700 sm:text-xs"
                >
                  <option value="SEMUA">Semua Akta</option>
                  <option value="Akta 852">Akta 852</option>
                  <option value="Akta 281">Akta 281</option>
                  <option value="Akta 154">Akta 154</option>
                  <option value="Akta 342">Akta 342</option>
                </select>
              </div>

              {filteredCases.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center">
                  <p className="text-xs font-semibold text-slate-600">
                    Tiada fail kes sepadan ditemui.
                  </p>
                  <button
                    type="button"
                    onClick={() => setMode("new")}
                    className="mt-3 inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Daftar Kes IP Baharu
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredCases.map((c) => {
                    const isActive = c.id === activeCaseId;
                    const confirming = confirmDeleteId === c.id;
                    return (
                      <div
                        key={c.id}
                        className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3 transition ${
                          isActive
                            ? "border-blue-600 bg-blue-50/75"
                            : "border-slate-200 bg-slate-50/40 hover:border-blue-300 hover:bg-blue-50/30"
                        }`}
                      >
                        <div
                          className="flex-1 cursor-pointer min-w-[200px]"
                          onClick={() => {
                            onSelectCase(c);
                            onClose();
                          }}
                        >
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[10px] font-bold text-white">
                              {c.akta_utama}
                            </span>
                            {isActive && (
                              <span className="rounded bg-blue-600 px-2 py-0.5 text-[10px] font-bold text-white">
                                Sedang Dibuka
                              </span>
                            )}
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
                            className="min-h-[38px] rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-blue-700 ring-1 ring-blue-300 hover:bg-blue-50"
                          >
                            Buka Kes
                          </button>

                          {confirming ? (
                            <div className="flex items-center gap-1 rounded-lg bg-rose-50 p-1 ring-1 ring-rose-300">
                              <button
                                type="button"
                                onClick={() => handleDelete(c.id)}
                                className="rounded bg-rose-600 px-2 py-1 text-[11px] font-bold text-white hover:bg-rose-700"
                              >
                                Ya, Padam
                              </button>
                              <button
                                type="button"
                                onClick={() => setConfirmDeleteId(null)}
                                className="rounded bg-white px-2 py-1 text-[11px] font-semibold text-slate-700"
                              >
                                Batal
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setConfirmDeleteId(c.id)}
                              className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                              title="Padam kes"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleCreateNew} className="grid grid-cols-1 gap-2.5 text-xs sm:grid-cols-2">
              <div className="rounded-lg border border-blue-200 bg-blue-50/60 px-3 py-2 text-[11px] text-blue-900 sm:col-span-2">
                Tip: Jika anda sudah ada fail PDF/Word atau gambar bukti kes, anda juga boleh terus muat naik fail tersebut di skrin utama tanpa perlu mengisi semua ruangan di bawah.
              </div>
              <div>
                <label className="font-semibold text-slate-700">
                  No. Fail IP PKD <span className="text-rose-600">*</span>
                </label>
                <input
                  required
                  type="text"
                  value={noIp}
                  onChange={(e) => setNoIp(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700">
                  Akta Utama <span className="text-rose-600">*</span>
                </label>
                <select
                  value={akta}
                  onChange={(e) => handleAktaChange(e.target.value)}
                  className={INPUT_CLASS}
                >
                  <option value="Akta 852">Akta 852 (Produk Merokok &amp; Vape)</option>
                  <option value="Akta 281">Akta Makanan 1983 &amp; PPKM 2009</option>
                  <option value="Akta 154">Akta 154 (Aedes / Serangga Pembawa Penyakit)</option>
                  <option value="Akta 342">Akta 342 (Penyakit Berjangkit)</option>
                </select>
              </div>
              <div>
                <label className="font-semibold text-slate-700">Daerah / Negeri</label>
                <input
                  type="text"
                  value={daerah}
                  onChange={(e) => setDaerah(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-slate-700">Tarikh Kejadian</label>
                  <input
                    type="text"
                    placeholder="cth: 18 Nov 2026"
                    value={tarikh}
                    onChange={(e) => setTarikh(e.target.value)}
                    className={INPUT_CLASS}
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Masa</label>
                  <input
                    type="text"
                    placeholder="cth: 10.15 pagi"
                    value={masa}
                    onChange={(e) => setMasa(e.target.value)}
                    className={INPUT_CLASS}
                  />
                </div>
              </div>
              <div>
                <label className="font-semibold text-slate-700">Nama Premis / Syarikat</label>
                <input
                  type="text"
                  value={namaPremis}
                  onChange={(e) => setNamaPremis(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700">No. Pendaftaran SSM</label>
                <input
                  type="text"
                  value={noSsm}
                  onChange={(e) => setNoSsm(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="font-semibold text-slate-700">Alamat Lengkap Tempat Kejadian</label>
                <input
                  type="text"
                  value={alamat}
                  onChange={(e) => setAlamat(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700">Nama Penuh OKT / Pemilik (MyKad)</label>
                <input
                  type="text"
                  value={namaOkt}
                  onChange={(e) => setNamaOkt(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700">No. Kad Pengenalan (12 Digit)</label>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="XXXXXX-XX-XXXX"
                  value={noKpOkt}
                  onChange={(e) => setNoKpOkt(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700">Nama Pegawai Penyiasat (IO)</label>
                <input
                  type="text"
                  value={pegawaiIo}
                  onChange={(e) => setPegawaiIo(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700">No. Kad Kuasa KKM</label>
                <input
                  type="text"
                  value={kadKuasa}
                  onChange={(e) => setKadKuasa(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="font-semibold text-slate-700">Ringkasan Fakta Kesalahan Lapangan</label>
                <textarea
                  rows={3}
                  value={kesalahan}
                  onChange={(e) => setKesalahan(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
                <button
                  type="button"
                  onClick={() => setMode("list")}
                  className="min-h-[40px] rounded-lg border border-slate-300 px-4 py-2 font-semibold text-slate-700"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 font-bold text-white hover:bg-slate-800 disabled:opacity-60"
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
