import type { DeliveryStatus } from './client'

/** What the deliveries list is narrowed to; an absent field means any. */
export interface DeliveryFilters {
  status?: DeliveryStatus
  endpointId?: string
  eventId?: string
}

/**
 * Every Vue Query key, built here so invalidation can target a whole feature
 * (`queryKeys.deliveries.all`) or one entry of it. Mutation keys let a view ask
 * which rows have a request in flight.
 */
export const queryKeys = {
  endpoints: {
    all: ['endpoints'] as const,
    list: () => [...queryKeys.endpoints.all, 'list'] as const,
    setEnabled: () => [...queryKeys.endpoints.all, 'setEnabled'] as const,
    replayFailed: () => [...queryKeys.endpoints.all, 'replayFailed'] as const
  },
  events: {
    all: ['events'] as const,
    list: () => [...queryKeys.events.all, 'list'] as const
  },
  deliveries: {
    all: ['deliveries'] as const,
    lists: () => [...queryKeys.deliveries.all, 'list'] as const,
    list: (filters: DeliveryFilters) => [...queryKeys.deliveries.lists(), filters] as const,
    counts: (filters: DeliveryFilters) => [...queryKeys.deliveries.all, 'counts', filters] as const,
    details: () => [...queryKeys.deliveries.all, 'detail'] as const,
    detail: (deliveryId: string) => [...queryKeys.deliveries.details(), deliveryId] as const
  }
}
