import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { api, type Schemas } from '~/api/client'
import { type ApiError, unwrap } from '~/api/errors'
import { queryKeys } from '~/api/queryKeys'

/** Poll slowly so events triggered elsewhere (e.g. with curl) show up without a reload. */
export const EVENTS_POLL_MS = 5000

/** The newest events, each with its fan-out count. */
export function useRecentEvents() {
  return useQuery({
    queryKey: queryKeys.events.list(),
    queryFn: ({ signal }) => unwrap(api.GET('/events', { signal })),
    refetchInterval: EVENTS_POLL_MS
  })
}

export type TriggerEventInput = Schemas['EventCreate'] & {
  /** Resubmitting with the same key returns the original event (`deduplicated: true`). */
  idempotencyKey: string
}

/** The 422 for a key already used with a different payload: a plain problem, unlike a validation 422. */
export function isIdempotencyKeyReused(error: ApiError | null | undefined): boolean {
  return error?.kind === 'problem' && error.status === 422 && error.issues.length === 0
}

export function useTriggerEvent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ idempotencyKey, ...body }: TriggerEventInput) => unwrap(api.POST('/events', {
      body,
      params: { header: { 'Idempotency-Key': idempotencyKey } }
    })),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.events.all }),
      queryClient.invalidateQueries({ queryKey: queryKeys.deliveries.all })
    ]),
    // The trigger form explains a reused key inline, next to the key it's about.
    meta: { toastError: error => !isIdempotencyKeyReused(error) }
  })
}
