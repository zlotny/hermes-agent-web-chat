<template>
  <div
    @click="$emit('select')"
    :class="[
      'p-2.5 cursor-pointer text-xs transition-all duration-200 relative overflow-hidden group',
      isActive
        ? 'bg-hover-bg rainbow-active'
        : 'hover:bg-hover-bg',
    ]"
  >
    <div class="text-[13px] mb-0.5 flex items-center gap-1.5 relative z-[1] min-w-0">
      <!-- Active pulsing dot -->
      <span
        v-if="agentActive"
        class="w-2 h-2 rounded-full bg-green-500 animate-pulse flex-shrink-0"
        title="Agent is generating..."
      ></span>
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="shrink-0 text-muted"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
      <span v-if="isUntitled" class="italic text-muted/60 truncate">New session…</span>
      <span v-else class="truncate group-hover:pr-5">{{ session.title }}</span>
      <!-- Delete button on hover, top-right of the card -->
      <button
        @click.stop="$emit('delete')"
        class="absolute -right-0.5 -top-0.5 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-muted/40 hover:text-red-500 hover:bg-red-500/10"
        title="Delete session"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </div>
    <div class="flex items-center justify-between text-muted text-[11px] ml-[22px] relative z-[1]">
      <!-- Default state: model + message count -->
      <span class="transition-opacity duration-200 flex items-center gap-1.5 min-w-0" :class="session.last_updated ? 'group-hover:opacity-0' : ''">
        <template v-if="session.model">
          <span class="bg-app-bg border border-border px-1 text-[10px] max-w-[140px] truncate">{{ shortModel(session.model) }}</span>
          <span>{{ session.message_count }} msgs</span>
        </template>
        <span v-else>{{ session.message_count }} msgs</span>
      </span>
      <!-- Hover state: full date -->
      <span v-if="session.last_updated" class="absolute right-0 transition-opacity duration-200 opacity-0 group-hover:opacity-100 whitespace-nowrap text-[10px]">{{ formatDate(session.last_updated) }}</span>
    </div>
  </div>
</template>

<script>
import { shortModel, formatMsgTime } from '../utils/helpers'

export default {
  props: {
    session: { type: Object, required: true },
    isActive: { type: Boolean, default: false },
    agentActive: { type: Boolean, default: false },
  },
  emits: ['select', 'delete'],
  computed: {
    /** Detect sessions whose title is still a raw Hermes auto-generated ID
     *  (YYYYMMDD_HHMMSS_XXXXXX format, 27 chars with underscores) or empty. */
    isUntitled() {
      const t = this.session?.title || ''
      if (!t) return true
      // Hermes auto-generated IDs look like 20260513_123456_abcdef
      // They're 27 chars with underscores in positions 8 and 15
      return /^\d{8}_\d{6}_[a-z0-9]{6}$/.test(t)
    },
  },
  methods: {
    shortModel(m) {
      return shortModel(m)
    },
    formatDate(iso) {
      return formatMsgTime(iso)
    },
  },
}
</script>
