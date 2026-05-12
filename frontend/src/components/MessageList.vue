<template>
  <div class="max-w-[800px] mx-auto px-4 pt-6 pb-28 space-y-5">
    <template v-for="(g, gi) in displayGroups" :key="gi">
      <!-- User or System or Assistant message -->
      <MessageBubble v-if="g.type === 'message'" :message="g.msg" />

      <!-- Merged tool chain (consecutive tool-only messages) -->
      <div v-if="g.type === 'toolchain'" class="flex justify-start -mt-3 mb-2">
        <div class="max-w-[85%]">
          <ToolChain :tool-calls="g.tool_calls" />
        </div>
      </div>
    </template>

    <!-- Streaming / thinking indicator -->
    <StreamingMessage
      :text="streamingMsg"
      :status="status"
      :status-detail="statusDetail"
      :tool-text="streamingTool"
    />

    <!-- Error -->
    <div v-if="error" class="text-[#f85149] text-xs text-center p-2">{{ error }}</div>
  </div>
</template>

<script>
import MessageBubble from './MessageBubble.vue'
import ToolChain from './ToolChain.vue'
import StreamingMessage from './StreamingMessage.vue'

export default {
  components: { MessageBubble, ToolChain, StreamingMessage },
  props: {
    messages: { type: Array, required: true },
    streamingMsg: { type: String, default: '' },
    streamingTool: { type: String, default: '' },
    status: { type: String, default: '' },
    statusDetail: { type: String, default: '' },
    error: { type: String, default: '' },
    showSystemMessages: { type: Boolean, default: false },
  },
  computed: {
    /** Filter chat-friendly messages, then group consecutive tool-only messages. */
    displayGroups() {
      const filtered = this.messages.filter((m) => {
        if (m.role !== 'user' && m.role !== 'assistant') return false
        // Use source field when available, fall back to content patterns
        if (m.source === 'system' && !this.showSystemMessages) return false
        if (!m.source && this._isSystemMsg(m) && !this.showSystemMessages) return false
        return true
      })

      const groups = []
      for (const m of filtered) {
        const isToolOnly =
          m.role === 'assistant' &&
          (!m.content || !m.content.trim()) &&
          m.tool_calls?.length
        if (isToolOnly) {
          const last = groups[groups.length - 1]
          if (last && last.type === 'toolchain') {
            last.tool_calls.push(...m.tool_calls)
          } else {
            groups.push({ type: 'toolchain', tool_calls: [...m.tool_calls] })
          }
        } else {
          groups.push({ type: 'message', msg: m })
        }
      }
      return groups
    },
  },
  methods: {
    _isSystemMsg(m) {
      if (!m || !m.content) return false
      if (m.source === 'system') return true
      if (m.source === 'user') return false
      const c = m.content.trim()
      return (
        c.startsWith('[IMPORTANT:') ||
        c.startsWith('Review the conversation above') ||
        c.startsWith('Review the conversation above and consider') ||
        c.startsWith('System:') ||
        c === '[SILENT]'
      )
    },
  },
}
</script>
