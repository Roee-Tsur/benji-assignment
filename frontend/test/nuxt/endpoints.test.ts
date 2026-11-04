import { HttpResponse } from 'msw'
import { afterEach, describe, expect, it, onTestFinished } from 'vitest'
import { ApiError } from '../../app/api/errors'
import { delivery, endpoint } from '../msw/fixtures'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache, withSetup } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

describe('useEndpoints', () => {
  it('loads endpoints through the API layer', async () => {
    const endpoints = await withSetup(() => useEndpoints())

    await expect.poll(() => endpoints.data.value).toEqual([endpoint])
  })

  it('retries a server error, then exposes it as an ApiError', async () => {
    let requests = 0
    server.use(http.get('/endpoints', ({ response }) => {
      requests++
      // Undeclared in the schema (any route can 500), hence untyped.
      return response.untyped(HttpResponse.json(
        { type: 'about:blank', title: 'Internal Server Error', status: 500 },
        { status: 500, headers: { 'content-type': 'application/problem+json' } }
      ))
    }))
    const queryClient = useNuxtApp().$queryClient
    const defaults = queryClient.getDefaultOptions()
    queryClient.setDefaultOptions({ ...defaults, queries: { ...defaults.queries, retryDelay: 0 } })
    onTestFinished(() => queryClient.setDefaultOptions(defaults))
    const endpoints = await withSetup(() => useEndpoints())

    await expect.poll(() => endpoints.error.value).toBeInstanceOf(ApiError)
    expect(endpoints.error.value).toMatchObject({ kind: 'problem', status: 500 })
    expect(requests).toBe(3)
  })
})

describe('useCreateEndpoint', () => {
  it('normalizes a validation problem into an ApiError with its issues', async () => {
    server.use(http.post('/endpoints', ({ response }) => response(422).json({
      type: 'about:blank',
      title: 'Request validation failed',
      status: 422,
      errors: [{ loc: ['body', 'url'], msg: 'Input should be a valid URL', type: 'url_parsing' }]
    })))
    const createEndpoint = await withSetup(() => useCreateEndpoint())

    const error: unknown = await createEndpoint.mutateAsync({ url: 'nope', event_types: ['campaign_updated'] }).catch(e => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ kind: 'problem', status: 422, message: 'url: Input should be a valid URL' })
  })
})

describe('useSetEndpointEnabled', () => {
  it('refetches deliveries after disabling, so the pending ones show as failed', async () => {
    let disabled = false
    server.use(
      http.patch('/endpoints/{endpoint_id}', async ({ request, response }) => {
        disabled = !(await request.json()).enabled
        return response(200).json({ ...endpoint, enabled: !disabled })
      }),
      http.get('/deliveries', ({ response }) => response(200).json([
        delivery(disabled ? { status: 'failed', failure_reason: 'endpoint_disabled' } : { status: 'pending' })
      ]))
    )
    const { deliveries, setEnabled } = await withSetup(() => ({ deliveries: useDeliveries(), setEnabled: useSetEndpointEnabled() }))
    await expect.poll(() => deliveries.data.value?.[0]?.status).toBe('pending')

    await setEnabled.mutateAsync({ endpointId: endpoint.id, enabled: false })

    await expect.poll(() => deliveries.data.value?.[0]?.status).toBe('failed')
  })

  it('reports which endpoint has a request in flight', async () => {
    let respond!: () => void
    server.use(http.patch('/endpoints/{endpoint_id}', async ({ response }) => {
      await new Promise<void>(resolve => (respond = resolve))
      return response(200).json({ ...endpoint, enabled: false })
    }))
    const setEnabled = await withSetup(() => useSetEndpointEnabled())

    const done = setEnabled.mutateAsync({ endpointId: 'ep_1', enabled: false })

    await expect.poll(() => setEnabled.isPendingFor('ep_1')).toBe(true)
    expect(setEnabled.isPendingFor('ep_2')).toBe(false)
    await expect.poll(() => respond).toBeTypeOf('function')
    respond()
    await done
    await expect.poll(() => setEnabled.isPendingFor('ep_1')).toBe(false)
  })
})

describe('useReplayFailed', () => {
  it('resolves to the replayed count and refetches deliveries', async () => {
    let deliveryRequests = 0
    server.use(
      http.post('/endpoints/{endpoint_id}/replay-failed', ({ response }) => response(200).json({ replayed: 3 })),
      http.get('/deliveries', ({ response }) => {
        deliveryRequests++
        return response(200).json([delivery()])
      })
    )
    const { deliveries, replayFailed } = await withSetup(() => ({ deliveries: useDeliveries(), replayFailed: useReplayFailed() }))
    await expect.poll(() => deliveries.data.value).toBeDefined()
    const before = deliveryRequests

    await expect(replayFailed.mutateAsync({ endpointId: endpoint.id })).resolves.toEqual({ replayed: 3 })

    await expect.poll(() => deliveryRequests).toBeGreaterThan(before)
  })
})
