<script setup lang="ts">
import type { EventSubmitted, EventType } from '~/api/client'
import { parseEventData } from '~/domain/eventData'
import { eventTypeOptions, eventTypes } from '~/domain/eventTypes'
import { formatCount } from '~/domain/format'

const triggerEvent = useTriggerEvent()
const state = reactive({
  type: 'reward_transaction_created' as EventType,
  json: ''
})

// Each type starts from its sample payload.
watch(() => state.type, (type) => {
  state.json = JSON.stringify(eventTypes[type].sample, null, 2)
}, { immediate: true })

const parsed = computed(() => parseEventData(state.json))
const jsonError = computed(() => 'error' in parsed.value ? parsed.value.error : undefined)

// Keyed on the parsed data, not the text, so "Format" or re-indenting keeps the key.
const { key: idempotencyKey, renew: newKey } = useIdempotencyKey(() =>
  'data' in parsed.value ? JSON.stringify([state.type, parsed.value.data]) : undefined
)
const keyError = computed(() => idempotencyKey.value.trim() ? undefined : 'Enter a key, or click "New key".')

const canSubmit = computed(() => !jsonError.value && !keyError.value && !triggerEvent.isPending.value)
const submitted = ref<EventSubmitted>()
// Only while the key it was about is still the one in the form.
const keyReused = computed(() => isIdempotencyKeyReused(triggerEvent.error.value)
  && triggerEvent.variables.value?.idempotencyKey === idempotencyKey.value)

function format() {
  if ('data' in parsed.value) state.json = JSON.stringify(parsed.value.data, null, 2)
}

function submit() {
  if (!canSubmit.value || !('data' in parsed.value)) return
  submitted.value = undefined
  triggerEvent.mutate({ type: state.type, data: parsed.value.data, idempotencyKey: idempotencyKey.value }, {
    onSuccess: (event) => {
      submitted.value = event
    }
  })
}

const deliveriesOf = (eventId: string) => ({ path: '/deliveries', query: { event: eventId } })
</script>

<template>
  <form
    class="max-w-xl space-y-4"
    aria-label="Trigger an event"
    @submit.prevent="submit"
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
      :error="jsonError"
      help="Prefilled with a sample for the type. ⌘/Ctrl + Enter submits."
    >
      <template #hint>
        <UButton
          label="Format"
          icon="i-lucide-wand-sparkles"
          color="neutral"
          variant="ghost"
          size="xs"
          :disabled="Boolean(jsonError)"
          @click="format"
        />
      </template>
      <UTextarea
        v-model="state.json"
        :rows="8"
        autoresize
        spellcheck="false"
        class="w-full font-mono"
        @keydown.enter.meta.prevent="submit"
        @keydown.enter.ctrl.prevent="submit"
      />
    </UFormField>

    <UFormField
      label="Idempotency key"
      name="idempotencyKey"
      :error="keyError"
      help="Kept until the event changes, so resubmitting is deduplicated."
    >
      <UFieldGroup class="w-full">
        <UInput
          v-model="idempotencyKey"
          name="idempotencyKey"
          class="w-full font-mono"
        />
        <UButton
          label="New key"
          icon="i-lucide-refresh-cw"
          color="neutral"
          variant="outline"
          @click="newKey"
        />
      </UFieldGroup>
    </UFormField>

    <UButton
      type="submit"
      icon="i-lucide-zap"
      label="Trigger event"
      :loading="triggerEvent.isPending.value"
      :disabled="!canSubmit"
    />

    <div aria-live="polite">
      <UAlert
        v-if="keyReused"
        color="error"
        variant="subtle"
        icon="i-lucide-circle-x"
        title="This key was already used for a different event"
        description="The API rejected it (422) rather than return an event that doesn't match. Use a new key to send this as a new event."
        :actions="[{ label: 'New key', color: 'error', variant: 'outline', onClick: newKey }]"
      />
      <UAlert
        v-else-if="submitted?.deduplicated"
        color="warning"
        variant="subtle"
        icon="i-lucide-copy-check"
        title="Duplicate submission: this is the original event"
        :description="`This key was already used for the same event, so ${submitted.id} was returned again. No new deliveries were created (it fanned out to ${formatCount(submitted.delivery_count, 'delivery', 'deliveries')} when first submitted).`"
        :actions="[
          { label: 'View its deliveries', to: deliveriesOf(submitted.id), color: 'neutral', variant: 'outline' },
          { label: 'New key', color: 'neutral', variant: 'ghost', onClick: newKey }
        ]"
      />
      <UAlert
        v-else-if="submitted?.delivery_count === 0"
        color="warning"
        variant="subtle"
        icon="i-lucide-circle-alert"
        title="Event triggered, but nothing to deliver"
        :description="`No enabled endpoint is subscribed to ${eventTypes[submitted.type].label.toLowerCase()} events, so ${submitted.id} fanned out to no deliveries.`"
        :actions="[{ label: 'Add an endpoint', to: '/endpoints', color: 'neutral', variant: 'outline' }]"
      />
      <UAlert
        v-else-if="submitted"
        color="success"
        variant="subtle"
        icon="i-lucide-circle-check"
        title="Event triggered"
        :description="`${submitted.id} fanned out to ${formatCount(submitted.delivery_count, 'delivery', 'deliveries')}.`"
        :actions="[{ label: 'View its deliveries', to: deliveriesOf(submitted.id), color: 'neutral', variant: 'outline' }]"
      />
    </div>
  </form>
</template>
