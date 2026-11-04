import { defineVitestProject } from '@nuxt/test-utils/config'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    projects: [
      // Pure TypeScript (the API layer): plain Node, no Nuxt app.
      { test: { name: 'unit', include: ['test/unit/**/*.test.ts'], environment: 'node' } },
      // Composables and components: a real Nuxt app, with the API mocked by MSW.
      await defineVitestProject({
        test: {
          name: 'nuxt',
          include: ['test/nuxt/**/*.test.ts'],
          environment: 'nuxt',
          setupFiles: ['test/nuxt/setup.ts']
        }
      })
    ]
  }
})
