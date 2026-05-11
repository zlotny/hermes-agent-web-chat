/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: '#161b22',
        border: '#30363d',
        muted: '#8b949e',
        accent: '#58a6ff',
      },
    },
  },
  plugins: [],
}
