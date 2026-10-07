"use client";

import { AppShell } from "@/components/app-shell";
import { MeProvider } from "@/components/me-context";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <MeProvider>
      <AppShell>{children}</AppShell>
    </MeProvider>
  );
}
