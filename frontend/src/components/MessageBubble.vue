<template>
  <!-- User message (real) -->
  <div
    v-if="message.role === 'user' && message.source !== 'system' && !isSystemMsg"
    class="flex justify-end group animate-fade-in"
  >
    <div class="max-w-[75%] relative">
      <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 flex items-center justify-end gap-2">
        <span v-if="message.timestamp" class="text-[10px] font-normal normal-case text-muted/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200">{{ formatMsgTime(message.timestamp) }}</span>
        <span>You</span>
      </div>
      <div class="bg-accent/10 border border-accent/20 px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words">
        {{ message.content }}
      </div>
      <!-- Copy button -->
      <div class="absolute -top-0.5 -right-9 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        <button
          title="Copy message"
          @click="copyContent"
          class="p-1 text-muted/40 hover:text-default hover:bg-hover-bg transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        </button>
      </div>
    </div>
  </div>

  <!-- System message -->
  <div
    v-if="message.role === 'user' && (message.source === 'system' || isSystemMsg)"
    class="flex justify-center animate-fade-in"
  >
    <div class="max-w-[90%]">
      <div class="text-[11px] font-semibold text-[#d4a853]/80 uppercase tracking-wider mb-1 text-center">System</div>
      <div class="bg-[#d4a853]/5 border border-[#d4a853]/20 px-4 py-2.5 text-xs leading-relaxed whitespace-pre-wrap break-words text-[#d4a853]/70">
        {{ message.content }}
      </div>
    </div>
  </div>

  <!-- Assistant message -->
  <div v-if="message.role === 'assistant'" class="flex justify-start min-w-0 group animate-fade-in">
    <div class="max-w-[85%] min-w-0 relative">
      <div class="text-[11px] font-semibold text-muted/60 uppercase tracking-wider mb-1 flex items-center justify-between gap-2">
        <span>Hermes</span>
        <span v-if="message.timestamp" class="text-[10px] font-normal normal-case text-muted/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200">{{ formatMsgTime(message.timestamp) }}</span>
      </div>
      <div class="px-1 text-sm leading-relaxed whitespace-pre-wrap break-words" v-html="renderedContent"></div>
      <!-- Tool calls within this message -->
      <div v-if="message.tool_calls && message.tool_calls.length" class="mt-2">
        <ToolChain :tool-calls="message.tool_calls" />
      </div>
      <!-- Copy button (no longer has timestamp, it's in the header) -->
      <div class="absolute top-0 -right-9 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        <button
          title="Copy message"
          @click="copyContent"
          class="p-1 text-muted/40 hover:text-default hover:bg-hover-bg transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import ToolChain from './ToolChain.vue'
import { isSystemMsg, renderContent, formatMsgTime } from '../utils/helpers'

export default {
  components: { ToolChain },
  props: {
    message: { type: Object, required: true },
  },
  computed: {
    isSystemMsg() {
      return isSystemMsg(this.message)
    },
    renderedContent() {
      return renderContent(this.message.content)
    },
  },
  methods: {
    formatMsgTime(ts) {
      return formatMsgTime(ts)
    },
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
