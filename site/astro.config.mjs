// @ts-check
import { defineConfig } from 'astro/config';

import solidJs from '@astrojs/solid-js';

import mdx from '@astrojs/mdx';

// https://astro.build/config
export default defineConfig({
  // Endereço público: usado nos links absolutos das prévias (WhatsApp, redes).
  site: 'https://orcamentobrasileiro.com.br',
  integrations: [solidJs(), mdx()]
});