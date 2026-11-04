// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'
import betterTailwindcss from 'eslint-plugin-better-tailwindcss'
import { getDefaultAttributes } from 'eslint-plugin-better-tailwindcss/api/defaults'

const useComposables = 'UI talks to the API only through composables (app/composables).'

export default withNuxt(
  { ignores: ['app/api/schema.d.ts'] },
  betterTailwindcss.configs['correctness-error'],
  {
    settings: {
      'better-tailwindcss': {
        entryPoint: 'app/assets/css/main.css',
        attributes: [
          ...getDefaultAttributes(),
          ['^v-bind:ui$', [{ match: 'objectValues' }]]
        ]
      }
    }
  },
  {
    // The layering rule (UI → composables → API layer), enforced rather than hoped for.
    files: ['app/pages/**', 'app/components/**', 'app/layouts/**', 'app/app.vue'],
    rules: {
      'no-restricted-globals': ['error', ...['fetch', '$fetch', 'useFetch', 'useAsyncData'].map(name => ({ name, message: useComposables }))],
      '@typescript-eslint/no-restricted-imports': ['error', {
        patterns: [
          { group: ['~/api/client', '**/api/client'], importNames: ['api'], message: useComposables, allowTypeImports: true },
          { group: ['openapi-fetch', '@tanstack/vue-query'], message: useComposables }
        ]
      }]
    }
  }
)
