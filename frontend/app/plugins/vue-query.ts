import { MutationCache, QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import type { ApiError } from '~/api/errors'

declare module '@tanstack/vue-query' {
  interface Register {
    defaultError: ApiError
  }
}

export default defineNuxtPlugin((nuxtApp) => {
  const toast = useToast()

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000,
        retry: (failureCount, error) => error.isTransient && failureCount < 2
      }
    },
    // Mutation failures always surface as a toast; query failures render inline (`QueryError`).
    mutationCache: new MutationCache({
      onError: error => toast.add({ title: 'Request failed', description: error.message, color: 'error', icon: 'i-lucide-circle-alert' })
    })
  })

  nuxtApp.vueApp.use(VueQueryPlugin, { queryClient })
  return { provide: { queryClient } }
})
