<template>
  <div class="login-page">
    <div class="card">
      <h1>Hermes</h1>
      <div v-if="error" class="error">{{ error }}</div>
      <form @submit.prevent="login">
        <label for="pwd">Password</label>
        <input id="pwd" v-model="password" type="password" autofocus />
        <button type="submit" :disabled="loading">
          {{ loading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return { password: '', error: '', loading: false }
  },
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
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: #0d1117;
}
.card {
  background: #161b22; border: 1px solid #30363d;
  border-radius: 12px; padding: 2rem; width: 340px;
}
h1 { font-size: 1.3rem; margin-bottom: 1.5rem; text-align: center; color: #58a6ff; }
label { font-size: 0.85rem; color: #8b949e; display: block; margin-bottom: 6px; }
input[type=password] {
  width: 100%; padding: 10px 12px;
  background: #0d1117; border: 1px solid #30363d;
  border-radius: 6px; color: #c9d1d9; font-size: 0.9rem;
  outline: none; margin-bottom: 1rem;
}
input[type=password]:focus { border-color: #58a6ff; }
button {
  width: 100%; padding: 10px;
  background: #58a6ff; color: #fff;
  border: none; border-radius: 6px; font-size: 0.9rem;
  cursor: pointer; font-weight: 500;
}
button:hover { background: #79c0ff; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
.error { color: #f85149; font-size: 0.85rem; margin-bottom: 1rem; text-align: center; }
</style>
