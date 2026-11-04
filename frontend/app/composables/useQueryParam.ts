import type { WritableComputedRef } from 'vue'

/**
 * View state held in the URL query (`?status=failed`), so views deep-link and the back button works.
 * `parse` narrows the raw value to the allowed set; anything else reads as `undefined`, which also
 * removes the param when written.
 */
export function useQueryParam<T extends string>(
  name: string,
  parse: (raw: string) => T | undefined
): WritableComputedRef<T | undefined> {
  const route = useRoute()
  const router = useRouter()
  return computed({
    get: () => {
      const raw = route.query[name]
      return typeof raw === 'string' ? parse(raw) : undefined
    },
    set: (value) => {
      void router.push({ query: { ...route.query, [name]: value } })
    }
  })
}

/** A `parse` for `useQueryParam` that accepts exactly the given values. */
export function oneOf<T extends string>(values: readonly T[]): (raw: string) => T | undefined {
  return raw => values.find(value => value === raw)
}
