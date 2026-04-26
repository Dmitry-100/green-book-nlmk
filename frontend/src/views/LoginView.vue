<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <span class="login-badge">НЛМК</span>
        <h1>Зелёная книга</h1>
        <p>Вход для разработки</p>
      </div>

      <form class="login-form" @submit.prevent="login">
        <label class="login-field">
          <span>ФИО тестировщика</span>
          <input
            v-model="displayName"
            autocomplete="name"
            placeholder="Например, Иван Иванович Иванов"
          />
        </label>

        <label class="login-field">
          <span>Email, если нужен тот же пользователь на другом устройстве</span>
          <input
            v-model="email"
            autocomplete="email"
            inputmode="email"
            placeholder="name@nlmk.com"
          />
        </label>

        <div class="login-roles">
          <button
            v-for="r in roles"
            :key="r.role"
            type="button"
            class="role-option"
            :class="{ selected: selectedRole === r.role }"
            @click="selectedRole = r.role"
          >
            <span class="role-icon">{{ r.icon }}</span>
            <span>
              <strong>{{ r.label }}</strong>
              <small>{{ r.desc }}</small>
            </span>
          </button>
        </div>

        <p v-if="loginError" class="login-error">{{ loginError }}</p>
        <button class="login-submit" type="submit" :disabled="loading">
          {{ loading ? 'Входим...' : `Войти как ${selectedRoleLabel}` }}
        </button>
        <p class="login-helper">
          Для тестового контура имя попадёт в наблюдения, рейтинги и комментарии. Если email не указан, создадим стабильный dev-профиль по ФИО и роли.
        </p>
      </form>

      <p class="login-note">В продакшене вход через корпоративный SSO (Blitz Identity Provider)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import {
  DEV_AUTH_DISPLAY_NAME_STORAGE_KEY,
  DEV_AUTH_EMAIL_STORAGE_KEY,
  buildDevAuthEmail,
  isInvalidDevAuthEmail,
  normalizeDevAuthDisplayName,
  normalizeDevAuthEmail,
  type DevAuthRole,
} from '../utils/devAuthIdentity'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const selectedRole = ref<DevAuthRole>('employee')
const displayName = ref(localStorage.getItem(DEV_AUTH_DISPLAY_NAME_STORAGE_KEY) || '')
const email = ref(localStorage.getItem(DEV_AUTH_EMAIL_STORAGE_KEY) || '')
const loginError = ref('')

const roles: Array<{ role: DevAuthRole; icon: string; label: string; desc: string }> = [
  { role: 'employee', icon: '👤', label: 'Сотрудник', desc: 'Создаёт наблюдения' },
  { role: 'ecologist', icon: '🔬', label: 'Эколог', desc: 'Валидирует наблюдения' },
  { role: 'admin', icon: '⚙️', label: 'Администратор', desc: 'Управляет системой' },
]

const selectedRoleLabel = computed(() => (
  roles.find(r => r.role === selectedRole.value)?.label || 'Сотрудник'
))

async function login() {
  loginError.value = ''
  const testerName = normalizeDevAuthDisplayName(displayName.value)
  const testerEmail = normalizeDevAuthEmail(email.value)
  if (!testerName) {
    loginError.value = 'Введите ФИО, чтобы тестовые наблюдения были подписаны вашим именем.'
    return
  }
  if (isInvalidDevAuthEmail(email.value)) {
    loginError.value = 'Проверьте email или оставьте поле пустым.'
    return
  }

  loading.value = true
  try {
    const devEmail = buildDevAuthEmail(testerName, selectedRole.value, testerEmail)
    const { data } = await axios.post('/api/dev/token', null, {
      params: {
        name: testerName,
        email: devEmail,
        role: selectedRole.value,
      }
    })
    localStorage.setItem(DEV_AUTH_DISPLAY_NAME_STORAGE_KEY, testerName)
    if (testerEmail) {
      localStorage.setItem(DEV_AUTH_EMAIL_STORAGE_KEY, testerEmail)
    } else {
      localStorage.removeItem(DEV_AUTH_EMAIL_STORAGE_KEY)
    }
    auth.setToken(data.token)
    auth.setUser({
      id: 0,
      displayName: data.user.name,
      email: data.user.email,
      role: data.user.role,
    })
    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirectTo)
  } catch (e) {
    console.error(e)
    loginError.value = 'Не удалось войти в тестовый контур. Попробуйте ещё раз.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: linear-gradient(135deg, #5C7F86, #6B8E95);
}
.login-card {
  background: var(--white);
  border-radius: 8px;
  padding: 40px;
  width: min(460px, calc(100vw - 32px));
  box-shadow: 0 24px 80px rgba(0,0,0,0.2);
}
.login-header { text-align: center; margin-bottom: 28px; }
.login-badge {
  display: inline-block;
  background: var(--slate-bg);
  color: var(--slate-deep);
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.5px;
  margin-bottom: 12px;
}
.login-header h1 { font-family: var(--font-display); font-size: 28px; color: var(--teal-dark); }
.login-header p { font-size: 14px; color: var(--slate-mid); margin-top: 4px; }
.login-form { display: flex; flex-direction: column; gap: 14px; }
.login-field { display: flex; flex-direction: column; gap: 6px; }
.login-field span { font-size: 13px; font-weight: 700; color: var(--slate-deep); }
.login-field input {
  width: 100%;
  border: 1.5px solid var(--slate-wash);
  border-radius: 8px;
  padding: 12px 14px;
  font: inherit;
  color: var(--slate-deep);
  outline: none;
}
.login-field input:focus { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(42,122,110,0.1); }
.login-roles { display: flex; flex-direction: column; gap: 8px; }
.role-option {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px; border: 1.5px solid var(--slate-wash);
  border-radius: 8px; cursor: pointer; transition: all 0.2s;
  background: var(--white);
  text-align: left;
}
.role-option:hover { border-color: var(--teal); }
.role-option.selected { border-color: var(--teal); background: rgba(42,122,110,0.06); box-shadow: 0 0 0 3px rgba(42,122,110,0.1); }
.role-icon { font-size: 28px; }
.role-option strong { display: block; font-size: 15px; color: var(--slate-deep); }
.role-option small { display: block; font-size: 12px; color: var(--slate-mid); margin-top: 2px; }
.login-error { color: #A63A3A; font-size: 13px; font-weight: 700; }
.login-submit {
  width: 100%;
  border: 0;
  border-radius: 8px;
  padding: 14px 18px;
  background: var(--teal);
  color: var(--white);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}
.login-submit:hover:not(:disabled) { background: var(--teal-dark); }
.login-submit:disabled { opacity: 0.65; cursor: progress; }
.login-helper { font-size: 12px; line-height: 1.5; color: var(--slate-mid); }
.login-note { text-align: center; font-size: 11px; color: var(--slate-light); margin-top: 16px; }
</style>
