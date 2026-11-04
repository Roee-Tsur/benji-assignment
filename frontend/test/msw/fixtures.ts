import type { Attempt, Delivery, DeliveryDetail, Endpoint } from '../../app/api/client'

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

export function attempt(overrides: Partial<Attempt> = {}): Attempt {
  return {
    id: 'att_1',
    number: 1,
    started_at: '2026-11-04T10:00:00Z',
    finished_at: '2026-11-04T10:00:00.120Z',
    request_headers: { 'webhook-id': 'dlv_1', 'content-type': 'application/json' },
    outcome: 'response',
    response_status: 200,
    response_body: 'ok',
    error: null,
    ...overrides
  }
}

export function deliveryDetail(overrides: Partial<DeliveryDetail> = {}): DeliveryDetail {
  const base = delivery(overrides)
  return {
    ...base,
    payload: { id: base.event_id, type: base.event_type, timestamp: base.created_at, data: { points: 10 } },
    attempts: [attempt()],
    ...overrides
  }
}
