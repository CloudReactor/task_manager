import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import viteTsconfigPaths from 'vite-tsconfig-paths';
import svgrPlugin from 'vite-plugin-svgr';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), viteTsconfigPaths(), svgrPlugin()],

  resolve: {
    alias: [
      {
        find: /^~.+/,
        replacement: (value: string) => value.replace(/^~/, '')
      },
    ]
  },
  server: {
    port: 3000,
    strictPort: true
  },
  preview: {
    port: 3000,
    strictPort: true
  },
  commonjsOptions: {
    transformMixedEsModules: true
  },
  build: {
    outDir: 'build',
    manifest: true
  }
});
