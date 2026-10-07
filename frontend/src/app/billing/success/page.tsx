"use client";

import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";

export default function Success() {
  const { t } = useI18n();
  return (
    <main className="mx-auto max-w-md px-4 py-24">
      <h1>{t("price.success")}</h1>
      <Link href="/dashboard" className={buttonVariants({ className: "mt-6" })}>{t("nav.dashboard")}</Link>
    </main>
  );
}
