<template>
  <div class="flex h-screen bg-[#0d1117] text-[#c9d1d9] overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-[280px] min-w-[280px] bg-surface border-r border-border flex flex-col overflow-hidden">
      <div class="flex items-center justify-between px-4 py-4 border-b border-border">
        <h2 class="text-sm font-semibold">Sessions</h2>
        <button @click="newChat" class="bg-accent text-white text-xs font-medium px-3 py-1 rounded-md hover:bg-[#79c0ff]">+ New</button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-0.5">
        <!-- Skeleton -->
        <div v-if="loadingSessions" class="space-y-3 px-2 pt-2">
          <div v-for="n in 5" :key="n" class="space-y-1.5">
            <div class="skel h-3 w-[85%]"></div>
            <div class="skel h-2 w-[45%]"></div>
          </div>
        </div>
        <div v-else-if="sidebarError" class="text-[#f85149] text-xs p-2">{{ sidebarError }}</div>
        <template v-else>
          <div v-for="s in visibleSessions" :key="s.id"
               @click="loadSession(s.id)"
               :class="['p-2.5 rounded-md cursor-pointer text-xs', s.id === currentSessionId ? 'bg-[#1c2333] border-l-[3px] border-accent' : 'hover:bg-[#1c2333]']">
            <div class="truncate text-[13px] mb-0.5">{{ s.title }}</div>
            <div class="flex items-center gap-1.5 text-muted text-[11px]">
              <span>{{ s.message_count }} msgs</span>
              <span v-if="s.model" class="bg-[#0d1117] border border-border rounded px-1 text-[10px]">{{ shortModel(s.model) }}</span>
            </div>
          </div>
          <button v-if="allSessions.length > visibleSessions.length"
                  @click="showAllSessions"
                  class="w-full py-2 mt-1 text-xs text-muted border border-border rounded-md bg-transparent hover:border-accent hover:text-accent">
            Show all ({{ allSessions.length }})
          </button>
        </template>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 flex flex-col min-w-0">
      <!-- Messages -->
      <div ref="messagesRef" class="flex-1 overflow-y-auto px-4 py-6 max-w-[800px] w-full mx-auto">
        <div v-if="!chatMessages.length && !streamingMsg" class="flex flex-col items-center justify-center h-full text-center text-muted">
          <h1 class="text-2xl text-[#c9d1d9] mb-2">Hermes</h1>
          <p class="text-sm max-w-[360px] leading-relaxed">Type a message below to start a conversation.</p>
        </div>
        <template v-for="(m, i) in chatMessages" :key="i">
          <div v-if="m.role === 'user'" class="mb-5">
            <div class="text-[11px] font-semibold text-muted uppercase tracking-wider mb-1">You</div>
            <div class="bg-[#1f6feb] px-4 py-3 rounded-lg rounded-br-sm text-sm leading-relaxed whitespace-pre-wrap break-words inline-block">
              {{ m.content }}
            </div>
          </div>
          <div v-if="m.role === 'assistant'" class="mb-5">
            <div class="text-[11px] font-semibold text-muted uppercase tracking-wider mb-1">Hermes</div>
            <div class="bg-surface border border-border px-4 py-3 rounded-lg rounded-bl-sm text-sm leading-relaxed whitespace-pre-wrap break-words"
                 v-html="renderContent(m.content || '')">
            </div>
            <div v-if="m.tool_calls && m.tool_calls.length" class="flex flex-wrap gap-1 mt-1.5">
              <span v-for="tc in m.tool_calls" :key="tc.id || tc.call_id"
                    class="text-[11px] bg-[#1c2333] border border-border rounded px-2 py-0.5 text-muted">
                ⚡ {{ tc.function?.name || tc.name || 'tool' }}
              </span>
            </div>
          </div>
        </template>
        <!-- Streaming message -->
        <div v-if="streamingMsg" class="mb-5">
          <div class="text-[11px] font-semibold text-muted uppercase tracking-wider mb-1">Hermes</div>
          <div class="bg-surface border border-border px-4 py-3 rounded-lg rounded-bl-sm text-sm leading-relaxed whitespace-pre-wrap break-words"
               v-html="renderContent(streamingMsg)">
          </div>
          <div v-if="streamingTool" class="text-muted text-xs italic mt-1">⚡ {{ streamingTool }}...</div>
        </div>
        <div v-if="loadError" class="text-[#f85149] text-xs p-2">{{ loadError }}</div>
      </div>

      <!-- Input -->
      <div class="border-t border-border px-4 py-4 bg-surface">
        <div class="max-w-[800px] mx-auto flex gap-2">
          <textarea ref="chatInput" v-model="inputText" rows="1" placeholder="Type a message..."
            @keydown.enter.exact.prevent="sendMessage"
            @input="resizeTextarea"
            class="flex-1 bg-[#0d1117] border border-border rounded-md text-[#c9d1d9] px-3.5 py-2.5 text-sm outline-none resize-none min-h-[44px] max-h-[200px] leading-relaxed focus:border-accent">
          </textarea>
          <button @click="sendMessage" :disabled="sending"
            class="bg-accent text-white px-5 rounded-md text-sm font-medium hover:bg-[#79c0ff] disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap">
            Send
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  data() {
    return {
      allSessions: [],
      currentSessionId: null,
      allMessages: [],
      inputText: '',
      loadingSessions: true,
      sending: false,
      sidebarError: '',
      loadError: '',
      streamingMsg: '',
      streamingTool: '',
      showAll: false,
    }
  },
  computed: {
    chatMessages() {
      return this.allMessages.filter(m => m.role === 'user' || m.role === 'assistant')
    },
    visibleSessions() {
      return this.showAll ? this.allSessions : this.allSessions.slice(0, 5)
    }
  },
  async mounted() {
    const ok = await this.checkAuth()
    if (ok) this.loadSessions()
  },
  updated() { this.$nextTick(() => this.scrollToBottom()) },
  methods: {
    scrollToBottom() {
      const el = this.$refs.messagesRef
      if (el) el.scrollTop = el.scrollHeight
    },
    async checkAuth() {
      try {
        const res = await fetch('/api/sessions?limit=5', { credentials: 'same-origin' })
        if (res.status === 401) {
          this.$router.push('/login')
          return false
        }
        return true
      } catch { return false }
    },
    async loadSessions() {
      this.sidebarError = ''
      this.loadingSessions = true
      try {
        const res = await fetch('/api/sessions?limit=5', { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        this.allSessions = await res.json()
      } catch (e) { this.sidebarError = 'Failed: ' + e.message }
      finally { this.loadingSessions = false }
    },
    async showAllSessions() {
      this.showAll = true
      if (this.allSessions.length <= 5) return
      try {
        const res = await fetch('/api/sessions', { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        this.allSessions = await res.json()
      } catch (e) { this.sidebarError = 'Failed: ' + e.message }
    },
    async loadSession(id) {
      this.currentSessionId = id
      this.loadError = ''
      this.sending = true
      try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(id)}`, { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        this.allMessages = (await res.json()).messages || []
      } catch (e) { this.loadError = 'Error: ' + e.message; this.allMessages = [] }
      finally { this.sending = false }
    },
    newChat() {
      this.currentSessionId = null
      this.allMessages = []
      this.streamingMsg = ''
      this.streamingTool = ''
      this.loadError = ''
      this.inputText = ''
      this.$nextTick(() => { if (this.$refs.chatInput) this.$refs.chatInput.focus() })
    },
    shortModel(m) { return m ? (m.split('/').pop() || m) : '' },
    renderContent(t) {
      if (!t) return ''
      let h = t.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
      h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      h = h.replace(/\n\n/g, '</p><p>')
      h = h.replace(/\n/g, '<br>')
      return '<p>' + h + '</p>'
    },
    async sendMessage() {
      if (!this.inputText.trim() || this.sending) return
      const text = this.inputText.trim()
      this.inputText = ''
      this.loadError = ''
      this.allMessages.push({ role: 'user', content: text })
      this.streamingMsg = ''
      this.streamingTool = ''
      this.sending = true
      try {
        const res = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ message: text, session_id: this.currentSessionId || null }),
        })
        if (!res.ok) { this.loadError = (await res.json()).error || `HTTP ${res.status}`; this.sending = false; return }
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
              const d = JSON.parse(line.slice(6))
              if (d.token) this.streamingMsg += d.token
              if (d.error) { this.loadError = d.error; this.sending = false }
              if (d.done) {
                if (this.streamingMsg) this.allMessages.push({ role: 'assistant', content: this.streamingMsg })
                this.currentSessionId = d.session_id || this.currentSessionId
                this.streamingMsg = ''
                this.sending = false
                this.loadSessions()
              }
            } catch (e) { /* skip partial */ }
          }
        }
      } catch (e) { this.loadError = 'Error: ' + e.message }
      finally { this.sending = false }
    },
    resizeTextarea(e) {
      const el = e.target
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    },
  }
}
</script>
