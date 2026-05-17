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

  // Per-session message cache: survives navigation away and back while
  // the stream is still running (API hasn't persisted full messages yet).
  const messageCache = ref({})

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

  const loadingMessageId = ref(null)

  async function loadSession(id) {
    currentSessionId.value = id
    loadingMessageId.value = id
    sidebarError.value = ''

    // Don't clear messages immediately — prevents EmptyState flash.
    // If we have cached messages (from a stream in progress), restore them.
    const chatStore = useChatStore()
    if (id && messageCache.value[id]) {
      allMessages.value = [...messageCache.value[id]]
      loadingMessageId.value = null
      return
    }

    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
        credentials: 'same-origin',
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      allMessages.value = data.messages || []

      // Merge in cached messages if the session has extra messages
      // from a stream that hasn't fully persisted yet
      if (messageCache.value[id]) {
        const cached = messageCache.value[id]
        for (const cm of cached) {
          if (cm.role === 'assistant' && cm.content) {
            const exists = allMessages.value.some(m => m.content === cm.content)
            if (!exists) allMessages.value.push(cm)
          }
        }
      }

      if (data.model) {
        chatStore.setCurrentModel(data.model)
      }
    } catch (e) {
      sidebarError.value = 'Error: ' + e.message
      allMessages.value = []
    } finally {
      loadingMessageId.value = null
    }
  }

  function saveMessageCache(sessionId) {
    if (sessionId && allMessages.value.length) {
      messageCache.value = { ...messageCache.value, [sessionId]: [...allMessages.value] }
    }
  }

  function clearMessageCache(sessionId) {
    if (sessionId) {
      const next = { ...messageCache.value }
      delete next[sessionId]
      messageCache.value = next
    }
  }

  function addPlaceholderSession(tempId) {
    // Inject a fake session into the sidebar immediately so "New session…"
    // appears before the backend round-trip.
    const exists = allSessions.value.some(s => s.id === tempId)
    if (exists) return
    allSessions.value = [
      {
        id: tempId,
        title: '',
        model: '',
        message_count: 0,
        last_updated: '',
        started_at: '',
        is_cron: false,
      },
      ...allSessions.value,
    ]
  }

  function replaceSessionId(oldId, newId) {
    // Swap a temp placeholder ID for the real Hermes session ID in-place,
    // preserving array identity so Vue doesn't re-render all SessionItems.
    const idx = allSessions.value.findIndex(s => s.id === oldId)
    if (idx !== -1) {
      allSessions.value.splice(idx, 1, { ...allSessions.value[idx], id: newId })
    }
  }

  async function updateSessionInPlace(sessionId) {
    // Targeted refresh of a single session in the sidebar list
    // without reloading all sessions — avoids flicker from full re-render.
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
        credentials: 'same-origin',
      })
      if (!res.ok) return
      const data = await res.json()
      const idx = allSessions.value.findIndex(s => s.id === sessionId)
      if (idx !== -1) {
        allSessions.value.splice(idx, 1, {
          ...allSessions.value[idx],
          id: data.id || sessionId,
          title: data.title || allSessions.value[idx].title,
          model: data.model || allSessions.value[idx].model,
          message_count: data.message_count ?? allSessions.value[idx].message_count,
          last_updated: data.last_updated || new Date().toISOString(),
        })
      }
    } catch {
      // Silently fail — next full loadSessions() will fix it
    }
  }

  function newChat() {
    currentSessionId.value = null
    allMessages.value = []
  }

  async function deleteSession(sessionId) {
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
        credentials: 'same-origin',
      })
      if (!res.ok) throw new Error(await res.text())
      // Remove from sidebar
      const idx = allSessions.value.findIndex(s => s.id === sessionId)
      if (idx !== -1) {
        allSessions.value.splice(idx, 1)
      }
      // Clear message cache
      clearMessageCache(sessionId)
      totalSessions.value = Math.max(0, totalSessions.value - 1)
      loadedCount.value = Math.max(0, loadedCount.value - 1)
      // If the deleted session was the active one, redirect to new chat
      if (currentSessionId.value === sessionId) {
        newChat()
      }
      return true
    } catch (e) {
      sidebarError.value = 'Failed to delete: ' + e.message
      return false
    }
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
    messageCache,
    loadingMessageId,
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
    saveMessageCache,
    clearMessageCache,
    addPlaceholderSession,
    replaceSessionId,
    updateSessionInPlace,
    deleteSession,
    newChat,
  }
})
