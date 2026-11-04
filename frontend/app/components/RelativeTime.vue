<script setup lang="ts">
import { formatDateTime, formatRelativeTime } from '~/domain/format'

const props = defineProps<{ datetime: string }>()

// Read here rather than in the table, so each tick re-renders this text, not every row.
const now = useClock()
const relative = computed(() => formatRelativeTime(props.datetime, now.value.getTime()))
const absolute = computed(() => formatDateTime(props.datetime))
</script>

<template>
  <!-- Relative to scan, absolute on hover. -->
  <time
    :datetime="datetime"
    :title="absolute"
    class="whitespace-nowrap tabular-nums"
  >{{ relative }}</time>
</template>
