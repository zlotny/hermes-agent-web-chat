/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        border: 'rgb(var(--color-border) / <alpha-value>)',
        muted: 'rgb(var(--color-text-muted) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'app-bg': 'rgb(var(--color-app-bg) / <alpha-value>)',
        'hover-bg': 'rgb(var(--color-hover-bg) / <alpha-value>)',
        'code-bg': 'rgb(var(--color-code-bg) / <alpha-value>)',
        default: 'rgb(var(--color-default) / <alpha-value>)',
        panel: 'rgb(var(--color-panel) / <alpha-value>)',
      },
    },
  },
  plugins: [],
}
