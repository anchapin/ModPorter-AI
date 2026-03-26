/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
              return 'vendor';
            }
            if (id.includes('@mui') || id.includes('@emotion')) {
              return 'ui';
            }
            if (id.includes('monaco-editor')) {
              return 'editor';
            }
            if (id.includes('mermaid')) {
              return 'diagrams';
            }
            return 'vendor_other';
          }
        },
      },
      onwarn(warning, warn) {
        // Suppress specific TypeScript import warnings
        if (warning.code === 'UNRESOLVED_IMPORT') return;
        warn(warning);
      },
    },
    chunkSizeWarningLimit: 1000, // Increase limit to reduce warnings while still optimizing
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['e2e/**/*', 'node_modules/**/*', 'dist/**/*'],
    hookTimeout: 30000,
    testTimeout: 10000,
  },
});
