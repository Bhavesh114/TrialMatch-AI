// vite.config.js
import { defineConfig } from "file:///sessions/bold-quirky-allen/mnt/TrailMatch-AI/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///sessions/bold-quirky-allen/mnt/TrailMatch-AI/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [react()],
  // [IMPLEMENTATION]: Development server settings
  server: {
    port: 5173,
    host: "0.0.0.0",
    // [IMPLEMENTATION]: Proxy API calls to backend in development
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  },
  // [IMPLEMENTATION]: Build optimization
  build: {
    outDir: "dist",
    sourcemap: process.env.NODE_ENV !== "production",
    // [IMPLEMENTATION]: Code splitting configuration
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          api: ["axios"]
        }
      }
    }
  },
  // [IMPLEMENTATION]: Environment variables
  define: {
    __DEV__: process.env.NODE_ENV !== "production"
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvc2Vzc2lvbnMvYm9sZC1xdWlya3ktYWxsZW4vbW50L1RyYWlsTWF0Y2gtQUkvZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIi9zZXNzaW9ucy9ib2xkLXF1aXJreS1hbGxlbi9tbnQvVHJhaWxNYXRjaC1BSS9mcm9udGVuZC92aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vc2Vzc2lvbnMvYm9sZC1xdWlya3ktYWxsZW4vbW50L1RyYWlsTWF0Y2gtQUkvZnJvbnRlbmQvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJztcbmltcG9ydCByZWFjdCBmcm9tICdAdml0ZWpzL3BsdWdpbi1yZWFjdCc7XG5cbi8vIFtJTVBMRU1FTlRBVElPTl06IFZpdGUgY29uZmlndXJhdGlvbiBmb3IgUmVhY3QgZnJvbnRlbmRcbi8vIEZlYXR1cmVzOlxuLy8gLSBSZWFjdCBGYXN0IFJlZnJlc2ggZm9yIGRldmVsb3BtZW50XG4vLyAtIEFQSSBwcm94eSBmb3IgbG9jYWwgYmFja2VuZCBkZXZlbG9wbWVudFxuLy8gLSBPcHRpbWl6ZWQgYnVpbGQgb3V0cHV0XG4vLyAtIFNvdXJjZSBtYXBzIGZvciBkZWJ1Z2dpbmdcblxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcbiAgcGx1Z2luczogW3JlYWN0KCldLFxuXG4gIC8vIFtJTVBMRU1FTlRBVElPTl06IERldmVsb3BtZW50IHNlcnZlciBzZXR0aW5nc1xuICBzZXJ2ZXI6IHtcbiAgICBwb3J0OiA1MTczLFxuICAgIGhvc3Q6ICcwLjAuMC4wJyxcblxuICAgIC8vIFtJTVBMRU1FTlRBVElPTl06IFByb3h5IEFQSSBjYWxscyB0byBiYWNrZW5kIGluIGRldmVsb3BtZW50XG4gICAgcHJveHk6IHtcbiAgICAgICcvYXBpJzoge1xuICAgICAgICB0YXJnZXQ6IHByb2Nlc3MuZW52LlZJVEVfQVBJX1VSTCB8fCAnaHR0cDovL2xvY2FsaG9zdDo4MDAwJyxcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxuICAgICAgICByZXdyaXRlOiAocGF0aCkgPT4gcGF0aCxcbiAgICAgIH0sXG4gICAgfSxcbiAgfSxcblxuICAvLyBbSU1QTEVNRU5UQVRJT05dOiBCdWlsZCBvcHRpbWl6YXRpb25cbiAgYnVpbGQ6IHtcbiAgICBvdXREaXI6ICdkaXN0JyxcbiAgICBzb3VyY2VtYXA6IHByb2Nlc3MuZW52Lk5PREVfRU5WICE9PSAncHJvZHVjdGlvbicsXG5cbiAgICAvLyBbSU1QTEVNRU5UQVRJT05dOiBDb2RlIHNwbGl0dGluZyBjb25maWd1cmF0aW9uXG4gICAgcm9sbHVwT3B0aW9uczoge1xuICAgICAgb3V0cHV0OiB7XG4gICAgICAgIG1hbnVhbENodW5rczoge1xuICAgICAgICAgIHZlbmRvcjogWydyZWFjdCcsICdyZWFjdC1kb20nLCAncmVhY3Qtcm91dGVyLWRvbSddLFxuICAgICAgICAgIGFwaTogWydheGlvcyddLFxuICAgICAgICB9LFxuICAgICAgfSxcbiAgICB9LFxuICB9LFxuXG4gIC8vIFtJTVBMRU1FTlRBVElPTl06IEVudmlyb25tZW50IHZhcmlhYmxlc1xuICBkZWZpbmU6IHtcbiAgICBfX0RFVl9fOiBwcm9jZXNzLmVudi5OT0RFX0VOViAhPT0gJ3Byb2R1Y3Rpb24nLFxuICB9LFxufSk7XG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQW9WLFNBQVMsb0JBQW9CO0FBQ2pYLE9BQU8sV0FBVztBQVNsQixJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUMsTUFBTSxDQUFDO0FBQUE7QUFBQSxFQUdqQixRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixNQUFNO0FBQUE7QUFBQSxJQUdOLE9BQU87QUFBQSxNQUNMLFFBQVE7QUFBQSxRQUNOLFFBQVEsUUFBUSxJQUFJLGdCQUFnQjtBQUFBLFFBQ3BDLGNBQWM7QUFBQSxRQUNkLFNBQVMsQ0FBQyxTQUFTO0FBQUEsTUFDckI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBO0FBQUEsRUFHQSxPQUFPO0FBQUEsSUFDTCxRQUFRO0FBQUEsSUFDUixXQUFXLFFBQVEsSUFBSSxhQUFhO0FBQUE7QUFBQSxJQUdwQyxlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixjQUFjO0FBQUEsVUFDWixRQUFRLENBQUMsU0FBUyxhQUFhLGtCQUFrQjtBQUFBLFVBQ2pELEtBQUssQ0FBQyxPQUFPO0FBQUEsUUFDZjtBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBO0FBQUEsRUFHQSxRQUFRO0FBQUEsSUFDTixTQUFTLFFBQVEsSUFBSSxhQUFhO0FBQUEsRUFDcEM7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
