<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Event } from '~/api/client'
import { eventTypes } from '~/domain/eventTypes'

const events = useRecentEvents()

const columns: TableColumn<Event>[] = [
  { accessorKey: 'type', header: 'Event type' },
  { accessorKey: 'id', header: 'Event' },
  { accessorKey: 'idempotency_key', header: 'Idempotency key' },
  { accessorKey: 'delivery_count', header: 'Fan-out' },
  { accessorKey: 'created_at', header: 'Created' }
]
</script>

<template>
  <section
    aria-labelledby="recent-events-heading"
    class="space-y-3"
  >
    <h2
      id="recent-events-heading"
      class="font-semibold"
    >
      Recent events
    </h2>
    <QueryError
      v-if="events.error.value"
      :error="events.error.value"
      @retry="events.refetch()"
    />
    <UTable
      v-if="events.data.value || !events.error.value"
      :data="events.data.value ?? []"
      :columns="columns"
      :loading="events.isPending.value"
      empty="No events yet. Trigger one above."
    >
      <template #type-cell="{ row }">
        {{ eventTypes[row.original.type].label }}
      </template>
      <template #id-cell="{ row }">
        <span class="font-mono text-sm">{{ row.original.id }}</span>
      </template>
      <template #idempotency_key-cell="{ row }">
        <span
          class="block max-w-48 truncate font-mono text-sm text-muted"
          :title="row.original.idempotency_key"
        >
          {{ row.original.idempotency_key }}
        </span>
      </template>
      <template #delivery_count-cell="{ row }">
        <ULink
          :to="{ path: '/deliveries', query: { event: row.original.id } }"
          :aria-label="`View the ${row.original.delivery_count} deliveries of ${row.original.id}`"
          class="inline-flex items-center gap-1"
        >
          {{ row.original.delivery_count }} {{ row.original.delivery_count === 1 ? 'delivery' : 'deliveries' }}
          <UIcon name="i-lucide-arrow-right" />
        </ULink>
      </template>
      <template #created_at-cell="{ row }">
        <NuxtTime
          :datetime="row.original.created_at"
          date-style="medium"
          time-style="medium"
        />
      </template>
    </UTable>
  </section>
</template>
