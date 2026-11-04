<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'

const links: NavigationMenuItem[] = [
  { label: 'Deliveries', icon: 'i-lucide-send', to: '/deliveries' },
  { label: 'Events', icon: 'i-lucide-zap', to: '/events' },
  { label: 'Endpoints', icon: 'i-lucide-webhook', to: '/endpoints' }
]
</script>

<template>
  <UDashboardGroup>
    <UDashboardSidebar>
      <template #header>
        <span class="font-semibold">Benji Webhooks</span>
      </template>

      <UNavigationMenu
        :items="links"
        orientation="vertical"
        aria-label="Main"
      />
    </UDashboardSidebar>

    <slot />
  </UDashboardGroup>
</template>
