"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { ErrorNote } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") {
        await api.post("/auth/register", { email, password, name: name || null, locale });
        router.push("/onboarding");
      } else {
        await api.post("/auth/login", { email, password });
        const next = params.get("next");
        router.push(next && next.startsWith("/") ? next : "/dashboard");
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <h1 className="mb-2 text-3xl">{mode === "login" ? t("auth.login.title") : t("auth.register.title")}</h1>
      {mode === "register" && (
        <div><Label htmlFor="name">{t("auth.name")}</Label><Input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></div>
      )}
      <div><Label htmlFor="email">{t("auth.email")}</Label>
        <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></div>
      <div><Label htmlFor="password" hint={mode === "register" ? t("auth.passwordHint") : undefined}>{t("auth.password")}</Label>
        <Input id="password" type="password" required minLength={mode === "register" ? 8 : 1} value={password}
          onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} /></div>
      <ErrorNote error={error} />
      <Button type="submit" size="lg" disabled={busy}>{mode === "login" ? t("auth.login") : t("auth.register")}</Button>
      <p className="text-sm text-muted">
        {mode === "login" ? t("auth.noAccount") : t("auth.haveAccount")}{" "}
        <Link className="font-medium text-ink underline underline-offset-2" href={mode === "login" ? "/register" : "/login"}>
          {mode === "login" ? t("auth.register") : t("auth.login")}
        </Link>
      </p>
    </form>
  );
}
