/**
 * happy-dom drops the headers of `new Request(url, { headers })` when `headers` is a `Headers`
 * instance, which is what openapi-fetch passes, so MSW handlers never saw e.g. `Idempotency-Key`.
 * Passing them as a plain record works, so convert them on the way in.
 */
const HappyDomRequest = globalThis.Request

globalThis.Request = class extends HappyDomRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.headers instanceof Headers ? { ...init, headers: Object.fromEntries(init.headers) } : init)
  }
}
