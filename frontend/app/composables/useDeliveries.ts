import { useQuery } from '@tanstack/vue-query'
import { api } from '~/api/client'
import { unwrap } from '~/api/errors'
import { queryKeys } from '~/api/queryKeys'
import { deliveryStatuses } from '~/domain/deliveryStatus'

/** Poll fast while any delivery can still change, slowly otherwise to pick up new ones. */
export const DELIVERIES_POLL_MS = { active: 1500, idle: 5000 } as const

/** The newest deliveries, kept live by polling (paused while the tab is hidden). */
export function useDeliveries() {
  return useQuery({
    queryKey: queryKeys.deliveries.list(),
    queryFn: ({ signal }) => unwrap(api.GET('/deliveries', { signal })),
    refetchInterval: query => query.state.data?.some(delivery => !deliveryStatuses[delivery.status].terminal)
      ? DELIVERIES_POLL_MS.active
      : DELIVERIES_POLL_MS.idle
  })
}
