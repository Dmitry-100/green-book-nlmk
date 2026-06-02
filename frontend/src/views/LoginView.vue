<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <img src="/logo-nlmk.svg" alt="НЛМК" class="login-logo" />
        <h1>Зелёная книга</h1>
        <p>Вход нужен для наблюдений и личных разделов.</p>
      </div>

      <div class="login-tabs" role="tablist" aria-label="Вход и регистрация">
        <button
          type="button"
          class="login-tab"
          :class="{ active: mode === 'login' }"
          @click="mode = 'login'"
        >
          Вход
        </button>
        <button
          type="button"
          class="login-tab"
          :class="{ active: mode === 'register' }"
          @click="mode = 'register'"
        >
          Регистрация
        </button>
      </div>

      <form v-if="mode === 'login'" class="login-form" @submit.prevent="login">
        <label class="login-field">
          <span>Логин</span>
          <input v-model="loginForm.login" autocomplete="username" placeholder="ivanov_dm" />
        </label>

        <label class="login-field">
          <span>Пароль</span>
          <input
            v-model="loginForm.password"
            autocomplete="current-password"
            type="password"
          />
        </label>

        <p v-if="message" class="login-message" :class="{ error: hasError }">{{ message }}</p>
        <button class="login-submit" type="submit" :disabled="loading">
          {{ loading ? 'Проверяем...' : 'Войти' }}
        </button>
      </form>

      <form v-else class="login-form" @submit.prevent="register">
        <label class="login-field">
          <span>Логин</span>
          <input v-model="registerForm.login" autocomplete="username" placeholder="ivanov_dm" />
        </label>

        <label class="login-field">
          <span>Фамилия, имя и отчество</span>
          <input
            v-model="registerForm.displayName"
            autocomplete="name"
            placeholder="Иванов Дмитрий Максимович"
          />
        </label>

        <label class="login-field">
          <span>Email</span>
          <input
            v-model="registerForm.email"
            autocomplete="email"
            inputmode="email"
            placeholder="name@example.com"
          />
        </label>

        <label class="login-field">
          <span>Пароль</span>
          <input
            v-model="registerForm.password"
            autocomplete="new-password"
            type="password"
          />
        </label>

        <label class="notice-check">
          <input v-model="registerForm.personalDataNoticeAccepted" type="checkbox" />
          <span>
            Я понимаю, что имя, логин и email будут использоваться для входа,
            обработки наблюдений и служебного аудита. В публичных разделах будут
            отображаться инициалы.
          </span>
        </label>

        <p v-if="message" class="login-message" :class="{ error: hasError }">{{ message }}</p>
        <button class="login-submit" type="submit" :disabled="loading">
          {{ loading ? 'Отправляем...' : 'Отправить заявку' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'

type AuthUserPayload = {
  id: number
  display_name: string
  public_name: string
  email: string | null
  role: 'employee' | 'ecologist' | 'admin'
  approval_status: 'pending' | 'approved' | 'rejected'
  is_active: boolean
  must_change_password: boolean
}

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const mode = ref<'login' | 'register'>('login')
const message = ref('')
const hasError = ref(false)

const loginForm = reactive({
  login: '',
  password: '',
})

const registerForm = reactive({
  login: '',
  displayName: '',
  email: '',
  password: '',
  personalDataNoticeAccepted: false,
})

function mapUser(user: AuthUserPayload) {
  return {
    id: user.id,
    displayName: user.display_name,
    publicName: user.public_name,
    email: user.email,
    role: user.role,
    approvalStatus: user.approval_status,
    isActive: user.is_active,
    mustChangePassword: user.must_change_password,
  }
}

function readError(error: unknown, fallback: string): string {
  const response = (error as any)?.response
  const detail = response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) return 'Проверьте заполнение полей.'
  return fallback
}

function resetMessage() {
  message.value = ''
  hasError.value = false
}

async function login() {
  resetMessage()
  if (!loginForm.login.trim() || !loginForm.password) {
    message.value = 'Введите логин и пароль.'
    hasError.value = true
    return
  }

  loading.value = true
  try {
    const { data } = await api.post('/auth/login', {
      login: loginForm.login,
      password: loginForm.password,
    })
    auth.setSession(data.access_token, mapUser(data.user))
    const redirectTo = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirectTo)
  } catch (error) {
    message.value = readError(error, 'Не удалось войти. Попробуйте ещё раз.')
    hasError.value = true
  } finally {
    loading.value = false
  }
}

async function register() {
  resetMessage()
  if (
    !registerForm.login.trim()
    || !registerForm.displayName.trim()
    || !registerForm.password
  ) {
    message.value = 'Заполните логин, имя и пароль.'
    hasError.value = true
    return
  }
  if (!registerForm.personalDataNoticeAccepted) {
    message.value = 'Подтвердите уведомление об обработке данных.'
    hasError.value = true
    return
  }

  loading.value = true
  try {
    const { data } = await api.post('/auth/register', {
      login: registerForm.login,
      password: registerForm.password,
      display_name: registerForm.displayName,
      email: registerForm.email || null,
      personal_data_notice_accepted: registerForm.personalDataNoticeAccepted,
    })
    mode.value = 'login'
    loginForm.login = registerForm.login
    loginForm.password = ''
    message.value = data.message || 'Заявка отправлена и ожидает подтверждения.'
    hasError.value = false
  } catch (error) {
    message.value = readError(error, 'Не удалось отправить заявку. Проверьте поля.')
    hasError.value = true
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 105px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: linear-gradient(135deg, #5C7F86, #F4CF62);
}

.login-card {
  width: min(480px, calc(100vw - 32px));
  border-radius: 8px;
  padding: 36px;
  background: var(--white);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.login-logo {
  width: 86px;
  height: auto;
  margin-bottom: 10px;
}

.login-header h1 {
  font-family: var(--font-display);
  font-size: 30px;
  color: var(--teal-dark);
}

.login-header p {
  font-size: 14px;
  color: var(--slate-mid);
  margin-top: 4px;
}

.login-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  margin-bottom: 18px;
  padding: 4px;
  border-radius: 8px;
  background: var(--slate-bg);
}

.login-tab {
  min-height: 38px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--slate-mid);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.login-tab.active {
  background: var(--white);
  color: var(--teal-dark);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.login-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.login-field span {
  font-size: 13px;
  font-weight: 700;
  color: var(--slate-deep);
}

.login-field input {
  width: 100%;
  border: 1.5px solid var(--slate-wash);
  border-radius: 8px;
  padding: 12px 14px;
  font: inherit;
  color: var(--slate-deep);
  outline: none;
}

.login-field input:focus {
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(42, 122, 110, 0.1);
}

.notice-check {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid rgba(42, 122, 110, 0.18);
  border-radius: 8px;
  color: var(--slate-mid);
  font-size: 12px;
  line-height: 1.45;
  background: rgba(42, 122, 110, 0.06);
}

.notice-check input {
  width: 18px;
  height: 18px;
  margin-top: 1px;
}

.login-message {
  color: var(--teal-dark);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
}

.login-message.error {
  color: #A63A3A;
}

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

.login-submit:hover:not(:disabled) {
  background: var(--teal-dark);
}

.login-submit:disabled {
  opacity: 0.65;
  cursor: progress;
}
</style>
