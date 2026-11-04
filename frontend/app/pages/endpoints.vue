<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Endpoint } from '~/api/client'
import { eventTypes } from '~/domain/eventTypes'

useHead({ title: 'Endpoints' })

const endpoints = useEndpoints()
const creating = ref(false)

const columns: TableColumn<Endpoint>[] = [
  { accessorKey: 'url', header: 'URL' },
  { accessorKey: 'event_types', header: 'Event types' },
  { accessorKey: 'enabled', header: 'Status' },
  { accessorKey: 'created_at', header: 'Created' }
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
        v-else
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
          <UBadge
            v-bind="row.original.enabled
              ? { label: 'Enabled', color: 'success', icon: 'i-lucide-circle-check' }
              : { label: 'Disabled', color: 'neutral', icon: 'i-lucide-circle-pause' }"
            variant="subtle"
          />
        </template>
        <template #created_at-cell="{ row }">
          <NuxtTime
            :datetime="row.original.created_at"
            date-style="medium"
            time-style="short"
          />
        </template>
      </UTable>

      <CreateEndpointModal v-model:open="creating" />
    </template>
  </UDashboardPanel>
</template>
