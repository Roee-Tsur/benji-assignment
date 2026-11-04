import type { Delivery, Endpoint, Event } from '../../app/api/client'

export const endpoint: Endpoint = {
  id: 'ep_1',
  url: 'http://127.0.0.1:8000/mock/ok',
  event_types: ['reward_transaction_created'],
  enabled: true,
  created_at: '2026-11-04T10:00:00Z'
}

export function delivery(overrides: Partial<Delivery> = {}): Delivery {
  return {
    id: 'dlv_1',
    event_id: 'evt_1',
    event_type: 'reward_transaction_created',
    endpoint_id: endpoint.id,
    endpoint_url: endpoint.url,
    status: 'succeeded',
    failure_reason: null,
    attempt_count: 1,
    attempts_used: 1,
    attempt_budget: 6,
    next_attempt_at: '2026-11-04T10:00:00Z',
    created_at: '2026-11-04T10:00:00Z',
    updated_at: '2026-11-04T10:00:01Z',
    ...overrides
  }
}

export function event(overrides: Partial<Event> = {}): Event {
  return {
    id: 'evt_1',
    type: 'reward_transaction_created',
    idempotency_key: 'key-1',
    created_at: '2026-11-04T10:00:00Z',
    delivery_count: 1,
    ...overrides
  }
}
