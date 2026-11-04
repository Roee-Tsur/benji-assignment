import { createOpenApiHttp } from 'openapi-msw'
import type { paths } from '../../app/api/schema'

/** MSW's `http`, typed from the OpenAPI schema: paths, params, bodies, and responses must match the API. */
export const http = createOpenApiHttp<paths>({ baseUrl: '*/api' })
