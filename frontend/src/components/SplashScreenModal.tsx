"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  ExternalLink,
  FileText,
  Loader2,
  Mail,
  Scale,
  UserCheck,
} from "lucide-react";
import { fetchRuntimeSettings, googleSignInOfficer } from "@/lib/api";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { OfficerProfile } from "@/lib/types";

const DEFAULT_GOOGLE_CLIENT_ID =
  "290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com";

interface SplashScreenModalProps {
  open: boolean;
  officer: OfficerProfile | null;
  onEnterApp: (mode: ActiveAppMode) => void;
  onOpenGoogleAuth: () => void;
  onOpenEmailAuth: (initialTab: "login" | "register") => void;
  onAuthenticated?: (officer: OfficerProfile, token: string) => void;
  onClose: () => void;
}

const PREVIEW_TABS = [
  {
    id: "ssm",
    label: "Foto SSM → Kompaun",
    icon: Camera,
    input: "Tangkap / muat naik foto Sijil SSM",
    outputTitle: "Notis Kompaun Word (.docx) + 10 Semakan",
    outputNote: "Auto-isi nama, No. SSM & alamat; amaran terus jika amaun langgar had Akta.",
  },
  {
    id: "audit",
    label: "PDF IP → Semak TPR",
    icon: Scale,
    input: "Muat naik PDF Kertas Siasatan atau gambar",
    outputTitle: "Skor Pra-TPR + Kesan Ralat Seksyen & S.90A",
    outputNote: "Kesan awal salah seksyen (S.38/S.44/Akta 514), tarikh bercanggah & kurang Sijil 90A.",
  },
  {
    id: "draft",
    label: "Fakta → Borang 114",
    icon: FileText,
    input: "Taip fakta ringkas kejadian di lokasi",
    outputTitle: "Pakej Fail IP Lengkap (Bahagian A–G)",
    outputNote: "Siap Borang 114, Saman 111, Diari S.119, Rakaman S.112 & Sijil 90A dalam Word.",
  },
] as const;

export default function SplashScreenModal({
  open,
  officer,
  onOpenGoogleAuth,
  onOpenEmailAuth,
  onAuthenticated,
  onClose,
}: SplashScreenModalProps) {
  const [googleClientId, setGoogleClientId] = useState(DEFAULT_GOOGLE_CLIENT_ID);
  const [gsiReady, setGsiReady] = useState(false);
  const [gsiFailed, setGsiFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [previewIdx, setPreviewIdx] = useState(0);
  const gsiBtnRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || officer) return;
    setAuthError(null);
    fetchRuntimeSettings()
      .then((s) => {
        const cid = (s.google_client_id || "").trim() || DEFAULT_GOOGLE_CLIENT_ID;
        setGoogleClientId(cid);
      })
      .catch(() => {
        setGoogleClientId(DEFAULT_GOOGLE_CLIENT_ID);
      });
  }, [open, officer]);

  useEffect(() => {
    if (!open || !officer) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, officer, onClose]);

  useEffect(() => {
    if (!open || officer || !googleClientId) {
      setGsiReady(false);
      setGsiFailed(false);
      return;
    }
    let cancelled = false;
    setGsiFailed(false);

    const initGisButton = () => {
      if (cancelled || !window.google?.accounts?.id) return;
      setGsiReady(true);
      setGsiFailed(false);
      if (gsiBtnRef.current) {
        gsiBtnRef.current.innerHTML = "";
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: { credential?: string }) => {
            if (!response?.credential) return;
            setLoading(true);
            setAuthError(null);
            try {
              const res = await googleSignInOfficer({
                id_token: response.credential,
                district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
                state_jkn: "Jabatan Kesihatan Negeri Terengganu",
              });
              if (onAuthenticated) {
                onAuthenticated(res.user, res.token);
              } else {
                onClose();
              }
            } catch (err) {
              setAuthError(
                err instanceof Error ? err.message : "Pengesahan Akaun Google gagal."
              );
            } finally {
              setLoading(false);
            }
          },
        });
        const btnWidth = Math.max(
          240,
          Math.min(340, (gsiBtnRef.current.parentElement?.clientWidth || 320) - 8)
        );
        window.google.accounts.id.renderButton(gsiBtnRef.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "pill",
          width: btnWidth,
        });
      }
    };

    const failTimer = window.setTimeout(() => {
      if (!cancelled && !window.google?.accounts?.id) {
        setGsiFailed(true);
      }
    }, 4500);

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
        script.onerror = () => {
          if (!cancelled) setGsiFailed(true);
        };
        document.head.appendChild(script);
      } else {
        existingScript.addEventListener("load", initGisButton);
      }
    }

    return () => {
      cancelled = true;
      window.clearTimeout(failTimer);
    };
  }, [open, officer, googleClientId, onAuthenticated, onClose]);

  const handlePopupGoogle = () => {
    const oauth2 = window.google?.accounts?.oauth2;
    if (!oauth2) {
      onOpenGoogleAuth();
      return;
    }
    setAuthError(null);
    const tokenClient = oauth2.initTokenClient({
      client_id: googleClientId,
      scope: "openid email profile",
      callback: async (tokenResp: { access_token?: string; error?: string }) => {
        if (tokenResp.error || !tokenResp.access_token) {
          setAuthError("Log masuk Google dibatalkan atau tidak berjaya.");
          return;
        }
        setLoading(true);
        try {
          const res = await googleSignInOfficer({
            access_token: tokenResp.access_token,
            district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
            state_jkn: "Jabatan Kesihatan Negeri Terengganu",
          });
          if (onAuthenticated) {
            onAuthenticated(res.user, res.token);
          } else {
            onClose();
          }
        } catch (err) {
          setAuthError(err instanceof Error ? err.message : "Pengesahan Akaun Google gagal.");
        } finally {
          setLoading(false);
        }
      },
    });
    tokenClient.requestAccessToken({ prompt: "select_account" });
  };

  if (!open) return null;

  const activePreview = PREVIEW_TABS[previewIdx];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Log Masuk i-UIP Nerus"
      onClick={() => {
        if (officer) onClose();
      }}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-3 backdrop-blur-sm sm:items-center sm:p-6"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="my-auto relative w-full max-w-4xl overflow-hidden rounded-3xl border border-slate-700/50 bg-white shadow-2xl"
      >
        <div className="grid grid-cols-1 md:grid-cols-12">
          {/* BAHAGIAN KIRI / ATAS: NILAI APLIKASI JELAS DALAM 5 SAAT (DESKTOP & TELEFON) */}
          <div className="flex flex-col justify-between bg-[#0f2744] p-5 text-white md:col-span-6 md:p-7">
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/images/logo-iuip-nerus.png"
                    alt="Logo Rasmi i-UIP Nerus"
                    className="h-12 w-12 shrink-0 rounded-full bg-white p-1 object-contain shadow-md ring-2 ring-white/40"
                  />
                  <div>
                    <h2 className="text-xl font-extrabold tracking-tight text-white">
                      i-UIP Nerus
                    </h2>
                    <p className="text-xs font-medium text-slate-300">
                      Unit Inspektorat &amp; Perundangan • PKD Kuala Nerus
                    </p>
                  </div>
                </div>
                <div className="rounded-xl bg-white/95 px-2.5 py-1 shadow-sm">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/images/logo-pkdkn.png"
                    alt="Logo PKD Kuala Nerus"
                    className="h-7 w-auto object-contain"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <h3 className="text-base font-extrabold leading-snug text-white sm:text-lg">
                  Pembantu Kerja Harian PPKP &amp; Pegawai Penyiasat (IO)
                </h3>
                <p className="text-sm leading-relaxed text-slate-200">
                  Rujuk seksyen di lokasi, snap foto SSM terus jadi Notis Kompaun (Word), semak 20 perkara Pra-TPR &amp; siapkan Borang 114 dalam beberapa saat.
                </p>
              </div>

              {/* Pratonton Mini 3 Kemampuan (Tunjuk, Bukan Ceramah — Kelihatan di Telefon & Desktop) */}
              <div className="rounded-2xl bg-white/10 p-3.5 ring-1 ring-white/15 space-y-3">
                <div className="text-xs font-bold uppercase tracking-wide text-slate-300">
                  Apa aplikasi ini boleh buat untuk anda?
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {PREVIEW_TABS.map((t, idx) => {
                    const Icon = t.icon;
                    const active = idx === previewIdx;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setPreviewIdx(idx)}
                        className={`flex min-h-[40px] flex-col items-center justify-center gap-1 rounded-xl px-2 py-1.5 text-center text-xs font-bold transition ${
                          active
                            ? "bg-white text-[#0f2744] shadow-sm"
                            : "bg-white/5 text-slate-200 hover:bg-white/15"
                        }`}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        <span className="line-clamp-1">{t.label}</span>
                      </button>
                    );
                  })}
                </div>

                <div className="rounded-xl bg-white p-3 text-slate-900 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                    <span>Input:</span>
                    <span className="font-bold text-slate-800">{activePreview.input}</span>
                  </div>
                  <div className="flex items-start gap-1.5 text-sm font-extrabold text-[#0f2744]">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>{activePreview.outputTitle}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-600">
                    {activePreview.outputNote}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 hidden border-t border-white/15 pt-3 md:flex md:items-center md:justify-between">
              <span className="text-xs italic text-slate-300">
                &ldquo;Satu Hati, Satu Tekad&rdquo;
              </span>
              <a
                href="https://g.dev/syrzy"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-semibold text-slate-200 hover:text-white"
              >
                <span>Pembangun Sistem: g.dev/syrzy</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>

          {/* BAHAGIAN KANAN / BAWAH: LOG MASUK TENANG & RINGKAS */}
          <div className="flex flex-col justify-center bg-slate-50 p-5 sm:p-7 md:col-span-6">
            {officer ? (
              <div className="space-y-4">
                <div>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                    Sudah Log Masuk
                  </span>
                  <h3 className="mt-2 text-lg font-extrabold text-slate-900">
                    Selamat bertugas, {officer.full_name}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {officer.district_pkd} • Gred {officer.grade}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-sm font-extrabold text-white hover:bg-slate-800"
                >
                  Masuk ke Halaman Utama <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-extrabold text-slate-900">
                    Log Masuk Pegawai UIP
                  </h3>
                  <p className="mt-1 text-sm leading-relaxed text-slate-600">
                    Log masuk sekali sahaja — nama, No. Kad Kuasa &amp; PKD anda diisi automatik pada setiap borang.
                  </p>
                </div>

                {authError && (
                  <div className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-800">
                    {authError}
                  </div>
                )}

                <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="text-xs font-bold text-slate-700">
                    Cara Paling Pantas (1 Klik dengan Akaun Google)
                  </div>

                  {loading ? (
                    <div className="flex min-h-[44px] items-center justify-center gap-2 rounded-full bg-slate-100 text-xs font-bold text-[#0f2744]">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sedang mengesahkan Akaun Google anda...
                    </div>
                  ) : (
                    <div className="flex flex-col items-start gap-2.5">
                      <div ref={gsiBtnRef} className={gsiReady ? "min-h-[44px]" : ""} />
                      {!gsiReady && !gsiFailed && (
                        <button
                          type="button"
                          onClick={onOpenGoogleAuth}
                          className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-800 hover:bg-slate-50"
                        >
                          Teruskan dengan Akaun Google
                        </button>
                      )}
                      {gsiFailed && (
                        <div className="w-full rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-950">
                          Butang Google tidak dapat dimuatkan (mungkin disekat rangkaian pejabat). Sila guna{" "}
                          <strong>Log Masuk E-mel</strong> di bawah.
                        </div>
                      )}
                      {gsiReady && (
                        <button
                          type="button"
                          onClick={handlePopupGoogle}
                          className="text-xs font-semibold text-[#0f2744] hover:underline"
                        >
                          Butang Google tidak keluar? Cuba log masuk di sini →
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs font-semibold text-slate-500">
                  <div className="h-px flex-1 bg-slate-200" />
                  <span>atau guna e-mel kerja</span>
                  <div className="h-px flex-1 bg-slate-200" />
                </div>

                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => onOpenEmailAuth("login")}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2 text-sm font-bold text-white hover:bg-slate-800"
                  >
                    <Mail className="h-4 w-4" />
                    Log Masuk E-mel
                  </button>
                  <button
                    type="button"
                    onClick={() => onOpenEmailAuth("register")}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-800 hover:bg-slate-100"
                  >
                    <UserCheck className="h-4 w-4 text-emerald-700" />
                    Daftar Akaun Baharu
                  </button>
                </div>

                <div className="pt-1 text-center text-xs text-slate-500 md:hidden">
                  <a
                    href="https://g.dev/syrzy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold text-slate-700 hover:underline"
                  >
                    Pembangun Sistem: g.dev/syrzy
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
