import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { UApp } from '#components'
import EndpointsPage from '../../app/pages/endpoints.vue'
import { endpoint } from '../msw/fixtures'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

describe('endpoints page', () => {
  it('says how many deliveries "Replay failed" would retry, and disables it when there are none', async () => {
    server.use(http.get('/endpoints', ({ response }) => response(200).json([
      { ...endpoint, id: 'ep_failing', url: 'http://failing.test/hook', failed_count: 3 },
      { ...endpoint, id: 'ep_healthy', url: 'http://healthy.test/hook', failed_count: 0 }
    ])))
    // UApp provides the tooltip context the page's buttons sit in.
    const page = await mountSuspended(defineComponent({ setup: () => () => h(UApp, () => h(EndpointsPage)) }))
    const button = (ariaLabel: string) => page.find(`button[aria-label="${ariaLabel}"]`)

    await vi.waitFor(() => expect(button('Replay 3 failed: http://failing.test/hook').exists()).toBe(true))
    expect(button('Replay 3 failed: http://failing.test/hook').text()).toBe('Replay 3 failed')
    expect(button('Replay 3 failed: http://failing.test/hook').attributes('disabled')).toBeUndefined()
    expect(button('Replay failed: http://healthy.test/hook').attributes('disabled')).toBeDefined()
  })
})
