/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx,mdx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      // Paleta editorial: todos los colores referencian CSS variables para
      // respetar los 3 temas (paper / dark / journal).
      colors: {
        paper: {
          DEFAULT: "var(--paper)",
          2: "var(--paper-2)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          2: "var(--ink-2)",
        },
        muted: "var(--muted)",
        rule: "var(--rule)",
        accent: "var(--accent)",
        mode: {
          auto: "var(--auto)",
          metro: "var(--metro)",
          bici: "var(--bici)",
          walk: "var(--walk)",
          tele: "var(--tele)",
        },
        stratum: {
          1: "var(--s1)",
          2: "var(--s2)",
          3: "var(--s3)",
          alto: "var(--s1)",
          medio: "var(--s2)",
          bajo: "var(--s3)",
        },
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        fig: ["var(--font-fig)"],
        serif: ["var(--font-serif)"],
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      borderRadius: {
        none: "0",
        DEFAULT: "0",
      },
      keyframes: {
        "skeleton-pulse": {
          "0%, 100%": { opacity: "0.3", transform: "scaleY(0.6)" },
          "50%": { opacity: "0.9", transform: "scaleY(1)" },
        },
        "iteration-flash": {
          "0%": { boxShadow: "0 0 0 0 color-mix(in srgb, var(--accent) 60%, transparent)" },
          "100%": { boxShadow: "0 0 0 12px transparent" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
      },
      animation: {
        "skeleton-pulse": "skeleton-pulse 1.8s ease-in-out infinite",
        "iteration-flash": "iteration-flash 500ms ease-out",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
