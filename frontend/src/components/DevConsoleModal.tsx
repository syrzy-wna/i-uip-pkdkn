"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Archive,
  CheckCircle2,
  Coins,
  Cpu,
  Database,
  ExternalLink,
  KeyRound,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import DevVaultTab from "@/components/DevVaultTab";
import { fetchDevOverview, fetchRuntimeSettings, saveRuntimeSettings } from "@/lib/api";
import type { DevOverviewResponse } from "@/lib/types";

interface DevConsoleModalProps {
  open: boolean;
  onClose: () => void;
  authToken?: string | null;
  developerEmail?: string;
}

const ACTION_BADGES: Record<string, string> = {
  LOGIN_GOOGLE: "bg-blue-100 text-blue-800 border-blue-200",
  LOGIN_EMAIL: "bg-slate-100 text-slate-800 border-slate-200",
  REGISTER_ACCOUNT: "bg-emerald-100 text-emerald-800 border-emerald-200",
  TANYA_PAKAR_UIP: "bg-indigo-100 text-indigo-800 border-indigo-200",
  AUDIT_IP_20: "bg-amber-100 text-amber-800 border-amber-200",
  JANA_DRAF_IP: "bg-purple-100 text-purple-800 border-purple-200",
  EXPORT_DOCX: "bg-teal-100 text-teal-800 border-teal-200",
  SEMAK_KOMPAUN: "bg-orange-100 text-orange-800 border-orange-200",
  EKSTRAK_BUKTI_OCR: "bg-rose-100 text-rose-800 border-rose-200",
  SIMPAN_KES_IP: "bg-cyan-100 text-cyan-800 border-cyan-200",
  CARIAN_RAG_AKTA: "bg-slate-100 text-slate-700 border-slate-200",
};

export default function DevConsoleModal({
  open,
  onClose,
  authToken,
  developerEmail,
}: DevConsoleModalProps) {
  const [tab, setTab] = useState<"users" | "activities" | "costs" | "google_oauth" | "vault">("users");
  const [data, setData] = useState<DevOverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [actionFilter, setActionFilter] = useState("SEMUA");
  const [vaultUserFilter, setVaultUserFilter] = useState("");
  const [vaultRefreshSignal, setVaultRefreshSignal] = useState(0);

  // Tetapan Google OAuth Web Client ID dari Konsol Dev
  const [googleClientId, setGoogleClientId] = useState("");
  const [savingOauth, setSavingOauth] = useState(false);
  const [oauthMsg, setOauthMsg] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, runtime] = await Promise.all([
        fetchDevOverview(authToken),
        fetchRuntimeSettings(),
      ]);
      setData(overview);
      setGoogleClientId(runtime.google_client_id || "");
      setVaultRefreshSignal((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuatkan Konsol Pembangun.");
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  const openVaultForUser = (email: string) => {
    setVaultUserFilter(email);
    setTab("vault");
  };

  useEffect(() => {
    if (!open) return;
    loadOverview();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, loadOverview, onClose]);

  const filteredUsers = useMemo(() => {
    if (!data) return [];
    const q = searchQuery.trim().toLowerCase();
    if (!q) return data.users;
    return data.users.filter(
      (u) =>
        u.full_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.district_pkd.toLowerCase().includes(q) ||
        (u.kkm_authority_card_no || "").toLowerCase().includes(q)
    );
  }, [data, searchQuery]);

  const filteredActivities = useMemo(() => {
    if (!data) return [];
    const q = searchQuery.trim().toLowerCase();
    return data.activities.filter((act) => {
      if (actionFilter !== "SEMUA" && act.action_type !== actionFilter) return false;
      if (!q) return true;
      return (
        act.user_name.toLowerCase().includes(q) ||
        act.user_email.toLowerCase().includes(q) ||
        act.action_detail.toLowerCase().includes(q) ||
        act.model_used.toLowerCase().includes(q)
      );
    });
  }, [data, searchQuery, actionFilter]);

  const handleSaveGoogleClientId = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingOauth(true);
    setOauthMsg(null);
    setError(null);
    try {
      await saveRuntimeSettings({ google_client_id: googleClientId.trim() });
      setOauthMsg(
        googleClientId.trim()
          ? "Google OAuth Client ID berjaya diaktifkan. Butang rasmi Google Identity Services kini aktif di tetingkap Log Masuk."
          : "Google Client ID dikosongkan. Sistem menggunakan mod Pemilih Akaun Google Pantas."
      );
      await loadOverview();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menyimpan Google Client ID.");
    } finally {
      setSavingOauth(false);
    }
  };

  if (!open) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/65 p-0 backdrop-blur-sm sm:items-center sm:p-5"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`flex max-h-[94dvh] w-full flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-white shadow-2xl transition-all sm:rounded-2xl ${
          tab === "vault" ? "max-w-7xl" : "max-w-6xl"
        }`}
      >
        {/* Header Konsol Pembangun */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-gradient-to-r from-[#0b1e36] via-[#0f2744] to-[#13355c] px-5 py-3.5 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-400/20 ring-1 ring-amber-300/40">
              <Cpu className="h-5 w-5 text-amber-300" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-sm sm:text-base font-extrabold tracking-tight">
                  Konsol Pembangun &amp; Audit Penggunaan ({data?.developer || "g.dev/syrzy"})
                </h2>
                <a
                  href="https://g.dev/syrzy"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-full bg-amber-400 px-2 py-0.5 text-[10px] font-extrabold text-slate-950 hover:bg-amber-300"
                >
                  g.dev/syrzy <ExternalLink className="h-2.5 w-2.5" />
                </a>
                {data?.vault_summary && (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                      data.vault_summary.db_engine === "postgresql"
                        ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/40"
                        : "bg-rose-500/25 text-rose-100 ring-1 ring-rose-400/50"
                    }`}
                  >
                    <Database className="h-2.5 w-2.5" />
                    {data.vault_summary.db_engine === "postgresql"
                      ? "PostgreSQL Kekal (Neon)"
                      : "SQLite Sementara (Reset Bila Tidur)"}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-300">
                Semak siapa menggunakan i-UIP Nerus, apa aktiviti yang dijalankan, panggilan Gemini API &amp; anggaran kos operasi masa nyata.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadOverview}
              disabled={loading}
              className="inline-flex items-center gap-1 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Muat Semula
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Tab Bar & Carian (1 baris skrol mendatar di mobile) */}
        <div className="flex flex-col gap-2 border-b border-slate-200 bg-white px-4 pt-2.5 pb-2 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
            {[
              { id: "users", label: `1. Siapa Guna (${data?.users.length ?? 0})`, icon: Users },
              { id: "activities", label: `2. Apa Dibuat (${data?.activities.length ?? 0})`, icon: Activity },
              { id: "costs", label: "3. Kos Operasi & API (RM/USD)", icon: Coins },
              { id: "google_oauth", label: "4. Connector Google OAuth", icon: KeyRound },
              {
                id: "vault",
                label: `5. Arkib & Bucket Dev (${data?.vault_summary?.total_records ?? 0})`,
                icon: Archive,
              },
            ].map((item) => {
              const Icon = item.icon;
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setTab(item.id as typeof tab)}
                  className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                    active
                      ? "bg-[#0f2744] text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              );
            })}
          </div>

          {(tab === "users" || tab === "activities") && (
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative flex-1 sm:flex-none">
                <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Cari nama pegawai, emel atau kes..."
                  className="w-full rounded-lg border border-slate-300 pl-8 pr-3 py-1.5 text-base focus:border-blue-500 focus:outline-none sm:w-56 sm:text-xs"
                />
              </div>
              {tab === "activities" && data && (
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-base font-semibold text-slate-700 sm:text-xs"
                >
                  <option value="SEMUA">Semua Aktiviti</option>
                  {data.summary.action_breakdown.map((b) => (
                    <option key={b.action_type} value={b.action_type}>
                      {b.action_type} ({b.count})
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}
        </div>

        {/* Kandungan Boleh Tatal (termasuk KPI pada mobile supaya jadual luas) */}
        <div className="flex-1 overflow-y-auto p-4 bg-slate-50/40 sm:p-5 space-y-4">
          {data && (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Pegawai Berdaftar</span>
                  <Users className="h-4 w-4 text-blue-600" />
                </div>
                <div className="mt-1 text-xl font-extrabold text-slate-900">
                  {data.summary.total_users}
                </div>
                <div className="text-[10px] text-emerald-700 font-medium">
                  {data.summary.active_sessions} sesi log masuk aktif
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Aktiviti Direkod</span>
                  <Activity className="h-4 w-4 text-indigo-600" />
                </div>
                <div className="mt-1 text-xl font-extrabold text-slate-900">
                  {data.summary.total_actions}
                </div>
                <div className="text-[10px] text-slate-600">
                  {data.summary.local_free_calls} tempatan • {data.summary.cloud_api_calls} Cloud API
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Kos Operasi</span>
                  <Coins className="h-4 w-4 text-amber-600" />
                </div>
                <div className="mt-1 text-xl font-extrabold text-emerald-700">
                  RM {data.summary.total_cost_myr.toFixed(4)}
                </div>
                <div className="text-[10px] text-slate-500">
                  USD {data.summary.total_cost_usd.toFixed(5)}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Status Connector</span>
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                </div>
                <div className="mt-1 text-xs font-extrabold text-slate-900">
                  Google: {data.google_client_id_configured ? "Aktif" : "Belum"}
                </div>
                <div className="mt-0.5 text-[10px] text-slate-600">
                  Gemini: {data.gemini_api_key_configured ? "Aktif" : "Mod RM0"}
                </div>
              </div>

              <button
                type="button"
                onClick={() => setTab("vault")}
                className="col-span-2 rounded-xl border border-indigo-200 bg-indigo-50/70 p-3 text-left transition hover:border-indigo-400 hover:bg-indigo-50 sm:col-span-1"
              >
                <div className="flex items-center justify-between text-[11px] font-semibold text-indigo-900">
                  <span>Arkib &amp; Bucket Dev</span>
                  <Database className="h-4 w-4 text-indigo-700" />
                </div>
                <div className="mt-1 text-xl font-extrabold text-indigo-950">
                  {data.vault_summary?.total_records ?? 0} Rekod
                </div>
                <div className="text-[10px] font-semibold text-indigo-800">
                  {data.vault_summary?.total_files ?? 0} fail •{" "}
                  {data.vault_summary?.is_cloud_bucket ? "Private S3/Neon" : "DB + Local"}
                </div>
              </button>
            </div>
          )}
          {data?.vault_summary?.db_engine === "sqlite" && (
            <div className="flex items-start gap-2.5 rounded-xl border border-rose-300 bg-rose-50/90 px-3.5 py-2.5 text-xs text-rose-950">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
              <div className="space-y-1 leading-relaxed">
                <p>
                  <span className="font-extrabold">Amaran Storan Sementara (SQLite):</span> Data pengguna, aktiviti &amp; Arkib Dev kini disimpan dalam SQLite tempatan (<code className="rounded bg-rose-100 px-1 py-0.5 text-[11px] font-semibold">/tmp/uip_command.db</code> di Cloud Run) yang akan <span className="font-bold">reset menjadi kosong setiap kali Cloud Run tidur (<em>scale-to-zero</em>) atau revisi baharu di-deploy</span>.
                </p>
                <p>
                  <span className="font-extrabold">Tindakan Kekal:</span> Masukkan <code className="rounded bg-rose-100 px-1 py-0.5 text-[11px] font-semibold">DATABASE_URL</code> (Connection String PostgreSQL Neon bermula <code className="rounded bg-rose-100 px-1 py-0.5 text-[11px] font-semibold">postgresql://...</code>) dalam <span className="font-bold">Google Cloud Run → Edit &amp; Deploy New Revision → Variables &amp; Secrets</span>, kemudian sahkan <code className="rounded bg-rose-100 px-1 py-0.5 text-[11px] font-semibold">/api/health</code> memulangkan <code className="rounded bg-rose-100 px-1 py-0.5 text-[11px] font-semibold">{`{"status":"ok","db":"postgres"}`}</code>.
                </p>
              </div>
            </div>
          )}
          {error && (
            <div className="mb-3 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
              {error}
            </div>
          )}

          {loading && !data ? (
            <div className="flex items-center justify-center py-12 text-xs text-slate-500 gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Memuatkan data telemetri pembangun...
            </div>
          ) : null}

          {/* TAB 1: SIAPA GUNA */}
          {data && tab === "users" && (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-100 text-[11px] font-bold uppercase text-slate-600">
                  <tr>
                    <th className="px-3.5 py-2.5">Pegawai &amp; Emel</th>
                    <th className="px-3.5 py-2.5">Kaedah Masuk</th>
                    <th className="px-3.5 py-2.5">Pejabat PKD / JKN</th>
                    <th className="px-3.5 py-2.5">Kad Kuasa / Gred</th>
                    <th className="px-3.5 py-2.5 text-center">Bil. Tindakan</th>
                    <th className="px-3.5 py-2.5">Aktif Terakhir</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/80">
                      <td className="px-3.5 py-2.5">
                        <div className="font-bold text-slate-900">{u.full_name}</div>
                        <div className="text-[11px] text-slate-500">{u.email}</div>
                      </td>
                      <td className="px-3.5 py-2.5">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            u.auth_provider === "google"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {u.auth_provider === "google" ? "Google OAuth" : "Emel KKM"}
                        </span>
                      </td>
                      <td className="px-3.5 py-2.5">
                        <div className="font-medium text-slate-800">{u.district_pkd}</div>
                        <div className="text-[10px] text-slate-500">{u.state_jkn}</div>
                      </td>
                      <td className="px-3.5 py-2.5">
                        <div className="font-mono text-[11px] text-slate-800">
                          {u.kkm_authority_card_no || "-"}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          Gred {u.grade} • {u.system_role}
                        </div>
                      </td>
                      <td className="px-3.5 py-2.5 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <span className="inline-flex min-w-[2rem] items-center justify-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-extrabold text-indigo-800">
                            {u.total_actions}
                          </span>
                          {(u.archived_records_count ?? 0) > 0 && (
                            <button
                              type="button"
                              onClick={() => openVaultForUser(u.email)}
                              title="Lihat rekod & dokumen pegawai ini dalam Arkib Dev"
                              className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 ring-1 ring-emerald-200 hover:bg-emerald-100"
                            >
                              <Archive className="h-2.5 w-2.5" />
                              {u.archived_records_count}
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-3.5 py-2.5 text-[11px] text-slate-600 whitespace-nowrap">
                        {u.latest_activity_at || u.updated_at}
                      </td>
                    </tr>
                  ))}
                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-xs text-slate-500">
                        Tiada akaun pegawai sepadan dengan carian anda.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 2: APA DIBUAT */}
          {data && tab === "activities" && (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-100 text-[11px] font-bold uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2.5">Waktu</th>
                    <th className="px-3 py-2.5">Pegawai</th>
                    <th className="px-3 py-2.5">Tindakan</th>
                    <th className="px-3 py-2.5">Perincian Aktiviti</th>
                    <th className="px-3 py-2.5">Enjin / Model</th>
                    <th className="px-3 py-2.5 text-right">Masa / Kos</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredActivities.map((act) => (
                    <tr key={act.id} className="hover:bg-slate-50/80">
                      <td className="px-3 py-2 text-[11px] text-slate-500 whitespace-nowrap">
                        {act.created_at}
                      </td>
                      <td className="px-3 py-2">
                        <div className="font-bold text-slate-900">{act.user_name}</div>
                        <div className="text-[10px] text-slate-500">{act.user_email}</div>
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span
                          className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold ${
                            ACTION_BADGES[act.action_type] || "bg-slate-100 text-slate-700 border-slate-200"
                          }`}
                        >
                          {act.action_type}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-800 max-w-md">
                        {act.action_detail}
                      </td>
                      <td className="px-3 py-2">
                        <div className="font-mono text-[10px] text-slate-700">{act.model_used}</div>
                        <div className="text-[10px] text-slate-400">
                          {act.is_cloud_api
                            ? `${act.est_input_tokens} in / ${act.est_output_tokens} out token`
                            : "Tempatan (Tiada token awan)"}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <div className="font-bold text-emerald-700">
                          {act.is_cloud_api ? `RM ${act.est_cost_myr.toFixed(4)}` : "RM 0.00"}
                        </div>
                        <div className="text-[10px] text-slate-400">{act.latency_ms} ms</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 3: KOS OPERASI & PANGGILAN API */}
          {data && tab === "costs" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
                <div className="text-xs font-extrabold text-emerald-950">
                  Rumusan Kos Operasi Sebenar (Hibrid Tempatan + Cloud Gemini)
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-emerald-900">
                  Lebih 85% aliran kerja harian PPKP di pejabat kesihatan seluruh Malaysia (Tanya Pakar Mod Pantas, 16 templat dokumen IP, Borang 114, Notis Kompaun, Eksport Word <code>.docx</code>, Carian RAG Akta &amp; Penyamaran PDPA) diproses <strong>100% di dalam pelayan/PC tempatan pada kos RM 0.00</strong>. Caj API Gemini hanya berlaku apabila pegawai menekan Semak IP AI (20 Kriteria), Ekstrak Gambar OCR, atau togol &ldquo;Mod AI Mendalam&rdquo;.
                </p>
              </div>

              {/* Pecahan Mengikut Modul Aktiviti */}
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <div className="border-b border-slate-200 bg-slate-100 px-4 py-2 text-xs font-bold text-slate-800">
                  Penggunaan &amp; Kos Terkumpul Mengikut Jenis Aktiviti (1 USD = RM {data.summary.usd_to_myr_rate.toFixed(2)})
                </div>
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  <thead className="bg-slate-50 text-[11px] font-bold text-slate-600">
                    <tr>
                      <th className="px-4 py-2">Jenis Aktiviti</th>
                      <th className="px-4 py-2 text-center">Jumlah Guna</th>
                      <th className="px-4 py-2 text-center">Panggilan Cloud Gemini</th>
                      <th className="px-4 py-2 text-right">Kos USD</th>
                      <th className="px-4 py-2 text-right">Kos MYR (RM)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.summary.action_breakdown.map((b) => (
                      <tr key={b.action_type}>
                        <td className="px-4 py-2 font-bold text-slate-800">{b.action_type}</td>
                        <td className="px-4 py-2 text-center">{b.count}</td>
                        <td className="px-4 py-2 text-center">{b.cloud_calls}</td>
                        <td className="px-4 py-2 text-right font-mono">${b.total_usd.toFixed(5)}</td>
                        <td className="px-4 py-2 text-right font-bold text-emerald-700">
                          RM {b.total_myr.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Jadual Rujukan Kadar Kos Per Panggilan */}
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <div className="border-b border-slate-200 bg-slate-100 px-4 py-2 text-xs font-bold text-slate-800">
                  Jadual Rujukan Kos Setiap Panggilan API &amp; Enjin i-UIP Nerus
                </div>
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  <thead className="bg-slate-50 text-[11px] font-bold text-slate-600">
                    <tr>
                      <th className="px-4 py-2">Modul Aplikasi</th>
                      <th className="px-4 py-2">Enjin / Model</th>
                      <th className="px-4 py-2">Anggaran Kos / Panggilan</th>
                      <th className="px-4 py-2">Catatan Operasi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.pricing_reference.map((item) => (
                      <tr key={item.module}>
                        <td className="px-4 py-2 font-bold text-slate-900">{item.module}</td>
                        <td className="px-4 py-2 font-mono text-[11px] text-slate-700">{item.engine}</td>
                        <td className="px-4 py-2 font-extrabold text-emerald-700 whitespace-nowrap">
                          {item.cost_per_call_myr}
                        </td>
                        <td className="px-4 py-2 text-slate-600">{item.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: CONNECTOR GOOGLE OAUTH */}
          {data && tab === "google_oauth" && (
            <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">
                  Konfigurasi Google Sign-In Connector (OAuth 2.0 Web Client ID)
                </h3>
                <p className="mt-1 text-xs text-slate-600 leading-relaxed">
                  Tampalkan <strong>Google OAuth 2.0 Web Client ID</strong> daripada Google Cloud Console di sini untuk mengaktifkan butang rasmi <em>Google Identity Services (GIS)</em> dan pengesahan token Google sebenar. Kos Google Sign-In ialah <strong>RM 0.00 (Percuma)</strong>.
                </p>
              </div>

              <form onSubmit={handleSaveGoogleClientId} className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700">
                    GOOGLE_CLIENT_ID (Web Application Client ID)
                  </label>
                  <input
                    type="text"
                    value={googleClientId}
                    onChange={(e) => setGoogleClientId(e.target.value)}
                    placeholder="Contoh: 987654321098-abc123def456.apps.googleusercontent.com"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs font-mono focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-3 text-[11px] text-blue-950 space-y-1">
                  <div className="font-bold">Langkah Pautan Google Cloud Console (Percuma):</div>
                  <div>1. Buka <code>console.cloud.google.com</code> → <strong>APIs &amp; Services</strong> → <strong>Credentials</strong>.</div>
                  <div>2. Cipta <strong>OAuth client ID (Web application)</strong> → masukkan <em>Authorized JavaScript origins</em>: <code>http://localhost:3000</code> dan domain rasmi PKD anda.</div>
                  <div>3. Salin Client ID (<code>...apps.googleusercontent.com</code>) dan simpan di atas.</div>
                </div>

                {oauthMsg && (
                  <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-xs font-semibold text-emerald-800">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    <span>{oauthMsg}</span>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={savingOauth}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
                  >
                    {savingOauth && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    Simpan Google Client ID
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 5: ARKIB & BUCKET EKSKLUSIF DEV */}
          {tab === "vault" && (
            <DevVaultTab
              authToken={authToken}
              developerEmail={developerEmail}
              initialUserFilter={vaultUserFilter}
              onClearInitialUserFilter={() => setVaultUserFilter("")}
              refreshSignal={vaultRefreshSignal}
            />
          )}
        </div>
      </div>
    </div>
  );
}
