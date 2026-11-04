<script setup lang="ts">
import type { FormError } from '@nuxt/ui'
import type { EventSubmitted, EventType } from '~/api/client'
import { parseEventData } from '~/domain/eventData'
import { eventTypeOptions, eventTypes } from '~/domain/eventTypes'

useHead({ title: 'Events' })

const triggerEvent = useTriggerEvent()
const state = reactive({
  type: 'reward_transaction_created' as EventType,
  json: ''
})
const submitted = ref<EventSubmitted>()

// Each type starts from its sample payload.
watch(() => state.type, (type) => {
  state.json = JSON.stringify(eventTypes[type].sample, null, 2)
}, { immediate: true })

function validate(): FormError[] {
  return parseEventData(state.json) ? [] : [{ name: 'json', message: 'Enter a JSON object.' }]
}

function submit() {
  submitted.value = undefined
  triggerEvent.mutate({
    type: state.type,
    data: parseEventData(state.json)!,
    // A fresh key per submit for now; a key that persists for visible dedup is #7.
    idempotencyKey: crypto.randomUUID()
  }, {
    onSuccess: (event) => {
      submitted.value = event
    }
  })
}
</script>

<template>
  <UDashboardPanel id="events">
    <template #header>
      <UDashboardNavbar title="Events" />
    </template>

    <template #body>
      <UForm
        :state="state"
        :validate="validate"
        class="max-w-xl space-y-4"
        @submit="submit"
      >
        <UFormField
          label="Event type"
          name="type"
        >
          <USelect
            v-model="state.type"
            :items="eventTypeOptions"
            class="w-full"
          />
        </UFormField>
        <UFormField
          label="Data (JSON)"
          name="json"
        >
          <UTextarea
            v-model="state.json"
            :rows="8"
            autoresize
            class="w-full font-mono"
          />
        </UFormField>
        <UButton
          type="submit"
          icon="i-lucide-zap"
          label="Trigger event"
          :loading="triggerEvent.isPending.value"
        />
      </UForm>

      <UAlert
        v-if="submitted"
        class="max-w-xl"
        :color="submitted.deduplicated ? 'warning' : 'success'"
        variant="subtle"
        icon="i-lucide-circle-check"
        :title="submitted.deduplicated ? 'Already submitted: this is the original event' : 'Event triggered'"
        :description="`${submitted.id} · ${submitted.delivery_count} ${submitted.delivery_count === 1 ? 'delivery' : 'deliveries'}`"
        :actions="[{ label: 'View deliveries', to: '/deliveries', color: 'neutral', variant: 'outline' }]"
      />
    </template>
  </UDashboardPanel>
</template>
