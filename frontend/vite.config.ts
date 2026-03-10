/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

const shouldAnalyze = process.env.VITE_ANALYZE === 'true';

export default defineConfig({
  plugins: [
    react(),
    ...(shouldAnalyze ? [visualizer({ filename: 'dist/stats.html', open: false, gzipSize: true, brotliSize: true })] : []),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: [
            '@mui/material',
            '@mui/icons-material',
            '@emotion/react',
            '@emotion/styled',
          ],
          editor: ['@monaco-editor/react', 'monaco-editor'],
          utils: ['axios', 'date-fns'],
          diagrams: ['mermaid'],
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
