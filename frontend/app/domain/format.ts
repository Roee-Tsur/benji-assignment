/** How every view writes numbers and times, so they read the same everywhere. */

const numberFormat = new Intl.NumberFormat('en-US')
const dateFormat = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' })
const dateTimeFormat = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'medium' })

/** `1` → `1 delivery`, `12345` → `12,345 deliveries`. */
export function formatCount(count: number, singular: string, plural: string): string {
  return `${numberFormat.format(count)} ${count === 1 ? singular : plural}`
}

/** `42` → `42 ms`, `4234` → `4.2 s`. */
export function formatMilliseconds(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`
}

/** The full local date and time, e.g. for a tooltip: `Nov 4, 2026, 10:00:00 AM`. */
export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}

const units: [seconds: number, suffix: string][] = [[86_400, 'd'], [3600, 'h'], [60, 'm'], [1, 's']]

/**
 * How long ago `iso` was, as of `now` (ms), in its largest unit: `12s ago`, `5m ago`, `3h ago`.
 * Under 5s (or slightly in the future, from clock skew) is `just now`; a week or more is the date.
 */
export function formatRelativeTime(iso: string, now: number): string {
  const seconds = Math.floor((now - Date.parse(iso)) / 1000)
  if (Number.isNaN(seconds)) return '—'
  if (seconds < 5) return 'just now'
  if (seconds >= 7 * 86_400) return dateFormat.format(new Date(iso))
  const [size, suffix] = units.find(([size]) => seconds >= size)!
  return `${Math.floor(seconds / size)}${suffix} ago`
}
