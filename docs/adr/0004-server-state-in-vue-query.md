# Server state lives in Vue Query; no Pinia

Almost everything the dashboard shows is server state: endpoints, events, deliveries, and attempts, all changing underneath us as the worker runs. We keep it only in TanStack Vue Query, behind feature composables and a query key factory. Polling, deduplication of in-flight requests, cache invalidation after mutations, optimistic updates with rollback, and loading/error state then come from one place instead of being re-implemented in store actions. The little client state left (filters, which delivery is open) lives in the URL, so views are deep-linkable and survive a reload. Pinia stays out until there is client-only state that belongs in neither place.

## Considered Options

- **Pinia stores fetching and caching API data**: the common Nuxt default, but each store would hand-roll staleness, polling, request dedup, and error state. Copying server data into a store is exactly the second source of truth that lets a live view drift.
- **Nuxt `useFetch` / `useAsyncData`**: built in, but it has no infinite queries, no shared cache across components, and no mutation or optimistic-update story, all of which the deliveries view needs.
