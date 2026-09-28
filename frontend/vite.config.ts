import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Forward /api calls to the FastAPI backend, so the browser sees one origin
    proxy: {
      '/api': process.env.API_URL ?? 'http://localhost:8000',
    },
  },
})
