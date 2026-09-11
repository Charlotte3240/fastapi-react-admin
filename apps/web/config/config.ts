import { defineConfig } from '@umijs/max';
import routes from './routes';

export default defineConfig({
  esbuildMinifyIIFE: true,
  access: {},
  antd: {},
  initialState: {},
  layout: {
    locale: false,
    title: 'UniBiz',
  },
  locale: {
    default: 'zh-CN',
    antd: true,
    baseNavigator: false,
  },
  model: {},
  request: {},
  routes,
  npmClient: 'pnpm',
  proxy: {
    '/api': {
      target: process.env.UNIBIZ_API_TARGET ?? 'http://localhost:8000',
      changeOrigin: true,
    },
  },
});
