import { createSharedComposable, useNow } from '@vueuse/core'

/** The current time, ticking every second; one timer shared by every countdown and "updated 2s ago". */
export const useClock = createSharedComposable(() => useNow({ interval: 1000 }))
