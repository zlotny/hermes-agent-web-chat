<template>
  <div class="border-t border-border p-3 relative">
    <button
      @click="settingsOpen = !settingsOpen"
      class="flex items-center gap-2 text-xs text-muted hover:text-[#c9d1d9] transition-colors w-full p-1.5 rounded-md hover:bg-[#1c2333]"
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
        <circle cx="12" cy="12" r="3" />
        <path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
        />
      </svg>
      Settings
    </button>

    <div
      v-if="settingsOpen"
      class="absolute bottom-full left-3 mb-1 w-[220px] bg-surface border border-border rounded-lg shadow-xl shadow-black/30 p-2 z-50"
    >
      <div
        class="flex items-center justify-between px-3 py-2 rounded-md hover:bg-[#1c2333] cursor-pointer transition-colors"
        @click="sessionsStore.showCrons = !sessionsStore.showCrons; settingsOpen = false"
      >
        <span class="text-xs">Show crons</span>
        <div
          :class="['w-8 h-4 rounded-full transition-colors relative', sessionsStore.showCrons ? 'bg-accent' : 'bg-[#30363d]']"
        >
          <div
            :class="['w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform', sessionsStore.showCrons ? 'translate-x-4' : 'translate-x-0.5']"
          ></div>
        </div>
      </div>
      <div
        class="flex items-center justify-between px-3 py-2 rounded-md hover:bg-[#1c2333] cursor-pointer transition-colors"
        @click="sessionsStore.showSystemMessages = !sessionsStore.showSystemMessages; settingsOpen = false"
      >
        <span class="text-xs">System messages</span>
        <div
          :class="['w-8 h-4 rounded-full transition-colors relative', sessionsStore.showSystemMessages ? 'bg-accent' : 'bg-[#30363d]']"
        >
          <div
            :class="['w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform', sessionsStore.showSystemMessages ? 'translate-x-4' : 'translate-x-0.5']"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useSessionsStore } from '../stores/sessions'

export default {
  setup() {
    return { sessionsStore: useSessionsStore() }
  },
  data() {
    return { settingsOpen: false }
  },
}
</script>
