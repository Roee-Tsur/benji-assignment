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
        <!-- Home is the first view (Deliveries): `/` redirects there. -->
        <NuxtLink
          to="/"
          class="flex items-center gap-2 rounded-md outline-primary focus-visible:outline-2"
        >
          <span class="flex size-7 items-center justify-center rounded-md bg-primary text-inverted">
            <UIcon
              name="i-lucide-webhook"
              class="size-4"
            />
          </span>
          <span class="font-semibold text-highlighted">Benji Webhooks</span>
        </NuxtLink>
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
