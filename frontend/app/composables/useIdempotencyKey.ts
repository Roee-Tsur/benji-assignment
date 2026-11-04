/**
 * The trigger form's idempotency key. It stays the same while the submission stays the same,
 * so a resubmit is deduplicated, and is replaced when `submission` changes or on `renew()`.
 *
 * `submission` should return a canonical form of what's being sent (so reformatting the JSON
 * keeps the key), or `undefined` while the input is invalid (which keeps the key too).
 */
export function useIdempotencyKey(submission: () => string | undefined) {
  const key = ref(crypto.randomUUID())
  let keyedSubmission = submission()

  function renew() {
    key.value = crypto.randomUUID()
  }

  watch(submission, (next) => {
    if (next === undefined || next === keyedSubmission) return
    keyedSubmission = next
    renew()
  })

  return { key, renew }
}
