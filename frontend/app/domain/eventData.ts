/** Parses the trigger form's JSON into an event's `data`, which must be a JSON object; anything else is `undefined`. */
export function parseEventData(json: string): Record<string, unknown> | undefined {
  try {
    const data: unknown = JSON.parse(json)
    return typeof data === 'object' && data !== null && !Array.isArray(data) ? data as Record<string, unknown> : undefined
  } catch {
    return undefined
  }
}
