<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Endpoint } from '~/api/client'
import { eventTypes } from '~/domain/eventTypes'
import { formatCount } from '~/domain/format'

useHead({ title: 'Endpoints' })

const endpoints = useEndpoints()
const loadError = useLoadError(endpoints)
const setEnabled = useSetEndpointEnabled()
const replayFailed = useReplayFailed()
const toast = useToast()
const creating = ref(false)

function toggle(endpoint: Endpoint, enabled: boolean) {
  setEnabled.mutate({ endpointId: endpoint.id, enabled }, {
    onSuccess: () => toast.add(enabled
      ? { title: 'Endpoint enabled', description: 'Its failed deliveries stay failed until you replay them.', color: 'success', icon: 'i-lucide-circle-check' }
      : { title: 'Endpoint disabled', description: 'Its pending deliveries were marked failed. Enable it and use "Replay failed" to recover them.', color: 'neutral', icon: 'i-lucide-circle-pause' })
  })
}

function replay(endpoint: Endpoint) {
  replayFailed.mutate({ endpointId: endpoint.id }, {
    onSuccess: ({ replayed }) => toast.add({
      title: replayed === 0 ? 'No failed deliveries to replay' : `Replayed ${formatCount(replayed, 'failed delivery', 'failed deliveries')}`,
      color: replayed === 0 ? 'neutral' : 'success',
      icon: 'i-lucide-rotate-ccw',
      actions: replayed === 0 ? undefined : [{ label: 'View deliveries', to: { path: '/deliveries', query: { endpoint: endpoint.id } } }]
    })
  })
}

// Fixed widths, so toggling an endpoint or a refetch doesn't shift the columns; the URL takes the rest.
const columns: TableColumn<Endpoint>[] = [
  { accessorKey: 'url', header: 'URL', meta: { class: { td: 'truncate' } } },
  { accessorKey: 'event_types', header: 'Event types', meta: { class: { th: 'w-96', td: 'whitespace-normal' } } },
  { accessorKey: 'enabled', header: 'Status', meta: { class: { th: 'w-36' } } },
  { accessorKey: 'created_at', header: 'Created', meta: { class: { th: 'w-28' } } },
  { id: 'actions', header: 'Actions', meta: { class: { th: 'w-44' } } }
]
</script>

<template>
  <UDashboardPanel id="endpoints">
    <template #header>
      <UDashboardNavbar title="Endpoints">
        <template #right>
          <UButton
            icon="i-lucide-plus"
            label="New endpoint"
            @click="creating = true"
          />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <QueryError
        v-if="loadError"
        :error="loadError"
        @retry="endpoints.refetch()"
      />
      <UTable
        v-else
        :data="endpoints.data.value ?? []"
        :columns="columns"
        :ui="{ base: 'w-full table-fixed' }"
      >
        <template #empty>
          <TableSkeleton v-if="endpoints.isPending.value" />
          <UEmpty
            v-else
            variant="naked"
            icon="i-lucide-webhook"
            title="No endpoints yet"
            description="An endpoint is a URL that receives a signed notification for each event type it subscribes to."
            :actions="[{ label: 'New endpoint', icon: 'i-lucide-plus', onClick: () => { creating = true } }]"
          />
        </template>
        <template #url-cell="{ row }">
          <span
            class="font-mono text-sm"
            :title="row.original.url"
          >{{ row.original.url }}</span>
        </template>
        <template #event_types-cell="{ row }">
          <div class="flex flex-wrap gap-1">
            <UBadge
              v-for="type in row.original.event_types"
              :key="type"
              :label="eventTypes[type].label"
              color="neutral"
              variant="outline"
            />
          </div>
        </template>
        <template #enabled-cell="{ row }">
          <!-- The visible label carries the state as text; the accessible name repeats it and says which endpoint. -->
          <USwitch
            :model-value="row.original.enabled"
            :label="row.original.enabled ? 'Enabled' : 'Disabled'"
            :aria-label="`${row.original.enabled ? 'Enabled' : 'Disabled'}: ${row.original.url}`"
            :loading="setEnabled.isPendingFor(row.original.id)"
            @update:model-value="enabled => toggle(row.original, enabled)"
          />
        </template>
        <template #created_at-cell="{ row }">
          <RelativeTime :datetime="row.original.created_at" />
        </template>
        <template #actions-cell="{ row }">
          <UTooltip
            :text="row.original.enabled ? 'Retry every failed delivery with a fresh attempt budget' : 'Enable the endpoint to replay its failed deliveries'"
          >
            <!-- A wrapper, so the tooltip still shows while the button is disabled. -->
            <span class="inline-flex">
              <UButton
                label="Replay failed"
                icon="i-lucide-rotate-ccw"
                color="neutral"
                variant="outline"
                size="sm"
                :aria-label="`Replay failed deliveries of ${row.original.url}`"
                :disabled="!row.original.enabled"
                :loading="replayFailed.isPendingFor(row.original.id)"
                @click="replay(row.original)"
              />
            </span>
          </UTooltip>
        </template>
      </UTable>

      <CreateEndpointModal v-model:open="creating" />
    </template>
  </UDashboardPanel>
</template>
