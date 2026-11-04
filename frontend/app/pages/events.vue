<script setup lang="ts">
useHead({ title: 'Events' })
</script>

<template>
  <UDashboardPanel id="events">
    <template #header>
      <UDashboardNavbar title="Events" />
    </template>

    <template #body>
      <section
        aria-labelledby="trigger-heading"
        class="space-y-3"
      >
        <h2
          id="trigger-heading"
          class="text-base font-semibold text-highlighted"
        >
          Trigger an event
        </h2>
        <TriggerEventForm />
      </section>
      <USeparator class="my-2" />
      <RecentEventsTable />
    </template>
  </UDashboardPanel>
</template>
