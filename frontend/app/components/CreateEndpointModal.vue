<script setup lang="ts">
import type { FormError } from '@nuxt/ui'
import type { EndpointCreated, EventType } from '~/api/client'
import { eventTypeOptions } from '~/domain/eventTypes'

const open = defineModel<boolean>('open', { required: true })

const createEndpoint = useCreateEndpoint()
const state = reactive({
  url: 'http://127.0.0.1:8000/mock/ok',
  eventTypes: eventTypeOptions.map(option => option.value) as EventType[]
})
const created = ref<EndpointCreated>()
const copied = ref(false)

function validate(): FormError[] {
  return state.eventTypes.length === 0 ? [{ name: 'eventTypes', message: 'Pick at least one event type.' }] : []
}

async function submit() {
  created.value = await createEndpoint.mutateAsync({ url: state.url, event_types: state.eventTypes })
}

async function copySecret() {
  if (!created.value) return
  await navigator.clipboard.writeText(created.value.secret)
  copied.value = true
}

// The secret is dropped on close: it is shown once and never again.
watch(open, (isOpen) => {
  if (!isOpen) {
    created.value = undefined
    copied.value = false
    createEndpoint.reset()
  }
})
</script>

<template>
  <UModal
    v-model:open="open"
    :title="created ? 'Endpoint created' : 'New endpoint'"
    :dismissible="!created"
  >
    <template #body>
      <div
        v-if="created"
        class="space-y-4"
      >
        <UAlert
          color="warning"
          variant="subtle"
          icon="i-lucide-key-round"
          title="Copy the signing secret now"
          description="It's shown only this once. Your receiver uses it to verify every notification."
        />
        <UFieldGroup class="w-full">
          <UInput
            :model-value="created.secret"
            readonly
            aria-label="Signing secret"
            class="w-full font-mono"
          />
          <UButton
            :icon="copied ? 'i-lucide-check' : 'i-lucide-copy'"
            :label="copied ? 'Copied' : 'Copy'"
            color="neutral"
            variant="outline"
            @click="copySecret"
          />
        </UFieldGroup>
      </div>

      <UForm
        v-else
        id="create-endpoint"
        :state="state"
        :validate="validate"
        class="space-y-4"
        @submit="submit"
      >
        <UFormField
          label="URL"
          name="url"
          required
        >
          <UInput
            v-model="state.url"
            type="url"
            class="w-full"
          />
        </UFormField>
        <UFormField
          label="Event types"
          name="eventTypes"
          required
        >
          <UCheckboxGroup
            v-model="state.eventTypes"
            :items="eventTypeOptions"
          />
        </UFormField>
      </UForm>
    </template>

    <template #footer>
      <UButton
        v-if="created"
        label="Done"
        @click="open = false"
      />
      <UButton
        v-else
        type="submit"
        form="create-endpoint"
        label="Create endpoint"
        :loading="createEndpoint.isPending.value"
      />
    </template>
  </UModal>
</template>
