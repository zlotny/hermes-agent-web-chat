<template>
  <div class="min-h-screen bg-[#0d1117] flex items-center justify-center relative overflow-hidden">
    <!-- Subtle background decoration -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-accent/3 blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-accent/3 blur-3xl"></div>
    </div>
    <div class="bg-surface/80 backdrop-blur-sm border border-border/60 rounded-xl p-8 w-[360px] relative z-10 shadow-2xl shadow-black/40 animate-fade-in">
      <div class="flex flex-col items-center mb-6">
        <div class="w-20 h-20 rounded-2xl bg-[#e6e6e6] border border-border/70 flex items-center justify-center mb-4">
          <img src="/nousresearch.svg" alt="NousResearch" class="w-12 h-12 text-muted" />
        </div>
        <h1 class="text-lg font-semibold text-[#c9d1d9]">Welcome to<br><span class="text-accent text-xl">Hermes Agent</span></h1>
        <p class="text-xs text-muted/60 mt-1.5 text-center">Sign in to your AI assistant</p>
      </div>
      <div v-if="error" class="text-[#f85149] text-sm text-center mb-4 bg-[#f85149]/10 border border-[#f85149]/30 rounded-md px-3 py-2">{{ error }}</div>
      <form @submit.prevent="login">
        <label class="text-xs text-muted block mb-1.5" for="pwd">Password</label>
        <input id="pwd" v-model="password" type="password" autofocus
          class="w-full px-3 py-2.5 bg-[#0d1117] border border-border rounded-md text-[#c9d1d9] text-sm outline-none mb-5 focus:border-accent/70 transition-colors" />
        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-accent text-white rounded-md text-sm font-medium hover:bg-[#79c0ff] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-accent/20">
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
