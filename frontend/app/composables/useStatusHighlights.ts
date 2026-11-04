import type { Delivery, DeliveryStatus } from '~/api/client'
import { statusChanges } from '~/domain/deliveryProgress'

/**
 * Ids of the deliveries whose status changed within the last `ms`, so their rows can flash.
 * A delivery seen for the first time (on load, a new filter, or a new page) isn't a change.
 */
export function useStatusHighlights(deliveries: () => readonly Delivery[], ms = 1500): Readonly<Ref<ReadonlySet<string>>> {
  const seen = new Map<string, DeliveryStatus>()
  const highlighted = shallowRef<ReadonlySet<string>>(new Set())
  const timers = new Map<string, ReturnType<typeof setTimeout>>()

  function unhighlight(id: string) {
    timers.delete(id)
    highlighted.value = new Set([...highlighted.value].filter(other => other !== id))
  }

  watch(deliveries, (rows) => {
    const changed = statusChanges(seen, rows)
    for (const row of rows) seen.set(row.id, row.status)
    if (changed.length === 0) return
    highlighted.value = new Set([...highlighted.value, ...changed])
    for (const id of changed) {
      clearTimeout(timers.get(id))
      timers.set(id, setTimeout(() => unhighlight(id), ms))
    }
  }, { immediate: true })

  onScopeDispose(() => timers.forEach(clearTimeout))
  return readonly(highlighted)
}
