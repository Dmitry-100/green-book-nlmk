import type { AxiosResponse } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import api, { clearCachedGets, getCached } from './client'

function makeResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {},
    request: null,
  } as AxiosResponse<T>
}

describe('api client cache', () => {
  beforeEach(() => {
    clearCachedGets()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('reuses cached responses within ttl', async () => {
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue(makeResponse({ value: 1 }))

    const first = await getCached('/species', { params: { group: 'birds' } }, 5_000)
    const second = await getCached('/species', { params: { group: 'birds' } }, 5_000)

    expect(first.data).toEqual({ value: 1 })
    expect(second.data).toEqual({ value: 1 })
    expect(getSpy).toHaveBeenCalledTimes(1)
  })

  it('dedupes inflight requests for the same key', async () => {
    let resolveCall: (value: AxiosResponse<{ ok: boolean }>) => void = () => undefined
    const pending = new Promise<AxiosResponse<{ ok: boolean }>>((resolve) => {
      resolveCall = resolve
    })
    const getSpy = vi.spyOn(api, 'get').mockReturnValue(pending)

    const first = getCached('/dashboard/summary', {}, 5_000)
    const second = getCached('/dashboard/summary', {}, 5_000)

    expect(getSpy).toHaveBeenCalledTimes(1)
    resolveCall(makeResponse({ ok: true }))

    await expect(first).resolves.toMatchObject({ data: { ok: true } })
    await expect(second).resolves.toMatchObject({ data: { ok: true } })
  })

  it('expires cache entries after ttl', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-11T10:00:00.000Z'))

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue(makeResponse({ value: 1 }))

    await getCached('/species', { params: { group: 'birds' } }, 1_000)
    vi.setSystemTime(new Date('2026-04-11T10:00:01.100Z'))
    await getCached('/species', { params: { group: 'birds' } }, 1_000)

    expect(getSpy).toHaveBeenCalledTimes(2)
  })

  it('supports prefix invalidation', async () => {
    const getSpy = vi.spyOn(api, 'get')
      .mockResolvedValueOnce(makeResponse({ scope: 'admin' }))
      .mockResolvedValueOnce(makeResponse({ scope: 'species' }))
      .mockResolvedValueOnce(makeResponse({ scope: 'admin-refreshed' }))

    await getCached('/admin/ops/summary', {}, 10_000, 'admin:ops:summary')
    await getCached('/species', { params: { limit: 10 } }, 10_000, 'species:list:10')

    clearCachedGets('admin:ops:')

    const adminAfterInvalidation = await getCached('/admin/ops/summary', {}, 10_000, 'admin:ops:summary')
    const speciesStillCached = await getCached('/species', { params: { limit: 10 } }, 10_000, 'species:list:10')

    expect(adminAfterInvalidation.data).toEqual({ scope: 'admin-refreshed' })
    expect(speciesStillCached.data).toEqual({ scope: 'species' })
    expect(getSpy).toHaveBeenCalledTimes(3)
  })
})
