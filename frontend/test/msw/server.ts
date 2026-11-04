import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { delivery, endpoint, event } from './fixtures'
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
    http.get('/deliveries', ({ response }) => response(200).json([delivery()])),
    http.get('/events', ({ response }) => response(200).json([event()]))
  )
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
  afterEach(() => server.resetHandlers())
  afterAll(() => server.close())
  return server
}
