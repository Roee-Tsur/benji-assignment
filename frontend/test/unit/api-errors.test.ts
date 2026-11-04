import { describe, expect, it } from 'vitest'
import { ApiError, toApiError, unwrap } from '../../app/api/errors'

const response = (status: number, statusText = '') => new Response(null, { status, statusText })

describe('toApiError', () => {
  it('reads a problem document', () => {
    const error = toApiError(
      { type: 'about:blank', title: 'Not Found', status: 404, detail: 'No endpoint ep_1' },
      response(404)
    )

    expect(error).toMatchObject({ kind: 'problem', status: 404, title: 'Not Found', detail: 'No endpoint ep_1' })
    expect(error.message).toBe('No endpoint ep_1')
  })

  it('reads the issues of a validation problem into the message', () => {
    const error = toApiError({
      type: 'about:blank',
      title: 'Request validation failed',
      status: 422,
      errors: [
        { loc: ['body', 'url'], msg: 'Input should be a valid URL', type: 'url_parsing' },
        { loc: ['header', 'Idempotency-Key'], msg: 'Field required', type: 'missing' }
      ]
    }, response(422))

    expect(error.kind).toBe('problem')
    expect(error.issues).toHaveLength(2)
    expect(error.message).toBe('url: Input should be a valid URL; Idempotency-Key: Field required')
  })

  it('falls back to the HTTP status when the body is not a problem document', () => {
    const error = toApiError('<html>Bad Gateway</html>', response(502, 'Bad Gateway'))

    expect(error).toMatchObject({ kind: 'http', status: 502, title: 'Bad Gateway', detail: null })
  })

  it('treats a missing response as a network failure', () => {
    const error = toApiError(new TypeError('Failed to fetch'))

    expect(error).toMatchObject({ kind: 'network', status: null, detail: 'Failed to fetch' })
  })

  it.each([
    [toApiError(new TypeError('offline')), true],
    [toApiError({ title: 'Internal Server Error', status: 500 }, response(500)), true],
    [toApiError({ title: 'Conflict', status: 409 }, response(409)), false]
  ])('marks only network and 5xx failures as transient', (error, transient) => {
    expect(error.isTransient).toBe(transient)
  })
})

describe('unwrap', () => {
  it('returns the data of a successful call', async () => {
    await expect(unwrap(Promise.resolve({ data: { id: 'ep_1' }, response: response(200) }))).resolves.toEqual({ id: 'ep_1' })
  })

  it('throws an ApiError for an error response', async () => {
    const call = unwrap(Promise.resolve({ error: { title: 'Conflict', status: 409 }, response: response(409) }))

    await expect(call).rejects.toBeInstanceOf(ApiError)
    await expect(call).rejects.toMatchObject({ kind: 'problem', status: 409 })
  })

  it('throws an ApiError when the request never got a response', async () => {
    await expect(unwrap(Promise.reject(new TypeError('Failed to fetch')))).rejects.toMatchObject({ kind: 'network' })
  })

  it('lets cancellation through untouched, so Vue Query sees it as cancelled', async () => {
    const abort = new DOMException('Aborted', 'AbortError')

    await expect(unwrap(Promise.reject(abort))).rejects.toBe(abort)
  })
})
