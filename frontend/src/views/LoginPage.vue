<template>
  <div class="min-h-screen bg-app-bg flex items-center justify-center relative overflow-hidden"
    style="padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px);">
    <!-- Animated noise grain overlay -->
    <div class="noise"></div>

    <!-- Warm glow backdrop -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 bg-warm-glow/6 dark:bg-warm-glow/10 blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-warm-glow/6 dark:bg-warm-glow/10 blur-3xl"></div>
    </div>
    <div class="bg-surface/80 backdrop-blur-sm border border-border p-8 w-[360px] relative z-10 shadow-2xl shadow-black/50 animate-fade-in">
      <div class="flex flex-col items-center mb-6">
        <div class="w-20 h-20 bg-[#e8ddd0] dark:bg-[#ffe6cb] border border-border flex items-center justify-center mb-4">
          <img src="/nousresearch.svg" alt="NousResearch" class="w-12 h-12" />
        </div>
        <h1 class="text-lg font-semibold text-default">Welcome to<br><span class="text-accent text-xl animate-glitch">Hermes Agent</span></h1>
        <p class="text-xs text-muted/60 mt-1.5 text-center uppercase tracking-[0.15em]">Sign in to your AI assistant</p>
      </div>
      <div v-if="error" class="text-[#f85149] text-sm text-center mb-4 bg-[#f85149]/10 border border-[#f85149]/30 px-3 py-2">{{ error }}</div>
      <form @submit.prevent="login">
        <label class="text-xs text-muted block mb-1.5 uppercase tracking-[0.1em]" for="pwd">Password</label>
        <input id="pwd" v-model="password" type="password" autofocus
          class="w-full px-3 py-2.5 bg-app-bg border border-border text-default text-sm outline-none mb-5 focus:border-accent/70 transition-colors" />
        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-accent text-white text-sm font-medium hover:bg-[#c9a04a] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200">
          {{ loading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import { useAuthStore } from '../stores/auth'

export default {
  setup() {
    return { authStore: useAuthStore() }
  },
  data() { return { password: '', error: '', loading: false } },
  methods: {
    async login() {
      this.error = ''
      this.loading = true
      try {
        await this.authStore.login(this.password)
        this.$router.push('/')
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    }
  }
}
</script>
