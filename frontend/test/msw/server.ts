import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { delivery, deliveryDetail, endpoint } from './fixtures'
import { http } from './http'

/**
 * Mocks the API for the calling test file, with happy-path defaults that a test
 * overrides via `server.use(...)`. Called per file rather than from a Vitest setup
 * file: the Nuxt environment loads setup files in a separate module graph, so a
 * shared server instance would not be the one the test sees.
 */
export function useMockApi() {
  const server = setupServer(
    http.get('/endpoints', ({ response }) => response(200).json([endpoint])),
    http.get('/deliveries', ({ response }) => response(200).json({ items: [delivery()], next_cursor: null })),
    http.get('/deliveries/counts', ({ response }) => response(200).json({ pending: 0, in_progress: 0, succeeded: 1, failed: 0 })),
    http.get('/deliveries/{delivery_id}', ({ response }) => response(200).json(deliveryDetail()))
  )
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
  afterEach(() => server.resetHandlers())
  afterAll(() => server.close())
  return server
}
