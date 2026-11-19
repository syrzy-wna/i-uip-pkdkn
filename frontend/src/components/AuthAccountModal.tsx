"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  Building2,
  KeyRound,
  Loader2,
  LogOut,
  Save,
  ShieldCheck,
  UserCheck,
  UserPlus,
  X,
} from "lucide-react";
import {
  fetchRuntimeSettings,
  googleSignInOfficer,
  loginOfficer,
  logoutOfficer,
  registerOfficer,
  updateOfficerProfile,
} from "@/lib/api";

const DEFAULT_GOOGLE_CLIENT_ID =
  "290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com";

const SSPA_GRADE_GROUPS: Array<{
  label: string;
  items: Array<{ value: string; text: string }>;
}> = [
  {
    label: "Skim PPKP (Kumpulan Pelaksana — SSPA)",
    items: [
      { value: "U5", text: "U5 — PPKP (dahulu U29)" },
      { value: "U6", text: "U6 — PPKP Penyelia / Kanan (dahulu U32)" },
      { value: "U7", text: "U7 — PPKP Kanan / KPPKP (dahulu U36/U38)" },
      { value: "U8", text: "U8 — Ketua PPKP / KPPKP (dahulu U40)" },
    ],
  },
  {
    label: "Skim PKP (Pengurusan & Profesional — SSPA)",
    items: [
      { value: "U9", text: "U9 — PKP (dahulu U41/U42)" },
      { value: "U10", text: "U10 — PKP Kanan (dahulu U44)" },
      { value: "U12", text: "U12 — PKP Kanan (dahulu U48)" },
      { value: "U13", text: "U13 — PKP Kanan (dahulu U52)" },
      { value: "U14", text: "U14 — PKP Kanan (dahulu U54)" },
    ],
  },
  {
    label: "Pegawai Perubatan / PKD (SSPA)",
    items: [
      { value: "UD9", text: "UD9 — Pegawai Perubatan (dahulu UD41/43)" },
      { value: "UD10", text: "UD10 — Pegawai Perubatan (dahulu UD44)" },
      { value: "UD12", text: "UD12 — Pegawai Perubatan (dahulu UD48)" },
      { value: "UD13", text: "UD13 — Pakar / Pegawai Perubatan (dahulu UD52)" },
      { value: "UD14", text: "UD14 — Pakar / PKD (dahulu UD54)" },
    ],
  },
  {
    label: "Pegawai Sains Entomologi / Mikrobiologi (SSPA)",
    items: [
      { value: "C9", text: "C9 — Pegawai Sains (dahulu C41)" },
      { value: "C10", text: "C10 — Pegawai Sains (dahulu C44)" },
      { value: "C12", text: "C12 — Pegawai Sains (dahulu C48)" },
      { value: "C13", text: "C13 — Pegawai Sains (dahulu C52)" },
      { value: "C14", text: "C14 — Pegawai Sains (dahulu C54)" },
    ],
  },
];

function renderSspaGradeOptions() {
  return SSPA_GRADE_GROUPS.map((grp) => (
    <optgroup key={grp.label} label={grp.label}>
      {grp.items.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.text}
        </option>
      ))}
    </optgroup>
  ));
}
import type { OfficerProfile } from "@/lib/types";

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: {
          initialize: (cfg: Record<string, unknown>) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
        };
        oauth2?: {
          initTokenClient: (cfg: Record<string, unknown>) => {
            requestAccessToken: (opts?: Record<string, unknown>) => void;
          };
        };
      };
    };
  }
}

interface AuthAccountModalProps {
  open: boolean;
  onClose: () => void;
  officer: OfficerProfile | null;
  authToken: string | null;
  initialTab?: "google" | "login" | "register" | "profile";
  onAuthenticated: (officer: OfficerProfile, token: string) => void;
  onProfileUpdated: (officer: OfficerProfile) => void;
  onLoggedOut: () => void;
}

export default function AuthAccountModal({
  open,
  onClose,
  officer,
  authToken,
  initialTab = "google",
  onAuthenticated,
  onProfileUpdated,
  onLoggedOut,
}: AuthAccountModalProps) {
  const [tab, setTab] = useState<"google" | "login" | "register" | "profile">(
    officer ? "profile" : initialTab
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Tetapan & Token Google OAuth 2.0 Sebenar
  const [googleClientId, setGoogleClientId] = useState(DEFAULT_GOOGLE_CLIENT_ID);
  const [gsiReady, setGsiReady] = useState(false);
  const gsiBtnRef = useRef<HTMLDivElement | null>(null);

  // Borang Log Masuk Emel Biasa
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Borang Daftar Akaun Emel Biasa (Lalai PKD Kuala Nerus, Terengganu)
  const [regForm, setRegForm] = useState({
    email: "",
    password: "",
    full_name: "",
    ic_number: "",
    designation: "Penolong Pegawai Kesihatan Persekitaran (PPKP)",
    grade: "U5",
    kkm_authority_card_no: "",
    prosecution_authorization_no: "",
    state_jkn: "Jabatan Kesihatan Negeri Terengganu",
    district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
    office_address: "Lot PT 37820, Taman Permint Perdana, Seberang Takir, 21300 Kuala Nerus, Terengganu",
    unit_assignment: "Unit Inspektorat dan Perundangan (UIP)",
    default_magistrate_court: "MAHKAMAH MAJISTRET DI KUALA TERENGGANU, DALAM NEGERI TERENGGANU DARUL IMAN",
    system_role: "PEGAWAI_PENYIASAT",
    default_computer_desc: "Komputer Meja Rasmi KKM Dell OptiPlex Pejabat UIP PKD Kuala Nerus",
    default_printer_desc: "Pencetak Laser Warna Pejabat UIP PKD Kuala Nerus",
    default_camera_desc: "Kamera Digital Rasmi Penguatkuasaan PKD Kuala Nerus",
  });

  // Borang Sunting Profil
  const [profileForm, setProfileForm] = useState<Partial<OfficerProfile>>({});

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSuccessMsg(null);
    if (officer) {
      setTab("profile");
      setProfileForm(officer);
    } else {
      setTab(initialTab === "profile" ? "google" : initialTab);
      fetchRuntimeSettings()
        .then((s) => {
          const cid = (s.google_client_id || "").trim() || DEFAULT_GOOGLE_CLIENT_ID;
          setGoogleClientId(cid);
        })
        .catch(() => {
          setGoogleClientId(DEFAULT_GOOGLE_CLIENT_ID);
        });
    }
  }, [open, officer, initialTab]);

  useEffect(() => {
    if (!open || officer || tab !== "google" || !googleClientId) {
      setGsiReady(false);
      return;
    }
    let cancelled = false;
    const initGisButton = () => {
      if (cancelled || !window.google?.accounts?.id) return;
      setGsiReady(true);
      if (gsiBtnRef.current) {
        gsiBtnRef.current.innerHTML = "";
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: { credential?: string }) => {
            if (!response?.credential) return;
            setLoading(true);
            setError(null);
            try {
              const res = await googleSignInOfficer({
                id_token: response.credential,
                district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
                state_jkn: "Jabatan Kesihatan Negeri Terengganu",
              });
              onAuthenticated(res.user, res.token);
              onClose();
            } catch (err) {
              setError(
                err instanceof Error
                  ? err.message
                  : "Pengesahan token Google OAuth gagal."
              );
            } finally {
              setLoading(false);
            }
          },
        });
        window.google.accounts.id.renderButton(gsiBtnRef.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "pill",
          width: 320,
        });
      }
    };

    if (window.google?.accounts?.id) {
      initGisButton();
    } else {
      const existingScript = document.getElementById("google-gsi-client-script");
      if (!existingScript) {
        const script = document.createElement("script");
        script.id = "google-gsi-client-script";
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = initGisButton;
        document.head.appendChild(script);
      } else {
        existingScript.addEventListener("load", initGisButton);
      }
    }
    return () => {
      cancelled = true;
    };
  }, [open, officer, tab, googleClientId, onAuthenticated, onClose]);

  if (!open) return null;

  const handleRealGooglePopup = () => {
    if (!googleClientId) {
      setError("GOOGLE_CLIENT_ID belum ditetapkan. Sila masukkan Google OAuth Web Client ID di bawah.");
      return;
    }
    const oauth2 = window.google?.accounts?.oauth2;
    if (!oauth2) {
      setError("SDK Google Identity Services sedang dimuatkan atau disekat rangkaian. Sila cuba sebentar lagi.");
      return;
    }
    setError(null);
    const tokenClient = oauth2.initTokenClient({
      client_id: googleClientId,
      scope: "openid email profile",
      callback: async (tokenResp: { access_token?: string; error?: string }) => {
        if (tokenResp.error || !tokenResp.access_token) {
          setError("Log masuk Google dibatalkan atau gagal memberi kebenaran akses.");
          return;
        }
        setLoading(true);
        try {
          const res = await googleSignInOfficer({
            access_token: tokenResp.access_token,
            district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
            state_jkn: "Jabatan Kesihatan Negeri Terengganu",
          });
          onAuthenticated(res.user, res.token);
          onClose();
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "Pengesahan Google OAuth gagal."
          );
        } finally {
          setLoading(false);
        }
      },
    });
    tokenClient.requestAccessToken({ prompt: "select_account" });
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await loginOfficer(loginEmail, loginPassword);
      onAuthenticated(res.user, res.token);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal log masuk.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await registerOfficer(regForm);
      onAuthenticated(res.user, res.token);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mendaftar akaun.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authToken) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await updateOfficerProfile(authToken, profileForm);
      onProfileUpdated(updated);
      setSuccessMsg("Profil pegawai & tetapan perkakasan S.90A berjaya dikemas kini.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengemas kini profil.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    if (authToken) {
      await logoutOfficer(authToken).catch(() => {});
    }
    onLoggedOut();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
      <div className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header Modal */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-[#0f2744] px-5 py-3.5 text-white">
          <div className="flex items-center gap-2.5">
            <UserCheck className="h-5 w-5 text-amber-300" />
            <div>
              <h2 className="text-sm font-bold">
                Akaun Rasmi Pegawai UIP KKM (Auto-Isi Borang 114, DS &amp; Sijil 90A)
              </h2>
              <p className="text-[11px] text-slate-300">
                Daftar akaun pegawai sebenar supaya Kad Kuasa, PKD, Mahkamah &amp; butiran komputer S.90A terus masuk ke dokumen.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-300 hover:bg-white/10 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex flex-wrap border-b border-slate-200 bg-slate-50 px-5 pt-2.5 gap-1.5">
          {!officer ? (
            <>
              <button
                type="button"
                onClick={() => setTab("google")}
                className={`inline-flex items-center gap-1.5 rounded-t-lg px-3.5 py-2 text-xs font-bold transition ${
                  tab === "google"
                    ? "border border-b-white border-slate-200 bg-white text-[#0f2744]"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <span className="font-extrabold text-blue-600">G</span> Akaun Google (Mudah)
              </button>
              <button
                type="button"
                onClick={() => setTab("login")}
                className={`inline-flex items-center gap-1.5 rounded-t-lg px-3.5 py-2 text-xs font-bold transition ${
                  tab === "login"
                    ? "border border-b-white border-slate-200 bg-white text-[#0f2744]"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <KeyRound className="h-3.5 w-3.5" /> Log Masuk Emel Biasa
              </button>
              <button
                type="button"
                onClick={() => setTab("register")}
                className={`inline-flex items-center gap-1.5 rounded-t-lg px-3.5 py-2 text-xs font-bold transition ${
                  tab === "register"
                    ? "border border-b-white border-slate-200 bg-white text-[#0f2744]"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <UserPlus className="h-3.5 w-3.5" /> Daftar Emel Biasa
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setTab("profile")}
              className="inline-flex items-center gap-1.5 rounded-t-lg border border-b-white border-slate-200 bg-white px-4 py-2 text-xs font-bold text-[#0f2744]"
            >
              <BadgeCheck className="h-3.5 w-3.5 text-emerald-600" /> Profil Pegawai Aktif
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
              {error}
            </div>
          )}
          {successMsg && (
            <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">
              {successMsg}
            </div>
          )}

          {/* TAB 0: GOOGLE OAUTH 2.0 SEBENAR */}
          {tab === "google" && !officer && (
            <div className="space-y-4">
              <div className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50/90 to-white p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
                    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                      <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z" />
                      <path fill="#FBBC05" d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z" />
                      <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z" />
                    </svg>
                    <span>Google OAuth 2.0 Connector (Pengesahan Pelayan Google Sebenar)</span>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                      googleClientId
                        ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300"
                        : "bg-amber-100 text-amber-800 ring-1 ring-amber-300"
                    }`}
                  >
                    {googleClientId ? "OAuth 2.0 Sebenar Aktif" : "Perlu GOOGLE_CLIENT_ID"}
                  </span>
                </div>

                {googleClientId ? (
                  <div className="space-y-3">
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      Klik butang Google rasmi di bawah. Google akan membuka tetingkap pengesahan akaun sebenar dan menghantar token rasmi (<code>id_token</code> / <code>access_token</code>) untuk disahkan oleh pelayan <strong>i-UIP Nerus</strong> sebelum mendaftarkan sesi pegawai.
                    </p>
                    <div className="flex flex-wrap items-center gap-3 pt-1">
                      <div ref={gsiBtnRef} className="min-h-[40px]" />
                      <button
                        type="button"
                        disabled={loading || !gsiReady}
                        onClick={handleRealGooglePopup}
                        className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 shadow-xs transition hover:border-blue-400 hover:bg-blue-50/50 disabled:opacity-60"
                      >
                        {loading ? (
                          <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                        ) : (
                          <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                            <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                            <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z" />
                            <path fill="#FBBC05" d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z" />
                            <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z" />
                          </svg>
                        )}
                        <span>Log Masuk / Daftar dengan Google (Popup OAuth)</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-[11px] text-amber-950 leading-relaxed">
                      <strong>Google Sign-In belum dikonfigurasi pada pelayan ini.</strong>{" "}
                      Sila gunakan tab <strong>Daftar Emel Biasa</strong> atau <strong>Log Masuk Emel Biasa</strong> untuk akses segera.
                    </div>
                    <button
                      type="button"
                      onClick={() => setTab("register")}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-bold text-white hover:bg-emerald-800"
                    >
                      <UserPlus className="h-3.5 w-3.5" /> Daftar Akaun Emel Pegawai
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 1: LOG MASUK */}
          {tab === "login" && !officer && (
            <div className="space-y-4">
              <form onSubmit={handleLogin} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700">
                      Emel Rasmi Pegawai
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="contoh: nama@moh.gov.my"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700">
                      Kata Laluan
                    </label>
                    <input
                      type="password"
                      required
                      placeholder="Masukkan kata laluan"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
                    />
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
                  >
                    {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <KeyRound className="h-3.5 w-3.5" />}
                    Log Masuk ke i-UIP Nerus
                  </button>
                  <button
                    type="button"
                    onClick={() => setTab("register")}
                    className="text-xs font-bold text-blue-700 hover:underline"
                  >
                    Belum ada akaun? Daftar Akaun Sebenar →
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 2: DAFTAR AKAUN BAHARU */}
          {tab === "register" && !officer && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 space-y-3">
                <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                  <ShieldCheck className="h-4 w-4 text-blue-700" />
                  1. Maklumat Log Masuk &amp; Perjawatan KKM
                </h4>
                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Emel Rasmi KKM / Kerja *</label>
                    <input
                      type="email"
                      required
                      placeholder="nama@moh.gov.my"
                      value={regForm.email}
                      onChange={(e) => setRegForm({ ...regForm, email: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Kata Laluan (min. 6 aksara) *</label>
                    <input
                      type="password"
                      required
                      minLength={6}
                      value={regForm.password}
                      onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Nama Penuh &amp; Gelaran Pegawai *</label>
                    <input
                      type="text"
                      required
                      placeholder="cth: PPKP Mohd Amirul bin Zaki"
                      value={regForm.full_name}
                      onChange={(e) => setRegForm({ ...regForm, full_name: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">No. Kad Pengenalan (untuk Sijil 90A)</label>
                    <input
                      type="text"
                      placeholder="890101-10-5511"
                      value={regForm.ic_number}
                      onChange={(e) => setRegForm({ ...regForm, ic_number: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Jawatan</label>
                    <select
                      value={regForm.designation}
                      onChange={(e) => setRegForm({ ...regForm, designation: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    >
                      <option>Penolong Pegawai Kesihatan Persekitaran (PPKP)</option>
                      <option>Pegawai Kesihatan Persekitaran (PKP)</option>
                      <option>Pegawai Perubatan Kesihatan Daerah (PKD)</option>
                      <option>Pegawai Sains (Entomologi / Mikrobiologi)</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-700">Gred (SSPA)</label>
                      <select
                        value={regForm.grade}
                        onChange={(e) => setRegForm({ ...regForm, grade: e.target.value })}
                        className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs"
                      >
                        {renderSspaGradeOptions()}
                      </select>
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-slate-700">Peranan UIP</label>
                      <select
                        value={regForm.system_role}
                        onChange={(e) => setRegForm({ ...regForm, system_role: e.target.value })}
                        className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs"
                      >
                        <option value="PEGAWAI_PEMERIKSA">Pegawai Pemeriksa</option>
                        <option value="PEGAWAI_PENYIASAT">Pegawai Penyiasat (IO)</option>
                        <option value="PENYEMAK_KANAN_UIP">Penyemak Kanan / KPPKP</option>
                        <option value="PEGAWAI_PENDAKWA">Pegawai Pendakwa (PO)</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">No. Kad Kuasa Rasmi KKM</label>
                    <input
                      type="text"
                      placeholder="cth: KKM/SEL/PKD-PTG/0991"
                      value={regForm.kkm_authority_card_no}
                      onChange={(e) => setRegForm({ ...regForm, kkm_authority_card_no: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">No. Tauliah S.377(b) KTJ (Jika PO)</label>
                    <input
                      type="text"
                      placeholder="Pilihan - hanya jika Pegawai Pendakwa"
                      value={regForm.prosecution_authorization_no}
                      onChange={(e) => setRegForm({ ...regForm, prosecution_authorization_no: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 space-y-2.5">
                <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                  <Building2 className="h-4 w-4 text-emerald-700" />
                  2. Penempatan PKD, Mahkamah &amp; Perkakasan Tetap Sijil Seksyen 90A
                </h4>
                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Jabatan Kesihatan Negeri (JKN)</label>
                    <input
                      type="text"
                      value={regForm.state_jkn}
                      onChange={(e) => setRegForm({ ...regForm, state_jkn: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Pejabat Kesihatan Daerah (PKD)</label>
                    <input
                      type="text"
                      value={regForm.district_pkd}
                      onChange={(e) => setRegForm({ ...regForm, district_pkd: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-[11px] font-semibold text-slate-700">Mahkamah Majistret Bidang Kuasa</label>
                    <input
                      type="text"
                      value={regForm.default_magistrate_court}
                      onChange={(e) => setRegForm({ ...regForm, default_magistrate_court: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Kamera / Telefon Rasmi S.90A</label>
                    <input
                      type="text"
                      value={regForm.default_camera_desc}
                      onChange={(e) => setRegForm({ ...regForm, default_camera_desc: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-700">Komputer Pejabat S.90A</label>
                    <input
                      type="text"
                      value={regForm.default_computer_desc}
                      onChange={(e) => setRegForm({ ...regForm, default_computer_desc: e.target.value })}
                      className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-800 disabled:opacity-60"
              >
                {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserPlus className="h-3.5 w-3.5" />}
                Daftar &amp; Aktifkan Akaun Pegawai
              </button>
            </form>
          )}

          {/* TAB 3: PROFIL PEGAWAI AKTIF */}
          {officer && (
            <form onSubmit={handleSaveProfile} className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-200 bg-emerald-50/70 p-3">
                <div>
                  <div className="text-xs font-bold text-emerald-950">
                    {officer.full_name} ({officer.grade})
                  </div>
                  <div className="text-[11px] text-emerald-800">
                    {officer.email} | Kad Kuasa: {officer.kkm_authority_card_no || "-"} | {officer.district_pkd}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700"
                >
                  <LogOut className="h-3.5 w-3.5" /> Log Keluar
                </button>
              </div>

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">Nama Penuh Pegawai</label>
                  <input
                    type="text"
                    value={profileForm.full_name || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">Jawatan</label>
                  <select
                    value={profileForm.designation || "Penolong Pegawai Kesihatan Persekitaran (PPKP)"}
                    onChange={(e) => setProfileForm({ ...profileForm, designation: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                  >
                    <option>Penolong Pegawai Kesihatan Persekitaran (PPKP)</option>
                    <option>Pegawai Kesihatan Persekitaran (PKP)</option>
                    <option>Pegawai Perubatan Kesihatan Daerah (PKD)</option>
                    <option>Pegawai Sains (Entomologi / Mikrobiologi)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">Gred (SSPA)</label>
                  <select
                    value={profileForm.grade || "U5"}
                    onChange={(e) => setProfileForm({ ...profileForm, grade: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                  >
                    {renderSspaGradeOptions()}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">No. Kad Kuasa KKM</label>
                  <input
                    type="text"
                    value={profileForm.kkm_authority_card_no || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, kkm_authority_card_no: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">Pejabat Kesihatan Daerah (PKD)</label>
                  <input
                    type="text"
                    value={profileForm.district_pkd || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, district_pkd: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">JKN Negeri</label>
                  <input
                    type="text"
                    value={profileForm.state_jkn || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, state_jkn: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-semibold text-slate-700">Mahkamah Majistret Tetap</label>
                  <input
                    type="text"
                    value={profileForm.default_magistrate_court || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_magistrate_court: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">Kamera Rasmi (Sijil 90A)</label>
                  <input
                    type="text"
                    value={profileForm.default_camera_desc || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_camera_desc: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700">Komputer Pejabat (Sijil 90A)</label>
                  <input
                    type="text"
                    value={profileForm.default_computer_desc || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_computer_desc: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-semibold text-slate-700">Pencetak Pejabat (Sijil 90A)</label>
                  <input
                    type="text"
                    value={profileForm.default_printer_desc || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_printer_desc: e.target.value })}
                    className="mt-0.5 w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
              >
                {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Simpan Kemas Kini Profil
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
