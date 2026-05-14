<template>
  <div class="relative inline-flex" @mouseenter="onBadgeEnter" @mouseleave="onBadgeLeave">
    <span
      class="text-[11px] bg-hover-bg border border-border px-2 py-0.5 text-muted cursor-default whitespace-nowrap transition-colors"
      :class="open ? 'border-accent/40 text-default' : ''"
    >
      <span class="text-muted/60">{{ toolName }}</span>
      <span v-if="argPreview" class="text-muted/40 ml-1">{{ argPreview }}</span>
    </span>
    <Transition name="tooltip-fade">
      <div
        v-if="open"
        class="absolute bottom-full left-0 mb-2 w-72 max-w-[calc(100vw-280px-4rem)] p-3 bg-app-bg border border-border shadow-2xl shadow-black/40 z-50 text-xs leading-relaxed max-h-60 overflow-y-auto"
        @mouseenter="onTooltipEnter"
        @mouseleave="onTooltipLeave"
      >
        <div class="font-semibold text-accent mb-1 text-[11px]">{{ toolName }}</div>
        <div v-if="argsStr" class="text-muted mb-2">
          <pre class="!bg-transparent !border-0 !p-0 !m-0 text-[10px] leading-relaxed">{{ prettyArgs }}</pre>
        </div>
        <div class="text-muted/60 text-[10px] italic">Tool call</div>
      </div>
    </Transition>
  </div>
</template>

<script>
import { toolArgPreview, prettyJson } from '../utils/helpers'

// Module-level shared state so all ToolBadge instances coordinate:
// when one opens, any previously open one closes immediately.
let _closeOther = null

export default {
  props: {
    toolCall: { type: Object, required: true },
  },
  data() {
    return {
      open: false,
      hideTimer: null,
    }
  },
  computed: {
    toolName() {
      return this.toolCall.function?.name || this.toolCall.name || 'tool'
    },
    argsStr() {
      return this.toolCall.function?.arguments || ''
    },
    argPreview() {
      return toolArgPreview(this.toolCall)
    },
    prettyArgs() {
      return prettyJson(this.argsStr)
    },
  },
  methods: {
    _close() {
      clearTimeout(this.hideTimer)
      this.open = false
    },
    onBadgeEnter() {
      clearTimeout(this.hideTimer)
      // Immediately close whatever other tooltip was open
      if (_closeOther) _closeOther()
      _closeOther = () => this._close()
      this.open = true
    },
    onBadgeLeave() {
      this.hideTimer = setTimeout(() => {
        this.open = false
        _closeOther = null
      }, 250)
    },
    onTooltipEnter() {
      clearTimeout(this.hideTimer)
    },
    onTooltipLeave() {
      this.hideTimer = setTimeout(() => {
        this.open = false
        _closeOther = null
      }, 250)
    },
  },
  beforeUnmount() {
    clearTimeout(this.hideTimer)
  },
}
</script>

<style scoped>
.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.12s ease;
}
.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
}
</style>
