import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  optimizeDeps: { include: ['@iconify/vue'] },
  server: {
    port: 5173,
    watch: { usePolling: true, interval: 500 },
    strictPort: true,
    proxy: {
      '/api/chat': {
        target: 'http://127.0.0.1:8320',
        changeOrigin: true,
        proxyTimeout: 0,
        timeout: 0,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            proxyReq.setHeader('Accept-Encoding', 'identity');
            // 关掉 Nagle 算法：SSE 小包立即发送，不等攒满
            proxyReq.setNoDelay(true);
          });
        },
      },
      '/api': {
        target: 'http://127.0.0.1:8320',
        changeOrigin: true,
        proxyTimeout: 0,
        timeout: 0,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Accept-Encoding', 'identity');
            proxyReq.setNoDelay(true);
          });
        },
      },
      '/sse': {
        target: 'http://127.0.0.1:8320',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
