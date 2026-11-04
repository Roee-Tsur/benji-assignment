import { describe, expect, it } from 'vitest'
import { withSetup } from './helpers'

const statuses = ['pending', 'failed'] as const

describe('useQueryParam', () => {
  it('reads an allowed value from the URL and ignores anything else', async () => {
    const router = useRouter()
    const status = await withSetup(() => useQueryParam('status', oneOf(statuses)))

    await router.push({ query: { status: 'failed' } })
    expect(status.value).toBe('failed')

    await router.push({ query: { status: 'bogus' } })
    expect(status.value).toBeUndefined()
  })

  it('writes to the URL as a history entry, keeping other params, and removes itself when cleared', async () => {
    const router = useRouter()
    const status = await withSetup(() => useQueryParam('status', oneOf(statuses)))
    await router.push({ query: { endpoint: 'ep_1' } }) // after mounting, which navigates to `/`

    status.value = 'pending'
    await expect.poll(() => router.currentRoute.value.query).toEqual({ endpoint: 'ep_1', status: 'pending' })

    status.value = undefined
    await expect.poll(() => router.currentRoute.value.query).toEqual({ endpoint: 'ep_1' })
  })
})
