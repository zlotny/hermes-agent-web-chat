<template>
  <div class="chat-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>Sessions</h2>
        <button class="btn-new" @click="newChat">+ New</button>
      </div>
      <div class="session-list">
        <div v-if="sidebarError" class="error-msg">{{ sidebarError }}</div>
        <div v-for="s in sessions" :key="s.id"
             :class="['session-item', { active: s.id === currentSessionId }]"
             @click="loadSession(s.id)">
          <div class="s-title">{{ s.title }}</div>
          <div class="s-meta">
            <span>{{ s.message_count }} msgs</span>
            <span v-if="s.model" class="model-badge">{{ shortModel(s.model) }}</span>
          </div>
        </div>
      </div>
    </aside>

    <main class="main">
      <div class="messages" ref="messagesRef">
        <div v-if="!chatMessages.length && !streamingMsg" class="empty-state">
          <h1>Hermes</h1>
          <p>Type a message below to start a conversation.</p>
        </div>
        <template v-for="(m, i) in chatMessages" :key="i">
          <div v-if="m.role === 'user'" class="msg user">
            <div class="role">You</div>
            <div class="bubble">{{ m.content }}</div>
          </div>
          <div v-if="m.role === 'assistant'" class="msg assistant">
            <div class="role">Hermes</div>
            <div class="bubble" v-html="renderContent(m.content || '')"></div>
            <div v-if="m.tool_calls && m.tool_calls.length" class="tool-chips">
              <span v-for="tc in m.tool_calls" :key="tc.id || tc.call_id" class="tool-chip">
                ⚡ {{ tc.function?.name || tc.name || 'tool' }}
              </span>
            </div>
          </div>
        </template>
        <!-- Streaming message -->
        <div v-if="streamingMsg" class="msg assistant">
          <div class="role">Hermes</div>
          <div class="bubble" v-html="renderContent(streamingMsg)"></div>
          <div v-if="streamingTool" class="typing">⚡ {{ streamingTool }}...</div>
        </div>
        <div v-if="loadError" class="error-msg">{{ loadError }}</div>
      </div>

      <div class="input-area">
        <div class="input-row">
          <textarea v-model="inputText" rows="1" placeholder="Type a message..."
            @keydown.enter.exact.prevent="sendMessage"
            @input="resizeTextarea" ref="chatInput"></textarea>
          <button @click="sendMessage" :disabled="sending">Send</button>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  data() {
    return {
      sessions: [],
      currentSessionId: null,
      allMessages: [],
      inputText: '',
      sending: false,
      sidebarError: '',
      loadError: '',
      streamingMsg: '',
      streamingTool: '',
    }
  },
  computed: {
    chatMessages() {
      return this.allMessages.filter(m => m.role === 'user' || m.role === 'assistant')
    }
  },
  async mounted() {
    const ok = await this.checkAuth()
    if (ok) this.loadSessions()
  },
  updated() {
    this.$nextTick(() => this.scrollToBottom())
  },
  methods: {
    scrollToBottom() {
      const el = this.$refs.messagesRef
      if (el) el.scrollTop = el.scrollHeight
    },
    async checkAuth() {
      try {
        const res = await fetch('/api/sessions', { credentials: 'same-origin' })
        if (res.status === 401) {
          this.$router.push('/login')
          return false
        }
        return true
      } catch {
        return false
      }
    },
    async loadSessions() {
      this.sidebarError = ''
      try {
        const res = await fetch('/api/sessions', { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        this.sessions = await res.json()
      } catch (e) {
        this.sidebarError = 'Failed to load sessions: ' + e.message
      }
    },
    async loadSession(id) {
      this.currentSessionId = id
      this.loadError = ''
      this.sending = true
      try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        this.allMessages = data.messages || []
      } catch (e) {
        this.loadError = 'Error: ' + e.message
        this.allMessages = []
      } finally {
        this.sending = false
      }
    },
    newChat() {
      this.currentSessionId = null
      this.allMessages = []
      this.streamingMsg = ''
      this.streamingTool = ''
      this.loadError = ''
      this.inputText = ''
      this.$nextTick(() => {
        if (this.$refs.chatInput) this.$refs.chatInput.focus()
      })
    },
    shortModel(model) {
      if (!model) return ''
      const parts = model.split('/')
      return parts[parts.length - 1] || model
    },
    renderContent(text) {
      if (!text) return ''
      let html = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\n\n/g, '</p><p>')
      html = html.replace(/\n/g, '<br>')
      return '<p>' + html + '</p>'
    },
    async sendMessage() {
      if (!this.inputText.trim() || this.sending) return
      const text = this.inputText.trim()
      this.inputText = ''
      this.loadError = ''

      // Add user message
      this.allMessages.push({ role: 'user', content: text })
      this.streamingMsg = ''
      this.streamingTool = ''
      this.sending = true

      try {
        const res = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            message: text,
            session_id: this.currentSessionId || null,
          }),
        })
        if (!res.ok) {
          const err = await res.json()
          this.loadError = err.error || `HTTP ${res.status}`
          this.sending = false
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const data = JSON.parse(line.slice(6))
              if (data.token) {
                this.streamingMsg += data.token
              }
              if (data.error) {
                this.loadError = data.error
                this.sending = false
              }
              if (data.done) {
                // Move streaming message to permananent messages
                if (this.streamingMsg) {
                  this.allMessages.push({
                    role: 'assistant',
                    content: this.streamingMsg,
                  })
                }
                this.currentSessionId = data.session_id || this.currentSessionId
                this.streamingMsg = ''
                this.sending = false
                this.loadSessions() // refresh sidebar
              }
            } catch (e) {
              // skip parse errors on partial lines
            }
          }
        }
      } catch (e) {
        this.loadError = 'Connection error: ' + e.message
      } finally {
        this.sending = false
      }
    },
    resizeTextarea(e) {
      const el = e.target
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    },
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex; height: 100vh; overflow: hidden;
  background: #0d1117; color: #c9d1d9;
}
.sidebar {
  width: 280px; min-width: 280px;
  background: #161b22; border-right: 1px solid #30363d;
  display: flex; flex-direction: column; overflow: hidden;
}
.sidebar-header {
  padding: 16px; border-bottom: 1px solid #30363d;
  display: flex; justify-content: space-between; align-items: center;
}
.sidebar-header h2 { font-size: 0.9rem; font-weight: 600; }
.btn-new {
  background: #58a6ff; color: #fff; border: none;
  padding: 4px 12px; border-radius: 6px; font-size: 0.8rem;
  cursor: pointer; font-weight: 500;
}
.btn-new:hover { background: #79c0ff; }
.session-list { flex: 1; overflow-y: auto; padding: 8px; }
.session-item {
  padding: 10px 12px; border-radius: 6px; cursor: pointer;
  margin-bottom: 2px;
}
.session-item:hover { background: #1c2333; }
.session-item.active { background: #1c2333; border-left: 3px solid #58a6ff; }
.s-title {
  font-size: 0.82rem; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; margin-bottom: 2px;
}
.s-meta { font-size: 0.72rem; color: #8b949e; display: flex; align-items: center; gap: 6px; }
.model-badge {
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 3px; padding: 0 4px; font-size: 0.68rem;
}
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.messages {
  flex: 1; overflow-y: auto; padding: 24px 16px;
  max-width: 800px; margin: 0 auto; width: 100%;
}
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: 100%; text-align: center;
  color: #8b949e;
}
.empty-state h1 { font-size: 1.5rem; margin-bottom: 8px; color: #c9d1d9; }
.msg { margin-bottom: 20px; }
.msg .role {
  font-size: 0.75rem; font-weight: 600; color: #8b949e;
  margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;
}
.msg.user .bubble {
  background: #1f6feb; padding: 12px 16px; border-radius: 8px;
  border-bottom-right-radius: 2px; line-height: 1.6; font-size: 0.9rem;
  white-space: pre-wrap; word-wrap: break-word; display: inline-block;
}
.msg.assistant .bubble {
  background: #161b22; border: 1px solid #30363d; padding: 12px 16px;
  border-radius: 8px; border-bottom-left-radius: 2px;
  line-height: 1.6; font-size: 0.9rem; white-space: pre-wrap; word-wrap: break-word;
}
.msg .bubble pre {
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 4px; padding: 8px 12px; overflow-x: auto;
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.82rem;
  margin: 8px 0;
}
.msg .bubble code {
  font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.82rem;
  background: #0d1117; padding: 1px 4px; border-radius: 3px;
}
.tool-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.tool-chip {
  font-size: 0.72rem; background: #1c2333;
  border: 1px solid #30363d; border-radius: 4px;
  padding: 2px 8px; color: #8b949e;
}
.typing { color: #8b949e; font-size: 0.85rem; font-style: italic; padding: 8px 0; }
.input-area { border-top: 1px solid #30363d; padding: 16px; background: #161b22; }
.input-row {
  max-width: 800px; margin: 0 auto; display: flex; gap: 8px;
}
.input-row textarea {
  flex: 1; background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #c9d1d9; padding: 10px 14px;
  font-family: inherit; font-size: 0.9rem; resize: none;
  outline: none; min-height: 44px; max-height: 200px; line-height: 1.4;
}
.input-row textarea:focus { border-color: #58a6ff; }
.input-row button {
  background: #58a6ff; color: #fff; border: none;
  border-radius: 6px; padding: 0 20px; font-size: 0.9rem;
  cursor: pointer; font-weight: 500;
}
.input-row button:hover { background: #79c0ff; }
.input-row button:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg { color: #f85149; font-size: 0.85rem; padding: 8px; }
@media (max-width: 640px) {
  .sidebar { display: none; }
  .messages { padding: 16px 12px; }
  .input-area { padding: 12px; }
}
</style>
