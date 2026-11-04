import { MutationCache, QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import type { ApiError } from '~/api/errors'

declare module '@tanstack/vue-query' {
  interface Register {
    defaultError: ApiError
    mutationMeta: {
      /** Return `false` for an error the view explains inline instead of as a toast. */
      toastError?: (error: ApiError) => boolean
    }
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
    // Mutation failures surface as a toast unless the view explains them inline (`meta.toastError`);
    // query failures render inline (`QueryError`).
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        if (mutation.meta?.toastError?.(error) === false) return
        toast.add({ title: 'Request failed', description: error.message, color: 'error', icon: 'i-lucide-circle-alert' })
      }
    })
  })

  nuxtApp.vueApp.use(VueQueryPlugin, { queryClient })
  return { provide: { queryClient } }
})
