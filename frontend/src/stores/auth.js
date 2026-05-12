import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const checked = ref(false)
  const isAuthenticated = ref(false)

  async function checkAuth() {
    checked.value = true
    try {
      const res = await fetch('/api/sessions?limit=1&show_crons=false', {
        credentials: 'same-origin',
      })
      isAuthenticated.value = res.status !== 401
      return isAuthenticated.value
    } catch {
      isAuthenticated.value = false
      return false
    }
  }

  async function login(password) {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
    if (!res.ok) throw new Error('Invalid password')
    isAuthenticated.value = true
  }

  async function logout() {
    await fetch('/api/logout', { credentials: 'same-origin' })
    isAuthenticated.value = false
  }

  return { checked, isAuthenticated, checkAuth, login, logout }
})
