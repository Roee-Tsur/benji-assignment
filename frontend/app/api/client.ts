import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type Schemas = components['schemas']
export type Endpoint = Schemas['EndpointOut']
export type EndpointCreated = Schemas['EndpointCreated']
export type EventType = Schemas['EventType']
export type EventSubmitted = Schemas['EventSubmitted']
export type Delivery = Schemas['DeliveryOut']
export type DeliveryStatus = Schemas['DeliveryStatus']

/** Typed client for the backend, reached through the `/api` proxy (see `nuxt.config.ts`). */
export const api = createClient<paths>({
  baseUrl: `${window.location.origin}/api`,
  // Resolve `fetch` per request rather than once at import, so test interceptors (MSW) see it.
  fetch: request => globalThis.fetch(request)
})
