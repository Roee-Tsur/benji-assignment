/**
 * Every Vue Query key, built here so invalidation can target a whole feature
 * (`queryKeys.deliveries.all`) or one entry of it.
 */
export const queryKeys = {
  endpoints: {
    all: ['endpoints'] as const,
    list: () => [...queryKeys.endpoints.all, 'list'] as const
  },
  deliveries: {
    all: ['deliveries'] as const,
    list: () => [...queryKeys.deliveries.all, 'list'] as const,
    detail: (deliveryId: string) => [...queryKeys.deliveries.all, 'detail', deliveryId] as const
  }
}
