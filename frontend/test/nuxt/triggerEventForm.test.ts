import { mountSuspended } from '@nuxt/test-utils/runtime'
import type { VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import type { EventSubmitted } from '../../app/api/client'
import TriggerEventForm from '../../app/components/TriggerEventForm.vue'
import { http } from '../msw/http'
import { useMockApi } from '../msw/server'
import { clearQueryCache } from './helpers'

const server = useMockApi()
afterEach(() => {
  clearQueryCache()
  useToast().clear()
})

/** A fake `POST /events` with the real dedup rule (same key → the original event), recording each request. */
function acceptEvents({ deliveryCount = 2 } = {}) {
  const submissions: { key: string, data: unknown }[] = []
  const originals = new Map<string, EventSubmitted>()
  server.use(http.post('/events', async ({ request, response }) => {
    const key = request.headers.get('Idempotency-Key')!
    const body = await request.json()
    submissions.push({ key, data: body.data })
    const original = originals.get(key)
    if (original) return response(200).json({ ...original, deduplicated: true })
    const created: EventSubmitted = {
      id: `evt_${originals.size + 1}`,
      type: body.type,
      data: body.data,
      idempotency_key: key,
      created_at: '2026-11-04T10:00:00Z',
      delivery_count: deliveryCount,
      deduplicated: false
    }
    originals.set(key, created)
    return response(201).json(created)
  }))
  return submissions
}

function button(wrapper: VueWrapper, label: string) {
  const found = wrapper.findAll('button').find(b => b.text() === label)
  if (!found) throw new Error(`No "${label}" button`)
  return found
}

async function submit(wrapper: VueWrapper, submissions: unknown[]) {
  const before = submissions.length
  await wrapper.find('form').trigger('submit')
  await expect.poll(() => submissions.length).toBe(before + 1)
}

describe('TriggerEventForm', () => {
  it('keeps the key across resubmits, so the resubmit is deduplicated and says so', async () => {
    const submissions = acceptEvents()
    const wrapper = await mountSuspended(TriggerEventForm)

    await submit(wrapper, submissions)
    await expect.poll(() => wrapper.text()).toContain('Event triggered')
    await submit(wrapper, submissions)

    expect(submissions[1]!.key).toBe(submissions[0]!.key)
    await expect.poll(() => wrapper.text()).toContain('Duplicate submission')
    expect(wrapper.text()).toContain('No new deliveries were created')
  })

  it('says when an event fanned out to no deliveries, and points at the endpoints', async () => {
    const submissions = acceptEvents({ deliveryCount: 0 })
    const wrapper = await mountSuspended(TriggerEventForm)

    await submit(wrapper, submissions)

    await expect.poll(() => wrapper.text()).toContain('Event triggered, but nothing to deliver')
    expect(wrapper.text()).toContain('No enabled endpoint is subscribed to reward transaction created events')
    expect(wrapper.find('a[href="/endpoints"]').exists()).toBe(true)
  })

  it('replaces the key when the data changes, but not when it is only reformatted', async () => {
    const submissions = acceptEvents()
    const wrapper = await mountSuspended(TriggerEventForm)
    const textarea = wrapper.find('textarea')
    const sample = JSON.parse(textarea.element.value)

    await submit(wrapper, submissions)
    await textarea.setValue(JSON.stringify(sample))
    await button(wrapper, 'Format').trigger('click')
    await submit(wrapper, submissions)
    await textarea.setValue(JSON.stringify({ ...sample, points: 1 }))
    await submit(wrapper, submissions)

    const [first, reformatted, changed] = submissions.map(s => s.key)
    expect(reformatted).toBe(first)
    expect(changed).not.toBe(first)
  })

  it('replaces the key on "New key"', async () => {
    const submissions = acceptEvents()
    const wrapper = await mountSuspended(TriggerEventForm)

    await submit(wrapper, submissions)
    await button(wrapper, 'New key').trigger('click')
    await submit(wrapper, submissions)

    expect(submissions[1]!.key).not.toBe(submissions[0]!.key)
  })

  it('explains a key reused for a different payload inline, not as a toast', async () => {
    server.use(http.post('/events', ({ response }) => response(422).json({
      type: 'about:blank',
      title: 'Unprocessable Content',
      status: 422,
      detail: 'idempotency key \'k\' was already used for a different payload'
    })))
    const wrapper = await mountSuspended(TriggerEventForm)

    await wrapper.find('form').trigger('submit')

    await expect.poll(() => wrapper.text()).toContain('This key was already used for a different event')
    expect(useToast().toasts.value).toEqual([])
  })

  it('shows invalid JSON inline and won\'t submit it', async () => {
    const submissions = acceptEvents()
    const wrapper = await mountSuspended(TriggerEventForm)

    await wrapper.find('textarea').setValue('{ "points": ')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('Invalid JSON')
    expect(button(wrapper, 'Trigger event').attributes('disabled')).toBeDefined()
    expect(button(wrapper, 'Format').attributes('disabled')).toBeDefined()
    expect(submissions).toEqual([])
  })
})
