import { reactive, ref } from 'vue'
import api, { clearCachedGets, getCached } from '../../api/client'
import { defaultAdminMessages, type AdminMessages } from './adminMessages'

export type AuditEvent = {
  id: number
  created_at: string
  action: string
  actor_user_id: number | null
  actor_role: string | null
  target_type: string
  target_id: number | null
  outcome: string
  details: Record<string, unknown>
  request_id: string | null
}

export type OpsAlert = {
  code: string
  severity: string
  message: string
  value: number
  threshold: number
}

export type OpsSummary = Record<string, unknown>

type ApiClient = {
  get: (url: string, config?: Record<string, unknown>) => Promise<any>
  post: (url: string, data?: unknown, config?: Record<string, unknown>) => Promise<any>
}

type UseAdminAuditOpsOptions = {
  apiClient?: ApiClient
  getCachedGet?: typeof getCached
  clearCache?: typeof clearCachedGets
  messages?: AdminMessages
  confirm?: (message: string) => boolean
}

function defaultConfirm(message: string): boolean {
  return typeof window !== 'undefined' ? window.confirm(message) : false
}

export function useAdminAuditOps(options: UseAdminAuditOpsOptions = {}) {
  const apiClient = options.apiClient || api
  const cachedGet = options.getCachedGet || getCached
  const clearCache = options.clearCache || clearCachedGets
  const messages = options.messages || defaultAdminMessages
  const confirm = options.confirm || defaultConfirm

  const auditEvents = ref<AuditEvent[]>([])
  const auditLoading = ref(false)
  const auditPurgeLoading = ref(false)
  const auditRetentionDays = ref(180)
  const auditPage = ref(1)
  const auditPageSize = 20
  const auditTotal = ref(0)
  const opsSummary = ref<OpsSummary | null>(null)
  const opsLoading = ref(false)
  const opsAlerts = ref<OpsAlert[]>([])
  const opsAlertsLoading = ref(false)
  const opsAlertStatus = ref<'ok' | 'alert'>('ok')
  const auditFilters = reactive({
    action: '',
    target_type: '',
    actor_user_id: '',
    outcome: '',
    request_id: '',
  })

  function buildAuditParams(): Record<string, string | number | boolean> {
    const params: Record<string, string | number | boolean> = {
      skip: (auditPage.value - 1) * auditPageSize,
      limit: auditPageSize,
      include_total: true,
    }
    const action = auditFilters.action.trim()
    if (action) {
      params.action = action
    }
    const targetType = auditFilters.target_type.trim()
    if (targetType) {
      params.target_type = targetType
    }
    const outcome = auditFilters.outcome.trim()
    if (outcome) {
      params.outcome = outcome
    }
    const requestId = auditFilters.request_id.trim()
    if (requestId) {
      params.request_id = requestId
    }
    const actorUserId = Number.parseInt(auditFilters.actor_user_id.trim(), 10)
    if (Number.isInteger(actorUserId) && actorUserId > 0) {
      params.actor_user_id = actorUserId
    }
    return params
  }

  function buildAuditCacheKey(params: Record<string, string | number | boolean>): string {
    const safe = {
      action: params.action || '',
      target_type: params.target_type || '',
      actor_user_id: params.actor_user_id || '',
      outcome: params.outcome || '',
      request_id: params.request_id || '',
      skip: params.skip,
      limit: params.limit,
    }
    return `admin:audit:${JSON.stringify(safe)}`
  }

  async function reloadAudit(force = false) {
    auditLoading.value = true
    const params = buildAuditParams()
    try {
      const response = force
        ? await apiClient.get('/admin/audit/events', { params })
        : await cachedGet(
            '/admin/audit/events',
            { params },
            10 * 1000,
            buildAuditCacheKey(params)
          )
      auditEvents.value = response.data.items || []
      auditTotal.value = response.data.total ?? auditEvents.value.length
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось загрузить журнал аудита')
    } finally {
      auditLoading.value = false
    }
  }

  async function loadOpsSummary(force = false) {
    opsLoading.value = true
    try {
      const response = force
        ? await apiClient.get('/admin/ops/summary')
        : await cachedGet(
            '/admin/ops/summary',
            {},
            10 * 1000,
            'admin:ops:summary'
          )
      opsSummary.value = response.data
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось загрузить операционную сводку')
    } finally {
      opsLoading.value = false
    }
  }

  async function loadOpsAlerts(force = false) {
    opsAlertsLoading.value = true
    try {
      const response = force
        ? await apiClient.get('/admin/ops/alerts')
        : await cachedGet(
            '/admin/ops/alerts',
            {},
            10 * 1000,
            'admin:ops:alerts'
          )
      opsAlertStatus.value = response.data.status === 'alert' ? 'alert' : 'ok'
      opsAlerts.value = response.data.alerts || []
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось загрузить пороговые оповещения')
    } finally {
      opsAlertsLoading.value = false
    }
  }

  async function loadOpsSnapshot(force = false) {
    await Promise.all([loadOpsSummary(force), loadOpsAlerts(force)])
  }

  function clearAuditOpsCaches() {
    clearCache('admin:audit:')
    clearCache('admin:ops:')
  }

  async function runAuditPurge(dryRun: boolean) {
    auditPurgeLoading.value = true
    try {
      const { data } = await apiClient.post(
        '/admin/audit/purge',
        null,
        {
          params: {
            older_than_days: auditRetentionDays.value,
            dry_run: dryRun,
          },
        }
      )
      if (dryRun) {
        messages.info(`Кандидатов на удаление: ${data.candidates}`)
        return
      }
      messages.success(`Удалено записей: ${data.deleted}`)
      clearAuditOpsCaches()
      await Promise.all([loadOpsSnapshot(true), reloadAudit(true)])
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось очистить audit logs')
    } finally {
      auditPurgeLoading.value = false
    }
  }

  async function previewAuditPurge() {
    await runAuditPurge(true)
  }

  async function confirmAndPurgeAudit() {
    const confirmed = confirm(
      `Удалить audit-события старше ${auditRetentionDays.value} дней?`
    )
    if (!confirmed) {
      return
    }
    await runAuditPurge(false)
  }

  async function applyAuditFilters() {
    auditPage.value = 1
    clearCache('admin:audit:')
    await reloadAudit(true)
  }

  async function resetAuditFilters() {
    auditFilters.action = ''
    auditFilters.target_type = ''
    auditFilters.actor_user_id = ''
    auditFilters.outcome = ''
    auditFilters.request_id = ''
    await applyAuditFilters()
  }

  async function onAuditPageChange(page: number) {
    auditPage.value = page
    await reloadAudit()
  }

  return {
    auditEvents,
    auditLoading,
    auditPurgeLoading,
    auditRetentionDays,
    auditPage,
    auditPageSize,
    auditTotal,
    opsSummary,
    opsLoading,
    opsAlerts,
    opsAlertsLoading,
    opsAlertStatus,
    auditFilters,
    reloadAudit,
    loadOpsSummary,
    loadOpsAlerts,
    loadOpsSnapshot,
    runAuditPurge,
    previewAuditPurge,
    confirmAndPurgeAudit,
    applyAuditFilters,
    resetAuditFilters,
    onAuditPageChange,
  }
}
