import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import LoginPage from './views/LoginPage.vue'
import ChatPage from './views/ChatPage.vue'
import { useSettingsStore } from './stores/settings'
import './style.css'

const routes = [
  { path: '/login', component: LoginPage },
  { path: '/', component: ChatPage },
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
