import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  // --- State ---
  const inputText = ref('')
  const sending = ref(false)
  const streamingMsg = ref('')
  const streamingTool = ref('')
  const status = ref('')       // 'sending' | 'thinking' | '' (idle)
  const statusDetail = ref('') // e.g. "analyzing your request…"
  const loadError = ref('')

  // --- Pure helpers (shared between store and components) ---

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

  // --- Actions ---

  function resetStreamState() {
    streamingMsg.value = ''
    streamingTool.value = ''
    status.value = ''
    statusDetail.value = ''
  }

  async function sendMessage({ message, sessionId, onSessionUpdate }) {
    if (!message.trim() || sending.value) return

    loadError.value = ''
    resetStreamState()
    status.value = 'sending'
    sending.value = true

    // Debounced status progression: sending → thinking if no tokens arrive
    let tokenReceived = false
    const statusTimer = setTimeout(() => {
      if (!tokenReceived) {
        status.value = 'thinking'
        const details = [
          'analyzing your request…',
          'consulting knowledge base…',
          'reasoning through response…',
          'gathering context…',
        ]
        let di = 0
        const detailInterval = setInterval(() => {
          if (tokenReceived || status.value !== 'thinking') {
            clearInterval(detailInterval)
            return
          }
          statusDetail.value = details[di % details.length]
          di++
        }, 2500)
      }
    }, 800)

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          message,
          session_id: sessionId || null,
        }),
      })

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        loadError.value = errBody.error || `HTTP ${res.status}`
        sending.value = false
        status.value = ''
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
                status.value = ''
              }
              streamingMsg.value += d.token
              streamingTool.value = ''
            }

            if (d.tool_start) {
              if (!tokenReceived) {
                tokenReceived = true
                clearTimeout(statusTimer)
              }
              if (!streamingMsg.value) {
                // No text streamed yet — show as thinking+tool
                status.value = 'thinking'
              }
              streamingTool.value =
                d.tool_start +
                (d.tool_preview ? ': ' + d.tool_preview : '')
              statusDetail.value = 'running tool: ' + d.tool_start
            }

            if (d.tool_complete) {
              status.value = 'thinking'
              streamingTool.value = d.tool_complete + ' ready'
              statusDetail.value = ''
              setTimeout(() => {
                if (
                  streamingTool.value === d.tool_complete + ' ready'
                ) {
                  streamingTool.value = ''
                }
              }, 1200)
            }

            if (d.status) {
              statusDetail.value = d.status
            }

            if (d.error) {
              loadError.value = d.error
              sending.value = false
              status.value = ''
              statusDetail.value = ''
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

      if (shouldReload && onSessionUpdate) {
        onSessionUpdate(lastSessionId)
      }
    } catch (e) {
      loadError.value = 'Error: ' + e.message
      status.value = ''
    } finally {
      clearTimeout(statusTimer)
      sending.value = false
      status.value = ''
    }
  }

  return {
    // state
    inputText,
    sending,
    streamingMsg,
    streamingTool,
    status,
    statusDetail,
    loadError,
    // helpers
    isSystemMsg,
    toolArgPreview,
    prettyJson,
    renderContent,
    shortModel,
    // actions
    resetStreamState,
    sendMessage,
  }
})
