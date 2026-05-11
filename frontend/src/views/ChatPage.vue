<template>
  <div class="flex h-screen bg-[#0d1117] text-[#c9d1d9] overflow-hidden relative">
    <!-- Sidebar overlay (mobile) -->
    <div v-if="sidebarOpen && !isDesktop"
         class="fixed inset-0 bg-black/50 z-20 lg:hidden"
         @click="sidebarOpen = false"></div>

    <!-- Sidebar -->
    <aside :class="[
      'bg-surface border-r border-border flex flex-col overflow-hidden transition-all duration-300 z-30',
      isDesktop ? 'relative' : 'fixed left-0 top-0 h-full',
      sidebarOpen ? (isDesktop ? 'w-[280px] min-w-[280px]' : 'w-[280px]') : 'w-0 min-w-0 border-0',
    ]">
      <div v-if="sidebarOpen" class="flex flex-col h-full min-w-[280px]">
          <div class="flex items-center justify-between px-4 py-4 border-b border-border">
            <h2 class="text-sm font-semibold tracking-wide">Sessions</h2>
            <div class="flex items-center gap-1">
              <button @click="newChat" class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted hover:text-[#c9d1d9] transition-colors" title="New chat">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              </button>
              <button @click="sidebarOpen = false" class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted hover:text-[#c9d1d9] transition-colors" title="Collapse sidebar">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
              </button>
            </div>
          </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-0.5">
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
                 :class="['p-2.5 rounded-md cursor-pointer text-xs transition-colors', s.id === currentSessionId ? 'bg-[#1c2333] border-l-[3px] border-accent' : 'hover:bg-[#1c2333]']">
              <div class="truncate text-[13px] mb-0.5 flex items-center gap-1.5">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="shrink-0 text-muted"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                {{ s.title }}
              </div>
              <div class="flex items-center gap-1.5 text-muted text-[11px] ml-[22px]">
                <span>{{ s.message_count }} msgs</span>
                <span v-if="s.model" class="bg-[#0d1117] border border-border rounded px-1 text-[10px]">{{ shortModel(s.model) }}</span>
              </div>
            </div>
            <button v-if="!showAll && totalSessions > visibleSessions.length"
                    @click="showAllSessions"
                    class="w-full py-2 mt-1 text-xs text-muted border border-border rounded-md bg-transparent hover:border-accent hover:text-accent transition-colors">
            Show all ({{ totalSessions }})
            </button>
          </template>
        </div>
        <!-- Settings footer -->
        <div class="border-t border-border p-3 relative">
          <button @click="settingsOpen = !settingsOpen"
                  class="flex items-center gap-2 text-xs text-muted hover:text-[#c9d1d9] transition-colors w-full p-1.5 rounded-md hover:bg-[#1c2333]">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Settings
          </button>
          <!-- Context menu -->
          <div v-if="settingsOpen"
               class="absolute bottom-full left-3 mb-1 w-[220px] bg-surface border border-border rounded-lg shadow-xl shadow-black/30 p-2 z-50">
            <div class="flex items-center justify-between px-3 py-2 rounded-md hover:bg-[#1c2333] cursor-pointer transition-colors"
                 @click="showCrons = !showCrons; settingsOpen = false">
              <span class="text-xs">Show crons</span>
              <div :class="['w-8 h-4 rounded-full transition-colors relative', showCrons ? 'bg-accent' : 'bg-[#30363d]']">
                <div :class="['w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform', showCrons ? 'translate-x-4' : 'translate-x-0.5']"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Sidebar toggle button (desktop, when collapsed) -->
    <button v-if="isDesktop && !sidebarOpen"
            @click="sidebarOpen = true"
            class="absolute left-3 top-3 z-10 p-2 rounded-md bg-surface border border-border text-muted hover:text-[#c9d1d9] transition-colors"
            title="Open sidebar">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>

    <!-- Main -->
    <main class="flex-1 flex flex-col min-w-0 relative">
      <!-- Mobile top bar -->
      <div v-if="!isDesktop" class="flex items-center justify-between px-4 py-3 border-b border-border bg-surface">
        <button @click="sidebarOpen = true" class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <h1 class="text-sm font-semibold text-muted">Hermes</h1>
        <button @click="newChat" class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>

      <!-- Scroll area -->
      <div ref="messagesRef" class="flex-1 overflow-y-auto">
        <!-- Empty state -->
        <div v-if="!chatMessages.length && !streamingMsg"
             class="flex flex-col items-center justify-center min-h-full px-4 py-12">
          <div class="mb-2 text-accent">
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5-4 8-10 8-2.5 0-4.8-.8-6.7-2.2L2 22l1.8-4.5A9.8 9.8 0 0 1 2 12 10 10 0 0 1 12 2z"/></svg>
          </div>
          <h1 class="text-xl font-semibold text-[#c9d1d9] mb-1">How can I help you?</h1>
          <p class="text-sm text-muted mb-8">Start a conversation with your AI assistant</p>
          <div class="w-full max-w-[640px]">
            <div class="flex gap-2 bg-surface border border-border rounded-xl p-2 shadow-lg shadow-black/20">
              <textarea ref="emptyInput" v-model="inputText" rows="1" placeholder="Type a message..."
                @keydown.enter.exact.prevent="sendMessage"
                @input="resizeTextarea"
                class="flex-1 bg-transparent text-[#c9d1d9] px-3 py-2.5 text-sm outline-none resize-none min-h-[44px] max-h-[200px] leading-relaxed placeholder:text-muted/60">
              </textarea>
              <button @click="sendMessage" :disabled="sending || !inputText.trim()"
                class="self-end p-2.5 rounded-lg bg-accent text-white hover:bg-[#79c0ff] transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
            <p class="text-[11px] text-muted/50 text-center mt-3">Hermes may produce inaccurate information. Verify important facts.</p>
          </div>
        </div>

        <!-- Messages -->
        <div v-else class="max-w-[800px] mx-auto px-4 pt-6 pb-44 space-y-5">
          <template v-for="(m, i) in chatMessages" :key="i">
            <div v-if="m.role === 'user'" class="flex justify-end">
              <div class="max-w-[75%]">
                <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 text-right">You</div>
                <div class="bg-accent/10 border border-accent/20 px-4 py-3 rounded-2xl rounded-br-md text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {{ m.content }}
                </div>
              </div>
            </div>
            <div v-if="m.role === 'assistant'" class="flex justify-start">
              <div class="max-w-[85%]">
                <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent"><path d="M12 2a10 10 0 0 1 10 10c0 5-4 8-10 8-2.5 0-4.8-.8-6.7-2.2L2 22l1.8-4.5A9.8 9.8 0 0 1 2 12 10 10 0 0 1 12 2z"/></svg>
                  Hermes
                </div>
                <div class="px-1 text-sm leading-relaxed whitespace-pre-wrap break-words"
                     v-html="renderContent(m.content || '')">
                </div>
                <div v-if="m.tool_calls && m.tool_calls.length" class="flex flex-wrap gap-1 mt-2">
                  <span v-for="tc in m.tool_calls" :key="tc.id || tc.call_id"
                        class="text-[11px] bg-[#1c2333] border border-border rounded-md px-2 py-0.5 text-muted flex items-center gap-1">
                    <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>
                    {{ tc.function?.name || tc.name || 'tool' }}
                  </span>
                </div>
              </div>
            </div>
          </template>
          <!-- Streaming message -->
          <div v-if="streamingMsg" class="flex justify-start">
            <div class="max-w-[85%]">
              <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent"><path d="M12 2a10 10 0 0 1 10 10c0 5-4 8-10 8-2.5 0-4.8-.8-6.7-2.2L2 22l1.8-4.5A9.8 9.8 0 0 1 2 12 10 10 0 0 1 12 2z"/></svg>
                Hermes
              </div>
              <div class="px-1 text-sm leading-relaxed whitespace-pre-wrap break-words"
                   v-html="renderContent(streamingMsg)">
              </div>
              <div v-if="streamingTool" class="text-muted text-xs italic mt-1 flex items-center gap-1.5">
                <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
                {{ streamingTool }}
              </div>
            </div>
          </div>
          <div v-if="loadError" class="text-[#f85149] text-xs text-center p-2">{{ loadError }}</div>
        </div>
      </div>

      <!-- Floating input (non-empty) -->
      <div v-if="chatMessages.length || streamingMsg"
           class="sticky bottom-0 left-0 right-0 bg-gradient-to-t from-[#0d1117] via-[#0d1117]/95 to-transparent pt-6 pb-4 px-4">
        <div class="max-w-[800px] mx-auto">
          <div class="flex gap-2 bg-surface border border-border rounded-xl p-2 shadow-lg shadow-black/30">
            <textarea v-model="inputText" rows="1" placeholder="Type a message..."
              @keydown.enter.exact.prevent="sendMessage"
              @input="resizeTextarea"
              class="flex-1 bg-transparent text-[#c9d1d9] px-3 py-2.5 text-sm outline-none resize-none min-h-[44px] max-h-[200px] leading-relaxed placeholder:text-muted/60">
            </textarea>
            <button @click="sendMessage" :disabled="sending || !inputText.trim()"
              class="self-end p-2.5 rounded-lg bg-accent text-white hover:bg-[#79c0ff] transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
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
      showCrons: false,
      settingsOpen: false,
      totalSessions: 0,
      sidebarOpen: true,
      isDesktop: true,
      wasDesktop: true,
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
  created() {
    this.isDesktop = window.innerWidth >= 1024
    this.wasDesktop = this.isDesktop
    this.sidebarOpen = this.isDesktop
  },
  mounted() {
    window.addEventListener('resize', this.onResize)
    this.checkAuth().then(ok => { if (ok) this.loadSessions() })
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.onResize)
  },
  watch: {
    showCrons() { this.showAll = false; this.loadSessions() }
  },
  updated() { this.$nextTick(() => this.scrollToBottom()) },
  methods: {
    onResize() {
      const desktop = window.innerWidth >= 1024
      this.isDesktop = desktop
      // Auto-collapse when narrowing past breakpoint, auto-open when widening
      if (this.wasDesktop && !desktop) this.sidebarOpen = false
      if (!this.wasDesktop && desktop) this.sidebarOpen = true
      this.wasDesktop = desktop
    },
    scrollToBottom() {
      const el = this.$refs.messagesRef
      if (el) el.scrollTop = el.scrollHeight
    },
    async checkAuth() {
      try {
        const res = await fetch('/api/sessions?limit=5&show_crons=false', { credentials: 'same-origin' })
        if (res.status === 401) { this.$router.push('/login'); return false }
        return true
      } catch { return false }
    },
    async loadSessions() {
      this.sidebarError = ''
      this.loadingSessions = true
      try {
        const url = `/api/sessions?limit=5&show_crons=${this.showCrons}`
        const res = await fetch(url, { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        this.allSessions = data.sessions || []
        this.totalSessions = data.total || 0
      } catch (e) { this.sidebarError = 'Failed: ' + e.message }
      finally { this.loadingSessions = false }
    },
    async showAllSessions() {
      this.showAll = true
      if (this.allSessions.length >= this.totalSessions) return
      try {
        const url = `/api/sessions?show_crons=${this.showCrons}`
        const res = await fetch(url, { credentials: 'same-origin' })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        this.allSessions = data.sessions || []
      } catch (e) { this.sidebarError = 'Failed: ' + e.message }
    },
    async loadSession(id) {
      this.currentSessionId = id
      this.loadError = ''
      this.sending = true
      if (!this.isDesktop) this.sidebarOpen = false
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
      if (!this.isDesktop) this.sidebarOpen = false
      this.$nextTick(() => {
        const el = this.$refs.emptyInput || this.$refs.chatInput
        if (el) el.focus()
      })
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
      this.$nextTick(() => this.scrollToBottom())
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
                this.$nextTick(() => this.scrollToBottom())
                this.loadSessions()
              }
            } catch (e) { /* skip */ }
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