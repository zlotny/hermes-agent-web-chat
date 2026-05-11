import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import LoginPage from './views/LoginPage.vue'
import ChatPage from './views/ChatPage.vue'
import './style.css'

const routes = [
  { path: '/login', component: LoginPage },
  { path: '/', component: ChatPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).mount('#app')
