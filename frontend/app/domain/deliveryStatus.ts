import type { DeliveryStatus } from '~/api/client'

type BadgeColor = 'neutral' | 'info' | 'success' | 'error'

/** How each delivery status looks and behaves; a `Record` so a new status fails typecheck until handled. */
export const deliveryStatuses: Record<DeliveryStatus, { label: string, color: BadgeColor, icon: string, terminal: boolean }> = {
  pending: { label: 'Pending', color: 'neutral', icon: 'i-lucide-clock', terminal: false },
  in_progress: { label: 'In progress', color: 'info', icon: 'i-lucide-loader-circle', terminal: false },
  succeeded: { label: 'Succeeded', color: 'success', icon: 'i-lucide-circle-check', terminal: true },
  failed: { label: 'Failed', color: 'error', icon: 'i-lucide-circle-x', terminal: true }
}
