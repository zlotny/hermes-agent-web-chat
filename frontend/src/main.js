import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import { useSettingsStore } from './stores/settings'
import './style.css'

const routes = [
  { path: '/login', component: () => import('./views/LoginPage.vue') },
  { path: '/', component: () => import('./views/ChatPage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// Init theme after mount (needs DOM ready)
const settings = useSettingsStore()
settings.init()
