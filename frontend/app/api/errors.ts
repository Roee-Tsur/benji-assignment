import type { components } from './schema'

type Problem = components['schemas']['Problem']
export type ValidationIssue = components['schemas']['ValidationIssue']

/**
 * - `problem`: the API answered with an RFC 9457 problem document.
 * - `http`: an error response that isn't one (e.g. a proxy's 502 page).
 * - `network`: no response at all.
 */
export type ApiErrorKind = 'problem' | 'http' | 'network'

/** The one error type the API layer throws; every view renders failures from it. */
export class ApiError extends Error {
  override readonly name = 'ApiError'

  constructor(
    readonly kind: ApiErrorKind,
    readonly status: number | null,
    readonly title: string,
    readonly detail: string | null = null,
    readonly issues: readonly ValidationIssue[] = []
  ) {
    super(detail ?? (issues.length > 0 ? issues.map(formatIssue).join('; ') : title))
  }

  /** Worth retrying automatically: the request may succeed unchanged. */
  get isTransient(): boolean {
    return this.status === null || this.status >= 500
  }
}

/** Normalizes whatever a failed request produced into an `ApiError`. */
export function toApiError(error: unknown, response?: Response): ApiError {
  if (error instanceof ApiError) return error
  if (!response) {
    return new ApiError('network', null, 'Can\'t reach the API', error instanceof Error ? error.message : null)
  }
  if (isProblem(error)) {
    const issues = 'errors' in error && Array.isArray(error.errors) ? error.errors as ValidationIssue[] : []
    return new ApiError('problem', error.status, error.title, error.detail ?? null, issues)
  }
  return new ApiError('http', response.status, response.statusText || `HTTP ${response.status}`)
}

/** Awaits an `openapi-fetch` call and returns its data, or throws an `ApiError`. */
export async function unwrap<T>(
  request: Promise<{ data?: T, error?: unknown, response: Response }>
): Promise<T> {
  let result
  try {
    result = await request
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error // Vue Query cancelled it
    throw toApiError(error)
  }
  if (!result.response.ok) throw toApiError(result.error, result.response)
  return result.data as T
}

function isProblem(body: unknown): body is Problem {
  return typeof body === 'object' && body !== null
    && typeof (body as Problem).status === 'number'
    && typeof (body as Problem).title === 'string'
}

/** `{ loc: ['body', 'url'], msg }` → `url: msg`; the first segment only says where the value came from. */
function formatIssue(issue: ValidationIssue): string {
  const field = issue.loc.slice(1).join('.')
  return field ? `${field}: ${issue.msg}` : issue.msg
}
