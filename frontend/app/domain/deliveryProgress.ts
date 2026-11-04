import type { Attempt, Delivery, DeliveryStatus, FailureReason } from '~/api/client'

/** A `Record` so a new failure reason fails typecheck until it has a label. */
export const failureReasons: Record<FailureReason, string> = {
  attempts_exhausted: 'Attempts exhausted',
  endpoint_disabled: 'Endpoint disabled',
  endpoint_gone: 'Endpoint gone (410)'
}

/** `125` → `2m 5s`: the two largest units, rounded to the second. */
export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const parts: [number, string][] = [[Math.floor(total / 3600), 'h'], [Math.floor(total / 60) % 60, 'm'], [total % 60, 's']]
  const first = parts.findIndex(([value]) => value > 0)
  if (first === -1) return '0s'
  return parts.slice(first, first + 2).filter(([value]) => value > 0).map(([value, unit]) => `${value}${unit}`).join(' ')
}

/**
 * One line on where a delivery stands, as of `now` (ms): for a pending one,
 * "attempt 3/6 · next in 12s", numbered within the current attempt budget.
 */
export function deliveryProgress(delivery: Delivery, now: number): string {
  const nextAttempt = `attempt ${delivery.attempts_used + 1}/${delivery.attempt_budget}`
  switch (delivery.status) {
    case 'pending': {
      const seconds = (Date.parse(delivery.next_attempt_at) - now) / 1000
      return `${nextAttempt} · ${seconds >= 0.5 ? `next in ${formatDuration(seconds)}` : 'due now'}`
    }
    case 'in_progress':
      return `${nextAttempt} · sending`
    case 'failed':
      return delivery.failure_reason ? failureReasons[delivery.failure_reason] : 'Failed'
    case 'succeeded':
      return delivery.attempts_used === 1 ? '1 attempt' : `${delivery.attempts_used} attempts`
  }
}

const outcomeLabels: Record<Exclude<Attempt['outcome'], 'response'>, string> = {
  // The receiver may have processed it; the retry carries the same `webhook-id` so it can dedupe.
  timeout: 'Timed out (outcome unknown)',
  connection_error: 'Connection error',
  interrupted: 'Interrupted'
}

export function attemptOutcome(attempt: Attempt): { label: string, ok: boolean } {
  if (attempt.outcome !== 'response') return { label: outcomeLabels[attempt.outcome], ok: false }
  const status = attempt.response_status ?? 0
  return { label: `HTTP ${status}`, ok: status >= 200 && status < 300 }
}

/** Ids of the deliveries whose status changed since `seen`; ones not in `seen` are new, not changed. */
export function statusChanges(seen: ReadonlyMap<string, DeliveryStatus>, deliveries: readonly Delivery[]): string[] {
  return deliveries
    .filter(delivery => seen.has(delivery.id) && seen.get(delivery.id) !== delivery.status)
    .map(delivery => delivery.id)
}
