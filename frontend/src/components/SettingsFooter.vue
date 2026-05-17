<template>
  <div class="border-t border-border p-3 relative">
    <button
      @click="settingsOpen = !settingsOpen"
      class="flex items-center gap-2 text-xs text-muted hover:text-default transition-colors w-full p-1.5 hover:bg-hover-bg"
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
      ref="settingsPanelRef"
      class="absolute bottom-full left-3 mb-1 w-[240px] bg-panel border border-border shadow-xl shadow-black/30 p-2 z-50"
    >
      <!-- Theme selector -->
      <div class="px-3 py-2">
        <div class="text-[10px] text-muted/60 uppercase tracking-wider mb-2 font-semibold">Theme</div>
        <div class="flex border border-border overflow-hidden">
          <button
            v-for="opt in themeOptions"
            :key="opt.value"
            @click="settingsStore.setTheme(opt.value)"
            :title="opt.label"
            :class="[
              'flex-1 flex items-center justify-center gap-1 py-1.5 text-xs transition-colors',
              settingsStore.theme === opt.value
                ? 'bg-accent text-white'
                : 'bg-app-bg text-muted hover:text-default hover:bg-hover-bg'
            ]"
          >
            <span v-html="opt.icon"></span>
            <span class="hidden sm:inline">{{ opt.label }}</span>
          </button>
        </div>
      </div>

      <!-- Divider -->
      <div class="border-t border-border mx-3"></div>

      <!-- Show crons toggle -->
      <div
        class="flex items-center justify-between px-3 py-2 hover:bg-hover-bg cursor-pointer transition-colors"
        @click="sessionsStore.showCrons = !sessionsStore.showCrons"
      >
        <span class="text-xs">Show crons</span>
        <div
          :class="['w-8 h-4 rounded-full transition-colors relative', sessionsStore.showCrons ? 'bg-accent' : 'bg-border']"
        >
          <div
            :class="['w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform shadow-sm', sessionsStore.showCrons ? 'translate-x-4' : 'translate-x-0.5']"
          ></div>
        </div>
      </div>

      <!-- Divider -->
      <div class="border-t border-border mx-3"></div>

      <!-- Edit core files -->
      <div
        class="flex items-center justify-between px-3 py-2 hover:bg-hover-bg cursor-pointer transition-colors"
        @click="editorOpen = true"
      >
        <span class="text-xs">Edit core files</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="text-muted/50"
        >
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </div>
    </div>

    <CoreFileEditor :show="editorOpen" @close="editorOpen = false" />
  </div>
</template>

<script>
import { useSessionsStore } from '../stores/sessions'
import { useSettingsStore } from '../stores/settings'
import CoreFileEditor from './CoreFileEditor.vue'

export default {
  components: { CoreFileEditor },
  setup() {
    return { sessionsStore: useSessionsStore(), settingsStore: useSettingsStore() }
  },
  data() {
    return {
      settingsOpen: false,
      editorOpen: false,
      themeOptions: [
        {
          value: 'light',
          label: 'Light',
          icon: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
        },
        {
          value: 'dark',
          label: 'Dark',
          icon: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
        },
        {
          value: 'system',
          label: 'Sys',
          icon: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
        },
      ],
    }
  },
  mounted() {
    document.addEventListener('click', this.handleClickOutside)
  },
  beforeUnmount() {
    document.removeEventListener('click', this.handleClickOutside)
  },
  methods: {
    handleClickOutside(e) {
      if (this.settingsOpen && this.$el && !this.$el.contains(e.target)) {
        this.settingsOpen = false
      }
    },
  },
}
</script>
