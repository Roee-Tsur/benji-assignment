/** Why an endpoint URL would be rejected, or `undefined` if it's fine. Mirrors the API's `http(s)`-only rule. */
export function endpointUrlError(url: string): string | undefined {
  const trimmed = url.trim()
  if (!trimmed) return 'Enter a URL.'
  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    return 'Enter a full URL, like https://receiver.example/webhooks.'
  }
  return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? undefined : 'Use an http or https URL.'
}
