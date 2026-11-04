<script setup lang="ts">
import type { Delivery } from '~/api/client'
import { deliveryProgress } from '~/domain/deliveryProgress'

const props = defineProps<{ delivery: Delivery }>()

// Read here rather than in the table, so each tick re-renders this text, not every row.
const now = useClock()
const text = computed(() => deliveryProgress(props.delivery, now.value.getTime()))
</script>

<template>
  <span
    class="text-sm tabular-nums"
    :class="delivery.status === 'failed' ? 'text-error' : 'text-muted'"
  >{{ text }}</span>
</template>
