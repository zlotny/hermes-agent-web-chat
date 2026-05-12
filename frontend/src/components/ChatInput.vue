<template>
  <div class="flex flex-col gap-1.5">
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
      class="flex gap-2 bg-surface/95 backdrop-blur-sm border border-border/80 rounded-xl p-2 shadow-lg shadow-black/40"
    >
      <textarea
        ref="textareaRef"
        v-model="text"
        rows="1"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="$emit('send')"
        @input="resize"
        class="flex-1 bg-transparent text-default px-3 py-2.5 text-sm outline-none resize-none min-h-[44px] max-h-[200px] leading-relaxed placeholder:text-muted/60"
      ></textarea>
      <button
        v-if="sending"
        @click="$emit('stop')"
        class="self-center p-2.5 rounded-lg bg-[#d97706] text-white hover:bg-[#b45309] transition-colors shadow-lg shadow-orange-900/30"
        title="Stop agent"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>
      <button
        v-else
        @click="$emit('send')"
        :disabled="disabled || !text.trim()"
        class="self-center p-2.5 rounded-lg bg-accent text-white hover:bg-[#79c0ff] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
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
  </div>
</template>

<script>
import ModelSelector from "./ModelSelector.vue";

export default {
  components: { ModelSelector },
  props: {
    modelValue: { type: String, default: "" },
    placeholder: { type: String, default: "Type a message..." },
    disabled: { type: Boolean, default: false },
    sending: { type: Boolean, default: false },
    currentModel: { type: String, default: "" },
    providers: { type: Array, default: () => [] },
    providersLoading: { type: Boolean, default: false },
  },
  emits: ["update:modelValue", "send", "select-model", "stop", "closed"],
  computed: {
    text: {
      get() {
        return this.modelValue;
      },
      set(v) {
        this.$emit("update:modelValue", v);
      },
    },
  },
  methods: {
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
};
</script>
