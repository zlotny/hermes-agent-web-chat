import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
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
  let _searchDebounce = null
  const _rawSearch = ref('')

  // Pending response tracking: set when transient in-flight state exists.
  // Stores the FULL streaming data so the UI can reconstruct the chat view
  // after a page reload as if the agent was never interrupted.
  const pendingResponse = ref(false)
  const pendingStreamingMsg = ref('')
  const pendingToolCalls = ref([])
  const pendingCurrentToolName = ref('')
  const pendingCurrentToolPreview = ref('')
  const pendingStatusDetail = ref('')
  let _pendingTransientTimer = null
  let _pendingSessionTimer = null

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

  // Debounced search — only recompute filteredSessions after 150ms idle
  watch(_rawSearch, (val) => {
    if (_searchDebounce) clearTimeout(_searchDebounce)
    _searchDebounce = setTimeout(() => {
      searchQuery.value = val
    }, 150)
  })

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

      // Auto-detect: if the last message in the DB is from user, the agent
      // was mid-response when we reloaded. Show thinking indicator and poll.
      // Also check for transient state (in-flight message not yet in DB).
      // After loading DB messages, check for transient in-flight state
      _checkTransientState(id)
      chatStore.checkPendingClarify(id)

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

  /** Check for transient in-flight state and start polling. */
  async function _checkTransientState(sessionId) {
    try {
      const res = await fetch(`/api/chat/transient/${encodeURIComponent(sessionId)}`, {
        credentials: 'same-origin',
      })
      if (!res.ok) return
      const data = await res.json()
      if (!data || !data.session_id) return

      // Inject user message from transient. Skip only if the last DB
      // message is already the same user message (no duplication).
      if (data.user_message) {
        const last = allMessages.value[allMessages.value.length - 1]
        const alreadyPresent = last && last.role === 'user' && last.content === data.user_message
        if (!alreadyPresent) {
          allMessages.value.push({ role: 'user', content: data.user_message, source: 'user' })
        }
      }

      // Populate pending state with FULL transient data
      pendingResponse.value = true
      pendingStreamingMsg.value = data.streaming_msg || ''
      pendingCurrentToolName.value = data.current_tool_name || ''
      pendingCurrentToolPreview.value = data.current_tool_preview || ''
      pendingStatusDetail.value = data.status_detail || ''
      // Map tool_calls to the format ToolChain expects
      pendingToolCalls.value = (data.tool_calls || []).filter(tc => tc.status === 'running').map(tc => ({
        id: 'rtc_' + tc.name,
        function: { name: tc.name, arguments: tc.preview || '' },
      }))

      // Poll for updates (transient changes) and completion (transient disappears)
      _pendingTransientTimer = setInterval(async () => {
        try {
          const r2 = await fetch(`/api/chat/transient/${encodeURIComponent(sessionId)}`, {
            credentials: 'same-origin',
          })
          if (r2.status === 404) {
            // Agent finished — reload from DB
            clearInterval(_pendingTransientTimer)
            _pendingTransientTimer = null
            _reloadFromDb(sessionId)
            return
          }
          if (!r2.ok) return
          const d = await r2.json()
          if (!d || !d.session_id) return
          pendingStreamingMsg.value = d.streaming_msg || ''
          pendingCurrentToolName.value = d.current_tool_name || ''
          pendingCurrentToolPreview.value = d.current_tool_preview || ''
          pendingStatusDetail.value = d.status_detail || ''
          pendingToolCalls.value = (d.tool_calls || []).filter(tc => tc.status === 'running').map(tc => ({
            id: 'rtc_' + tc.name,
            function: { name: tc.name, arguments: tc.preview || '' },
          }))
        } catch {
          // retry
        }
      }, 1000)
    } catch {
      // No transient state — nothing to do
    }
  }

  async function _reloadFromDb(sessionId) {
    _clearPendingState()
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
        credentials: 'same-origin',
      })
      if (!res.ok) return
      const data = await res.json()
      allMessages.value = data.messages || []
    } catch {
      // ignore
    }
  }

  function newChat() {
    _clearPendingState()
    currentSessionId.value = null
    allMessages.value = []
  }

  function _clearPendingState() {
    if (_pendingTransientTimer) {
      clearInterval(_pendingTransientTimer)
      _pendingTransientTimer = null
    }
    if (_pendingSessionTimer) {
      clearInterval(_pendingSessionTimer)
      _pendingSessionTimer = null
    }
    pendingResponse.value = false
    pendingStreamingMsg.value = ''
    pendingToolCalls.value = []
    pendingCurrentToolName.value = ''
    pendingCurrentToolPreview.value = ''
    pendingStatusDetail.value = ''
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
    _clearPendingState()
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
    _rawSearch,
    searchQuery,
    pendingResponse,
    pendingStreamingMsg,
    pendingToolCalls,
    pendingCurrentToolName,
    pendingCurrentToolPreview,
    pendingStatusDetail,
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
