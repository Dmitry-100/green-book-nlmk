import axios from 'axios'
import type { AxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '../stores/auth'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

type CacheEntry = {
  expiresAt: number
  data: unknown
}

const responseCache = new Map<string, CacheEntry>()
const inflightRequests = new Map<string, Promise<AxiosResponse<any>>>()

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
    return `{${entries.join(',')}}`
  }
  return JSON.stringify(value)
}

function buildCacheKey(url: string, params: unknown, customKey?: string): string {
  if (customKey) return customKey
  if (!params) return url
  return `${url}?${stableStringify(params)}`
}

export async function getCached<T = any>(
  url: string,
  config: AxiosRequestConfig = {},
  ttlMs = 0,
  customKey?: string
): Promise<AxiosResponse<T>> {
  if (ttlMs <= 0) {
    return api.get<T>(url, config)
  }

  const cacheKey = buildCacheKey(url, config.params, customKey)
  const now = Date.now()
  const cached = responseCache.get(cacheKey)
  if (cached && now < cached.expiresAt) {
    return {
      data: cached.data as T,
      status: 200,
      statusText: 'OK',
      headers: {},
      config: { ...(config || {}), url } as any,
      request: null,
    } as AxiosResponse<T>
  }

  const inflight = inflightRequests.get(cacheKey)
  if (inflight) {
    return inflight as Promise<AxiosResponse<T>>
  }

  const requestPromise = api.get<T>(url, config)
    .then((response) => {
      responseCache.set(cacheKey, {
        expiresAt: Date.now() + ttlMs,
        data: response.data,
      })
      return response
    })
    .finally(() => {
      inflightRequests.delete(cacheKey)
    })

  inflightRequests.set(cacheKey, requestPromise as Promise<AxiosResponse<any>>)
  return requestPromise
}

export function clearCachedGets(prefix?: string): void {
  if (!prefix) {
    responseCache.clear()
    inflightRequests.clear()
    return
  }
  for (const key of responseCache.keys()) {
    if (key.startsWith(prefix)) {
      responseCache.delete(key)
    }
  }
}

export default api
