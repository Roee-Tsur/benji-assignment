import { HttpResponse } from 'msw'
import { afterEach, describe, expect, it, onTestFinished, vi } from 'vitest'
import { ApiError } from '../../app/api/errors'
import { queryKeys } from '../../app/api/queryKeys'
import { endpoint } from '../msw/fixtures'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache, withSetup } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

/**
 * Records the query keys a mutation invalidates. Asserting on keys, not on refetched deliveries,
 * keeps these tests independent of the deliveries list's shape (owned by the deliveries view).
 */
function spyOnInvalidation() {
  const spy = vi.spyOn(useNuxtApp().$queryClient, 'invalidateQueries')
  onTestFinished(() => spy.mockRestore())
  return () => spy.mock.calls.map(([filters]) => (typeof filters === 'function' ? filters() : filters)?.queryKey)
}

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
  it('invalidates deliveries after disabling, so the pending ones show as failed', async () => {
    server.use(http.patch('/endpoints/{endpoint_id}', ({ response }) => response(200).json({ ...endpoint, enabled: false })))
    const invalidated = spyOnInvalidation()
    const setEnabled = await withSetup(() => useSetEndpointEnabled())

    await setEnabled.mutateAsync({ endpointId: endpoint.id, enabled: false })

    expect(invalidated()).toEqual(expect.arrayContaining([queryKeys.endpoints.all, queryKeys.deliveries.all]))
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
  it('resolves to the replayed count and invalidates deliveries and the failed counts', async () => {
    server.use(http.post('/endpoints/{endpoint_id}/replay-failed', ({ response }) => response(200).json({ replayed: 3 })))
    const invalidated = spyOnInvalidation()
    const replayFailed = await withSetup(() => useReplayFailed())

    await expect(replayFailed.mutateAsync({ endpointId: endpoint.id })).resolves.toEqual({ replayed: 3 })

    expect(invalidated()).toEqual(expect.arrayContaining([queryKeys.endpoints.all, queryKeys.deliveries.all]))
  })
})
