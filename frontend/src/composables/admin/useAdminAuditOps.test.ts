import { describe, expect, it, vi } from 'vitest'

import { useAdminAuditOps } from './useAdminAuditOps'

function makeAuditOps(confirm = vi.fn().mockReturnValue(false)) {
  const apiClient = {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    post: vi.fn().mockResolvedValue({ data: { candidates: 0, deleted: 0 } }),
  }
  const cachedGet = vi.fn().mockResolvedValue({ data: { items: [], total: 0 } })
  const clearCache = vi.fn()
  const messages = {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  }

  return {
    apiClient,
    cachedGet,
    clearCache,
    messages,
    confirm,
    auditOps: useAdminAuditOps({
      apiClient,
      getCachedGet: cachedGet,
      clearCache,
      messages,
      confirm,
    }),
  }
}

describe('useAdminAuditOps', () => {
  it('loads audit events with trimmed filters and a positive actor id', async () => {
    const { auditOps, apiClient } = makeAuditOps()

    auditOps.auditFilters.action = ' species.update '
    auditOps.auditFilters.target_type = ' species '
    auditOps.auditFilters.actor_user_id = ' 12 '
    auditOps.auditFilters.outcome = ' success '
    auditOps.auditFilters.request_id = ' req-1 '
    auditOps.auditPage.value = 2

    await auditOps.reloadAudit(true)

    expect(apiClient.get).toHaveBeenCalledWith('/admin/audit/events', {
      params: {
        skip: 20,
        limit: 20,
        include_total: true,
        action: 'species.update',
        target_type: 'species',
        actor_user_id: 12,
        outcome: 'success',
        request_id: 'req-1',
      },
    })
  })

  it('resets audit filters and invalidates audit cache before reloading', async () => {
    const { auditOps, apiClient, clearCache } = makeAuditOps()

    auditOps.auditFilters.action = 'species.create'
    auditOps.auditFilters.target_type = 'species'
    auditOps.auditFilters.actor_user_id = '7'
    auditOps.auditFilters.outcome = 'failed'
    auditOps.auditFilters.request_id = 'req-2'
    auditOps.auditPage.value = 4

    await auditOps.resetAuditFilters()

    expect(auditOps.auditFilters).toMatchObject({
      action: '',
      target_type: '',
      actor_user_id: '',
      outcome: '',
      request_id: '',
    })
    expect(auditOps.auditPage.value).toBe(1)
    expect(clearCache).toHaveBeenCalledWith('admin:audit:')
    expect(apiClient.get).toHaveBeenCalledWith('/admin/audit/events', {
      params: {
        skip: 0,
        limit: 20,
        include_total: true,
      },
    })
  })

  it('does not purge audit events when confirmation is declined', async () => {
    const { auditOps, apiClient, confirm } = makeAuditOps()

    await auditOps.confirmAndPurgeAudit()

    expect(confirm).toHaveBeenCalledWith('Удалить audit-события старше 180 дней?')
    expect(apiClient.post).not.toHaveBeenCalled()
    expect(auditOps.auditPurgeLoading.value).toBe(false)
  })
})
