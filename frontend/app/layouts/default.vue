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
        <div class="flex items-center gap-2">
          <span class="flex size-7 items-center justify-center rounded-md bg-primary text-inverted">
            <UIcon
              name="i-lucide-webhook"
              class="size-4"
            />
          </span>
          <span class="font-semibold text-highlighted">Benji Webhooks</span>
        </div>
      </template>

      <UNavigationMenu
        :items="links"
        orientation="vertical"
        aria-label="Main"
      />

      <template #footer>
        <UColorModeButton />
      </template>
    </UDashboardSidebar>

    <slot />
  </UDashboardGroup>
</template>
