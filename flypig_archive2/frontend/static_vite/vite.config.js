import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  optimizeDeps: { include: ['@iconify/vue'] },
  server: {
    port: 5173,
    proxy: {
      '/api/chat': {
        target: 'http://127.0.0.1:8321',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:8320',
        changeOrigin: true,
      },
      '/sse': {
        target: 'http://127.0.0.1:8320',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
