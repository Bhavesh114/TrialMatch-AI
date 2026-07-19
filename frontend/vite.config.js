import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// [IMPLEMENTATION]: Vite configuration for React frontend
// Features:
// - React Fast Refresh for development
// - API proxy for local backend development
// - Optimized build output
// - Source maps for debugging

export default defineConfig({
  plugins: [react()],

  // [IMPLEMENTATION]: Development server settings
  server: {
    port: 5173,
    host: '0.0.0.0',

    // [IMPLEMENTATION]: Proxy API calls to backend in development
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },

  // [IMPLEMENTATION]: Build optimization
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',

    // [IMPLEMENTATION]: Code splitting configuration
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          api: ['axios'],
        },
      },
    },
  },

  // [IMPLEMENTATION]: Environment variables
  define: {
    __DEV__: process.env.NODE_ENV !== 'production',
  },
});
