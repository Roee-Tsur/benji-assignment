import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Delivery, DeliveryStatus } from '../../app/api/client'
import { delivery, deliveryDetail } from '../msw/fixtures'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache, withSetup } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

/** A promise the test settles, to hold a mocked response open. */
function deferred() {
  let resolve!: () => void
  const promise = new Promise<void>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

describe('useDeliveries polling', () => {
  // Fake only the clocks Vue Query schedules with; promises and MSW keep running for real.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('polls fast while a delivery is non-terminal, backs off once all are terminal, and speeds up again', async () => {
    let status: DeliveryStatus = 'pending'
    let requests = 0
    server.use(http.get('/deliveries', ({ response }) => {
      requests++
      return response(200).json({ items: [delivery({ status })], next_cursor: null })
    }))
    const deliveries = await withSetup(() => useDeliveries())
    await vi.waitFor(() => expect(requests).toBe(1))

    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)
    expect(requests).toBe(2)

    status = 'succeeded'
    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)
    expect(requests).toBe(3)
    await vi.waitFor(() => expect(deliveries.deliveries.value[0]?.status).toBe('succeeded'))

    // Everything is terminal: no fast poll, only the slow one that picks up new deliveries.
    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)
    expect(requests).toBe(3)
    status = 'in_progress'
    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.idle - DELIVERIES_POLL_MS.active)
    expect(requests).toBe(4)

    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)
    expect(requests).toBe(5)
  })

  it('refreshes every loaded page on each poll, not just the first', async () => {
    const rows: Record<string, Delivery> = {
      dlv_new: delivery({ id: 'dlv_new', status: 'pending' }),
      dlv_old: delivery({ id: 'dlv_old', status: 'pending' })
    }
    const pageRequests: (string | null)[] = []
    server.use(http.get('/deliveries', ({ query, response }) => {
      const cursor = query.get('cursor')
      pageRequests.push(cursor)
      return cursor === 'dlv_new'
        ? response(200).json({ items: [rows.dlv_old!], next_cursor: null })
        : response(200).json({ items: [rows.dlv_new!], next_cursor: 'dlv_new' })
    }))
    const deliveries = await withSetup(() => useDeliveries())
    await vi.waitFor(() => expect(deliveries.hasNextPage.value).toBe(true))
    await deliveries.fetchNextPage()
    expect(deliveries.deliveries.value.map(d => d.id)).toEqual(['dlv_new', 'dlv_old'])

    rows.dlv_old = { ...rows.dlv_old!, status: 'succeeded' }
    pageRequests.length = 0
    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)

    expect(pageRequests).toEqual([null, 'dlv_new'])
    expect(deliveries.deliveries.value.map(d => d.status)).toEqual(['pending', 'succeeded'])
  })

  it('polls an open delivery\'s detail while it is non-terminal, and stops once it is terminal', async () => {
    let status: DeliveryStatus = 'in_progress'
    let requests = 0
    server.use(http.get('/deliveries/{delivery_id}', ({ response }) => {
      requests++
      return response(200).json(deliveryDetail({ status }))
    }))
    const detail = await withSetup(() => useDelivery('dlv_1'))
    await vi.waitFor(() => expect(requests).toBe(1))

    status = 'succeeded'
    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)
    expect(requests).toBe(2)
    await vi.waitFor(() => expect(detail.data.value?.status).toBe('succeeded'))

    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.idle * 2)
    expect(requests).toBe(2)
  })

  it('keeps polling a failed delivery\'s detail slowly, since a replay from elsewhere can revive it', async () => {
    let requests = 0
    server.use(http.get('/deliveries/{delivery_id}', ({ response }) => {
      requests++
      return response(200).json(deliveryDetail({ status: 'failed' }))
    }))
    await withSetup(() => useDelivery('dlv_1'))
    await vi.waitFor(() => expect(requests).toBe(1))

    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.active)
    expect(requests).toBe(1)
    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.idle - DELIVERIES_POLL_MS.active)
    expect(requests).toBe(2)
  })

  it('doesn\'t poll a detail that isn\'t active', async () => {
    let requests = 0
    server.use(http.get('/deliveries/{delivery_id}', ({ response }) => {
      requests++
      return response(200).json(deliveryDetail({ status: 'pending' }))
    }))
    await withSetup(() => useDelivery('dlv_1', false))

    await vi.advanceTimersByTimeAsync(DELIVERIES_POLL_MS.idle)
    expect(requests).toBe(0)
  })
})

describe('useDeliveries filters', () => {
  it('sends the filters as query parameters, to both the list and the counts', async () => {
    const urls: URL[] = []
    server.use(
      http.get('/deliveries', ({ request, response }) => {
        urls.push(new URL(request.url))
        return response(200).json({ items: [], next_cursor: null })
      }),
      http.get('/deliveries/counts', ({ request, response }) => {
        urls.push(new URL(request.url))
        return response(200).json({ pending: 0, in_progress: 0, succeeded: 0, failed: 0 })
      })
    )
    const filters = { status: 'failed', endpointId: 'ep_1', eventId: 'evt_1' } as const

    await withSetup(() => [useDeliveries(filters), useDeliveryCounts(filters)])

    await vi.waitFor(() => expect(urls).toHaveLength(2))
    const [list, counts] = [urls.find(url => url.pathname.endsWith('/deliveries'))!, urls.find(url => url.pathname.endsWith('/counts'))!]
    expect(Object.fromEntries(list.searchParams)).toEqual({ status: 'failed', endpoint_id: 'ep_1', event_id: 'evt_1' })
    // The chips count every status, so the status filter doesn't apply to them.
    expect(Object.fromEntries(counts.searchParams)).toEqual({ endpoint_id: 'ep_1', event_id: 'evt_1' })
  })
})

describe('useReplayDelivery', () => {
  it('flips the row to pending at once, then rolls it back with a toast when the replay fails', async () => {
    const replayAnswer = deferred()
    server.use(
      http.get('/deliveries', ({ response }) => response(200).json({
        items: [delivery({ status: 'failed', failure_reason: 'attempts_exhausted', attempts_used: 6 })],
        next_cursor: null
      })),
      http.post('/deliveries/{delivery_id}/replay', async ({ response }) => {
        await replayAnswer.promise
        return response(409).json({ type: 'about:blank', title: 'Conflict', status: 409, detail: 'endpoint is disabled' })
      })
    )
    const [deliveries, replay] = await withSetup(() => [useDeliveries(), useReplayDelivery()] as const)
    await vi.waitFor(() => expect(deliveries.deliveries.value[0]?.status).toBe('failed'))
    // From here the list answers nothing, so the row can only go back to `failed` by rollback.
    server.use(http.get('/deliveries', () => new Promise(() => {})))

    replay.mutate('dlv_1')

    await vi.waitFor(() => expect(deliveries.deliveries.value[0]).toMatchObject({ status: 'pending', failure_reason: null, attempts_used: 0 }))
    expect(replay.isPending.value).toBe(true)

    replayAnswer.resolve()

    await vi.waitFor(() => expect(deliveries.deliveries.value[0]).toMatchObject({ status: 'failed', failure_reason: 'attempts_exhausted', attempts_used: 6 }))
    expect(useToast().toasts.value).toContainEqual(expect.objectContaining({ description: 'endpoint is disabled', color: 'error' }))
  })

  it('keeps the row pending and shows the replayed detail when the replay succeeds', async () => {
    server.use(
      http.get('/deliveries', ({ response }) => response(200).json({ items: [delivery({ status: 'failed' })], next_cursor: null })),
      http.post('/deliveries/{delivery_id}/replay', ({ response }) => response(200).json(deliveryDetail({ status: 'pending', attempts_used: 0 })))
    )
    const [deliveries, detail, replay] = await withSetup(() => [useDeliveries(), useDelivery('dlv_1'), useReplayDelivery()] as const)
    await vi.waitFor(() => expect(deliveries.deliveries.value[0]?.status).toBe('failed'))
    server.use(
      http.get('/deliveries', ({ response }) => response(200).json({ items: [delivery({ status: 'pending' })], next_cursor: null })),
      http.get('/deliveries/{delivery_id}', ({ response }) => response(200).json(deliveryDetail({ status: 'pending' })))
    )

    await replay.mutateAsync('dlv_1')

    expect(detail.data.value?.status).toBe('pending')
    await vi.waitFor(() => expect(deliveries.deliveries.value[0]?.status).toBe('pending'))
  })
})
