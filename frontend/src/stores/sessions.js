import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSessionsStore = defineStore('sessions', () => {
  // --- State ---
  const allSessions = ref([])
  const totalSessions = ref(0)
  const loadingSessions = ref(false)
  const sidebarError = ref('')

  const currentSessionId = ref(null)
  const allMessages = ref([])

  const showAll = ref(false)
  const showCrons = ref(false)
  const showSystemMessages = ref(false)
  const searchQuery = ref('')

  // --- Getters ---
  const filteredSessions = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    if (!q) return allSessions.value
    return allSessions.value.filter((s) =>
      s.title.toLowerCase().includes(q)
    )
  })

  const visibleSessions = computed(() => {
    const base = filteredSessions.value
    return showAll.value ? base : base.slice(0, 20)
  })

  // --- Actions ---
  async function loadSessions() {
    sidebarError.value = ''
    loadingSessions.value = true
    try {
      const url = `/api/sessions?limit=20&show_crons=${showCrons.value}`
      const res = await fetch(url, { credentials: 'same-origin' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      allSessions.value = data.sessions || []
      totalSessions.value = data.total || 0
    } catch (e) {
      sidebarError.value = 'Failed: ' + e.message
    } finally {
      loadingSessions.value = false
    }
  }

  async function showAllSessions() {
    showAll.value = true
    if (allSessions.value.length >= totalSessions.value) return
    try {
      const url = `/api/sessions?show_crons=${showCrons.value}`
      const res = await fetch(url, { credentials: 'same-origin' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      allSessions.value = data.sessions || []
    } catch (e) {
      sidebarError.value = 'Failed: ' + e.message
    }
  }

  async function loadSession(id) {
    currentSessionId.value = id
    allMessages.value = []
    sidebarError.value = ''
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
        credentials: 'same-origin',
      })
      if (!res.ok) throw new Error(await res.text())
      allMessages.value = (await res.json()).messages || []
    } catch (e) {
      sidebarError.value = 'Error: ' + e.message
      allMessages.value = []
    }
  }

  function newChat() {
    currentSessionId.value = null
    allMessages.value = []
    showAll.value = false
  }

  return {
    // state
    allSessions,
    totalSessions,
    loadingSessions,
    sidebarError,
    currentSessionId,
    allMessages,
    showAll,
    showCrons,
    showSystemMessages,
    searchQuery,
    filteredSessions,
    // getters
    visibleSessions,
    // actions
    loadSessions,
    showAllSessions,
    loadSession,
    newChat,
  }
})
