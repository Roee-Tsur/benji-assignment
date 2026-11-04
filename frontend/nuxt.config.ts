// The backend has no CORS: the browser talks to `/api` on this origin and Nuxt proxies it.
const apiOrigin = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'

export default defineNuxtConfig({
  modules: ['@nuxt/eslint', '@nuxt/ui'],

  // An ops dashboard behind no public URL: a client-rendered SPA, no SSR.
  ssr: false,

  devtools: { enabled: true },

  css: ['~/assets/css/main.css'],

  routeRules: {
    '/api/**': { proxy: `${apiOrigin}/**` }
  },

  compatibilityDate: '2026-06-30',

  // Typecheck the tests too, not just the app.
  typescript: { strict: true, tsConfig: { include: ['../test/**/*'] } },

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
