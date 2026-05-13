import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useChatStore } from './chat'

const PAGE_SIZE = 20

export const useSessionsStore = defineStore('sessions', () => {
  // --- State ---
  const allSessions = ref([])
  const totalSessions = ref(0)
  const loadedCount = ref(0)
  const loadingSessions = ref(false)
  const loadingMore = ref(false)
  const sidebarError = ref('')

  const currentSessionId = ref(null)
  const allMessages = ref([])

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

  const hasMore = computed(() => loadedCount.value < totalSessions.value)

  // --- Actions ---
  async function loadSessions() {
    sidebarError.value = ''
    loadingSessions.value = true
    loadedCount.value = 0
    allSessions.value = []
    try {
      const url = `/api/sessions?limit=${PAGE_SIZE}&offset=0&show_crons=${showCrons.value}`
      const res = await fetch(url, { credentials: 'same-origin' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      allSessions.value = data.sessions || []
      totalSessions.value = data.total || 0
      loadedCount.value = allSessions.value.length
    } catch (e) {
      sidebarError.value = 'Failed: ' + e.message
    } finally {
      loadingSessions.value = false
    }
  }

  async function loadMoreSessions() {
    if (loadingMore.value || !hasMore.value || searchQuery.value.trim()) return
    loadingMore.value = true
    try {
      const url = `/api/sessions?limit=${PAGE_SIZE}&offset=${loadedCount.value}&show_crons=${showCrons.value}`
      const res = await fetch(url, { credentials: 'same-origin' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      if (data.sessions) {
        allSessions.value = [...allSessions.value, ...data.sessions]
        loadedCount.value = allSessions.value.length
        totalSessions.value = data.total || totalSessions.value
      }
    } catch (e) {
      sidebarError.value = 'Error loading more: ' + e.message
    } finally {
      loadingMore.value = false
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
      const data = await res.json()
      allMessages.value = data.messages || []
      // Update the chat store's current model from the session
      const chatStore = useChatStore()
      if (data.model) {
        chatStore.setCurrentModel(data.model)
      }
    } catch (e) {
      sidebarError.value = 'Error: ' + e.message
      allMessages.value = []
    }
  }

  function newChat() {
    currentSessionId.value = null
    allMessages.value = []
  }

  return {
    // state
    allSessions,
    totalSessions,
    loadedCount,
    loadingSessions,
    loadingMore,
    sidebarError,
    currentSessionId,
    allMessages,
    showCrons,
    showSystemMessages,
    searchQuery,
    filteredSessions,
    // getters
    hasMore,
    // actions
    loadSessions,
    loadMoreSessions,
    loadSession,
    newChat,
  }
})
