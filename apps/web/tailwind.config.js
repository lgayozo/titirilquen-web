/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        mode: {
          auto: "#FF8C00",
          bici: "#228B22",
          caminata: "#0000FF",
          metro: "#FF0000",
          teletrabajo: "#A9A9A9",
        },
        stratum: {
          alto: "#1f77b4",
          medio: "#ff7f0e",
          bajo: "#2ca02c",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
