import { describe, expect, it } from 'vitest'
import { parseEventData } from '../../app/domain/eventData'

describe('parseEventData', () => {
  it('returns a JSON object', () => {
    expect(parseEventData('{ "member_id": "mem_1", "points": 250 }')).toEqual({ data: { member_id: 'mem_1', points: 250 } })
  })

  it('explains invalid JSON with the parser\'s message', () => {
    const result = parseEventData('{ "member_id": ')

    expect(result).toEqual({ error: expect.stringMatching(/^Invalid JSON: .+/) })
  })

  it.each([
    ['an array', '[1, 2]'],
    ['null', 'null'],
    ['a string', '"hello"'],
    ['a number', '42']
  ])('rejects %s: data must be an object', (_case, json) => {
    expect(parseEventData(json)).toEqual({ error: 'Event data must be a JSON object, like { "key": "value" }.' })
  })

  it('asks for input when empty', () => {
    expect(parseEventData('  \n')).toEqual({ error: 'Enter the event data as a JSON object.' })
  })
})
