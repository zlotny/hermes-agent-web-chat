<template>
  <div class="flex flex-col items-center justify-center min-h-full px-4 py-12">
    <div class="mb-6">
      <div class="w-20 h-20 rounded-2xl bg-[#e6e6e6] border border-border/70 flex items-center justify-center">
        <img src="/nousresearch.svg" alt="NousResearch" class="w-12 h-12" />
      </div>
    </div>
    <h1 class="text-xl font-semibold text-default mb-1">
      Start a conversation
    </h1>
    <p class="text-sm text-muted mb-8">
      Starting a conversation here will start a new session
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