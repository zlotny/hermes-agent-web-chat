<template>
  <div v-if="visible" class="flex justify-start">
    <div class="max-w-[85%]">
      <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 flex items-center gap-1.5">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent"><path d="M12 2a10 10 0 0 1 10 10c0 5-4 8-10 8-2.5 0-4.8-.8-6.7-2.2L2 22l1.8-4.5A9.8 9.8 0 0 1 2 12 10 10 0 0 1 12 2z"/></svg>
        Hermes
        <span v-if="status === 'sending'" class="text-[10px] font-normal text-muted/50">connecting…</span>
        <span v-if="status === 'thinking' && !text" class="text-[10px] font-normal text-muted/50">thinking</span>
      </div>

      <!-- Streaming text with blinking cursor -->
      <div v-if="text" class="px-1 text-sm leading-relaxed whitespace-pre-wrap break-words">
        <span v-html="renderedText"></span>
        <span class="inline-block w-[2px] h-[1em] bg-accent ml-0.5 animate-blink align-middle"></span>
      </div>

      <!-- Animated thinking dots (pre-tokens) -->
      <div v-if="!text && (status === 'thinking' || status === 'sending')" class="px-1 py-3">
        <div class="flex items-center gap-2">
          <div class="thinking-dots flex items-center gap-[3px]">
            <span class="w-[5px] h-[5px] rounded-full bg-accent/60 animate-pulse-dot" style="animation-delay: 0s"></span>
            <span class="w-[5px] h-[5px] rounded-full bg-accent/60 animate-pulse-dot" style="animation-delay: 0.15s"></span>
            <span class="w-[5px] h-[5px] rounded-full bg-accent/60 animate-pulse-dot" style="animation-delay: 0.3s"></span>
          </div>
          <span v-if="statusDetail" class="text-[11px] text-muted/50 italic">{{ statusDetail }}</span>
        </div>
      </div>

      <!-- Tool indicator during streaming -->
      <div v-if="toolText" class="text-muted text-xs italic mt-1 flex items-center gap-1.5">
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
        {{ toolText }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    text: { type: String, default: '' },
    status: { type: String, default: '' },
    statusDetail: { type: String, default: '' },
    toolText: { type: String, default: '' },
  },
  computed: {
    visible() {
      return !!(this.text || this.status === 'sending' || this.status === 'thinking' || this.toolText)
    },
    renderedText() {
      const t = this.text || ''
      if (!t) return ''
      let h = t.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
      h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      h = h.replace(/\n\n/g, '</p><p>')
      h = h.replace(/\n/g, '<br>')
      return '<p>' + h + '</p>'
    },
  },
}
</script>
