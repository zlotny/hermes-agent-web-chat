<template>
  <aside
    :class="[
      'bg-surface border-r border-border flex flex-col overflow-hidden transition-all duration-300 z-30',
      isDesktop ? 'relative' : 'fixed left-0 top-0 h-full',
      open ? (isDesktop ? 'w-[280px] min-w-[280px]' : 'w-[280px]') : 'w-0 min-w-0 border-0',
    ]"
  >
    <div v-if="open" class="flex flex-col h-full min-w-[280px]">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-4 border-b border-border">
        <h2 class="text-sm font-semibold tracking-wide">Sessions</h2>
        <div class="flex items-center gap-1">
          <!-- Only show + when there's an active chat session -->
          <button
            v-if="sessionsStore.currentSessionId || sessionsStore.allMessages.length"
            @click="newChat"
            class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted hover:text-[#c9d1d9] transition-colors"
            title="New chat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <button
            @click="sessionsStore.loadSessions()"
            class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted hover:text-[#c9d1d9] transition-colors"
            title="Refresh sessions"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          </button>
          <button
            @click="$emit('close')"
            class="p-1.5 rounded-md hover:bg-[#1c2333] text-muted hover:text-[#c9d1d9] transition-colors"
            title="Collapse sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
        </div>
      </div>

      <!-- Session list -->
      <div class="flex-1 overflow-y-auto p-2 space-y-0.5">
        <div v-if="sessionsStore.loadingSessions" class="space-y-3 px-2 pt-2">
          <div v-for="n in 8" :key="n" class="space-y-1.5">
            <div class="skel h-3 w-[85%]"></div>
            <div class="skel h-2 w-[45%]"></div>
          </div>
        </div>
        <div
          v-else-if="sessionsStore.sidebarError"
          class="text-[#f85149] text-xs p-2"
        >
          {{ sessionsStore.sidebarError }}
        </div>
        <template v-else-if="sessionsStore.filteredSessions.length > 0">
          <SessionItem
            v-for="s in sessionsStore.visibleSessions"
            :key="s.id"
            :session="s"
            :is-active="s.id === sessionsStore.currentSessionId"
            :agent-active="chatStore.isSessionActive(s.id)"
            @select="loadSession(s.id)"
          />
          <button
            v-if="!sessionsStore.showAll && sessionsStore.totalSessions > sessionsStore.visibleSessions.length"
            @click="sessionsStore.showAllSessions()"
            class="w-full py-2 mt-1 text-xs text-muted border border-border rounded-md bg-transparent hover:border-accent hover:text-accent transition-colors"
          >
            Show all ({{ sessionsStore.totalSessions }})
          </button>
        </template>
        <div v-else class="text-muted/50 text-xs text-center py-6">
          No sessions match "{{ sessionsStore.searchQuery }}"
        </div>
      </div>

      <!-- Search + Settings -->
      <div class="border-t border-border">
        <div class="px-3 py-2">
          <div class="relative">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted/50 pointer-events-none"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input
              v-model="sessionsStore.searchQuery"
              type="text"
              placeholder="Search sessions…"
              class="w-full bg-[#0d1117] border border-border rounded-md pl-7 pr-2.5 py-1.5 text-xs text-[#c9d1d9] outline-none placeholder:text-muted/40 focus:border-accent/50 transition-colors"
            />
          </div>
        </div>
        <SettingsFooter />
      </div>
    </div>
  </aside>
</template>

<script>
import { useSessionsStore } from '../stores/sessions'
import { useChatStore } from '../stores/chat'
import SessionItem from './SessionItem.vue'
import SettingsFooter from './SettingsFooter.vue'

export default {
  components: { SessionItem, SettingsFooter },
  props: {
    open: { type: Boolean, default: true },
    isDesktop: { type: Boolean, default: true },
  },
  emits: ['close'],
  setup() {
    return { sessionsStore: useSessionsStore(), chatStore: useChatStore() }
  },
  watch: {
    'sessionsStore.searchQuery'(q) {
      // Auto-show-all when search yields no visible results — the session may be hidden
      if (q.trim() && this.sessionsStore.filteredSessions.length === 0) {
        this.sessionsStore.showAllSessions()
      }
    },
  },
  methods: {
    newChat() {
      this.sessionsStore.newChat()
      // Only close sidebar on mobile (desktop stays open for browsing)
      if (!this.isDesktop) this.$emit('close')
    },
    loadSession(id) {
      this.sessionsStore.loadSession(id)
      if (!this.isDesktop) this.$emit('close')
    },
  },
}
</script>
