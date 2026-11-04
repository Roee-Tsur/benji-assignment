<script setup lang="ts">
useHead({ title: 'Events' })
</script>

<template>
  <UDashboardPanel id="events">
    <template #header>
      <UDashboardNavbar title="Events" />
    </template>

    <template #body>
      <TriggerEventForm />
      <RecentEventsTable class="mt-8" />
    </template>
  </UDashboardPanel>
</template>
