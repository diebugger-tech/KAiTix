import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Ports über die Umgebung überschreibbar, damit mehrere Worktrees parallel laufen können.
// Ohne gesetzte Variablen gelten die bisherigen Standardwerte.
const frontendPort = Number(process.env.KAITIX_FRONTEND_PORT) || 5175;
const backendPort = Number(process.env.KAITIX_BACKEND_PORT) || 8003;

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true
      }
    }
  }
});
