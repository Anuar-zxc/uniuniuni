"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMe } from "@/components/me-context";
import { Meter } from "@/components/readiness";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { Section } from "@/components/ui/panel";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { LOCALES, useI18n } from "@/lib/i18n";

export default function ProfilePage() {
  const { t, tx, setLocale } = useI18n();
  const { me, reload } = useMe();
  const [form, setForm] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!me) return;
    const p = me.profile;
    setForm({
      name: me.user.name ?? "", desired_role: p?.desired_role ?? "", level: p?.level ?? "middle", stack: (p?.stack ?? []).join(", "),
      target_company: p?.target_company ?? "", interview_date: p?.interview_date ?? "", language: p?.language ?? "ru", locale: me.user.locale,
    });
  }, [me]);

  if (!me) return <Loading />;
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => { setSaved(false); setForm({ ...form, [k]: e.target.value }); };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.patch("/profile", {
        ...form, stack: form.stack.split(",").map((s) => s.trim()).filter(Boolean),
        interview_date: form.interview_date || null, target_company: form.target_company || null,
      });
      setLocale(form.locale as "ru" | "en" | "kk");
      await reload();
      setSaved(true);
    } catch (err) {
      setError(err);
    }
  };

  const exportData = async () => {
    const data = await api.get<unknown>("/profile/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "offerready-data.json";
    a.click();
    URL.revokeObjectURL(url);
  };
  const deleteAccount = async () => {
    if (!window.confirm(t("prof.deleteConfirm"))) return;
    await api.del("/profile");
    window.location.href = "/";
  };

  return (
    <div className="max-w-3xl">
      <h1>{t("prof.title")}</h1>
      <p className="mt-1 text-muted">{me.user.email}</p>
      <form onSubmit={save} className="mt-8 grid gap-4 sm:grid-cols-2">
        <div><Label htmlFor="n">{t("auth.name")}</Label><Input id="n" value={form.name ?? ""} onChange={set("name")} /></div>
        <div><Label htmlFor="r">{t("prof.desiredRole")}</Label><Input id="r" value={form.desired_role ?? ""} onChange={set("desired_role")} /></div>
        <div><Label htmlFor="l">{t("prof.level")}</Label>
          <Select id="l" value={form.level ?? "middle"} onChange={set("level")}>
            <option value="junior">{t("common.junior")}</option><option value="middle">{t("common.middle")}</option><option value="senior">{t("common.senior")}</option>
          </Select></div>
        <div><Label htmlFor="c">{t("prof.company")}</Label><Input id="c" value={form.target_company ?? ""} onChange={set("target_company")} /></div>
        <div className="sm:col-span-2"><Label htmlFor="s" hint={t("prof.stackHint")}>{t("prof.stack")}</Label><Input id="s" value={form.stack ?? ""} onChange={set("stack")} /></div>
        <div><Label htmlFor="d">{t("prof.date")}</Label><Input id="d" type="date" value={form.interview_date ?? ""} onChange={set("interview_date")} /></div>
        <div><Label htmlFor="lang">{t("prof.language")}</Label>
          <Select id="lang" value={form.language ?? "ru"} onChange={set("language")}>{LOCALES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</Select></div>
        <div><Label htmlFor="ui">{t("prof.uiLanguage")}</Label>
          <Select id="ui" value={form.locale ?? "ru"} onChange={set("locale")}>{LOCALES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</Select></div>
        <div className="flex items-center gap-4 sm:col-span-2">
          <Button type="submit">{t("prof.save")}</Button>
          {saved && <span className="text-sm text-muted" role="status">{t("prof.saved")}</span>}
        </div>
        <div className="sm:col-span-2"><ErrorNote error={error} /></div>
      </form>

      <Section title={t("prof.plan")} className="mt-8 border-t border-line" aside={<Link href="/pricing" className="text-sm underline underline-offset-2">{t("price.upgrade")}</Link>}>
        <p className="font-display text-xl">{me.plan.name}</p>
        <p className="mb-4 mt-4 text-sm text-muted">{t("prof.usage")}</p>
        <div className="grid gap-4 sm:grid-cols-2">
          {Object.entries(me.usage).map(([k, u]) => (
            <Meter key={k} label={`${tx(`price.limits.${k}`, k)}: ${u.used} / ${u.limit === -1 ? "∞" : u.limit}`} value={u.limit === -1 ? 0 : (u.used / Math.max(1, u.limit)) * 100} />
          ))}
        </div>
        {me.plan.code !== "free" && <Button variant="ghost" size="sm" className="mt-4" onClick={async () => { await api.post("/billing/cancel"); await reload(); }}>{t("prof.cancelPlan")}</Button>}
      </Section>

      <Section title={t("prof.privacy")} className="border-t border-line">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={exportData}>{t("prof.export")}</Button>
          <Button variant="danger" onClick={deleteAccount}>{t("prof.delete")}</Button>
        </div>
      </Section>
    </div>
  );
}
