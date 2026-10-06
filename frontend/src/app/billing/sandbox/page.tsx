"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorNote } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

function Sandbox() {
  const { t } = useI18n();
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<unknown>(null);
  const confirm = async () => {
    try {
      await api.post("/billing/sandbox/confirm", { external_id: params.get("session") });
      router.push("/billing/success");
    } catch (e) {
      setError(e);
    }
  };
  return (
    <main className="mx-auto max-w-md px-4 py-24">
      <h1>{t("price.sandbox.title")}</h1>
      <p className="mt-3 text-muted">{t("price.sandbox.lead")}</p>
      <div className="mt-6"><ErrorNote error={error} /></div>
      <Button size="lg" className="mt-4" onClick={confirm}>{t("price.sandbox.pay")}</Button>
    </main>
  );
}

export default function Page() {
  return <Suspense><Sandbox /></Suspense>;
}
