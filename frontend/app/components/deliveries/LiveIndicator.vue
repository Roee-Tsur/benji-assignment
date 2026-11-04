<script setup lang="ts">
import type { ApiError } from '~/api/errors'
import { formatRelativeTime } from '~/domain/format'

const props = defineProps<{
  /** When the data shown was last fetched (ms); 0 before the first fetch. */
  updatedAt: number
  /** The last poll's error, if it failed. */
  error: ApiError | null
}>()
defineEmits<{ retry: [] }>()

const now = useClock()
const ago = computed(() => `updated ${formatRelativeTime(new Date(props.updatedAt).toISOString(), now.value.getTime())}`)
</script>

<template>
  <div
    role="status"
    class="flex items-center gap-2 text-sm"
  >
    <template v-if="error">
      <UIcon
        name="i-lucide-wifi-off"
        class="text-error"
      />
      <span class="text-error">Updates failing</span>
      <span
        v-if="updatedAt"
        class="text-muted"
      >· last {{ ago }}</span>
      <UButton
        label="Retry"
        color="error"
        variant="link"
        size="xs"
        :title="error.message"
        @click="$emit('retry')"
      />
    </template>
    <template v-else-if="updatedAt">
      <span
        class="size-2 animate-pulse rounded-full bg-success"
        aria-hidden="true"
      />
      <span>Live</span>
      <span class="text-muted">· {{ ago }}</span>
    </template>
    <span
      v-else
      class="text-muted"
    >Connecting…</span>
  </div>
</template>
