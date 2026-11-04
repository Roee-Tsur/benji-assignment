import { useMutation, useMutationState, useQuery, useQueryClient } from '@tanstack/vue-query'
import { api, type Schemas } from '~/api/client'
import { unwrap } from '~/api/errors'
import { queryKeys } from '~/api/queryKeys'

/** Poll slowly, so failed counts follow deliveries that fail while the page is open. */
export const ENDPOINTS_POLL_MS = 5000

/** Newest first, each with its failed-delivery count. */
export function useEndpoints() {
  return useQuery({
    queryKey: queryKeys.endpoints.list(),
    queryFn: ({ signal }) => unwrap(api.GET('/endpoints', { signal })),
    refetchInterval: ENDPOINTS_POLL_MS
  })
}

/** Resolves to the created endpoint, including its signing secret: the only time the API returns it. */
export function useCreateEndpoint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Schemas['EndpointCreate']) => unwrap(api.POST('/endpoints', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.endpoints.all }),
    // Drop the finished mutation (and the secret in its data) as soon as nothing observes it,
    // rather than keeping it in the mutation cache for the default five minutes.
    gcTime: 0
  })
}

/** Ids of the endpoints that have a mutation with this key in flight, so each row can disable its own controls. */
function usePendingEndpointIds(mutationKey: readonly unknown[]) {
  const pending = useMutationState({
    filters: { mutationKey, status: 'pending' },
    select: mutation => (mutation.state.variables as { endpointId: string }).endpointId
  })
  return (endpointId: string) => pending.value.includes(endpointId)
}

/** Disabling fails the endpoint's pending deliveries (ADR 0003), so deliveries are refetched too. */
export function useSetEndpointEnabled() {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationKey: queryKeys.endpoints.setEnabled(),
    mutationFn: ({ endpointId, enabled }: { endpointId: string, enabled: boolean }) =>
      unwrap(api.PATCH('/endpoints/{endpoint_id}', { params: { path: { endpoint_id: endpointId } }, body: { enabled } })),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.endpoints.all }),
      queryClient.invalidateQueries({ queryKey: queryKeys.deliveries.all })
    ])
  })
  return { ...mutation, isPendingFor: usePendingEndpointIds(queryKeys.endpoints.setEnabled()) }
}

/** Replays every failed delivery of an endpoint; resolves to how many went back to pending. Refetches the endpoints' failed counts too. */
export function useReplayFailed() {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationKey: queryKeys.endpoints.replayFailed(),
    mutationFn: ({ endpointId }: { endpointId: string }) =>
      unwrap(api.POST('/endpoints/{endpoint_id}/replay-failed', { params: { path: { endpoint_id: endpointId } } })),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.endpoints.all }),
      queryClient.invalidateQueries({ queryKey: queryKeys.deliveries.all })
    ])
  })
  return { ...mutation, isPendingFor: usePendingEndpointIds(queryKeys.endpoints.replayFailed()) }
}
