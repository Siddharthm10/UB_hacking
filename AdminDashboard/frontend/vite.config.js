import { defineConfig, loadEnv } from 'vite';
import path from 'node:path';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true
    },
    preview: {
      port: 4173,
      host: true
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    define: {
      __API_BASE__: JSON.stringify(env.VITE_API_BASE || 'http://localhost:8000'),
      __SOCKET_URL__: JSON.stringify(env.VITE_SOCKET_URL || env.VITE_API_BASE || 'http://localhost:8000')
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/setupTests.js'
    }
  };
});
