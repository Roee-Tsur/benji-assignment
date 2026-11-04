import { describe, expect, it } from 'vitest'
import { attemptOutcome, deliveryProgress, formatDuration, statusChanges } from '../../app/domain/deliveryProgress'
import { attempt, delivery } from '../msw/fixtures'

const now = Date.parse('2026-11-04T10:00:00Z')
const inSeconds = (seconds: number) => new Date(now + seconds * 1000).toISOString()

describe('formatDuration', () => {
  it.each([
    [0, '0s'],
    [12.4, '12s'],
    [59.6, '1m'],
    [125, '2m 5s'],
    [3600, '1h'],
    [3725, '1h 2m']
  ])('%ss → %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected)
  })
})

describe('deliveryProgress', () => {
  it('counts down to a pending delivery\'s next attempt, numbered within its budget', () => {
    const pending = delivery({ status: 'pending', attempts_used: 2, attempt_budget: 6, next_attempt_at: inSeconds(12) })

    expect(deliveryProgress(pending, now)).toBe('attempt 3/6 · next in 12s')
  })

  it('says a pending delivery is due once its time has passed', () => {
    const due = delivery({ status: 'pending', attempts_used: 0, next_attempt_at: inSeconds(-3) })

    expect(deliveryProgress(due, now)).toBe('attempt 1/6 · due now')
  })

  it('shows the attempt underway for a delivery in progress', () => {
    expect(deliveryProgress(delivery({ status: 'in_progress', attempts_used: 1 }), now)).toBe('attempt 2/6 · sending')
  })

  it('shows a failed delivery\'s failure reason', () => {
    const failed = delivery({ status: 'failed', failure_reason: 'attempts_exhausted', attempts_used: 6 })

    expect(deliveryProgress(failed, now)).toBe('Attempts exhausted')
  })

  it('counts a succeeded delivery\'s attempts', () => {
    expect(deliveryProgress(delivery({ status: 'succeeded', attempts_used: 1 }), now)).toBe('1 attempt')
    expect(deliveryProgress(delivery({ status: 'succeeded', attempts_used: 3 }), now)).toBe('3 attempts')
  })
})

describe('attemptOutcome', () => {
  it('names a response by its HTTP status', () => {
    expect(attemptOutcome(attempt({ outcome: 'response', response_status: 503 }))).toEqual({ label: 'HTTP 503', ok: false })
    expect(attemptOutcome(attempt({ outcome: 'response', response_status: 204 }))).toEqual({ label: 'HTTP 204', ok: true })
  })

  it('says a timeout\'s outcome is unknown, since the receiver may have processed it', () => {
    expect(attemptOutcome(attempt({ outcome: 'timeout', response_status: null }))).toEqual({ label: 'Timed out (outcome unknown)', ok: false })
  })
})

describe('statusChanges', () => {
  it('lists deliveries whose status differs from the last one seen, ignoring ones not seen before', () => {
    const seen = new Map([['dlv_1', 'pending'], ['dlv_2', 'pending']] as const)
    const rows = [
      delivery({ id: 'dlv_1', status: 'in_progress' }),
      delivery({ id: 'dlv_2', status: 'pending' }),
      delivery({ id: 'dlv_3', status: 'failed' })
    ]

    expect(statusChanges(seen, rows)).toEqual(['dlv_1'])
  })
})
