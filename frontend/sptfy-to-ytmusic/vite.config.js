import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      ignored: ['**/node_modules/**'],
      usePolling: true, // Enable polling
      interval: 100, // Polling interval in milliseconds
    },
  },
})
