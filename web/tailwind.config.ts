import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)",
        surface: "var(--surface)",
        sunken: "var(--sunken)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        line: "var(--line)",
        // acentos por secao: Math e frio, R&W e quente
        math: "var(--math)",
        "math-soft": "var(--math-soft)",
        rw: "var(--rw)",
        "rw-soft": "var(--rw-soft)",
        right: "var(--right)",
        "right-soft": "var(--right-soft)",
        wrong: "var(--wrong)",
        "wrong-soft": "var(--wrong-soft)",
        accent: "var(--accent)",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      boxShadow: {
        // sombra solida deslocada: da o aspecto 2D recortado
        flat: "4px 4px 0 0 var(--ink)",
        "flat-sm": "2px 2px 0 0 var(--ink)",
        "flat-lg": "6px 6px 0 0 var(--ink)",
        "flat-color": "4px 4px 0 0 var(--shadow-color)",
      },
      borderRadius: {
        blob: "42% 58% 55% 45% / 48% 42% 58% 52%",
      },
      keyframes: {
        pop: {
          "0%": { transform: "scale(0.96)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        nudge: {
          "0%,100%": { transform: "translateX(0)" },
          "25%": { transform: "translateX(-4px)" },
          "75%": { transform: "translateX(4px)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0) rotate(0deg)" },
          "50%": { transform: "translateY(-10px) rotate(3deg)" },
        },
      },
      animation: {
        pop: "pop .18s ease-out",
        nudge: "nudge .3s ease-in-out",
        float: "float 9s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
