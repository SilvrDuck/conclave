import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const observer = env.VITE_OBSERVER_URL || 'http://localhost:8000';
  const senate = env.VITE_SENATE_URL || 'http://localhost:8001';
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api/observer': {
          target: observer,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/observer/, ''),
        },
        '/api/state': {
          target: observer,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/api/senate': {
          target: senate,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/senate/, ''),
        },
      },
    },
  };
});
