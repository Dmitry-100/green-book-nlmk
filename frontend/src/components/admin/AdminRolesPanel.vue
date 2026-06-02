<template>
  <div class="users-panel">
    <div class="users-panel__header">
      <div>
        <h2>Пользователи и роли</h2>
        <p class="admin-hint">
          Новые учетные записи получают роль сотрудника и начинают работать после подтверждения.
        </p>
      </div>
      <button type="button" class="refresh-button" :disabled="loading" @click="loadUsers">
        Обновить
      </button>
    </div>

    <div class="filters">
      <button
        v-for="option in statusFilters"
        :key="option.value"
        type="button"
        class="filter-button"
        :class="{ active: approvalStatus === option.value }"
        @click="setStatus(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <p v-if="message" class="panel-message" :class="{ error: hasError }">{{ message }}</p>

    <div v-if="loading" class="empty-state">Загружаем пользователей...</div>
    <div v-else-if="users.length === 0" class="empty-state">Заявок и пользователей нет.</div>
    <div v-else class="users-table">
      <div class="users-table__head">
        <span>Пользователь</span>
        <span>Статус</span>
        <span>Роль</span>
        <span>Действия</span>
      </div>

      <div v-for="user in users" :key="user.id" class="user-row">
        <div>
          <strong>{{ user.display_name }}</strong>
          <small>{{ user.email || 'email не указан' }}</small>
        </div>
        <span class="status-pill" :class="`status-pill--${user.approval_status}`">
          {{ statusLabel(user.approval_status) }}
        </span>
        <select
          :value="user.role"
          :disabled="!auth.isAdmin() || actionLoading === user.id"
          @change="setRole(user, ($event.target as HTMLSelectElement).value)"
        >
          <option value="employee">Сотрудник</option>
          <option value="ecologist">Эколог</option>
          <option value="admin">Администратор</option>
        </select>
        <div class="row-actions">
          <button
            v-if="user.approval_status !== 'approved'"
            type="button"
            :disabled="actionLoading === user.id"
            @click="approve(user)"
          >
            Подтвердить
          </button>
          <button
            v-if="user.approval_status !== 'rejected'"
            type="button"
            class="secondary"
            :disabled="actionLoading === user.id"
            @click="reject(user)"
          >
            Отклонить
          </button>
          <button
            v-if="auth.isAdmin() && user.is_active"
            type="button"
            class="danger"
            :disabled="actionLoading === user.id"
            @click="deactivate(user)"
          >
            Отключить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../../api/client'
import { useAuthStore } from '../../stores/auth'

type ApprovalStatus = 'pending' | 'approved' | 'rejected'
type UserRole = 'employee' | 'ecologist' | 'admin'

type UserItem = {
  id: number
  display_name: string
  public_name: string
  email: string | null
  role: UserRole
  approval_status: ApprovalStatus
  is_active: boolean
}

const users = ref<UserItem[]>([])
const auth = useAuthStore()
const loading = ref(false)
const actionLoading = ref<number | null>(null)
const message = ref('')
const hasError = ref(false)
const approvalStatus = ref<ApprovalStatus | 'all'>('pending')

const statusFilters: Array<{ value: ApprovalStatus | 'all'; label: string }> = [
  { value: 'pending', label: 'Ожидают' },
  { value: 'approved', label: 'Подтверждены' },
  { value: 'rejected', label: 'Отклонены' },
  { value: 'all', label: 'Все' },
]

function readError(error: unknown, fallback: string): string {
  const detail = (error as any)?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

function statusLabel(status: ApprovalStatus): string {
  if (status === 'pending') return 'Ожидает'
  if (status === 'approved') return 'Подтвержден'
  return 'Отклонен'
}

function showMessage(text: string, error = false) {
  message.value = text
  hasError.value = error
}

async function loadUsers() {
  loading.value = true
  showMessage('')
  try {
    const params: Record<string, string | number | boolean> = {
      limit: 100,
      include_inactive: true,
    }
    if (approvalStatus.value !== 'all') {
      params.approval_status = approvalStatus.value
    }
    const { data } = await api.get('/admin/users', { params })
    users.value = data.items || []
  } catch (error) {
    showMessage(readError(error, 'Не удалось загрузить пользователей.'), true)
  } finally {
    loading.value = false
  }
}

function setStatus(status: ApprovalStatus | 'all') {
  approvalStatus.value = status
  loadUsers()
}

async function runAction(user: UserItem, action: () => Promise<unknown>, success: string) {
  actionLoading.value = user.id
  showMessage('')
  try {
    await action()
    showMessage(success)
    await loadUsers()
  } catch (error) {
    showMessage(readError(error, 'Не удалось выполнить действие.'), true)
  } finally {
    actionLoading.value = null
  }
}

async function approve(user: UserItem) {
  await runAction(
    user,
    () => api.post(`/admin/users/${user.id}/approve`),
    'Пользователь подтвержден.'
  )
}

async function reject(user: UserItem) {
  await runAction(
    user,
    () => api.post(`/admin/users/${user.id}/reject`),
    'Пользователь отклонен.'
  )
}

async function deactivate(user: UserItem) {
  await runAction(
    user,
    () => api.post(`/admin/users/${user.id}/deactivate`),
    'Пользователь отключен.'
  )
}

async function setRole(user: UserItem, role: string) {
  if (role === user.role) return
  await runAction(
    user,
    () => api.post(`/admin/users/${user.id}/set-role`, { role }),
    'Роль обновлена.'
  )
}

onMounted(loadUsers)
</script>

<style scoped>
.users-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.users-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.admin-hint {
  max-width: 680px;
  margin-top: 6px;
  color: var(--slate-mid);
  font-size: 14px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-button,
.refresh-button,
.row-actions button {
  min-height: 34px;
  border: 1px solid var(--slate-wash);
  border-radius: 8px;
  padding: 0 12px;
  background: var(--white);
  color: var(--slate-deep);
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.filter-button.active {
  border-color: var(--teal);
  background: rgba(42, 122, 110, 0.08);
  color: var(--teal-dark);
}

.panel-message {
  color: var(--teal-dark);
  font-size: 13px;
  font-weight: 700;
}

.panel-message.error {
  color: #A63A3A;
}

.empty-state {
  padding: 22px;
  border-radius: 8px;
  background: var(--slate-bg);
  color: var(--slate-mid);
  text-align: center;
}

.users-table {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--slate-wash);
  border-radius: 8px;
}

.users-table__head,
.user-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.4fr) 130px 150px minmax(240px, 1.5fr);
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
}

.users-table__head {
  background: var(--slate-bg);
  color: var(--slate-mid);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.user-row {
  border-top: 1px solid var(--slate-wash);
}

.user-row strong,
.user-row small {
  display: block;
}

.user-row small {
  margin-top: 2px;
  color: var(--slate-mid);
  font-size: 12px;
}

.user-row select {
  width: 100%;
  border: 1px solid var(--slate-wash);
  border-radius: 8px;
  padding: 8px;
  font: inherit;
}

.status-pill {
  width: fit-content;
  border-radius: 8px;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 800;
  background: var(--slate-bg);
  color: var(--slate-mid);
}

.status-pill--approved {
  background: rgba(42, 122, 110, 0.12);
  color: var(--teal-dark);
}

.status-pill--pending {
  background: rgba(244, 207, 98, 0.22);
  color: #5C4A08;
}

.status-pill--rejected {
  background: rgba(166, 58, 58, 0.12);
  color: #A63A3A;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.row-actions .secondary {
  color: var(--slate-mid);
}

.row-actions .danger {
  border-color: rgba(166, 58, 58, 0.3);
  color: #A63A3A;
}

button:disabled,
select:disabled {
  cursor: progress;
  opacity: 0.6;
}

@media (max-width: 900px) {
  .users-table__head {
    display: none;
  }

  .user-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}
</style>
