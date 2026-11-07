// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  // GitHub Pages with a custom domain: the site lives at the root of https://shiningforu.com/
  site: 'https://shiningforu.com',
  output: 'static',
  trailingSlash: 'ignore',
});
