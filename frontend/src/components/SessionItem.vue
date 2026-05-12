<template>
  <div
    @click="$emit('select')"
    :class="[
      'p-2.5 rounded-md cursor-pointer text-xs transition-all duration-200 relative overflow-hidden animate-slide-in group',
      isActive
        ? 'bg-hover-bg rainbow-active'
        : 'hover:bg-hover-bg',
    ]"
  >
    <div class="truncate text-[13px] mb-0.5 flex items-center gap-1.5 relative z-[1]">
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
      {{ session.title }}
    </div>
    <div class="flex items-center justify-between text-muted text-[11px] ml-[22px] relative z-[1]">
      <!-- Default state: model + message count -->
      <span class="transition-opacity duration-200 flex items-center gap-1.5 min-w-0" :class="session.last_updated ? 'group-hover:opacity-0' : ''">
        <template v-if="session.model">
          <span class="bg-app-bg border border-border rounded px-1 text-[10px] max-w-[140px] truncate">{{ shortModel(session.model) }}</span>
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
export default {
  props: {
    session: { type: Object, required: true },
    isActive: { type: Boolean, default: false },
    agentActive: { type: Boolean, default: false },
  },
  emits: ['select'],
  methods: {
    shortModel(m) {
      const name = m ? (m.split('/').pop() || m) : ''
      // Middle ellipsis: show first ~10 chars and last ~6 if name is long
      if (name.length > 20) {
        return name.slice(0, 10) + '…' + name.slice(-6)
      }
      return name
    },
    formatDate(iso) {
      if (!iso) return ''
      const d = new Date(iso)
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
  },
}
</script>
