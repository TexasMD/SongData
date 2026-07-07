/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "primary": "#f95306",
        "background-light": "#f8f6f5",
        "background-dark": "#23150f",
        "console-primary": "#FF5000",
        "console-bg": "#09090A",
        "console-surface": "#141416",
        "console-surface-hover": "#1C1C1F",
        "console-text": "#EAEAEA",
        "console-muted": "#737378",
        "console-accent": "#00E5FF",
        "console-border": "#2A2A2E",
        "grid-border": "#3a2d27",
      },
      fontFamily: {
        "display": ["Space Grotesk", "sans-serif"],
        "mono": ["JetBrains Mono", "monospace"]
      },
      borderRadius: {"DEFAULT": "0px", "lg": "0px", "xl": "0px", "full": "0px"},
    },
  },
  plugins: [],
}
