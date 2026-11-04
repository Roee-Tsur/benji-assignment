import { useSessionStorage } from '@vueuse/core'

/**
 * The trigger form's idempotency key. It stays the same while the submission stays the same,
 * so a resubmit is deduplicated, and is replaced when `submission` changes or on `renew()`.
 *
 * `submission` should return a canonical form of what's being sent (so reformatting the JSON
 * keeps the key), or `undefined` while the input is invalid (which keeps the key too).
 *
 * The key and the submission it belongs to live in `sessionStorage`, not the component, so
 * leaving the page or reloading it and coming back to the same submission keeps the key.
 */
export function useIdempotencyKey(submission: () => string | undefined) {
  const key = useSessionStorage('trigger-event:idempotency-key', newKey)
  const keyedSubmission = useSessionStorage('trigger-event:keyed-submission', submission() ?? '')

  function renew() {
    key.value = newKey()
  }

  watch(submission, (next) => {
    if (next === undefined || next === keyedSubmission.value) return
    keyedSubmission.value = next
    renew()
  }, { immediate: true })

  return { key, renew }
}

/** `randomUUID` needs a secure context (HTTPS or localhost); `getRandomValues` works on any origin. */
function newKey(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('')
}
