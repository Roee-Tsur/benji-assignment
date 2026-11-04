import { describe, expect, it } from 'vitest'
import { formatCount, formatMilliseconds, formatRelativeTime, formatResponseBody } from '../../app/domain/format'

const now = Date.parse('2026-11-04T10:00:00Z')
const ago = (seconds: number) => new Date(now - seconds * 1000).toISOString()

describe('formatRelativeTime', () => {
  it.each([
    [0, 'just now'],
    [4, 'just now'],
    [12, '12s ago'],
    [59, '59s ago'],
    [60, '1m ago'],
    [125, '2m ago'],
    [3599, '59m ago'],
    [3600, '1h ago'],
    [23 * 3600, '23h ago'],
    [24 * 3600, '1d ago'],
    [6 * 24 * 3600, '6d ago']
  ])('%ss ago → %s', (seconds, expected) => {
    expect(formatRelativeTime(ago(seconds), now)).toBe(expected)
  })

  it('says "just now" for a time slightly ahead of the browser clock', () => {
    expect(formatRelativeTime(ago(-3), now)).toBe('just now')
  })

  it('shows a dash for a timestamp it cannot read, rather than throwing mid-render', () => {
    expect(formatRelativeTime('not a date', now)).toBe('—')
  })

  it('falls back to the date once it is a week old', () => {
    expect(formatRelativeTime('2026-10-01T12:00:00Z', now)).toBe('Oct 1, 2026')
  })
})

describe('formatMilliseconds', () => {
  it.each([
    [0, '0 ms'],
    [42, '42 ms'],
    [999, '999 ms'],
    [1000, '1.0 s'],
    [4234, '4.2 s'],
    [10_000, '10.0 s']
  ])('%sms → %s', (ms, expected) => {
    expect(formatMilliseconds(ms)).toBe(expected)
  })
})

describe('formatCount', () => {
  it.each([
    [0, '0 deliveries'],
    [1, '1 delivery'],
    [2, '2 deliveries'],
    [12_345, '12,345 deliveries']
  ])('%s → %s', (count, expected) => {
    expect(formatCount(count, 'delivery', 'deliveries')).toBe(expected)
  })
})

describe('formatResponseBody', () => {
  it('pretty-prints a JSON body', () => {
    expect(formatResponseBody('{"ok":true,"mode":"flaky","seen":[1,2]}')).toBe('{\n  "ok": true,\n  "mode": "flaky",\n  "seen": [\n    1,\n    2\n  ]\n}')
  })

  it.each([
    ['plain text', 'Internal Server Error'],
    ['HTML', '<html><body>502 Bad Gateway</body></html>'],
    ['JSON cut off at the 2 KB limit', '{"items":[{"id":1},{"id":'],
    ['a bare JSON scalar', '42']
  ])('leaves %s as sent', (_kind, body) => {
    expect(formatResponseBody(body)).toBe(body)
  })

  it('says the body was empty, rather than showing nothing', () => {
    expect(formatResponseBody('')).toBe('(empty)')
  })
})
