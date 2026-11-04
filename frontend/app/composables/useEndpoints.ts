import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { api, type Schemas } from '~/api/client'
import { unwrap } from '~/api/errors'
import { queryKeys } from '~/api/queryKeys'

export function useEndpoints() {
  return useQuery({
    queryKey: queryKeys.endpoints.list(),
    queryFn: ({ signal }) => unwrap(api.GET('/endpoints', { signal }))
  })
}

/** Resolves to the created endpoint, including its signing secret: the only time the API returns it. */
export function useCreateEndpoint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Schemas['EndpointCreate']) => unwrap(api.POST('/endpoints', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.endpoints.all })
  })
}
