import { HttpResponse } from 'msw'
import { afterEach, describe, expect, it, onTestFinished } from 'vitest'
import { ApiError } from '../../app/api/errors'
import { endpoint } from '../msw/fixtures'
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
