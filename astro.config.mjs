// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  // GitHub Pages project site: https://<user>.github.io/shining-light/
  base: '/shining-light',
  output: 'static',
  trailingSlash: 'ignore',
});
