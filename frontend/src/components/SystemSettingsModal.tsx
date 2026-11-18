"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, Eye, EyeOff, Loader2, Settings, X } from "lucide-react";
import { fetchRuntimeSettings, saveRuntimeSettings } from "@/lib/api";
import type { SystemStatus } from "@/lib/types";

interface SystemSettingsModalProps {
  open: boolean;
  onClose: () => void;
  status: SystemStatus | null;
  onStatusUpdated: (newStatus: SystemStatus) => void;
}

export default function SystemSettingsModal({
  open,
  onClose,
  status,
  onStatusUpdated,
}: SystemSettingsModalProps) {
  const [geminiKey, setGeminiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [maskedKey, setMaskedKey] = useState("");
  const [googleClientId, setGoogleClientId] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [ollamaModel, setOllamaModel] = useState("gemma3:12b");
  const [geminiModel, setGeminiModel] = useState("gemini-2.5-flash");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setMessage(null);
    setErrorMsg(null);
    fetchRuntimeSettings()
      .then((s) => {
        setMaskedKey(s.masked_gemini_api_key || "");
        setGoogleClientId(s.google_client_id || "");
        setOllamaUrl(s.ollama_base_url || "http://localhost:11434");
        setOllamaModel(s.ollama_model || "gemma3:12b");
        setGeminiModel(s.standard_fallback_model || "gemini-2.5-flash");
      })
      .catch(() => {});
  }, [open]);

  if (!open) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setErrorMsg(null);
    try {
      const payload: {
        gemini_api_key?: string;
        google_client_id: string;
        ollama_base_url: string;
        ollama_model: string;
        standard_fallback_model: string;
      } = {
        google_client_id: googleClientId.trim(),
        ollama_base_url: ollamaUrl,
        ollama_model: ollamaModel,
        standard_fallback_model: geminiModel,
      };
      if (geminiKey.trim()) {
        payload.gemini_api_key = geminiKey.trim();
      }
      const res = await saveRuntimeSettings(payload);
      onStatusUpdated(res.system_status);
      setMaskedKey(res.settings.masked_gemini_api_key || "");
      setGeminiKey("");
      setMessage("Tetapan berjaya disimpan ke pangkalan data dan diaktifkan serta-merta.");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal menyimpan tetapan.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-[#0f2744]" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Tetapan Enjin AI &amp; Privasi Tempatan PKD
              </h2>
              <p className="text-[11px] text-slate-500">
                Konfigurasi kunci API Gemini dan pelayan Ollama PC anda tanpa perlu menyunting fail .env.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="mt-4 space-y-3 text-xs">
          <div>
            <label className="font-bold text-slate-700">
              GEMINI_API_KEY {maskedKey ? `(Aktif: ${maskedKey})` : "(Belum ditetapkan)"}
            </label>
            <div className="relative mt-1">
              <input
                type={showKey ? "text" : "password"}
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder={
                  maskedKey
                    ? "Biarkan kosong untuk kekalkan kunci sedia ada, atau tampal kunci baharu..."
                    : "Masukkan kunci AIza... dari Google AI Studio"
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 pr-10 text-xs focus:border-blue-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-700"
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="font-bold text-slate-700">
              Google OAuth 2.0 Web Client ID (Google Sign-In Connector)
            </label>
            <input
              type="text"
              value={googleClientId}
              onChange={(e) => setGoogleClientId(e.target.value)}
              placeholder="Contoh: 1234567890-xxxx.apps.googleusercontent.com (Pilihan untuk tetingkap Google OAuth rasmi)"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-blue-500 focus:outline-none"
            />
            <p className="mt-0.5 text-[10px] text-slate-500">
              Wajib diisi daripada Google Cloud Console untuk mengaktifkan log masuk Google OAuth 2.0 sebenar (tiada akaun simulasi).
            </p>
          </div>

          <div>
            <label className="font-bold text-slate-700">Model Gemini Awan</label>
            <select
              value={geminiModel}
              onChange={(e) => setGeminiModel(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              <option value="gemini-2.5-flash">gemini-2.5-flash (Pantas &amp; Multimodal OCR)</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro (Penaakulan Undang-Undang Mendalam)</option>
              <option value="gemini-4-argon">gemini-4-argon (Interactions API)</option>
              <option value="gemini-4-hydrogen">gemini-4-hydrogen (Interactions API)</option>
            </select>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="font-bold text-slate-700">URL Pelayan Ollama (PC)</label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
              />
            </div>
            <div>
              <label className="font-bold text-slate-700">Model Ollama Tempatan</label>
              <input
                type="text"
                value={ollamaModel}
                onChange={(e) => setOllamaModel(e.target.value)}
                list="ollama-models-list"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
              />
              <datalist id="ollama-models-list">
                {(status?.ollama.available_models || []).map((m) => (
                  <option key={m} value={m} />
                ))}
                <option value="gemma3:12b" />
                <option value="qwen2.5:7b" />
              </datalist>
            </div>
          </div>

          {message && (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-emerald-800">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{message}</span>
            </div>
          )}
          {errorMsg && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-rose-800">
              {errorMsg}
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Tutup
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Simpan &amp; Uji Sambungan
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
