import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          editor: ['@monaco-editor/react', 'monaco-editor'],
          utils: ['axios', 'date-fns'],
          diagrams: ['mermaid']
        }
      },
      onwarn(warning, warn) {
        // Suppress specific TypeScript import warnings
        if (warning.code === 'UNRESOLVED_IMPORT') return;
        warn(warning);
      }
    },
    chunkSizeWarningLimit: 1000 // Increase limit to reduce warnings while still optimizing
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['e2e/**/*', 'node_modules/**/*', 'dist/**/*'],
    poolOptions: {
      vmThreads: {
        maxThreads: 2,
        minThreads: 1,
        isolate: false,
      },
    },
    hookTimeout: 30000,
    testTimeout: 10000,
  },
})
