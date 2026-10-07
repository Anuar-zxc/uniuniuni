"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

// Minimal typing for Google Identity Services (https://developers.google.com/identity/gsi/web).
type CredentialResponse = { credential: string };
type GoogleId = {
  initialize: (cfg: { client_id: string; callback: (r: CredentialResponse) => void; ux_mode?: "popup"; use_fedcm_for_prompt?: boolean }) => void;
  renderButton: (el: HTMLElement, opts: Record<string, string | number>) => void;
};
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } };
  }
}

const SCRIPT_ID = "google-gsi";

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    const s = existing ?? document.createElement("script");
    s.addEventListener("load", () => resolve());
    s.addEventListener("error", () => reject(new Error("gsi")));
    if (!existing) {
      s.id = SCRIPT_ID;
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      document.head.appendChild(s);
    }
  });
}

/** Renders Google's own sign-in button; hidden entirely when Google sign-in isn't configured on the server. */
export function GoogleButton({ mode, onError }: { mode: "login" | "register"; onError: (e: unknown) => void }) {
  const { locale, t } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const ref = useRef<HTMLDivElement>(null);
  const [clientId, setClientId] = useState<string | null>(null);

  useEffect(() => {
    api.peek<{ google: boolean; google_client_id: string | null }>("/auth/providers")
      .then((p) => setClientId(p.google ? p.google_client_id : null))
      .catch(() => setClientId(null));
  }, []);

  useEffect(() => {
    if (!clientId || !ref.current) return;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !ref.current || !window.google) return;
        const gid = window.google.accounts.id;
        gid.initialize({
          client_id: clientId,
          ux_mode: "popup",
          callback: async ({ credential }) => {
            try {
              const r = await api.post<{ is_new: boolean }>("/auth/google", { id_token: credential, locale });
              const next = params.get("next");
              router.push(r.is_new ? "/onboarding" : next && next.startsWith("/") ? next : "/dashboard");
            } catch {
              onError(new Error(t("auth.googleError")));
            }
          },
        });
        ref.current.innerHTML = "";
        gid.renderButton(ref.current, {
          type: "standard",
          theme: document.documentElement.classList.contains("dark") ? "filled_black" : "outline",
          size: "large",
          shape: "rectangular",
          text: mode === "register" ? "signup_with" : "continue_with",
          logo_alignment: "center",
          width: Math.min(400, Math.max(240, ref.current.offsetWidth)),
          locale: locale === "kk" ? "kk" : locale,
        });
      })
      .catch(() => onError(new Error(t("auth.googleError"))));
    return () => {
      cancelled = true;
    };
  }, [clientId, locale, mode]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!clientId) return null;
  return (
    <div className="flex flex-col gap-5">
      <div ref={ref} className="flex min-h-[44px] w-full justify-center" />
      <div className="flex items-center gap-3 text-sm text-muted" aria-hidden>
        <span className="h-px flex-1 bg-line" />
        {t("auth.or")}
        <span className="h-px flex-1 bg-line" />
      </div>
    </div>
  );
}
