<script setup lang="ts">
import type { FormError } from '@nuxt/ui'
import { useClipboard } from '@vueuse/core'
import type { EndpointCreated, EventType } from '~/api/client'
import { endpointUrlError } from '~/domain/endpointUrl'
import { eventTypeOptions } from '~/domain/eventTypes'

const open = defineModel<boolean>('open', { required: true })

const createEndpoint = useCreateEndpoint()
const state = reactive({
  url: 'http://127.0.0.1:8000/mock/ok',
  eventTypes: eventTypeOptions.map(option => option.value) as EventType[]
})
const created = ref<EndpointCreated>()
// `legacy` falls back to `execCommand` where the Clipboard API is unavailable (non-HTTPS hosts).
const { copy, copied } = useClipboard({ legacy: true })

function validate(): FormError[] {
  const errors: FormError[] = []
  const urlError = endpointUrlError(state.url)
  if (urlError) errors.push({ name: 'url', message: urlError })
  if (state.eventTypes.length === 0) errors.push({ name: 'eventTypes', message: 'Pick at least one event type.' })
  return errors
}

// `mutate`, not `mutateAsync`: failures are already toasted, and its callback is dropped
// if the modal closes (and resets the mutation) before the response arrives.
function submit() {
  createEndpoint.mutate({ url: state.url.trim(), event_types: state.eventTypes }, {
    onSuccess: (endpoint) => {
      created.value = endpoint
    }
  })
}

// The secret is dropped on close: it is shown once and never again.
watch(open, (isOpen) => {
  if (!isOpen) {
    created.value = undefined
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
            @click="copy(created.secret)"
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
