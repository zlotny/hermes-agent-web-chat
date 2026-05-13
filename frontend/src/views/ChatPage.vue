<template>
  <div
    class="flex h-screen bg-app-bg text-default overflow-hidden relative"
  >
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
      class="absolute left-3 top-3 z-10 p-2 rounded-md bg-surface border border-border text-muted hover:text-default transition-colors"
      title="Open sidebar"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <line x1="3" y1="12" x2="21" y2="12" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <line x1="3" y1="18" x2="21" y2="18" />
      </svg>
    </button>

    <!-- Main -->
    <main class="flex-1 flex flex-col min-w-0 relative overflow-hidden">
      <!-- Mobile top bar -->
      <div
        v-if="!isDesktop"
        class="flex items-center justify-between px-4 py-3 border-b border-border bg-surface"
      >
        <button
          @click="sidebarOpen = true"
          class="p-1.5 rounded-md hover:bg-hover-bg text-muted transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <h1 class="text-sm font-semibold text-muted">Hermes</h1>
        <button
          @click="sessionsStore.newChat()"
          class="p-1.5 rounded-md hover:bg-hover-bg text-muted transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>

      <!-- Scroll area -->
      <div
        ref="messagesRef"
        class="flex-1 overflow-y-auto overflow-x-hidden relative"
        @scroll="onScroll"
      >
        <!-- Reconnecting banner (shown on reload while agent is active) -->
        <div
          v-if="showReconnectingBanner"
          class="sticky top-0 z-10 mx-4 mt-2 px-4 py-2 rounded-lg bg-orange-900/30 border border-orange-700/50 text-orange-300 text-xs flex items-center gap-2"
        >
          <svg
            class="animate-spin h-3.5 w-3.5 flex-shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <span>Reconnecting — agent is still generating a response…</span>
        </div>

        <!-- Empty state -->
        <EmptyState
          ref="emptyState"
          v-if="
            !sessionsStore.allMessages.length &&
            !currentStream.streamingMsg &&
            !currentStream.status
          "
          @send="handleSendFromEmptyState"
          @select-model="onModelSelect"
        />

        <!-- Messages -->
        <MessageList
          v-else
          :messages="sessionsStore.allMessages"
          :streaming-msg="currentStream.streamingMsg"
          :streaming-tool="currentStream.streamingTool"
          :status="currentStream.status"
          :status-detail="currentStream.statusDetail"
          :error="currentStream.loadError"
          :show-system-messages="sessionsStore.showSystemMessages"
        />
      </div>

      <!-- Floating input (non-empty) -->
      <div
        v-if="
          sessionsStore.allMessages.length ||
          currentStream.streamingMsg ||
          currentStream.status
        "
        class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-app-bg/90 via-app-bg/60 to-transparent pt-8 pb-4 px-4 pointer-events-none"
      >
        <div
          class="max-w-[800px] w-full mx-auto px-2 sm:px-0 pointer-events-auto relative"
        >
          <!-- Scroll-to-bottom arrow, floating just right of the send button -->
          <button
            v-if="!atBottom"
            @click="scrollToBottomSmooth"
            class="absolute -top-12 right-0 z-20 p-2 rounded-full bg-surface/80 backdrop-blur-sm border border-border/60 text-muted/60 hover:text-default hover:border-accent/40 transition-all shadow-lg shadow-black/20"
            title="Scroll to bottom"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <polyline points="19 12 12 19 5 12" />
            </svg>
          </button>
          <ChatInput
            ref="floatingChatInput"
            v-model="chatStore.inputText"
            :disabled="currentStream.sending"
            :sending="currentStream.sending"
            :current-model="chatStore.currentModel"
            :providers="chatStore.availableProviders"
            :providers-loading="chatStore.providersLoading"
            :available-commands="chatStore.availableCommands"
            :commands-loading="chatStore.commandsLoading"
            @send="sendMessage"
            @select-model="onModelSelect"
            @stop="onStop"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { useSessionsStore } from "../stores/sessions";
import { useChatStore } from "../stores/chat";
import { useAuthStore } from "../stores/auth";
import SessionSidebar from "../components/SessionSidebar.vue";
import MessageList from "../components/MessageList.vue";
import EmptyState from "../components/EmptyState.vue";
import ChatInput from "../components/ChatInput.vue";

export default {
  components: { SessionSidebar, MessageList, EmptyState, ChatInput },
  setup() {
    return {
      sessionsStore: useSessionsStore(),
      chatStore: useChatStore(),
      authStore: useAuthStore(),
    };
  },
  data() {
    return {
      sidebarOpen: true,
      isDesktop: true,
      wasDesktop: true,
      atBottom: true,
      _bannerEligible: false,
      _bannerTimer: null,
    };
  },
  created() {
    this.isDesktop = window.innerWidth >= 1024;
    this.wasDesktop = this.isDesktop;
    this.sidebarOpen = this.isDesktop;
  },
  mounted() {
    window.addEventListener("resize", this.onResize);
    this.authStore.checkAuth().then((ok) => {
      if (ok) {
        this.sessionsStore.loadSessions();
        this.chatStore.fetchProviders().then(() => this.loadDefaultModel());
        this.chatStore.fetchDefaultModel().then(() => this.loadDefaultModel());
        this.chatStore.fetchCommands();
        // Start polling active sessions for reload resilience
        this.startActiveSessionPolling();
        // Focus the chat input after DOM settles
        setTimeout(() => this.focusChatInput(), 200);
      } else this.$router.push("/login");
    });
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.onResize);
    this.stopActiveSessionPolling();
  },
  watch: {
    "sessionsStore.currentSessionId"(newId, oldId) {
      // If there is no session anymore, reset model to default
      if (!newId) {
        this.loadDefaultModel();
      }
      // Focus the input after a short delay to let the DOM settle
      setTimeout(() => this.focusChatInput(), 100);
      // Clear reconnecting banner debounce on session switch
      this._resetBannerDebounce();
    },
    "sessionsStore.showCrons"() {
      this.sessionsStore.loadSessions();
    },
    /** Reset banner debounce when a new stream starts for the current session. */
    "currentStream.sending"(v) {
      if (v) this._resetBannerDebounce();
    },
  },
  updated() {
    if (this.atBottom) {
      this.$nextTick(() => this.scrollToBottom());
    }
  },
  methods: {
    onResize() {
      const desktop = window.innerWidth >= 1024;
      this.isDesktop = desktop;
      if (this.wasDesktop && !desktop) this.sidebarOpen = false;
      if (!this.wasDesktop && desktop) this.sidebarOpen = true;
      this.wasDesktop = desktop;
    },
    onScroll() {
      const el = this.$refs.messagesRef;
      if (!el) return;
      const bottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      this.atBottom = bottom;
    },
    scrollToBottom() {
      const el = this.$refs.messagesRef;
      if (el) el.scrollTop = el.scrollHeight;
    },
    scrollToBottomSmooth() {
      const el = this.$refs.messagesRef;
      if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    },
    /** Called when a message is sent from within the EmptyState component. */
    handleSendFromEmptyState() {
      // The EmptyState component has its own local input.
      // We use the text from the chat store if it's bound, otherwise fallback.
      if (this.chatStore.inputText.trim()) {
        this.sendMessage();
      }
    },
    async sendMessage() {
      const text = this.chatStore.inputText.trim();
      if (!text) return;

      const sid = this.sessionsStore.currentSessionId;
      const state = this.chatStore.getStreamState(sid);
      if (state.sending) return;

      // Push user message locally
      this.sessionsStore.allMessages.push({
        role: "user",
        content: text,
        source: "user",
      });
      this.chatStore.inputText = "";
      this.$nextTick(() => this.scrollToBottom());

      // Capture the session we were sending to at the time the message was
      // submitted. If the user navigates away during streaming, the backend
      // still persists messages via SessionDB — they'll see results when they
      // come back to this session.
      const sendingSessionId = sid;

      await this.chatStore.sendMessage({
        message: text,
        sessionId: sendingSessionId,
        onSessionUpdate: (newSessionId, sentMessage) => {
          // Only update the UI if the user hasn't navigated away from this
          // session during streaming.
          const currentId = this.sessionsStore.currentSessionId;
          const resolvedId = newSessionId || sendingSessionId;
          const stillOnSameSession =
            !currentId ||
            currentId === sendingSessionId ||
            currentId === newSessionId;

          if (stillOnSameSession) {
            // Commit the assistant message from the per-session state
            const st = this.chatStore.getStreamState(sendingSessionId);
            if (st.streamingMsg) {
              this.sessionsStore.allMessages.push({
                role: "assistant",
                content: st.streamingMsg,
                source: "assistant",
              });
            }
            if (newSessionId && newSessionId !== currentId) {
              this.loadSessionModel(newSessionId);
            }
            // If this was a /model command, refresh the model selector badge
            if (sentMessage && sentMessage.startsWith('/model ')) {
              this.loadSessionModel(resolvedId);
            }
            this.sessionsStore.currentSessionId = resolvedId;
            this.sessionsStore.loadSessions();
          }
          this.$nextTick(() => this.scrollToBottom());
        },
      });
    },
    /** Set the current model from the hermes global default or first provider. */
    loadDefaultModel() {
      // Prefer the config default model
      if (this.chatStore.defaultModel) {
        this.chatStore.setCurrentModel(this.chatStore.defaultModel);
        return;
      }
      const providers = this.chatStore.availableProviders;
      if (!providers.length) return;
      // Find the current provider or use the first one
      const current = providers.find((p) => p.is_current) || providers[0];
      if (current?.models?.length) {
        this.chatStore.setCurrentModel(current.models[0]);
      }
    },
    /** Load session model from the API after a new session is created. */
    async loadSessionModel(sessionId) {
      if (!sessionId) return;
      try {
        const res = await fetch(
          `/api/sessions/${encodeURIComponent(sessionId)}`,
          {
            credentials: "same-origin",
          },
        );
        if (!res.ok) return;
        const data = await res.json();
        if (data.model) {
          this.chatStore.setCurrentModel(data.model);
        }
      } catch {
        // Ignore errors
      }
    },
    /** Handle model selection from the ModelSelector dropdown.
     *  Sends a /model command through the chat stream so the user sees
     *  feedback ("✓ Model switched to...") and the model badge updates. */
    async onModelSelect(model) {
      this.chatStore.setCurrentModel(model);
      const sessionId = this.sessionsStore.currentSessionId;
      if (sessionId) {
        // Prefer sending via the SSE stream for feedback, but fall back
        // to the silent API call if we're already streaming.
        const state = this.chatStore.getStreamState(sessionId);
        if (!state.sending) {
          const prev = this.chatStore.inputText;
          this.chatStore.inputText = `/model ${model}`;
          this.sendMessage();
          this.chatStore.inputText = prev;
        } else {
          await this.chatStore.updateSessionModel(sessionId, model);
          this.loadSessionModel(sessionId);
        }
      }
    },
    focusChatInput() {
      // If messages exist, the floating input is visible—focus it
      if (this.$refs.floatingChatInput) {
        this.$refs.floatingChatInput.focus();
        return
      }
      // Otherwise the EmptyState input is visible—focus through that component
      if (this.$refs.emptyState) {
        this.$refs.emptyState.focusInput();
      }
    },
    /** Handle stop/abort button press. */
    async onStop() {
      const sid = this.sessionsStore.currentSessionId;
      if (sid) {
        await this.chatStore.abortStream(sid);
      }
    },
    /** Reset reconnecting-banner debounce timer. */
    _resetBannerDebounce() {
      this._bannerEligible = false;
      if (this._bannerTimer) {
        clearTimeout(this._bannerTimer);
        this._bannerTimer = null;
      }
    },
    /** Start polling for active sessions (for reload resilience). */
    startActiveSessionPolling() {
      this.stopActiveSessionPolling();
      this._activeSessionTimer = setInterval(() => {
        this.chatStore.fetchActiveSessions();
      }, 3000);
      // Also fetch immediately
      this.chatStore.fetchActiveSessions();
    },
    /** Stop polling for active sessions. */
    stopActiveSessionPolling() {
      if (this._activeSessionTimer) {
        clearInterval(this._activeSessionTimer);
        this._activeSessionTimer = null;
      }
    },
  },
  computed: {
    /** Per-session streaming state for the currently viewed session. */
    currentStream() {
      const sid = this.sessionsStore.currentSessionId;
      return this.chatStore.getStreamState(sid);
    },
    showReconnectingBanner() {
      const sid = this.sessionsStore.currentSessionId;
      if (!sid) return false;
      const state = this.chatStore.getStreamState(sid);
      if (state.sending) return false;
      // Don't show banner if we just finished a stream locally (5s window).
      if (this.chatStore.locallyCompletedSessions.has(sid)) return false;
      // 3s debounce: only show after the session has been active without
      // a local stream for at least 3 seconds. This handles page reloads
      // where the backend still reports the session as active.
      if (!this._bannerEligible) {
        if (this.chatStore.isSessionActive(sid)) {
          if (!this._bannerTimer) {
            this._bannerTimer = setTimeout(() => {
              this._bannerEligible = true
              this._bannerTimer = null
            }, 3000)
          }
        } else {
          // No longer active — cancel pending timer
          if (this._bannerTimer) {
            clearTimeout(this._bannerTimer)
            this._bannerTimer = null
          }
        }
        return false
      }
      return this.chatStore.isSessionActive(sid);
    },  // <-- keep comma here
  },
};
</script>
