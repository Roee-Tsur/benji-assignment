import { describe, expect, it } from 'vitest'
import { withSetup } from './helpers'

describe('useIdempotencyKey', () => {
  it('keeps the key while the submission is unchanged or invalid, and replaces it when it changes', async () => {
    const submission = ref<string | undefined>('a')
    const { key } = await withSetup(() => useIdempotencyKey(() => submission.value))
    const first = key.value

    submission.value = undefined
    await nextTick()
    submission.value = 'a'
    await nextTick()
    expect(key.value).toBe(first)

    submission.value = 'b'
    await nextTick()
    expect(key.value).not.toBe(first)
  })

  it('replaces the key on renew', async () => {
    const { key, renew } = await withSetup(() => useIdempotencyKey(() => 'a'))
    const first = key.value

    renew()

    expect(key.value).not.toBe(first)
  })
})
