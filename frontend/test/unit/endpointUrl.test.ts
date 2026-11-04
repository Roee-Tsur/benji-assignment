import { describe, expect, it } from 'vitest'
import { endpointUrlError } from '../../app/domain/endpointUrl'

describe('endpointUrlError', () => {
  it.each([
    'https://receiver.example/hooks',
    'http://127.0.0.1:8000/mock/ok',
    '  https://receiver.example  '
  ])('accepts %s', (url) => {
    expect(endpointUrlError(url)).toBeUndefined()
  })

  it.each([
    ['empty', '', 'Enter a URL.'],
    ['not a URL', 'receiver.example/hooks', 'Enter a full URL, like https://receiver.example/webhooks.'],
    ['another scheme', 'ftp://receiver.example', 'Use an http or https URL.']
  ])('rejects %s', (_case, url, message) => {
    expect(endpointUrlError(url)).toBe(message)
  })
})
