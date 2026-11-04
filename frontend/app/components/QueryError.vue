<script setup lang="ts">
import type { ApiError } from '~/api/errors'

defineProps<{
  error: ApiError
  /** A fetch is underway (the retry, or a poll), so Retry shows it's working. */
  retrying?: boolean
}>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <!-- The one inline treatment for a failed query, in every view. -->
  <UAlert
    color="error"
    variant="subtle"
    icon="i-lucide-circle-alert"
    :title="error.title"
    :description="error.message === error.title ? undefined : error.message"
    :actions="[{ label: 'Retry', icon: 'i-lucide-refresh-cw', color: 'error', variant: 'outline', loading: retrying, onClick: () => $emit('retry') }]"
  />
</template>
