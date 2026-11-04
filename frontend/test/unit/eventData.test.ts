import { describe, expect, it } from 'vitest'
import { parseEventData } from '../../app/domain/eventData'

describe('parseEventData', () => {
  it('returns a JSON object', () => {
    expect(parseEventData('{ "member_id": "mem_1", "points": 250 }')).toEqual({ member_id: 'mem_1', points: 250 })
  })

  it.each([
    ['invalid JSON', '{ "member_id": '],
    ['an array', '[1, 2]'],
    ['null', 'null'],
    ['a string', '"hello"'],
    ['a number', '42'],
    ['empty input', '']
  ])('rejects %s', (_case, json) => {
    expect(parseEventData(json)).toBeUndefined()
  })
})
