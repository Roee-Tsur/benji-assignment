import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DeliveriesPage from '../../app/pages/deliveries.vue'
import { delivery, deliveryDetail } from '../msw/fixtures'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

/** Records the query string of every list request. */
function recordListRequests() {
  const queries: Record<string, string>[] = []
  server.use(http.get('/deliveries', ({ request, response }) => {
    queries.push(Object.fromEntries(new URL(request.url).searchParams))
    return response(200).json({ items: [delivery()], next_cursor: null })
  }))
  return queries
}

describe('deliveries page', () => {
  it('reads its filters from the URL, writes them back as history entries, and follows the back button', async () => {
    const queries = recordListRequests()
    const page = await mountSuspended(DeliveriesPage, { route: '/deliveries?status=failed&endpoint=ep_1' })
    const router = useRouter()
    const chip = (label: string) => page.findAll('button').find(button => button.text().startsWith(label))!

    await vi.waitFor(() => expect(queries).toContainEqual({ status: 'failed', endpoint_id: 'ep_1' }))
    expect(chip('Failed').attributes('aria-pressed')).toBe('true')

    await chip('Pending').trigger('click')

    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ status: 'pending', endpoint: 'ep_1' }))
    await vi.waitFor(() => expect(queries).toContainEqual({ status: 'pending', endpoint_id: 'ep_1' }))

    router.back()

    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ status: 'failed', endpoint: 'ep_1' }))
    await vi.waitFor(() => expect(chip('Failed').attributes('aria-pressed')).toBe('true'))
  })

  it('opens the delivery named in the URL in a slideover, and opening a row puts it in the URL', async () => {
    server.use(http.get('/deliveries/{delivery_id}', ({ params, response }) => response(200).json(deliveryDetail({ id: params.delivery_id }))))
    const page = await mountSuspended(DeliveriesPage, { route: '/deliveries?delivery=dlv_deep' })
    const router = useRouter()

    await vi.waitFor(() => expect(document.body.textContent).toContain('Delivery dlv_deep'))
    await vi.waitFor(() => expect(document.body.textContent).toContain('Attempt 1'))

    await router.push({ query: {} })
    await vi.waitFor(() => expect(page.findAll('tbody tr')).toHaveLength(1))
    await page.find('tbody tr').trigger('keydown', { key: 'Enter' })

    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ delivery: 'dlv_1' }))
  })
})
