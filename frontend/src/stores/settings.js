import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'hermes-theme'

export const useSettingsStore = defineStore('settings', () => {
  // ── State ──
  const theme = ref('system') // 'system' | 'light' | 'dark'

  // ── Init ──
  function init() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && ['system', 'light', 'dark'].includes(saved)) {
      theme.value = saved
    }
    applyTheme()
    listenSystem()
    // Persist to localStorage on change
    watch(theme, (val) => {
      localStorage.setItem(STORAGE_KEY, val)
      applyTheme()
    })
  }

  // ── Apply theme class on <html> ──
  function applyTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const isDark =
      theme.value === 'dark' || (theme.value === 'system' && prefersDark)
    document.documentElement.classList.toggle('dark', isDark)
  }

  // ── Listen for OS-level system preference changes ──
  function listenSystem() {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', () => {
      if (theme.value === 'system') applyTheme()
    })
  }

  // ── Set theme ──
  function setTheme(val) {
    if (['system', 'light', 'dark'].includes(val)) {
      theme.value = val
    }
  }

  return { theme, init, applyTheme, setTheme }
})
