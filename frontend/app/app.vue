<script setup lang="ts">
useHead({
  titleTemplate: title => title ? `${title} · Benji Webhooks` : 'Benji Webhooks',
  htmlAttrs: { lang: 'en' },
  link: [{ rel: 'icon', href: '/favicon.ico' }]
})
</script>

<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
