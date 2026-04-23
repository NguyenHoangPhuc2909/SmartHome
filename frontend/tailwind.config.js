/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        mono: ["Space Mono", "monospace"],
        sans: ["DM Sans", "sans-serif"],
      },
      colors: {
        bg:      "#0d0f0f",
        surface: "#141718",
        accent:  "#b8f550",
      },
    },
  },
  plugins: [],
};