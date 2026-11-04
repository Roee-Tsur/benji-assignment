import { describe, expect, it, onTestFinished } from 'vitest'
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

describe('useIdempotencyKey off a secure context', () => {
  it('still makes distinct keys without crypto.randomUUID', async () => {
    const randomUUID = crypto.randomUUID
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true })
    onTestFinished(() => {
      Object.defineProperty(crypto, 'randomUUID', { value: randomUUID, configurable: true })
    })
    const { key, renew } = await withSetup(() => useIdempotencyKey(() => 'a'))
    const first = key.value

    renew()

    expect(first).toMatch(/^[0-9a-f]{32}$/)
    expect(key.value).not.toBe(first)
  })
})
