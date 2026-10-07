import type { Config } from "tailwindcss";

const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: v("paper"),
        raised: v("raised"),
        ink: v("ink"),
        muted: v("muted"),
        line: v("line"),
        primary: { DEFAULT: v("primary"), fg: v("primary-fg") },
        status: {
          notready: v("st-notready"),
          needswork: v("st-needswork"),
          almost: v("st-almost"),
          ready: v("st-ready"),
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      borderRadius: { panel: "14px" },
      maxWidth: { prose: "68ch" },
    },
  },
  plugins: [],
} satisfies Config;
