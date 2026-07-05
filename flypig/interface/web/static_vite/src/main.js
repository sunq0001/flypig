/** main.js — FlyPig 前端入口，挂载 Vue 应用 + Pinia 状态管理 + TDesign UI */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'
import './style/variables.css'
import './style/base.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(TDesign)
app.mount('#app')
