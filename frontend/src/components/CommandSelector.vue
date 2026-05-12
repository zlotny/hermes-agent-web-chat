<template>
  <!-- Fixed-position overlay to escape parent pointer-events containers -->
  <div
    v-if="show"
    class="fixed inset-0 z-[9999]"
    @mousedown="close"
    @mousedown.self="close"
  >
    <!-- Popup anchored above the input -->
    <div
      :style="popupStyle"
      class="absolute w-[380px] max-h-[min(50vh,420px)] bg-surface border border-border/80 rounded-xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden animate-dropdown-in"
      @mousedown.stop
      @click.stop
    >
      <!-- Header with count -->
      <div
        class="px-3 py-2 border-b border-border/50 text-xs font-semibold text-muted flex items-center justify-between flex-shrink-0"
      >
        <span>Commands</span>
        <span class="font-normal text-muted/60">{{ filteredCommands.length }} available</span>
      </div>

      <!-- Loading -->
      <div
        v-if="loading"
        class="flex items-center justify-center py-8 text-xs text-muted"
      >
        <svg
          class="animate-spin h-4 w-4 mr-2"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Loading commands…
      </div>

      <!-- Empty state -->
      <div
        v-else-if="filteredCommands.length === 0"
        class="flex items-center justify-center py-8 text-xs text-muted/60"
      >
        No matching commands
      </div>

      <!-- Command list grouped by category -->
      <div
        v-else
        ref="listRef"
        class="overflow-y-auto flex-1 py-1"
      >
        <template v-for="group in groupedCommands" :key="group.category">
          <!-- Category header -->
          <div
            class="sticky top-0 z-10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted/50 bg-surface/95 backdrop-blur-sm"
          >
            {{ group.category }}
          </div>

          <!-- Command items -->
          <button
            v-for="(cmd, idx) in group.items"
            :key="cmd.name"
            :ref="(el) => { if (el) itemRefs[idx] = el }"
            :class="[
              'w-full flex items-start gap-2 px-3 py-2 text-left transition-colors cursor-pointer border-0',
              globalIndex(group, idx) === selectedIndex
                ? 'bg-accent/10 text-default'
                : 'hover:bg-hover-bg text-default'
            ]"
            @mousedown.prevent="selectCommand(cmd)"
            @mouseenter="onMouseEnter(group, idx)"
          >
            <!-- Command name -->
            <span
              :class="[
                'font-mono text-sm flex-shrink-0 min-w-[80px]',
                globalIndex(group, idx) === selectedIndex ? 'text-accent' : 'text-default'
              ]"
            >
              /{{ cmd.name }}
            </span>
            <!-- Description + args hint -->
            <span class="flex flex-col min-w-0 text-xs leading-tight gap-0.5">
              <span class="truncate text-muted">{{ cmd.description }}</span>
              <span v-if="cmd.args_hint" class="text-muted/40 font-mono text-[10px] truncate">
                {{ cmd.args_hint }}
              </span>
            </span>
            <!-- Aliases badge -->
            <span
              v-if="cmd.aliases && cmd.aliases.length"
              class="flex-shrink-0 ml-auto text-[10px] text-muted/40 font-mono mt-0.5"
            >
              {{ cmd.aliases.slice(0, 2).map(a => '/' + a).join(', ') }}
            </span>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick } from 'vue'

export default {
  props: {
    show: { type: Boolean, default: false },
    commands: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    filter: { type: String, default: '' },
    selectedIndex: { type: Number, default: 0 },
    /** Element to anchor the popup above */
    anchorEl: { type: Object, default: null },
  },
  emits: ['close', 'select', 'update:selectedIndex'],
  setup(props, { emit }) {
    const listRef = ref(null)
    const itemRefs = ref({})

    // ── Filtered commands ─────────────────────────────────────────────
    const filteredCommands = computed(() => {
      if (!props.commands.length) return []
      const q = (props.filter || '').replace(/^[/\s]+/, '').toLowerCase()
      if (!q) return props.commands
      const seen = new Set()
      const results = []
      for (const cmd of props.commands) {
        if (seen.has(cmd.name)) continue
        const names = [cmd.name, ...(cmd.aliases || [])]
        if (names.some(n => n.toLowerCase().startsWith(q))) {
          results.push(cmd)
          seen.add(cmd.name)
        }
      }
      return results
    })

    // ── Group by category ──────────────────────────────────────────────
    const groupedCommands = computed(() => {
      const groups = {}
      for (const cmd of filteredCommands.value) {
        const cat = cmd.category || 'Other'
        if (!groups[cat]) groups[cat] = { category: cat, items: [] }
        groups[cat].items.push(cmd)
      }
      // Return in order of first appearance (preserves COMMAND_REGISTRY order)
      const seenCats = new Set()
      const ordered = []
      for (const cmd of filteredCommands.value) {
        const cat = cmd.category || 'Other'
        if (!seenCats.has(cat) && groups[cat]) {
          ordered.push(groups[cat])
          seenCats.add(cat)
        }
      }
      return ordered
    })

    // ── Map global index across groups ─────────────────────────────────
    function globalIndex(group, localIdx) {
      let idx = 0
      for (const g of groupedCommands.value) {
        if (g === group) return idx + localIdx
        idx += g.items.length
      }
      return localIdx
    }

    // ── Popup positioning ──────────────────────────────────────────────
    const popupStyle = computed(() => {
      const style = {
        left: '0px',
        bottom: '100%',
        marginBottom: '8px',
      }
      if (props.anchorEl) {
        const rect = props.anchorEl.getBoundingClientRect()
        style.left = `${Math.max(4, rect.left + 4)}px`
        style.bottom = `${window.innerHeight - rect.top + 8}px`
        style.position = 'fixed'
      }
      return style
    })

    // ── Select a command ───────────────────────────────────────────────
    function selectCommand(cmd) {
      emit('select', cmd)
      emit('close')
    }

    function close() {
      emit('close')
    }

    function onMouseEnter(group, localIdx) {
      const idx = globalIndex(group, localIdx)
      emit('update:selectedIndex', idx)
    }

    // ── Scroll selected item into view ─────────────────────────────────
    watch(
      () => props.selectedIndex,
      (idx) => {
        if (idx < 0) return
        nextTick(() => {
          const buttons = listRef.value?.querySelectorAll('button')
          if (buttons && buttons[idx]) {
            buttons[idx].scrollIntoView({ block: 'nearest' })
          }
        })
      }
    )

    return {
      listRef,
      itemRefs,
      filteredCommands,
      groupedCommands,
      globalIndex,
      popupStyle,
      selectCommand,
      close,
      onMouseEnter,
    }
  },
}
</script>

<style scoped>
.animate-dropdown-in {
  animation: dropdownIn 0.12s ease-out;
}

@keyframes dropdownIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
