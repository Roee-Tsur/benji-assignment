<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Delivery } from '~/api/client'
import { eventTypes } from '~/domain/eventTypes'

useHead({ title: 'Deliveries' })

const deliveries = useDeliveries()

const columns: TableColumn<Delivery>[] = [
  { accessorKey: 'status', header: 'Status' },
  { accessorKey: 'event_type', header: 'Event type' },
  { accessorKey: 'endpoint_url', header: 'Endpoint' },
  { accessorKey: 'attempts_used', header: 'Attempts' },
  { accessorKey: 'created_at', header: 'Created' }
]
</script>

<template>
  <UDashboardPanel id="deliveries">
    <template #header>
      <UDashboardNavbar title="Deliveries" />
    </template>

    <template #body>
      <QueryError
        v-if="deliveries.error.value"
        :error="deliveries.error.value"
        @retry="deliveries.refetch()"
      />
      <UTable
        v-else
        :data="deliveries.data.value ?? []"
        :columns="columns"
        :loading="deliveries.isPending.value"
        empty="No deliveries yet. Trigger an event to create some."
      >
        <template #status-cell="{ row }">
          <DeliveryStatusBadge :status="row.original.status" />
        </template>
        <template #event_type-cell="{ row }">
          {{ eventTypes[row.original.event_type].label }}
        </template>
        <template #endpoint_url-cell="{ row }">
          <span class="font-mono text-sm">{{ row.original.endpoint_url }}</span>
        </template>
        <template #attempts_used-cell="{ row }">
          {{ row.original.attempts_used }}/{{ row.original.attempt_budget }}
        </template>
        <template #created_at-cell="{ row }">
          <NuxtTime
            :datetime="row.original.created_at"
            date-style="medium"
            time-style="medium"
          />
        </template>
      </UTable>
    </template>
  </UDashboardPanel>
</template>
