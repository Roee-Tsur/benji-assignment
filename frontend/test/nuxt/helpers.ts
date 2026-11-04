import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent } from 'vue'

/** Runs a composable inside a mounted component, where Vue Query's client is injected. */
export async function withSetup<T>(composable: () => T): Promise<T> {
  let result!: T
  await mountSuspended(defineComponent({
    setup() {
      result = composable()
      return () => null
    }
  }))
  return result
}

/** The Nuxt app (and its query cache) lives for the whole file; call after each test. */
export function clearQueryCache() {
  useNuxtApp().$queryClient.clear()
}
