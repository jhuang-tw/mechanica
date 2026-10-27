import { defineConfig } from 'vite';

// `npm run dev` = Vite on 8099 with /api proxied to the Node server (`node server/serve.mjs`, 8098), so keys stay server-side.
export default defineConfig({
  server: { host: '0.0.0.0', port: 8099, proxy: { '/api': 'http://localhost:8098' } },
  build: { target: 'es2022' },
});
