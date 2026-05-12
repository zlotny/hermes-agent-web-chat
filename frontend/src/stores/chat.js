import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  // --- Model selector state (global, not per-session) ---
  const inputText = ref('')
  const currentModel = ref('')
  const defaultModel = ref('')
  const availableProviders = ref([])
  const selectedProvider = ref('')
  const providersLoading = ref(false)
  const modelSelectorOpen = ref(false)

  // --- Active sessions (reload resilience) ---
  const activeSessions = ref(new Set())

  /** Sessions whose stream finished locally — suppress reconnecting banner
   *  until the backend's active-session timeout catches up (~300s).
   *  Cleared 5 seconds after the stream completes. */
  const locallyCompletedSessions = ref(new Set())

  // ---------------------------------------------------------------------------
  // Per-session streaming state
  // ---------------------------------------------------------------------------
  // Each active stream gets its own reactive state object in this map.
  // This lets the user switch between sessions and see each one's
  // independent streaming progress. SSE readers persist even when the
  // user navigates away — the backend keeps running.
  // ---------------------------------------------------------------------------

  function _createStreamState() {
    return reactive({
      streamingMsg: '',
      streamingTool: '',
      status: '',       // 'sending' | 'thinking' | ''
      statusDetail: '',
      loadError: '',
      sending: false,
      _abortController: null,
    })
  }

  const streams = reactive(new Map())

  const _emptyStreamState = Object.freeze({
    streamingMsg: '',
    streamingTool: '',
    status: '',
    statusDetail: '',
    loadError: '',
    sending: false,
  })

  /**
   * When the sessions store doesn't yet have a currentSessionId (new chat),
   * this ref holds the temp key so getStreamState can find the right stream.
   */
  const currentStreamingId = ref('')

  /** Get the reactive streaming state for a session. */
  function getStreamState(sessionId) {
    // Fallback: if the caller has no sessionId but we're mid-stream, use the
    // streaming ID (which is set to the temp key for new chats, then updated
    // to the real Hermes ID when the stream completes).
    const key = sessionId || currentStreamingId.value
    if (!key) return _emptyStreamState
    return streams.get(key) || _emptyStreamState
  }

  function clearCurrentStreamingId() {
    currentStreamingId.value = ''
  }

  /**
   * When the backend finishes a new chat, it returns the real Hermes session ID.
   * Migrate the stream state from the temp key to the real ID so that
   * getStreamState(realId) still finds it.
   */
  function migrateStream(tempKey, realKey) {
    if (!tempKey || !realKey || tempKey === realKey) return
    const state = streams.get(tempKey)
    if (!state) return
    streams.set(realKey, state)
    streams.delete(tempKey)
  }

  function _ensureStream(sessionId) {
    if (!streams.has(sessionId)) {
      streams.set(sessionId, _createStreamState())
    }
    return streams.get(sessionId)
  }

  function _removeStream(sessionId) {
    const st = streams.get(sessionId)
    if (st) {
      if (st._abortController) {
        try { st._abortController.abort() } catch {}
      }
      streams.delete(sessionId)
    }
  }

  /** IDs of all sessions that currently have an active stream. */
  const activeStreamIds = computed(() => {
    const ids = []
    for (const [sid, st] of streams) {
      if (st.sending) ids.push(sid)
    }
    return ids
  })

  // ---------------------------------------------------------------------------
  // Pure helpers
  // ---------------------------------------------------------------------------

  function isSystemMsg(m) {
    if (!m || !m.content) return false
    if (m.source === 'system') return true
    if (m.source === 'user') return false
    const c = m.content.trim()
    return (
      c.startsWith('[IMPORTANT:') ||
      c.startsWith('Review the conversation above') ||
      c.startsWith('Review the conversation above and consider') ||
      c.startsWith('System:') ||
      c === '[SILENT]'
    )
  }

  function toolArgPreview(tc) {
    try {
      const args = JSON.parse(tc.function?.arguments || '{}')
      const val = Object.values(args).find(
        (v) => typeof v === 'string' && v.length < 40
      )
      return val || ''
    } catch {
      return ''
    }
  }

  function prettyJson(str) {
    try {
      return JSON.stringify(JSON.parse(str), null, 2)
    } catch {
      return str || ''
    }
  }

  function renderContent(t) {
    if (!t) return ''
    let h = t.replace(
      /```(\w*)\n([\s\S]*?)```/g,
      '<pre><code>$2</code></pre>'
    )
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    h = h.replace(/\n\n/g, '</p><p>')
    h = h.replace(/\n/g, '<br>')
    return '<p>' + h + '</p>'
  }

  function shortModel(m) {
    return m ? m.split('/').pop() || m : ''
  }
  function shortModelName(m) {
    return m ? m.split('/').pop() || m : ''
  }

  function providerName(slug) {
    const p = availableProviders.value.find(
      (pr) => pr.slug === slug || pr.slug.toLowerCase() === slug.toLowerCase()
    )
    return p?.name || slug
  }

  // ---------------------------------------------------------------------------
  // Model actions
  // ---------------------------------------------------------------------------

  async function fetchProviders() {
    providersLoading.value = true
    try {
      const res = await fetch('/api/providers', { credentials: 'same-origin' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      availableProviders.value = data.providers || []
    } catch (e) {
      console.warn('Failed to fetch providers:', e)
      availableProviders.value = []
    } finally {
      providersLoading.value = false
    }
  }

  function setCurrentModel(model) {
    currentModel.value = model || ''
    if (model && model.includes('/')) {
      selectedProvider.value = model.split('/')[0]
    }
  }

  async function updateSessionModel(sessionId, model) {
    if (!sessionId || !model) return false
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ model }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      if (data.model) setCurrentModel(data.model)
      return true
    } catch (e) {
      console.warn('Failed to update session model:', e)
      return false
    }
  }

  async function fetchDefaultModel() {
    try {
      const res = await fetch('/api/config/model-default', { credentials: 'same-origin' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      if (data.model) defaultModel.value = data.model
    } catch (e) {
      console.warn('Failed to fetch default model:', e)
    }
  }

  async function abortStream(sessionId) {
    if (!sessionId) return
    // Tell the backend to stop the agent.
    try {
      await fetch(`/api/chat/stop/${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        credentials: 'same-origin',
      })
    } catch {}
    // Suppress reconnecting banner for this session
    locallyCompletedSessions.value.add(sessionId)
    setTimeout(() => {
      locallyCompletedSessions.value.delete(sessionId)
    }, 5000)
    // Remove per-session stream state
    _removeStream(sessionId)
  }

  async function fetchActiveSessions() {
    try {
      const res = await fetch('/api/chat/active', { credentials: 'same-origin' })
      if (!res.ok) return
      const data = await res.json()
      activeSessions.value = new Set(data.active_sessions || [])
    } catch {}
  }

  function isSessionActive(sessionId) {
    return sessionId ? activeSessions.value.has(sessionId) : false
  }

  function resetStreamState(sessionId) {
    if (sessionId) _removeStream(sessionId)
  }

  let _tempSidCounter = 0

  async function sendMessage({ message, sessionId, onSessionUpdate }) {
    if (!message.trim()) return

    // Generate a lightweight temp key for stop-event mapping.
    // The backend will NOT pass this to AIAgent for new chats —
    // instead the agent auto-generates a Hermes-native session ID
    // (YYYYMMDD_HHMMSS_XXXXXX) which comes back in the SSE 'done' event.
    if (!sessionId) {
      _tempSidCounter++
      sessionId = 'tmp_' + Date.now() + '_' + _tempSidCounter
    }

    // For new chats (temp keys), immediately set currentStreamingId so
    // the UI can show streaming state right away via getStreamState().
    if (sessionId.startsWith('tmp_')) {
      currentStreamingId.value = sessionId
    }

    // Allocate per-session stream state
    const state = _ensureStream(sessionId)
    if (state.sending) return // Already streaming for this session

    state.loadError = ''
    state.streamingMsg = ''
    state.streamingTool = ''
    state.status = 'sending'
    state.statusDetail = ''
    state.sending = true

    // Create AbortController for this stream
    const abortController = new AbortController()
    state._abortController = abortController
    const signal = abortController.signal

    // Debounced status progression: sending → thinking if no tokens arrive
    let tokenReceived = false
    let detailInterval = null
    const statusTimer = setTimeout(() => {
      if (!tokenReceived) {
        state.status = 'thinking'
        const details = [
          'analyzing your request…',
          'consulting knowledge base…',
          'reasoning through response…',
          'gathering context…',
        ]
        let di = 0
        detailInterval = setInterval(() => {
          if (tokenReceived || state.status !== 'thinking') {
            clearInterval(detailInterval)
            detailInterval = null
            return
          }
          state.statusDetail = details[di % details.length]
          di++
        }, 2500)
      }
    }, 800)

    const cleanupStream = () => {
      clearTimeout(statusTimer)
      if (detailInterval) clearInterval(detailInterval)
      state.sending = false
      state._abortController = null
      // Clear streaming display state so StreamingMessage.vue doesn't
      // render already-committed text or stale status alongside the bubble.
      state.streamingMsg = ''
      state.streamingTool = ''
      state.status = ''
      state.statusDetail = ''
      // Mark session as locally-completed so reconnecting banner doesn't
      // fire immediately (backend still shows it active for ~300s).
      const resolvedKey = currentStreamingId.value || sessionId
      locallyCompletedSessions.value.add(resolvedKey)
      setTimeout(() => {
        locallyCompletedSessions.value.delete(resolvedKey)
      }, 5000)
    }

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        signal,
        body: JSON.stringify({
          message,
          session_id: sessionId,
          model: currentModel.value || null,
        }),
      })

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        state.loadError = errBody.error || `HTTP ${res.status}`
        cleanupStream()
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let shouldReload = false
      let lastSessionId = sessionId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const d = JSON.parse(line.slice(6))

            if (d.token) {
              if (!tokenReceived) {
                tokenReceived = true
                clearTimeout(statusTimer)
                state.status = ''
              }
              state.streamingMsg += d.token
              state.streamingTool = ''
            }

            if (d.tool_start) {
              if (!tokenReceived) {
                tokenReceived = true
                clearTimeout(statusTimer)
              }
              if (!state.streamingMsg) {
                state.status = 'thinking'
              }
              state.streamingTool =
                d.tool_start +
                (d.tool_preview ? ': ' + d.tool_preview : '')
              state.statusDetail = 'running tool: ' + d.tool_start
            }

            if (d.tool_complete) {
              state.status = 'thinking'
              state.streamingTool = d.tool_complete + ' ready'
              state.statusDetail = ''
              setTimeout(() => {
                if (state.streamingTool === d.tool_complete + ' ready') {
                  state.streamingTool = ''
                }
              }, 1200)
            }

            if (d.status) {
              state.statusDetail = d.status
            }

            if (d.error) {
              state.loadError = d.error
              state.status = ''
              state.statusDetail = ''
            }

            if (d.done) {
              lastSessionId = d.session_id || lastSessionId
              shouldReload = true
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }

      // Migrate stream state from temp key to real Hermes session ID
      if (lastSessionId && lastSessionId !== sessionId) {
        migrateStream(sessionId, lastSessionId)
        currentStreamingId.value = lastSessionId
      }

      if (shouldReload && onSessionUpdate) {
        onSessionUpdate(lastSessionId)
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        cleanupStream()
        return
      }
      state.loadError = 'Error: ' + e.message
      state.status = ''
    } finally {
      cleanupStream()
    }
  }

  return {
    // stream tracking
    currentStreamingId,
    clearCurrentStreamingId,
    migrateStream,
    // model state
    inputText,
    currentModel,
    defaultModel,
    availableProviders,
    selectedProvider,
    providersLoading,
    modelSelectorOpen,
    // active sessions
    activeSessions,
    locallyCompletedSessions,
    streams,
    activeStreamIds,
    // per-session stream state accessor
    getStreamState,
    // helpers
    isSystemMsg,
    toolArgPreview,
    prettyJson,
    renderContent,
    shortModel,
    shortModelName,
    providerName,
    // actions
    resetStreamState,
    sendMessage,
    fetchProviders,
    fetchDefaultModel,
    setCurrentModel,
    updateSessionModel,
    abortStream,
    fetchActiveSessions,
    isSessionActive,
  }
})
