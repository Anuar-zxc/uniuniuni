import type { Metadata } from "next";
import { Golos_Text, Unbounded } from "next/font/google";
import { I18nProvider } from "@/lib/i18n";
import { THEME_SCRIPT } from "@/lib/theme";
import "./globals.css";

const display = Unbounded({ subsets: ["latin", "cyrillic", "cyrillic-ext"], weight: ["500", "600"], variable: "--font-display", display: "swap" });
const body = Golos_Text({ subsets: ["latin", "cyrillic", "cyrillic-ext"], weight: ["400", "500", "600"], variable: "--font-body", display: "swap" });

export const metadata: Metadata = {
  title: { default: "OfferReady — AI interview coach", template: "%s · OfferReady" },
  description: "Practice for the interview you actually want: resume analysis, vacancy matching, realistic AI interviews, error memory and a readiness score.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning className={`${display.variable} ${body.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
