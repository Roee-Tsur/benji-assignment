<script setup lang="ts">
withDefaults(defineProps<{ rows?: number }>(), { rows: 3 })
</script>

<template>
  <!-- A table's first load, in its empty slot: placeholder rows rather than an "empty" message that isn't true yet. -->
  <div
    class="space-y-3 py-2"
    role="status"
    aria-label="Loading"
  >
    <USkeleton
      v-for="row in rows"
      :key="row"
      class="h-8 w-full"
    />
  </div>
</template>
