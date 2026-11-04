import type { Ref } from 'vue'
import type { ApiError } from '~/api/errors'

/**
 * The error to show in place of a query's data: set while it has no data and its last fetch failed.
 * Vue Query clears `error` whenever a fetch starts without data, so a poll or retry after a failed
 * first load would otherwise flip the view from its error state back to loading on every attempt.
 * Once data has loaded, a failed refetch keeps the data on screen and this stays `null`.
 */
export function useLoadError(query: { data: Ref<unknown>, error: Ref<ApiError | null> }) {
  const lastError = shallowRef<ApiError | null>(null)
  watch([query.data, query.error], ([data, error]) => {
    if (data !== undefined) lastError.value = null
    else if (error) lastError.value = error
  }, { immediate: true })
  return computed(() => query.data.value === undefined ? query.error.value ?? lastError.value : null)
}
