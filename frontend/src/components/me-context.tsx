"use client";

import { createContext, useContext, useEffect } from "react";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { Me } from "@/lib/types";

type Ctx = { me: Me | null; reload: () => Promise<void> };
const MeContext = createContext<Ctx>({ me: null, reload: async () => {} });

export function MeProvider({ children }: { children: React.ReactNode }) {
  const { data, reload } = useApi<Me>("/profile");
  const { setLocale } = useI18n();
  useEffect(() => {
    if (data?.user.locale) setLocale(data.user.locale);
  }, [data?.user.locale, setLocale]);
  return <MeContext.Provider value={{ me: data, reload }}>{children}</MeContext.Provider>;
}

export const useMe = () => useContext(MeContext);
