export type ParsedEventData = { data: Record<string, unknown> } | { error: string }

/** Parses the trigger form's JSON into an event's `data`, which must be a JSON object, or says why it can't. */
export function parseEventData(json: string): ParsedEventData {
  if (!json.trim()) return { error: 'Enter the event data as a JSON object.' }
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch (error) {
    return { error: `Invalid JSON: ${(error as SyntaxError).message}` }
  }
  return typeof data === 'object' && data !== null && !Array.isArray(data)
    ? { data: data as Record<string, unknown> }
    : { error: 'Event data must be a JSON object, like { "key": "value" }.' }
}
