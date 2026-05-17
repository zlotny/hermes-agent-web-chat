<template>
  <div class="flex flex-col gap-1.5 relative">
    <!-- Model selector row -->
    <div class="flex items-center px-1">
      <ModelSelector
        :current-model="currentModel"
        :providers="providers"
        :loading="providersLoading"
        @select-model="onModelSelect"
        @closed="focus"
      />
    </div>
    <div
      class="flex gap-1.5 bg-surface/95 backdrop-blur-sm border border-border/80 p-2 shadow-lg shadow-black/50 items-end"
    >
      <!-- Command button (tiny, left side) -->
      <button
        @click="toggleCommandSelector"
        class="self-center flex-shrink-0 w-7 h-7 flex items-center justify-center text-muted/50 hover:text-accent hover:bg-hover-bg transition-colors cursor-pointer border-0"
        title="Show commands (type /)"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      </button>

      <textarea
        ref="textareaRef"
        v-model="text"
        rows="1"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="onEnter"
        @keydown="onKeydown"
        @input="onInput"
        @compositionstart="composition = true"
        @compositionend="composition = false"
        class="flex-1 bg-transparent text-default px-2 py-2.5 text-sm outline-none resize-none min-h-[36px] max-h-[200px] leading-relaxed placeholder:text-muted/60"
      ></textarea>

      <button
        v-if="sending"
        @click="$emit('stop')"
        class="self-center flex-shrink-0 p-2 bg-[#d97706] text-white hover:bg-[#b45309] transition-colors shadow-lg shadow-orange-900/30"
        title="Stop agent"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>
      <button
        v-else
        @click="onSend"
        :disabled="disabled || !text.trim()"
        class="self-center flex-shrink-0 p-2 bg-accent text-white hover:bg-[#c9a04a] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>

    <!-- Command selector popup, anchored above the input area -->
    <CommandSelector
      :show="commandSelectorOpen"
      :commands="availableCommands"
      :loading="commandsLoading"
      :filter="commandFilter"
      :selected-index="commandSelectedIndex"
      :anchor-el="$el?.querySelector('.flex.gap-1\\.5') || null"
      @close="closeCommandSelector"
      @select="onCommandSelected"
      @update:selected-index="commandSelectedIndex = $event"
    />
  </div>
</template>

<script>
import ModelSelector from "./ModelSelector.vue";
import CommandSelector from "./CommandSelector.vue";
import { looksLikeFilePath } from "../utils/helpers";

export default {
  components: { ModelSelector, CommandSelector },
  props: {
    modelValue: { type: String, default: "" },
    placeholder: { type: String, default: "Type a message..." },
    disabled: { type: Boolean, default: false },
    sending: { type: Boolean, default: false },
    currentModel: { type: String, default: "" },
    providers: { type: Array, default: () => [] },
    providersLoading: { type: Boolean, default: false },
    availableCommands: { type: Array, default: () => [] },
    commandsLoading: { type: Boolean, default: false },
  },
  emits: ["update:modelValue", "send", "select-model", "stop", "closed"],
  data() {
    return {
      commandSelectorOpen: false,
      commandSelectedIndex: 0,
      composition: false,
      _suppressReopen: false,
    }
  },
  computed: {
    text: {
      get() {
        return this.modelValue;
      },
      set(v) {
        this.$emit("update:modelValue", v);
      },
    },
    /** The text after "/" when a slash command is being typed */
    commandFilter() {
      if (!this.commandSelectorOpen) return ''
      const t = this.text || ''
      if (!t.startsWith('/')) return ''
      // Only act on the first word — if there's a space, the user is
      // done typing the command name and is entering arguments.
      if (t.includes(' ')) return ''
      // Only treat as command if no additional "/" in the first word
      const firstWord = t.split(/\s+/)[0] || ''
      if (firstWord.includes('/', 1)) return ''  // file path like /Users/foo
      return firstWord.slice(1)  // return what's after /
    },
    /** Filtered commands matching the current partial input */
    _filteredCommands() {
      const q = (this.commandFilter || '').toLowerCase()
      if (!q) return this.availableCommands
      const seen = new Set()
      const results = []
      for (const cmd of this.availableCommands) {
        if (seen.has(cmd.name)) continue
        const names = [cmd.name, ...(cmd.aliases || [])]
        if (names.some(n => n.toLowerCase().startsWith(q))) {
          results.push(cmd)
          seen.add(cmd.name)
        }
      }
      return results
    },
  },
  watch: {
    text(val, oldVal) {
      if (this.composition) return
      // If the filter changed (text after / changed), reset selection
      const oldFilter = this._getFilter(oldVal)
      const newFilter = this._getFilter(val)
      if (oldFilter !== newFilter) {
        this.commandSelectedIndex = 0
      }
      // Don't detect if we're suppressing reopen (command was just selected)
      if (this._suppressReopen) return
      this.detectSlashCommand(val, oldVal)
    },
  },
  methods: {
    // ── Slash command detection ──────────────────────────────────────
    detectSlashCommand(val, oldVal) {
      if (this.commandSelectorOpen) {
        // If user deleted the leading /, close the selector
        if (!val.startsWith('/') || this._looksLikeFilePath(val)) {
          this.commandSelectorOpen = false
          return
        }
        // If there's a space, user is done typing command name — close
        if (val.includes(' ')) {
          this.commandSelectorOpen = false
          return
        }
        return
      }
      // Open when user types / at the start (and it's not a file path)
      if (
        val.startsWith('/') &&
        !this._looksLikeFilePath(val) &&
        !val.includes(' ') &&
        val.length > (oldVal || '').length
      ) {
        this.commandSelectorOpen = true
      }
    },

    /** Check if text looks like a file path rather than a slash command */
    _looksLikeFilePath(text) {
      return looksLikeFilePath(text)
    },

    // ── Command selector actions ─────────────────────────────────────
    toggleCommandSelector() {
      if (this.commandSelectorOpen) {
        this.closeCommandSelector()
      } else {
        this.commandSelectorOpen = true
        // Insert / at the start if the input is empty
        if (!this.text.trim()) {
          this.text = '/'
        }
        this.focus()
      }
    },

    closeCommandSelector() {
      this.commandSelectorOpen = false
      this.focus()
    },

    _getFilter(text) {
      const t = text || ''
      if (!t.startsWith('/')) return ''
      const firstWord = t.split(/\s+/)[0] || ''
      if (firstWord.includes('/', 1)) return ''
      return firstWord.slice(1)
    },

    onCommandSelected(cmd) {
      // Close the selector BEFORE changing text, so the watch doesn't re-open it
      this.commandSelectorOpen = false
      // Suppress reopen for one cycle — the new text starts with / and would
      // trigger detectSlashCommand again
      this._suppressReopen = true
      this.text = '/' + cmd.name + ' '
      this.$nextTick(() => { this._suppressReopen = false })
      this.resize()
      this.focus()
    },

    /**
     * Get whatever comes before the cursor that looks like a partial command.
     * Handles both bare "/" and "/partial".
     */
    _getCommandPrefix() {
      const t = this.text || ''
      if (!t.startsWith('/')) return ''
      const firstWord = t.split(/\s+/)[0] || ''
      return firstWord
    },

    // ── Input handlers ───────────────────────────────────────────────
    onInput() {
      this.resize()
    },

    onEnter() {
      if (this.commandSelectorOpen) {
        // Select the currently highlighted command
        const filtered = this._filteredCommands
        const cmd = filtered[this.commandSelectedIndex]
        if (cmd) {
          this.onCommandSelected(cmd)
        }
        return
      }
      this.$emit('send')
      // Reset textarea height after the model value gets cleared on send
      this.$nextTick(() => {
        const el = this.$refs.textareaRef;
        if (el) {
          el.style.height = "auto";
        }
      })
    },

    onKeydown(e) {
      if (this.commandSelectorOpen) {
        const filtered = this._filteredCommands
        const total = filtered.length
        if (total === 0) {
          if (e.key === 'Escape') {
            e.preventDefault()
            this.closeCommandSelector()
          }
          return
        }
        if (e.key === 'ArrowDown') {
          e.preventDefault()
          this.commandSelectedIndex = (this.commandSelectedIndex + 1) % total
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          this.commandSelectedIndex = (this.commandSelectedIndex - 1 + total) % total
        } else if (e.key === 'Enter') {
          e.preventDefault()
          const cmd = filtered[this.commandSelectedIndex]
          if (cmd) this.onCommandSelected(cmd)
        } else if (e.key === 'Escape') {
          e.preventDefault()
          this.closeCommandSelector()
        }
        return
      }
    },

    onSend() {
      if (this.commandSelectorOpen) {
        this.commandSelectorOpen = false
      }
      this.$emit('send')
      this.$nextTick(() => {
        const el = this.$refs.textareaRef;
        if (el) el.style.height = "auto";
      })
    },

    // ── Existing methods ─────────────────────────────────────────────
    resize() {
      const el = this.$refs.textareaRef;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 200) + "px";
    },
    focus() {
      this.$nextTick(() => this.$refs.textareaRef?.focus());
    },
    onModelSelect(model) {
      this.$emit("select-model", model);
    },
  },
  mounted() {
    // Pre-fetch commands if not already loaded
    if (this.availableCommands.length === 0 && !this.commandsLoading) {
      // Parent should handle fetching, but we can try if we have a store ref
    }
  },
};
</script>
