/// <reference types="vitest" />
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { '/api': env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000' },
    },
    build: {
      target: 'es2022',
      chunkSizeWarningLimit: 1100, // maplibre-gl is ~800 kB minified, loaded lazily
      rollupOptions: {
        output: { manualChunks: { maplibre: ['maplibre-gl'] } },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
    },
  };
});
