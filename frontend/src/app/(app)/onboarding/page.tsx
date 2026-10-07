"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { JobForm } from "@/components/job-views";
import { useMe } from "@/components/me-context";
import { ResumeUploader } from "@/components/resume-views";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { ErrorNote } from "@/components/ui/states";
import { api } from "@/lib/api";
import { LOCALES, useI18n } from "@/lib/i18n";
import type { Me } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function Onboarding() {
  const { t } = useI18n();
  const router = useRouter();
  const { me, reload } = useMe();
  const [step, setStep] = useState(0);
  const steps = [t("onb.step.resume"), t("onb.step.job"), t("onb.step.check")];

  return (
    <div className="max-w-3xl">
      <h1>{t("onb.title")}</h1>
      <p className="mt-3 max-w-prose text-muted">{t("onb.lead")}</p>
      <ol className="mt-8 flex gap-6 border-b border-line text-sm">
        {steps.map((s, i) => (
          <li key={s} className={cn("-mb-px border-b-2 pb-3", i === step ? "border-ink font-medium text-ink" : "border-transparent text-muted")}>
            {i + 1}. {s}
          </li>
        ))}
      </ol>
      <div className="pt-8">
        {step === 0 && <ResumeUploader onDone={async () => { await reload(); setStep(1); }} />}
        {step === 1 && (
          <div className="flex flex-col gap-4">
            <JobForm onDone={async () => { await reload(); setStep(2); }} />
            <button className="self-start text-sm text-muted underline underline-offset-2" onClick={() => setStep(2)}>{t("onb.skipJob")}</button>
          </div>
        )}
        {step === 2 && me && <CheckDetails me={me} onSaved={() => router.push("/dashboard")} />}
      </div>
      {step === 0 && <Link href="/dashboard" className="mt-8 inline-block text-sm text-muted underline underline-offset-2">{t("common.next")}</Link>}
    </div>
  );
}

function CheckDetails({ me, onSaved }: { me: Me; onSaved: () => void }) {
  const { t } = useI18n();
  const p = me.profile;
  const [form, setForm] = useState({
    desired_role: p?.desired_role ?? "", level: p?.level ?? "middle", stack: (p?.stack ?? []).join(", "),
    target_company: p?.target_company ?? "", interview_date: p?.interview_date ?? "", language: p?.language ?? "ru",
  });
  const [error, setError] = useState<unknown>(null);
  const save = async () => {
    try {
      await api.patch("/profile", {
        ...form, stack: form.stack.split(",").map((s) => s.trim()).filter(Boolean),
        interview_date: form.interview_date || null, target_company: form.target_company || null, onboarding_completed: true,
      });
      onSaved();
    } catch (e) {
      setError(e);
    }
  };
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div><Label htmlFor="r">{t("prof.desiredRole")}</Label><Input id="r" value={form.desired_role} onChange={set("desired_role")} /></div>
      <div><Label htmlFor="l">{t("prof.level")}</Label>
        <Select id="l" value={form.level} onChange={set("level")}>
          <option value="junior">{t("common.junior")}</option><option value="middle">{t("common.middle")}</option><option value="senior">{t("common.senior")}</option>
        </Select></div>
      <div className="sm:col-span-2"><Label htmlFor="s" hint={t("prof.stackHint")}>{t("prof.stack")}</Label><Input id="s" value={form.stack} onChange={set("stack")} /></div>
      <div><Label htmlFor="c">{t("prof.company")}</Label><Input id="c" value={form.target_company} onChange={set("target_company")} /></div>
      <div><Label htmlFor="d">{t("prof.date")}</Label><Input id="d" type="date" value={form.interview_date} onChange={set("interview_date")} /></div>
      <div><Label htmlFor="lang">{t("prof.language")}</Label>
        <Select id="lang" value={form.language} onChange={set("language")}>{LOCALES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</Select></div>
      <div className="sm:col-span-2"><ErrorNote error={error} /><Button className="mt-2" onClick={save}>{t("onb.done")}</Button></div>
    </div>
  );
}
