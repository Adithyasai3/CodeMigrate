import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const api = loadEnv(mode, '.', '').VITE_API_PROXY || 'http://localhost:8000'
  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true,
      proxy: { '/api': api, '/results-files': api },
    },
  }
})
