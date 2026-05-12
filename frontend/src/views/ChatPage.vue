<template>
  <div class="flex h-screen bg-[#0d1117] text-[#c9d1d9] overflow-hidden relative">
    <!-- Sidebar overlay (mobile) -->
    <div
      v-if="sidebarOpen && !isDesktop"
      class="fixed inset-0 bg-black/50 z-20 lg:hidden"
      @click="sidebarOpen = false"
    ></div>

    <!-- Sidebar -->
    <SessionSidebar
      :open="sidebarOpen"
      :is-desktop="isDesktop"
      @close="sidebarOpen = false"
    />

    <!-- Sidebar toggle button (desktop, when collapsed) -->
    <button
      v-if="isDesktop && !sidebarOpen"
      @click="sidebarOpen = true"
      class="absolute left-3 top-3 z-10 p-2 rounded-md bg-surface border border-border text-muted hover:text-[#c9d1d9] transition-colors"
      title="Open sidebar"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>

    <!-- Main -->
    <main class="flex-1 flex flex-col min-w-0 relative overflow-hidden">
      <!-- Mobile top bar -->
      <div v-if="!isDesktop" class="flex items-center justify-between px-4 py-3 border-b border-border bg-surface">
        <button @click="sidebarOpen = true" class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <h1 class="text-sm font-semibold text-muted">Hermes</h1>
        <button @click="sessionsStore.newChat()" class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>

      <!-- Scroll area -->
      <div ref="messagesRef" class="flex-1 overflow-y-auto overflow-x-hidden relative" @scroll="onScroll">
        <!-- Empty state -->
        <EmptyState
          v-if="!sessionsStore.allMessages.length && !chatStore.streamingMsg && !chatStore.status"
          @send="handleSendFromEmptyState"
        />

        <!-- Messages -->
        <MessageList
          v-else
          :messages="sessionsStore.allMessages"
          :streaming-msg="chatStore.streamingMsg"
          :streaming-tool="chatStore.streamingTool"
          :status="chatStore.status"
          :status-detail="chatStore.statusDetail"
          :error="chatStore.loadError"
          :show-system-messages="sessionsStore.showSystemMessages"
        />

      </div>

      <!-- Floating input (non-empty) -->
      <div
        v-if="sessionsStore.allMessages.length || chatStore.streamingMsg || chatStore.status"
        class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0d1117]/90 via-[#0d1117]/60 to-transparent pt-8 pb-4 px-4 pointer-events-none"
      >
        <div class="max-w-[800px] w-full mx-auto px-2 sm:px-0 pointer-events-auto relative">
          <!-- Scroll-to-bottom arrow, floating just right of the send button -->
          <button
            v-if="!atBottom"
            @click="scrollToBottomSmooth"
            class="absolute -top-12 right-0 z-20 p-2 rounded-full bg-surface/80 backdrop-blur-sm border border-border/60 text-muted/60 hover:text-[#c9d1d9] hover:border-accent/40 transition-all shadow-lg shadow-black/20"
            title="Scroll to bottom"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
          </button>
          <ChatInput
            v-model="chatStore.inputText"
            :disabled="chatStore.sending"
            @send="sendMessage"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { useSessionsStore } from '../stores/sessions'
import { useChatStore } from '../stores/chat'
import { useAuthStore } from '../stores/auth'
import SessionSidebar from '../components/SessionSidebar.vue'
import MessageList from '../components/MessageList.vue'
import EmptyState from '../components/EmptyState.vue'
import ChatInput from '../components/ChatInput.vue'

export default {
  components: { SessionSidebar, MessageList, EmptyState, ChatInput },
  setup() {
    return {
      sessionsStore: useSessionsStore(),
      chatStore: useChatStore(),
      authStore: useAuthStore(),
    }
  },
  data() {
    return {
      sidebarOpen: true,
      isDesktop: true,
      wasDesktop: true,
      atBottom: true,
    }
  },
  created() {
    this.isDesktop = window.innerWidth >= 1024
    this.wasDesktop = this.isDesktop
    this.sidebarOpen = this.isDesktop
  },
  mounted() {
    window.addEventListener('resize', this.onResize)
    this.authStore.checkAuth().then((ok) => {
      if (ok) this.sessionsStore.loadSessions()
      else this.$router.push('/login')
    })
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.onResize)
  },
  watch: {
    'sessionsStore.showCrons'() {
      this.sessionsStore.showAll = false
      this.sessionsStore.loadSessions()
    },
  },
  updated() {
    if (this.atBottom) {
      this.$nextTick(() => this.scrollToBottom())
    }
  },
  methods: {
    onResize() {
      const desktop = window.innerWidth >= 1024
      this.isDesktop = desktop
      if (this.wasDesktop && !desktop) this.sidebarOpen = false
      if (!this.wasDesktop && desktop) this.sidebarOpen = true
      this.wasDesktop = desktop
    },
    onScroll() {
      const el = this.$refs.messagesRef
      if (!el) return
      const bottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
      this.atBottom = bottom
    },
    scrollToBottom() {
      const el = this.$refs.messagesRef
      if (el) el.scrollTop = el.scrollHeight
    },
    scrollToBottomSmooth() {
      const el = this.$refs.messagesRef
      if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    },
    /** Called when a message is sent from within the EmptyState component. */
    handleSendFromEmptyState() {
      // The EmptyState component has its own local input.
      // We use the text from the chat store if it's bound, otherwise fallback.
      if (this.chatStore.inputText.trim()) {
        this.sendMessage()
      }
    },
    async sendMessage() {
      const text = this.chatStore.inputText.trim()
      if (!text || this.chatStore.sending) return

      // Push user message locally
      this.sessionsStore.allMessages.push({
        role: 'user',
        content: text,
        source: 'user',
      })
      this.chatStore.inputText = ''
      this.$nextTick(() => this.scrollToBottom())

      await this.chatStore.sendMessage({
        message: text,
        sessionId: this.sessionsStore.currentSessionId,
        onSessionUpdate: (newSessionId) => {
          // After the stream completes: commit the assistant message
          if (this.chatStore.streamingMsg) {
            this.sessionsStore.allMessages.push({
              role: 'assistant',
              content: this.chatStore.streamingMsg,
              source: 'assistant',
            })
          }
          this.sessionsStore.currentSessionId =
            newSessionId || this.sessionsStore.currentSessionId
          this.chatStore.resetStreamState()
          this.sessionsStore.loadSessions()
          this.$nextTick(() => this.scrollToBottom())
        },
      })
    },
  },
}
</script>