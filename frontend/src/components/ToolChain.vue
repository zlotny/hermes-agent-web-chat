<template>
  <div class="flex flex-wrap items-center gap-0.5">
    <template v-for="(tc, tci) in toolCalls" :key="tc.id || tc.call_id || tci">
      <span v-if="tci > 0" class="text-muted/40 text-[10px] mx-0.5">›</span>
      <ToolBadge :tool-call="tc" />
    </template>
  </div>
</template>

<script>
import ToolBadge from './ToolBadge.vue'

export default {
  components: { ToolBadge },
  props: {
    toolCalls: { type: Array, required: true },
  },
}
</script>
