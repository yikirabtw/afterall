import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  build: {
    // Шрифты не встраиваем в CSS: у них десятки наборов символов (греческий, вьетнамский…),
    // а браузер скачивает только нужные — встроенные же грузились бы все и всегда
    assetsInlineLimit: (file) => (/\.woff2?$/.test(file) ? false : undefined),
  },
  server: {
    // Явно IPv4: на Windows «localhost» у Node бывает только ::1, и браузер до сервера не достучится
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // Адреса HTTPS-туннеля Cloudflare — чтобы открыть dev-версию внутри Telegram
    allowedHosts: ['.trycloudflare.com'],
    // В разработке запросы к /api уходят на локальный бэкенд — тот же путь, что и в продакшене за прокси
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
