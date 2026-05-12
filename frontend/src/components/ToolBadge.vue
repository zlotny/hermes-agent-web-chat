<template>
  <div class="group relative inline-flex">
    <span
      class="text-[11px] bg-hover-bg border border-border rounded-md px-2 py-0.5 text-muted cursor-default whitespace-nowrap transition-colors group-hover:border-accent/40 group-hover:text-default"
    >
      <span class="text-muted/60">{{ toolName }}</span>
      <span v-if="argPreview" class="text-muted/40 ml-1">{{ argPreview }}</span>
    </span>
    <div
      class="absolute bottom-full left-0 mb-2 w-72 max-w-[calc(100vw-280px-4rem)] p-3 rounded-lg bg-app-bg border border-border shadow-2xl shadow-black/40 z-50 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity duration-150 text-xs leading-relaxed max-h-60 overflow-y-auto"
    >
      <div class="font-semibold text-accent mb-1 text-[11px]">{{ toolName }}</div>
      <div v-if="argsStr" class="text-muted mb-2">
        <pre class="!bg-transparent !border-0 !p-0 !m-0 text-[10px] leading-relaxed">{{ prettyArgs }}</pre>
      </div>
      <div class="text-muted/60 text-[10px] italic">Tool call</div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    toolCall: { type: Object, required: true },
  },
  computed: {
    toolName() {
      return this.toolCall.function?.name || this.toolCall.name || 'tool'
    },
    argsStr() {
      return this.toolCall.function?.arguments || ''
    },
    argPreview() {
      try {
        const args = JSON.parse(this.argsStr || '{}')
        const val = Object.values(args).find(
          (v) => typeof v === 'string' && v.length < 40
        )
        return val || ''
      } catch {
        return ''
      }
    },
    prettyArgs() {
      try {
        return JSON.stringify(JSON.parse(this.argsStr), null, 2)
      } catch {
        return this.argsStr || ''
      }
    },
  },
}
</script>
