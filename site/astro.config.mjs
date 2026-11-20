// @ts-check
import { defineConfig } from 'astro/config';

import solidJs from '@astrojs/solid-js';

import mdx from '@astrojs/mdx';

// https://astro.build/config
export default defineConfig({
  // Endereço público do site: é daqui que saem as URLs absolutas do canonical
  // e das meta tags de compartilhamento (ver src/layouts/Base.astro).
  site: 'https://orcamentobrasileiro.com.br',
  integrations: [solidJs(), mdx()]
});