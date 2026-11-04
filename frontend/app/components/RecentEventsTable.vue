<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Event } from '~/api/client'
import { eventTypes } from '~/domain/eventTypes'
import { formatCount } from '~/domain/format'

const events = useRecentEvents()
const loadError = useLoadError(events)

const fanOut = (count: number) => formatCount(count, 'delivery', 'deliveries')

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
      class="text-base font-semibold text-highlighted"
    >
      Recent events
    </h2>
    <QueryError
      v-if="loadError"
      :error="loadError"
      :retrying="events.isFetching.value"
      @retry="events.refetch()"
    />
    <UTable
      v-else
      :data="events.data.value ?? []"
      :columns="columns"
      :loading="events.isPending.value"
    >
      <template #empty>
        <TableSkeleton v-if="events.isPending.value" />
        <UEmpty
          v-else
          variant="naked"
          icon="i-lucide-zap"
          title="No events yet"
          description="Trigger one with the form above, or POST to /events. Each one fans out to every enabled endpoint subscribed to its type."
        />
      </template>
      <template #type-cell="{ row }">
        {{ eventTypes[row.original.type].label }}
      </template>
      <template #id-cell="{ row }">
        <span class="font-mono text-xs">{{ row.original.id }}</span>
      </template>
      <template #idempotency_key-cell="{ row }">
        <span
          class="block max-w-48 truncate font-mono text-xs text-muted"
          :title="row.original.idempotency_key"
        >
          {{ row.original.idempotency_key }}
        </span>
      </template>
      <template #delivery_count-cell="{ row }">
        <ULink
          :to="{ path: '/deliveries', query: { event: row.original.id } }"
          :aria-label="`${fanOut(row.original.delivery_count)} of ${row.original.id}`"
          class="inline-flex items-center gap-1"
        >
          {{ fanOut(row.original.delivery_count) }}
          <UIcon name="i-lucide-arrow-right" />
        </ULink>
      </template>
      <template #created_at-cell="{ row }">
        <RelativeTime :datetime="row.original.created_at" />
      </template>
    </UTable>
  </section>
</template>
