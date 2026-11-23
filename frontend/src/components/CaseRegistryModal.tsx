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

const AKTA_CHOICES = [
  { value: "Akta 852", label: "Akta 852 — Produk Merokok & Vape" },
  { value: "Akta 281", label: "Akta 281 — Makanan 1983 & PPKM 2009" },
  { value: "Akta 154", label: "Akta 154 — Aedes & Serangga Pembawa Penyakit" },
  { value: "Akta 342", label: "Akta 342 — Penyakit Berjangkit / Tibi" },
  { value: "Akta 593", label: "Akta 593 — Kanun Tatacara Jenayah (KTJ)" },
  { value: "Akta 56", label: "Akta 56 — Akta Keterangan 1950" },
];

const INPUT_CLASS =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 focus:border-[#0f2744] focus:outline-none focus:ring-2 focus:ring-slate-200 sm:text-sm";

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
  const [noIp, setNoIp] = useState(`PKD/UIP/852/${currentYear}/`);
  const [akta, setAkta] = useState("Akta 852");
  const [daerah, setDaerah] = useState("");
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

  const deriveOfficePrefix = (off?: OfficerProfile | null): string => {
    const raw = (off?.district_pkd || "").trim().toUpperCase();
    if (!raw) return "PKD";
    if (raw.includes("PKK") || raw.includes("KAWASAN")) return "PKK";
    if (raw.includes("PKB") || raw.includes("BAHAGIAN")) return "PKB";
    return "PKD";
  };

  useEffect(() => {
    if (!open) return;
    setMode(initialMode);
    setErrorMsg(null);
    setConfirmDeleteId(null);
    if (officer) {
      setPegawaiIo((prev) => prev || officer.full_name || "");
      setKadKuasa((prev) => prev || officer.kkm_authority_card_no || "");
      const officeStr = [officer.district_pkd, officer.state_jkn?.replace(/^Jabatan Kesihatan (?:Negeri|Wilayah Persekutuan)\s*/i, "")]
        .filter(Boolean)
        .join(", ");
      if (officeStr) {
        setDaerah((prev) => prev || officeStr);
      }
      const pfx = deriveOfficePrefix(officer);
      const actNum = akta.replace(/\D/g, "") || "852";
      setNoIp((prev) =>
        /^PK[DKB](?:-KN)?\/UIP\/\d+\/\d{4}\/$/.test(prev)
          ? `${pfx}/UIP/${actNum}/${currentYear}/`
          : prev
      );
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, initialMode, officer, onClose, akta, currentYear]);

  const handleAktaChange = (nextAkta: string) => {
    setAkta(nextAkta);
    const num = nextAkta.replace(/\D/g, "") || "852";
    const pfx = deriveOfficePrefix(officer);
    setNoIp((prev) => prev.replace(/^PK[DKB](?:-KN)?\/UIP\/\d+\//, `${pfx}/UIP/${num}/`));
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
DAERAH: ${daerah || officer?.district_pkd || "Pejabat Kesihatan"}
AKTA: ${akta}

1. BUTIRAN PEMERIKSAAN
Tarikh Kejadian: ${tarikh || "Sila isi tarikh"}
Masa Kejadian: ${masa || "Sila isi masa"}
Nama Premis: ${namaPremis || "Sila isi nama premis"}
No. SSM: ${noSsm || "-"}
Alamat Kejadian: ${alamat || "Sila isi alamat lengkap"}
Nama Tertuduh (OKT): ${namaOkt || "Sila isi nama penuh ikut MyKad"}
No. K/P: ${noKpOkt || "Sila isi 12 digit MyKad"}
Pegawai Penyiasat (IO): ${pegawaiIo || "PPKP"} (No. Kad Kuasa: ${kadKuasa || "-"})

2. RINGKASAN KESALAHAN
Kesalahan: ${kesalahan || "Sila nyatakan butiran kesalahan yang ditemui semasa pemeriksaan."}
`;
      const created = await saveCaseRecord({
        no_ip: noIp,
        tajuk_kes: `${noIp} — ${namaPremis || namaOkt || "Kes Baharu UIP"}`,
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
      const pfx = deriveOfficePrefix(officer);
      setNoIp(`${pfx}/UIP/${akta.replace(/\D/g, "") || "852"}/${currentYear}/`);
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
      aria-label="Fail Kes Saya"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/65 p-0 backdrop-blur-sm sm:items-center sm:p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-white p-4 shadow-2xl sm:rounded-2xl sm:p-6"
      >
        <div className="flex flex-col gap-3 border-b border-slate-200 pb-3.5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <FolderOpen className="h-5 w-5 shrink-0 text-[#0f2744]" />
              <div>
                <h2 className="text-base font-extrabold text-slate-900">
                  Fail Kes Saya
                </h2>
                <p className="text-xs text-slate-600">
                  Pilih mana-mana fail untuk terus buka ruang kerja, atau daftar fail baharu.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup senarai fail"
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 sm:hidden"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMode(mode === "list" ? "new" : "list")}
              className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 sm:flex-none"
            >
              <Plus className="h-4 w-4" />
              {mode === "list" ? "Daftar Kes Baharu" : "Lihat Senarai Fail"}
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup senarai fail"
              className="hidden min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 sm:inline-flex"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-3 rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-800">
            {errorMsg}
          </div>
        )}

        <div className="mt-4 flex-1 overflow-y-auto pr-1">
          {mode === "list" ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-[180px] flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Cari No. IP, nama atau premis..."
                    className="w-full rounded-xl border border-slate-300 py-2 pl-9 pr-3 text-base focus:border-[#0f2744] focus:outline-none sm:text-sm"
                  />
                </div>
                <select
                  value={aktaFilter}
                  onChange={(e) => setAktaFilter(e.target.value)}
                  className="min-h-[42px] rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-700 sm:text-sm"
                >
                  <option value="SEMUA">Semua Akta</option>
                  {AKTA_CHOICES.map((a) => (
                    <option key={a.value} value={a.value}>
                      {a.value}
                    </option>
                  ))}
                </select>
              </div>

              {filteredCases.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
                  <p className="text-sm font-semibold text-slate-600">
                    Tiada fail kes sepadan ditemui.
                  </p>
                  <button
                    type="button"
                    onClick={() => setMode("new")}
                    className="mt-3 inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
                  >
                    <Plus className="h-4 w-4" />
                    Daftar Kes Baharu
                  </button>
                </div>
              ) : (
                <div className="divide-y divide-slate-200 rounded-xl border border-slate-200">
                  {filteredCases.map((c) => {
                    const isActive = c.id === activeCaseId;
                    const confirming = confirmDeleteId === c.id;
                    const isSample = Boolean(c.is_sample || c.id.startsWith("kes-akta-"));
                    return (
                      <div
                        key={c.id}
                        className={`flex flex-wrap items-center justify-between gap-3 p-3.5 transition ${
                          isActive ? "bg-slate-50" : "bg-white hover:bg-slate-50/70"
                        }`}
                      >
                        <div
                          className="min-w-[200px] flex-1 cursor-pointer"
                          onClick={() => {
                            onSelectCase(c);
                            onClose();
                          }}
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-md bg-[#0f2744] px-2 py-0.5 text-xs font-bold text-white">
                              {c.akta_utama}
                            </span>
                            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                              {c.skor_audit ? `Skor ${c.skor_audit}%` : isSample ? "Contoh Kes" : c.status_kes}
                            </span>
                          </div>
                          <div className="mt-1.5 text-sm font-bold text-slate-900">
                            {c.tajuk_kes.replace(/^Kes \d+:\s*/, "")}
                          </div>
                          <div className="mt-0.5 text-xs text-slate-600">
                            {c.nama_okt || "-"} {c.nama_premis ? `• ${c.nama_premis}` : ""}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              onSelectCase(c);
                              onClose();
                            }}
                            className="min-h-[40px] rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-bold text-[#0f2744] hover:bg-slate-100"
                          >
                            Buka Fail
                          </button>

                          {!isSample && (
                            confirming ? (
                              <div className="flex items-center gap-1 rounded-lg bg-rose-50 p-1 ring-1 ring-rose-300">
                                <button
                                  type="button"
                                  onClick={() => handleDelete(c.id)}
                                  className="min-h-[40px] rounded bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700"
                                >
                                  Padam
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setConfirmDeleteId(null)}
                                  className="min-h-[40px] rounded bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
                                >
                                  Batal
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setConfirmDeleteId(c.id)}
                                className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"
                                title="Padam fail kes"
                                aria-label="Padam fail kes"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            )
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleCreateNew} className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-700 sm:col-span-2">
                Tip: Jika anda sudah ada fail PDF/Word atau gambar bukti kes, anda juga boleh terus muat naik fail tersebut di ruang <strong>Fail IP</strong> tanpa mengisi semua ruangan di bawah.
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
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
                <label className="text-xs font-semibold text-slate-700">
                  Akta Utama <span className="text-rose-600">*</span>
                </label>
                <select
                  value={akta}
                  onChange={(e) => handleAktaChange(e.target.value)}
                  className={INPUT_CLASS}
                >
                  {AKTA_CHOICES.map((a) => (
                    <option key={a.value} value={a.value}>
                      {a.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Daerah / Negeri</label>
                <input
                  type="text"
                  value={daerah}
                  onChange={(e) => setDaerah(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Tarikh Kejadian</label>
                  <input
                    type="text"
                    placeholder="cth: 18 Nov 2026"
                    value={tarikh}
                    onChange={(e) => setTarikh(e.target.value)}
                    className={INPUT_CLASS}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Masa</label>
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
                <label className="text-xs font-semibold text-slate-700">Nama Premis / Syarikat</label>
                <input
                  type="text"
                  value={namaPremis}
                  onChange={(e) => setNamaPremis(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">No. Pendaftaran SSM</label>
                <input
                  type="text"
                  value={noSsm}
                  onChange={(e) => setNoSsm(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Alamat Lengkap Tempat Kejadian</label>
                <input
                  type="text"
                  value={alamat}
                  onChange={(e) => setAlamat(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Nama Penuh OKT / Pemilik (MyKad)</label>
                <input
                  type="text"
                  value={namaOkt}
                  onChange={(e) => setNamaOkt(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">No. K/P (12 Digit) / Pasport</label>
                <input
                  type="text"
                  placeholder="XXXXXX-XX-XXXX"
                  value={noKpOkt}
                  onChange={(e) => setNoKpOkt(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Nama Pegawai Penyiasat (IO)</label>
                <input
                  type="text"
                  value={pegawaiIo}
                  onChange={(e) => setPegawaiIo(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">No. Kad Kuasa KKM</label>
                <input
                  type="text"
                  value={kadKuasa}
                  onChange={(e) => setKadKuasa(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Ringkasan Kesalahan Ditemui</label>
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
                  className="min-h-[44px] rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  Simpan &amp; Buka Fail IP
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
