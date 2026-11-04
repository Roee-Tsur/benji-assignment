<script setup lang="ts">
import { deliveryProgress } from '~/domain/deliveryProgress'
import { eventTypes } from '~/domain/eventTypes'
import { formatDateTime } from '~/domain/format'

/** The delivery to show; `undefined` closes the slideover. */
const deliveryId = defineModel<string | undefined>('deliveryId')

// Keep showing the last delivery while the slideover animates closed.
const shownId = ref(deliveryId.value)
watch(deliveryId, (id) => {
  if (id) shownId.value = id
})
const open = computed({
  get: () => Boolean(deliveryId.value),
  set: (isOpen) => {
    if (!isOpen) deliveryId.value = undefined
  }
})

// Polls only while open; the cached detail stays on screen through the close animation.
const detail = useDelivery(shownId, open)
const loadError = useLoadError(detail)
const replay = useReplayDelivery()
const replaying = computed(() => replay.isPending.value && replay.variables.value === shownId.value)
const now = useClock()
</script>

<template>
  <!-- A dialog underneath: it traps focus, closes on Escape, and returns focus on close. -->
  <USlideover
    v-model:open="open"
    description="Payload and attempt log; updates live until the delivery is final."
    :ui="{ content: 'max-w-2xl', title: 'pe-8' }"
  >
    <!-- A full id is long: it gets its own line under the heading rather than running into the close button. -->
    <template #title>
      Delivery <span class="block font-mono text-xs font-normal text-muted">{{ shownId }}</span>
    </template>

    <template #body>
      <QueryError
        v-if="loadError"
        :error="loadError"
        @retry="detail.refetch()"
      />
      <div
        v-else-if="!detail.data.value"
        class="space-y-3"
      >
        <USkeleton class="h-6 w-1/2" />
        <USkeleton class="h-32 w-full" />
      </div>
      <div
        v-else
        class="space-y-6"
      >
        <section class="flex flex-wrap items-center gap-3">
          <DeliveryStatusBadge :status="detail.data.value.status" />
          <span class="text-sm text-muted">{{ deliveryProgress(detail.data.value, now.getTime()) }}</span>
          <!-- Stays while replaying (the row already shows `pending`), so focus has somewhere to stay. -->
          <UButton
            v-if="detail.data.value.status === 'failed' || replaying"
            class="ml-auto"
            icon="i-lucide-rotate-ccw"
            label="Replay"
            :loading="replaying"
            :disabled="replaying"
            @click="replay.mutate(detail.data.value.id)"
          />
        </section>

        <dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
          <dt class="text-muted">
            Event
          </dt>
          <dd>
            {{ eventTypes[detail.data.value.event_type].label }}
            <span class="font-mono text-xs text-muted">{{ detail.data.value.event_id }}</span>
          </dd>
          <dt class="text-muted">
            Endpoint
          </dt>
          <dd class="font-mono break-all">
            {{ detail.data.value.endpoint_url }}
          </dd>
          <dt class="text-muted">
            Created
          </dt>
          <dd>
            {{ formatDateTime(detail.data.value.created_at) }}
            <span class="text-muted">· <RelativeTime :datetime="detail.data.value.created_at" /></span>
          </dd>
        </dl>

        <section class="space-y-2">
          <h3 class="text-sm font-semibold text-highlighted">
            Payload
          </h3>
          <pre class="max-h-64 overflow-auto rounded-md bg-elevated p-3 text-xs">{{ JSON.stringify(detail.data.value.payload, null, 2) }}</pre>
        </section>

        <section class="space-y-2">
          <h3 class="text-sm font-semibold text-highlighted">
            Attempts <span class="font-normal text-muted tabular-nums">({{ detail.data.value.attempts.length }})</span>
          </h3>
          <DeliveriesAttemptLog :attempts="detail.data.value.attempts" />
        </section>
      </div>
    </template>
  </USlideover>
</template>
