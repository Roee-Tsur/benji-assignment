import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import CreateEndpointModal from '../../app/components/CreateEndpointModal.vue'
import { endpoint } from '../msw/fixtures'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache } from './helpers'

const server = useMockApi()
afterEach(clearQueryCache)

const SECRET = 'whsec_c2hvd24tb25jZQ=='

const secretInput = () => document.querySelector<HTMLInputElement>('input[aria-label="Signing secret"]')

describe('CreateEndpointModal', () => {
  it('shows the signing secret once; after closing it is gone from the page and every cache', async () => {
    server.use(http.post('/endpoints', ({ response }) => response(201).json({ ...endpoint, secret: SECRET })))
    const open = ref(true)
    await mountSuspended(defineComponent({
      setup: () => () => h(CreateEndpointModal, { 'open': open.value, 'onUpdate:open': (value: boolean) => (open.value = value) })
    }))

    document.querySelector('form#create-endpoint')!.dispatchEvent(new Event('submit'))
    await expect.poll(() => secretInput()?.value).toBe(SECRET)

    open.value = false
    await nextTick()
    open.value = true
    await nextTick()

    expect(secretInput()).toBeNull()
    expect(document.querySelector('form#create-endpoint')).not.toBeNull()
    const queryClient = useNuxtApp().$queryClient
    await expect.poll(() => JSON.stringify(queryClient.getMutationCache().getAll().map(m => m.state.data))).not.toContain(SECRET)
    expect(JSON.stringify(queryClient.getQueryCache().getAll().map(q => q.state.data))).not.toContain(SECRET)
  })

  it('validates the URL inline once the field is left', async () => {
    const wrapper = await mountSuspended(defineComponent({
      setup: () => () => h(CreateEndpointModal, { open: true })
    }))
    const url = document.querySelector<HTMLInputElement>('form#create-endpoint input[type="url"]')!

    url.value = 'ftp://receiver.example'
    url.dispatchEvent(new Event('input'))
    url.dispatchEvent(new Event('blur'))

    await expect.poll(() => document.body.textContent).toContain('Use an http or https URL.')
    wrapper.unmount()
  })
})
