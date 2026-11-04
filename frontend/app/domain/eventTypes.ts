import type { EventType } from '~/api/client'

/** Every event type with a sample payload for the trigger form; a `Record` so none can be missed. */
export const eventTypes: Record<EventType, { label: string, sample: Record<string, unknown> }> = {
  reward_transaction_created: {
    label: 'Reward transaction created',
    sample: { transaction_id: 'txn_123', member_id: 'mem_456', points: 250 }
  },
  campaign_updated: {
    label: 'Campaign updated',
    sample: { campaign_id: 'cmp_789', status: 'active' }
  },
  member_account_linked: {
    label: 'Member account linked',
    sample: { member_id: 'mem_456', account_id: 'acct_321' }
  }
}

export const eventTypeOptions = (Object.keys(eventTypes) as EventType[])
  .map(value => ({ value, label: eventTypes[value].label }))
