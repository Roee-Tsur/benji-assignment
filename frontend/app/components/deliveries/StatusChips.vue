<script setup lang="ts">
import type { DeliveryStatus, Schemas } from '~/api/client'
import { deliveryStatuses } from '~/domain/deliveryStatus'

const props = defineProps<{ counts?: Schemas['DeliveryCounts'] }>()
/** The status filter; `undefined` is "All". */
const status = defineModel<DeliveryStatus | undefined>()

const chips = computed(() => [
  { value: undefined, label: 'All', icon: 'i-lucide-list', color: 'neutral' as const, count: props.counts && Object.values(props.counts).reduce((sum, n) => sum + n, 0) },
  ...(Object.keys(deliveryStatuses) as DeliveryStatus[]).map(value => ({ value, ...deliveryStatuses[value], count: props.counts?.[value] }))
])
</script>

<template>
  <div
    role="group"
    aria-label="Filter by status"
    class="flex flex-wrap gap-2"
  >
    <UButton
      v-for="chip in chips"
      :key="chip.label"
      :icon="chip.icon"
      :color="chip.color"
      :variant="status === chip.value ? 'solid' : 'outline'"
      :aria-pressed="status === chip.value"
      size="sm"
      @click="status = chip.value"
    >
      {{ chip.label }}
      <span
        v-if="chip.count !== undefined"
        class="tabular-nums opacity-80"
      >{{ chip.count }}</span>
    </UButton>
  </div>
</template>
