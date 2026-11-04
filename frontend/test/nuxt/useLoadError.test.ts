import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache, withSetup } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

const unavailable = () => new Response(JSON.stringify({ title: 'Service Unavailable', status: 503 }), {
  status: 503,
  headers: { 'content-type': 'application/problem+json' }
})

describe('useLoadError', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('keeps a failed first load\'s error through the polls that retry it, until data arrives', async () => {
    // The first load and its two retries fail; the poll after that hangs until the test lets it through.
    let requests = 0
    let recover!: () => void
    const recovered = new Promise<void>((resolve) => {
      recover = resolve
    })
    server.use(http.get('/events', async ({ response }) => {
      if (++requests <= 3) return unavailable()
      await recovered
      return response(200).json([])
    }))
    const { events, loadError } = await withSetup(() => {
      const events = useRecentEvents()
      return { events, loadError: useLoadError(events) }
    })

    await vi.advanceTimersByTimeAsync(4000)
    await vi.waitFor(() => expect(events.error.value?.status).toBe(503))
    expect(loadError.value?.status).toBe(503)

    // The next poll starts without data: Vue Query clears `error` for it, the load error stays.
    await vi.advanceTimersByTimeAsync(EVENTS_POLL_MS)
    await vi.waitFor(() => expect(requests).toBe(4))
    expect(events.error.value).toBeNull()
    expect(loadError.value?.status).toBe(503)

    recover()
    await vi.waitFor(() => expect(events.data.value).toEqual([]))
    expect(loadError.value).toBeNull()
  })

  it('drops the error when the query moves to another key, so the new key shows as loading', async () => {
    server.use(http.get('/deliveries', ({ query }) => query.get('endpoint_id') === 'ep_a' ? unavailable() : new Promise(() => {})))
    const filters = ref({ endpointId: 'ep_a' })
    const { deliveries, loadError } = await withSetup(() => {
      const deliveries = useDeliveries(filters)
      return { deliveries, loadError: useLoadError(deliveries) }
    })
    await vi.advanceTimersByTimeAsync(4000)
    await vi.waitFor(() => expect(loadError.value?.status).toBe(503))

    filters.value = { endpointId: 'ep_b' }
    await vi.waitFor(() => expect(deliveries.isPending.value).toBe(true))
    expect(loadError.value).toBeNull()
  })

  it('is null when a refetch fails after data has loaded: the data stays on screen', async () => {
    let up = true
    server.use(http.get('/events', ({ response }) => up ? response(200).json([]) : unavailable()))
    const { events, loadError } = await withSetup(() => {
      const events = useRecentEvents()
      return { events, loadError: useLoadError(events) }
    })
    await vi.waitFor(() => expect(events.data.value).toEqual([]))

    up = false
    await vi.advanceTimersByTimeAsync(EVENTS_POLL_MS + 4000)
    await vi.waitFor(() => expect(events.error.value?.status).toBe(503))
    expect(loadError.value).toBeNull()
  })
})
