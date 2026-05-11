<template>
  <div class="min-h-screen bg-[#0d1117] flex items-center justify-center">
    <div class="bg-surface border border-border rounded-xl p-8 w-[340px]">
      <h1 class="text-xl text-center text-accent mb-6 font-semibold">Hermes</h1>
      <div v-if="error" class="text-[#f85149] text-sm text-center mb-4">{{ error }}</div>
      <form @submit.prevent="login">
        <label class="text-xs text-muted block mb-1.5" for="pwd">Password</label>
        <input id="pwd" v-model="password" type="password" autofocus
          class="w-full px-3 py-2.5 bg-[#0d1117] border border-border rounded-md text-[#c9d1d9] text-sm outline-none mb-4 focus:border-accent" />
        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-accent text-white rounded-md text-sm font-medium hover:bg-[#79c0ff] disabled:opacity-50 disabled:cursor-not-allowed">
          {{ loading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() { return { password: '', error: '', loading: false } },
  methods: {
    async login() {
      this.error = ''
      this.loading = true
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: this.password }),
        })
        if (!res.ok) throw new Error('Invalid password')
        this.$router.push('/')
      } catch (e) { this.error = e.message }
      finally { this.loading = false }
    }
  }
}
</script>
