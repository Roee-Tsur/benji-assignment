<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Delivery, DeliveryStatus } from '~/api/client'
import type { DeliveryFilters } from '~/api/queryKeys'
import { deliveryStatuses } from '~/domain/deliveryStatus'
import { eventTypes } from '~/domain/eventTypes'

useHead({ title: 'Deliveries' })

// Filters and the open delivery live in the URL, so a view can be deep-linked and survives a reload.
const anyId = (raw: string) => raw || undefined
const status = useQueryParam('status', oneOf(Object.keys(deliveryStatuses) as DeliveryStatus[]))
const endpointId = useQueryParam('endpoint', anyId)
const eventId = useQueryParam('event', anyId)
const openDeliveryId = useQueryParam('delivery', anyId)
const filters = computed<DeliveryFilters>(() => ({ status: status.value, endpointId: endpointId.value, eventId: eventId.value }))
const filtered = computed(() => Object.values(filters.value).some(Boolean))

const route = useRoute()
const router = useRouter()
function clearFilters() {
  void router.push({ query: { delivery: route.query.delivery } })
}

const deliveries = useDeliveries(filters)
const counts = useDeliveryCounts(filters)
const endpoints = useEndpoints()
const highlighted = useStatusHighlights(() => deliveries.deliveries.value)

// Select items can't hold `undefined`, so "All endpoints" is a sentinel.
const ALL = 'all'
const endpointItems = computed(() => [
  { label: 'All endpoints', value: ALL },
  ...(endpoints.data.value ?? []).map(endpoint => ({ label: endpoint.url, value: endpoint.id }))
])
const endpointSelection = computed({
  get: () => endpointId.value ?? ALL,
  set: (value: string) => {
    endpointId.value = value === ALL ? undefined : value
  }
})

const columns: TableColumn<Delivery>[] = [
  { accessorKey: 'status', header: 'Status' },
  { id: 'progress', header: 'Progress' },
  { accessorKey: 'event_type', header: 'Event type' },
  { accessorKey: 'endpoint_url', header: 'Endpoint' },
  { accessorKey: 'created_at', header: 'Created' },
  { accessorKey: 'id', header: 'Delivery' }
]
</script>

<template>
  <UDashboardPanel id="deliveries">
    <template #header>
      <UDashboardNavbar title="Deliveries">
        <template #right>
          <!-- Only a failed poll counts; a failed "load more" is shown at the button. -->
          <DeliveriesLiveIndicator
            :updated-at="deliveries.dataUpdatedAt.value"
            :error="deliveries.isRefetchError.value ? deliveries.error.value : null"
            @retry="deliveries.refetch()"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <DeliveriesStatusChips
            v-model="status"
            :counts="counts.data.value"
          />
        </template>
        <template #right>
          <UButton
            v-if="eventId"
            :label="`Event ${eventId}`"
            trailing-icon="i-lucide-x"
            color="neutral"
            variant="subtle"
            size="sm"
            aria-label="Clear the event filter"
            @click="eventId = undefined"
          />
          <USelect
            v-model="endpointSelection"
            :items="endpointItems"
            aria-label="Filter by endpoint"
            class="w-72"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <QueryError
        v-if="deliveries.error.value && !deliveries.data.value"
        :error="deliveries.error.value"
        @retry="deliveries.refetch()"
      />
      <template v-else>
        <!-- Rows open with a click, or Enter/Space once focused; the id cell is also a plain link. -->
        <UTable
          :data="deliveries.deliveries.value"
          :columns="columns"
          :get-row-id="(row: Delivery) => row.id"
          :loading="deliveries.isPending.value || deliveries.isPlaceholderData.value"
          :meta="{ class: { tr: row => highlighted.has(row.original.id) ? 'bg-primary/10' : '' } }"
          :ui="{ tr: 'transition-colors duration-1000' }"
          @select="(_event, row) => openDeliveryId = row.original.id"
        >
          <template #empty>
            <div
              v-if="filtered"
              class="space-y-2"
            >
              <p>No deliveries match these filters.</p>
              <UButton
                label="Clear filters"
                color="neutral"
                variant="outline"
                size="sm"
                @click="clearFilters"
              />
            </div>
            <p v-else>
              No deliveries yet. <ULink
                to="/events"
                class="text-primary"
              >Trigger an event</ULink> to create some.
            </p>
          </template>
          <template #status-cell="{ row }">
            <DeliveryStatusBadge :status="row.original.status" />
          </template>
          <template #progress-cell="{ row }">
            <DeliveriesProgress :delivery="row.original" />
          </template>
          <template #event_type-cell="{ row }">
            {{ eventTypes[row.original.event_type].label }}
          </template>
          <template #endpoint_url-cell="{ row }">
            <span class="font-mono text-sm">{{ row.original.endpoint_url }}</span>
          </template>
          <template #created_at-cell="{ row }">
            <NuxtTime
              :datetime="row.original.created_at"
              date-style="medium"
              time-style="medium"
            />
          </template>
          <template #id-cell="{ row }">
            <ULink
              :to="{ query: { ...route.query, delivery: row.original.id } }"
              class="font-mono text-xs"
            >
              {{ row.original.id.slice(0, 12) }}…
            </ULink>
          </template>
        </UTable>

        <QueryError
          v-if="deliveries.isFetchNextPageError.value && deliveries.error.value"
          class="mt-4"
          :error="deliveries.error.value"
          @retry="deliveries.fetchNextPage()"
        />
        <div
          v-else-if="deliveries.hasNextPage.value"
          class="flex justify-center py-4"
        >
          <UButton
            label="Load more"
            color="neutral"
            variant="outline"
            :loading="deliveries.isFetchingNextPage.value"
            @click="deliveries.fetchNextPage()"
          />
        </div>
      </template>

      <DeliveriesSlideover v-model:delivery-id="openDeliveryId" />
    </template>
  </UDashboardPanel>
</template>
