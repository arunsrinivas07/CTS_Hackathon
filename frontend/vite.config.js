import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/api/agentic/copilot': {
        target: 'http://15.207.248.42',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/agentic/, '/api')
      },
      '/api/agentic': {
        target: 'http://15.207.248.42',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/agentic/, '/api')
      },
      '/api': {
        target: 'http://15.207.248.42',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

