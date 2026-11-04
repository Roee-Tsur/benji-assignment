import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient, type InfiniteData } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { api, type Delivery, type DeliveryDetail, type Schemas } from '~/api/client'
import { unwrap } from '~/api/errors'
import { queryKeys, type DeliveryFilters } from '~/api/queryKeys'
import { deliveryStatuses } from '~/domain/deliveryStatus'

/** Poll fast while anything shown can still change, slowly otherwise to pick up new deliveries. */
export const DELIVERIES_POLL_MS = { active: 1500, idle: 5000 } as const

type DeliveryPage = Schemas['DeliveryPage']

const isLive = (delivery: Delivery) => !deliveryStatuses[delivery.status].terminal

function toQuery(filters: DeliveryFilters) {
  return { endpoint_id: filters.endpointId, event_id: filters.eventId }
}

/**
 * The newest deliveries matching `filters`, a page of 50 at a time (`fetchNextPage`). Every poll
 * refetches every loaded page, so a row on page 2 stays as live as one on page 1. Polling pauses
 * while the tab is hidden, and the list refetches when it becomes visible again.
 */
export function useDeliveries(filters: MaybeRefOrGetter<DeliveryFilters> = {}) {
  const query = useInfiniteQuery({
    queryKey: computed(() => queryKeys.deliveries.list(toValue(filters))),
    queryFn: ({ queryKey: [, , filters], pageParam, signal }) => unwrap(api.GET('/deliveries', {
      params: { query: { ...toQuery(filters), status: filters.status, cursor: pageParam ?? undefined } },
      signal
    })),
    initialPageParam: null as string | null,
    getNextPageParam: (page: DeliveryPage) => page.next_cursor,
    // Changing a filter keeps showing the old rows until the new ones arrive, rather than flashing empty.
    placeholderData: keepPreviousData,
    refetchInterval: query => query.state.data?.pages.some(page => page.items.some(isLive))
      ? DELIVERIES_POLL_MS.active
      : DELIVERIES_POLL_MS.idle
  })
  return {
    ...query,
    deliveries: computed(() => query.data.value?.pages.flatMap(page => page.items) ?? [])
  }
}

/** How many deliveries are in each status, regardless of paging; `filters.status` doesn't apply. */
export function useDeliveryCounts(filters: MaybeRefOrGetter<DeliveryFilters> = {}) {
  return useQuery({
    queryKey: computed(() => {
      const { endpointId, eventId } = toValue(filters)
      return queryKeys.deliveries.counts({ endpointId, eventId })
    }),
    queryFn: ({ queryKey: [, , filters], signal }) => unwrap(api.GET('/deliveries/counts', {
      params: { query: toQuery(filters) },
      signal
    })),
    placeholderData: keepPreviousData,
    refetchInterval: query => (query.state.data?.pending ?? 0) + (query.state.data?.in_progress ?? 0) > 0
      ? DELIVERIES_POLL_MS.active
      : DELIVERIES_POLL_MS.idle
  })
}

/** One delivery with its payload and attempt log, polled on its own until it is terminal. */
export function useDelivery(deliveryId: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: computed(() => queryKeys.deliveries.detail(toValue(deliveryId) ?? '')),
    queryFn: ({ queryKey: [, , deliveryId], signal }) => unwrap(api.GET('/deliveries/{delivery_id}', {
      params: { path: { delivery_id: deliveryId } },
      signal
    })),
    enabled: computed(() => Boolean(toValue(deliveryId))),
    refetchInterval: query => query.state.data && isLive(query.state.data) ? DELIVERIES_POLL_MS.active : false
  })
}

/**
 * Replays a failed delivery. The delivery shows as `pending` at once, wherever it's cached; if the
 * request fails, it's rolled back (the toast comes from the global mutation error handler).
 */
export function useReplayDelivery() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (deliveryId: string) => unwrap(api.POST('/deliveries/{delivery_id}/replay', {
      params: { path: { delivery_id: deliveryId } }
    })),
    onMutate: async (deliveryId) => {
      const listsKey = queryKeys.deliveries.lists()
      const detailKey = queryKeys.deliveries.detail(deliveryId)
      // A poll already in flight would land after the optimistic update and undo it.
      await Promise.all([
        queryClient.cancelQueries({ queryKey: listsKey }),
        queryClient.cancelQueries({ queryKey: detailKey })
      ])
      const lists = queryClient.getQueriesData<InfiniteData<DeliveryPage>>({ queryKey: listsKey })
      const detail = queryClient.getQueryData<DeliveryDetail>(detailKey)

      const replayed = <T extends Delivery>(delivery: T): T => delivery.id === deliveryId
        ? { ...delivery, status: 'pending', failure_reason: null, attempts_used: 0, next_attempt_at: new Date().toISOString() }
        : delivery
      queryClient.setQueriesData<InfiniteData<DeliveryPage>>({ queryKey: listsKey }, data => data && {
        ...data,
        pages: data.pages.map(page => ({ ...page, items: page.items.map(replayed) }))
      })
      if (detail) queryClient.setQueryData(detailKey, replayed(detail))
      return { lists, detail }
    },
    onError: (_error, deliveryId, context) => {
      for (const [queryKey, data] of context?.lists ?? []) queryClient.setQueryData(queryKey, data)
      if (context?.detail) queryClient.setQueryData(queryKeys.deliveries.detail(deliveryId), context.detail)
    },
    onSuccess: detail => queryClient.setQueryData(queryKeys.deliveries.detail(detail.id), detail),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.deliveries.all })
  })
}
