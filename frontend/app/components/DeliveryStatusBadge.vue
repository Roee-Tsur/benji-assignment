<script setup lang="ts">
import type { DeliveryStatus } from '~/api/client'
import { deliveryStatuses } from '~/domain/deliveryStatus'

const props = defineProps<{ status: DeliveryStatus }>()
const meta = computed(() => deliveryStatuses[props.status])
</script>

<template>
  <!-- Color, icon, and text together: status is never conveyed by color alone. -->
  <UBadge
    :color="meta.color"
    :icon="meta.icon"
    :label="meta.label"
    variant="subtle"
  />
</template>
