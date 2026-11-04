import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { api, type Schemas } from '~/api/client'
import { unwrap } from '~/api/errors'
import { queryKeys } from '~/api/queryKeys'

export type TriggerEventInput = Schemas['EventCreate'] & {
  /** Resubmitting with the same key returns the original event (`deduplicated: true`). */
  idempotencyKey: string
}

export function useTriggerEvent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ idempotencyKey, ...body }: TriggerEventInput) => unwrap(api.POST('/events', {
      body,
      params: { header: { 'Idempotency-Key': idempotencyKey } }
    })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.deliveries.all })
  })
}
