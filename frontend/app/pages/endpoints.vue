<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Endpoint } from '~/api/client'
import { eventTypes } from '~/domain/eventTypes'

useHead({ title: 'Endpoints' })

const endpoints = useEndpoints()
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
      title: replayed === 0 ? 'No failed deliveries to replay' : `Replayed ${replayed} failed ${replayed === 1 ? 'delivery' : 'deliveries'}`,
      color: replayed === 0 ? 'neutral' : 'success',
      icon: 'i-lucide-rotate-ccw',
      actions: replayed === 0 ? undefined : [{ label: 'View deliveries', to: { path: '/deliveries', query: { endpoint: endpoint.id } } }]
    })
  })
}

const columns: TableColumn<Endpoint>[] = [
  { accessorKey: 'url', header: 'URL' },
  { accessorKey: 'event_types', header: 'Event types' },
  { accessorKey: 'enabled', header: 'Status' },
  { accessorKey: 'created_at', header: 'Created' },
  { id: 'actions', header: 'Actions' }
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
        v-if="endpoints.error.value"
        :error="endpoints.error.value"
        @retry="endpoints.refetch()"
      />
      <UTable
        v-if="endpoints.data.value || !endpoints.error.value"
        :data="endpoints.data.value ?? []"
        :columns="columns"
        :loading="endpoints.isPending.value"
        empty="No endpoints yet. Create one to start receiving events."
      >
        <template #url-cell="{ row }">
          <span class="font-mono text-sm">{{ row.original.url }}</span>
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
          <!-- The visible label carries the state as text; the accessible name says which endpoint. -->
          <USwitch
            :model-value="row.original.enabled"
            :label="row.original.enabled ? 'Enabled' : 'Disabled'"
            :aria-label="`Enabled: ${row.original.url}`"
            :loading="setEnabled.isPendingFor(row.original.id)"
            @update:model-value="enabled => toggle(row.original, enabled)"
          />
        </template>
        <template #created_at-cell="{ row }">
          <NuxtTime
            :datetime="row.original.created_at"
            date-style="medium"
            time-style="short"
          />
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
