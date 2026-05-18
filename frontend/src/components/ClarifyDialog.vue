<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <!-- Backdrop -->
      <div
        class="absolute inset-0 bg-black/60 backdrop-blur-sm"
        @click="$emit('cancel')"
      ></div>

      <!-- Dialog -->
      <div
        class="relative w-full max-w-lg bg-surface border border-border shadow-2xl shadow-black/40 overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center gap-2 px-5 pt-5 pb-2">
          <span class="text-lg">❓</span>
          <h2 class="text-sm font-semibold text-default">Agent asks…</h2>
        </div>

        <!-- Question -->
        <div class="px-5 py-3">
          <p class="text-sm text-default leading-relaxed whitespace-pre-wrap">
            {{ question }}
          </p>
        </div>

        <!-- Choices buttons -->
        <div
          v-if="choices && choices.length"
          class="px-5 pb-3 flex flex-col gap-1.5"
        >
          <button
            v-for="(choice, i) in choices"
            :key="i"
            @click="selectChoice(choice)"
            class="w-full text-left px-3 py-2 text-sm border border-border/60 bg-hover-bg/30 hover:bg-accent/10 hover:border-accent/40 text-default transition-colors"
          >
            <span class="text-muted/50 mr-2">{{ i + 1 }}.</span>
            {{ choice }}
          </button>
        </div>

        <!-- "Other" call to action when choices exist -->
        <div
          v-if="choices && choices.length"
          class="px-5 pb-2"
        >
          <p class="text-xs text-muted/60">…or type your own answer below.</p>
        </div>

        <!-- Text input -->
        <div class="px-5 pb-4">
          <textarea
            ref="inputRef"
            v-model="answer"
            rows="2"
            placeholder="Type your response…"
            class="w-full bg-app-bg border border-border text-default text-sm px-3 py-2 outline-none resize-none placeholder:text-muted/40 focus:border-accent/50 transition-colors"
            @keydown.enter.ctrl="submit"
            @keydown.enter.meta="submit"
          ></textarea>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-2 px-5 pb-4">
          <button
            @click="$emit('cancel')"
            class="px-3 py-1.5 text-xs text-muted hover:text-default border border-border/60 hover:border-border transition-colors"
          >
            Cancel
          </button>
          <button
            @click="submit"
            :disabled="!answer.trim()"
            class="px-4 py-1.5 text-xs bg-accent text-white hover:bg-[#c9a04a] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
export default {
  props: {
    show: Boolean,
    question: { type: String, default: '' },
    choices: { type: Array, default: null },
  },
  emits: ['resolve', 'cancel'],
  data() {
    return {
      answer: '',
    }
  },
  watch: {
    show(val) {
      if (val) {
        this.answer = ''
        this.$nextTick(() => {
          this.$refs.inputRef?.focus()
        })
      }
    },
  },
  methods: {
    selectChoice(choice) {
      this.answer = choice
      this.submit()
    },
    submit() {
      const txt = this.answer.trim()
      if (!txt) return
      this.$emit('resolve', txt)
      this.answer = ''
    },
  },
}
</script>
