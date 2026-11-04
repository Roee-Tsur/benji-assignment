<script setup lang="ts">
import type { Attempt } from '~/api/client'
import { attemptOutcome } from '~/domain/deliveryProgress'
import { formatDateTime, formatMilliseconds } from '~/domain/format'

const props = defineProps<{ attempts: readonly Attempt[] }>()

// Newest first: while a delivery is live, the attempt that just happened is the one to read.
const rows = computed(() => [...props.attempts].reverse().map(attempt => ({
  ...attempt,
  result: attemptOutcome(attempt),
  duration: formatMilliseconds(Date.parse(attempt.finished_at) - Date.parse(attempt.started_at))
})))
</script>

<template>
  <p
    v-if="rows.length === 0"
    class="text-sm text-muted"
  >
    No attempts yet. The first one is sent as soon as a worker claims the delivery.
  </p>
  <ol
    v-else
    class="space-y-3"
  >
    <li
      v-for="attempt in rows"
      :key="attempt.id"
      class="space-y-2 rounded-md border border-default p-3"
    >
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <span class="font-medium">Attempt {{ attempt.number }}</span>
        <UBadge
          :color="attempt.result.ok ? 'success' : 'error'"
          :icon="attempt.result.ok ? 'i-lucide-circle-check' : 'i-lucide-circle-x'"
          :label="attempt.result.label"
          variant="subtle"
          size="sm"
        />
        <span class="text-muted tabular-nums">{{ attempt.duration }}</span>
        <NuxtTime
          :datetime="attempt.started_at"
          time-style="medium"
          :title="formatDateTime(attempt.started_at)"
          class="ml-auto text-muted tabular-nums"
        />
      </div>
      <p
        v-if="attempt.error"
        class="font-mono text-xs text-error"
      >
        {{ attempt.error }}
      </p>
      <details v-if="attempt.response_body !== null">
        <summary class="cursor-pointer text-sm text-muted">
          Response body <span class="text-xs">(first 2 KB)</span>
        </summary>
        <pre class="mt-2 max-h-48 overflow-auto rounded bg-elevated p-2 text-xs whitespace-pre-wrap">{{ attempt.response_body || '(empty)' }}</pre>
      </details>
      <details>
        <summary class="cursor-pointer text-sm text-muted">
          Request headers
        </summary>
        <dl class="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono text-xs">
          <template
            v-for="(value, name) in attempt.request_headers"
            :key="name"
          >
            <dt class="text-muted">
              {{ name }}
            </dt>
            <dd class="break-all">
              {{ value }}
            </dd>
          </template>
        </dl>
      </details>
    </li>
  </ol>
</template>
