import type { Ref } from 'vue'
import type { ApiError } from '~/api/errors'

/**
 * The error to show in place of a query's data: set while it has no data and its last fetch failed.
 * Vue Query clears `error` whenever a fetch starts without data, so a poll or retry after a failed
 * first load would otherwise flip the view from its error state back to loading on every attempt.
 * Once data has loaded, a failed refetch keeps the data on screen and this stays `null`.
 */
export function useLoadError(query: { data: Ref<unknown>, error: Ref<ApiError | null>, errorUpdatedAt: Ref<number> }) {
  // Tagged with when it happened, so it only stands in for the query (key) that failed:
  // a refetch keeps `errorUpdatedAt`, a different key has its own.
  const last = shallowRef<{ error: ApiError, at: number }>()
  watch([query.data, query.error], ([data, error]) => {
    if (data !== undefined) last.value = undefined
    else if (error) last.value = { error, at: query.errorUpdatedAt.value }
  }, { immediate: true })
  return computed(() => {
    if (query.data.value !== undefined) return null
    if (query.error.value) return query.error.value
    return last.value?.at === query.errorUpdatedAt.value ? last.value.error : null
  })
}
