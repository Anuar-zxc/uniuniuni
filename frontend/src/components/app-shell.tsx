"use client";

import { BarChart3, Briefcase, Dumbbell, FileText, LayoutGrid, LogOut, Menu, MessagesSquare, Shield, Target, User, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { ThemeToggle } from "@/lib/theme";
import type { DictKey } from "@/lib/dict";
import { cn } from "@/lib/utils";
import { LangSwitch } from "./lang-switch";
import { useMe } from "./me-context";

const NAV: { href: string; key: DictKey; icon: typeof LayoutGrid }[] = [
  { href: "/dashboard", key: "nav.dashboard", icon: LayoutGrid },
  { href: "/resume", key: "nav.resume", icon: FileText },
  { href: "/jobs", key: "nav.jobs", icon: Briefcase },
  { href: "/interviews", key: "nav.interviews", icon: MessagesSquare },
  { href: "/weaknesses", key: "nav.weaknesses", icon: Target },
  { href: "/training", key: "nav.training", icon: Dumbbell },
  { href: "/profile", key: "nav.profile", icon: User },
];

export function Logo() {
  return (
    <Link href="/" className="font-display text-lg font-semibold tracking-tight text-ink">
      Offer<span className="text-muted">Ready</span>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useI18n();
  const { me } = useMe();
  const [open, setOpen] = useState(false);
  const items = me?.user.role === "admin" ? [...NAV, { href: "/admin", key: "nav.admin" as DictKey, icon: Shield }] : NAV;

  const logout = async () => {
    await api.post("/auth/logout").catch(() => {});
    router.push("/login");
  };

  const nav = (
    <nav className="flex flex-col gap-0.5" aria-label="Main">
      {items.map(({ href, key, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link key={href} href={href} onClick={() => setOpen(false)} aria-current={active ? "page" : undefined}
            className={cn("flex items-center gap-3 rounded-lg px-3 py-2 text-[15px]", active ? "bg-ink text-paper" : "text-muted hover:bg-line/50 hover:text-ink")}>
            <Icon size={18} aria-hidden /> {t(key)}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="hidden border-r border-line lg:flex lg:flex-col lg:gap-8 lg:px-4 lg:py-6">
        <div className="px-3"><Logo /></div>
        {nav}
        <div className="mt-auto flex flex-col gap-3 px-3">
          {me && (
            <Link href="/pricing" className="text-sm text-muted hover:text-ink">
              <BarChart3 size={14} className="mr-1 inline" aria-hidden />{me.plan.name}
            </Link>
          )}
          <div className="flex items-center gap-2"><LangSwitch persist /><ThemeToggle /></div>
          <button onClick={logout} className="flex items-center gap-2 text-sm text-muted hover:text-ink"><LogOut size={14} />{t("nav.logout")}</button>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-paper/95 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Menu" className="rounded-lg p-2 text-ink hover:bg-line/50">
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>
      {open && (
        <div className="fixed inset-x-0 top-[57px] z-20 border-b border-line bg-paper px-4 pb-5 pt-3 lg:hidden">
          {nav}
          <div className="mt-4 flex items-center gap-3"><LangSwitch persist /><ThemeToggle />
            <button onClick={logout} className="ml-auto text-sm text-muted">{t("nav.logout")}</button>
          </div>
        </div>
      )}

      <main className="mx-auto w-full max-w-[1100px] px-4 py-6 sm:px-8 lg:py-10">{children}</main>
    </div>
  );
}
