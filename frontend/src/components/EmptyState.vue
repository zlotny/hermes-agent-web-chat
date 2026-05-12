<template>
  <div class="flex flex-col items-center justify-center min-h-full px-4 py-12">
    <div class="mb-2 text-accent">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path
          d="M12 2a10 10 0 0 1 10 10c0 5-4 8-10 8-2.5 0-4.8-.8-6.7-2.2L2 22l1.8-4.5A9.8 9.8 0 0 1 2 12 10 10 0 0 1 12 2z"
        />
      </svg>
    </div>
    <h1 class="text-xl font-semibold text-[#c9d1d9] mb-1">
      How can I help you?
    </h1>
    <p class="text-sm text-muted mb-8">
      Start a conversation with your AI assistant
    </p>
    <div class="w-full max-w-[640px]">
      <ChatInput
        ref="inputRef"
        v-model="chatStore.inputText"
        placeholder="Type a message..."
        :current-model="chatStore.currentModel"
        :providers="chatStore.availableProviders"
        :providers-loading="chatStore.providersLoading"
        @send="$emit('send')"
        @select-model="(model) => $emit('select-model', model)"
      />
      <p class="text-[11px] text-muted/50 text-center mt-3">
        Hermes may produce inaccurate information. Verify important facts.
      </p>
    </div>
  </div>
</template>

<script>
import ChatInput from "./ChatInput.vue";
import { useChatStore } from "../stores/chat";

export default {
  components: { ChatInput },
  emits: ["send"],
  setup() {
    return { chatStore: useChatStore() };
  },
  methods: {
    focusInput() {
      this.$nextTick(() => this.$refs.inputRef?.focus());
    },
  },
};
</script>
