import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Prefijos que corresponden al backend Django (todo lo demás lo sirve Vite).
// Antes solo se proxeaba '/api', pero los endpoints ya no viven bajo ese
// prefijo (ver nura/urls.py): ahora son /chat/, /auth/, /sessions/, etc.
const BACKEND_PATHS = [
  '/admin', '/accounts', '/auth', '/static',
  '/chat', '/analyze', '/test', '/sessions',
  '/profile', '/workspace', '/datasets', '/tags', '/categories',
];

export default defineConfig(({ command }) => {
  const target = process.env.VITE_API_URL || 'http://localhost:8000';
  const proxy = {};
  for (const p of BACKEND_PATHS) {
    proxy[p] = { target, changeOrigin: true };
  }
  return {
    plugins: [tailwindcss(), react()],
    base: command === 'build' ? '/' : '/',
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy,
    }
  };
});
