<template>
  <div
    @click="$emit('select')"
    :class="[
      'p-2.5 rounded-md cursor-pointer text-xs transition-colors',
      isActive
        ? 'bg-[#1c2333] border-l-[3px] border-accent'
        : 'hover:bg-[#1c2333]',
    ]"
  >
    <div class="truncate text-[13px] mb-0.5 flex items-center gap-1.5">
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
    <div class="flex items-center gap-1.5 text-muted text-[11px] ml-[22px]">
      <span>{{ session.message_count }} msgs</span>
      <span
        v-if="session.model"
        class="bg-[#0d1117] border border-border rounded px-1 text-[10px]"
      >
        {{ shortModel(session.model) }}
      </span>
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
      return m ? (m.split('/').pop() || m) : ''
    },
  },
}
</script>
