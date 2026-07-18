/** main.js — FlyPig 前端入口，挂载 Vue 应用 + Pinia 状态管理 + TDesign UI */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'
import './style/variables.css'
import './style/base.css'
import './style/dropdown-dark.css'
import App from './App.vue'

/* ── 预加载 Iconify 图标集合，避免运行时从远程 API 获取 ── */
import { addCollection } from '@iconify/vue'
import mdiIcons from '@iconify-json/mdi/icons.json'
import simpleIcons from '@iconify-json/simple-icons/icons.json'
import logosIcons from '@iconify-json/logos/icons.json'
import vscodeIcons from '@iconify-json/vscode-icons/icons.json'
addCollection(mdiIcons)
addCollection(simpleIcons)
addCollection(logosIcons)
addCollection(vscodeIcons)

const app = createApp(App)
app.use(createPinia())
app.use(TDesign)
app.mount('#app')
