<template>
  <!-- User message (real) -->
  <div
    v-if="message.role === 'user' && message.source !== 'system' && !isSystemMsg"
    class="flex justify-end group"
  >
    <div class="max-w-[75%] relative">
      <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 text-right">You</div>
      <div class="bg-accent/10 border border-accent/20 px-4 py-3 rounded-2xl rounded-br-md text-sm leading-relaxed whitespace-pre-wrap break-words">
        {{ message.content }}
      </div>
      <!-- Copy button -->
      <button
        title="Copy message"
        @click="copyContent"
        class="absolute -top-0.5 -right-9 p-1 rounded-md text-muted/40 hover:text-[#c9d1d9] hover:bg-[#1c2333] transition-all opacity-0 group-hover:opacity-100"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      </button>
    </div>
  </div>

  <!-- System message -->
  <div
    v-if="message.role === 'user' && (message.source === 'system' || isSystemMsg)"
    class="flex justify-center"
  >
    <div class="max-w-[90%]">
      <div class="text-[11px] font-semibold text-[#d29922]/80 uppercase tracking-wider mb-1 text-center">System</div>
      <div class="bg-[#d29922]/5 border border-[#d29922]/20 px-4 py-2.5 rounded-xl text-xs leading-relaxed whitespace-pre-wrap break-words text-[#d29922]/70">
        {{ message.content }}
      </div>
    </div>
  </div>

  <!-- Assistant message -->
  <div v-if="message.role === 'assistant'" class="flex justify-start min-w-0 group">
    <div class="max-w-[85%] min-w-0 relative">
      <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 flex items-center gap-1.5">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent"><path d="M12 2a10 10 0 0 1 10 10c0 5-4 8-10 8-2.5 0-4.8-.8-6.7-2.2L2 22l1.8-4.5A9.8 9.8 0 0 1 2 12 10 10 0 0 1 12 2z"/></svg>
        Hermes
      </div>
      <div class="px-1 text-sm leading-relaxed whitespace-pre-wrap break-words" v-html="renderedContent"></div>
      <!-- Tool calls within this message -->
      <div v-if="message.tool_calls && message.tool_calls.length" class="mt-2">
        <ToolChain :tool-calls="message.tool_calls" />
      </div>
      <!-- Copy button -->
      <button
        title="Copy message"
        @click="copyContent"
        class="absolute top-0 -right-9 p-1 rounded-md text-muted/40 hover:text-[#c9d1d9] hover:bg-[#1c2333] transition-all opacity-0 group-hover:opacity-100"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      </button>
    </div>
  </div>
</template>

<script>
import ToolChain from './ToolChain.vue'

export default {
  components: { ToolChain },
  props: {
    message: { type: Object, required: true },
  },
  computed: {
    isSystemMsg() {
      if (!this.message || !this.message.content) return false
      if (this.message.source === 'system') return true
      if (this.message.source === 'user') return false
      const c = this.message.content.trim()
      return (
        c.startsWith('[IMPORTANT:') ||
        c.startsWith('Review the conversation above') ||
        c.startsWith('Review the conversation above and consider') ||
        c.startsWith('System:') ||
        c === '[SILENT]'
      )
    },
    renderedContent() {
      const t = this.message.content || ''
      if (!t) return ''
      let h = t.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
      h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      h = h.replace(/\n\n/g, '</p><p>')
      h = h.replace(/\n/g, '<br>')
      return '<p>' + h + '</p>'
    },
  },
  methods: {
    async copyContent() {
      try {
        await navigator.clipboard.writeText(this.message.content || '')
      } catch {
        // clipboard not available
      }
    },
  },
}
</script>
