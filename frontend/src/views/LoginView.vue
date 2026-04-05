<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <span class="login-badge">НЛМК</span>
        <h1>Зелёная книга</h1>
        <p>Вход для разработки</p>
      </div>
      <div class="login-roles">
        <div v-for="r in roles" :key="r.role" class="role-option" :class="{ selected: selectedRole === r.role }" @click="selectedRole = r.role">
          <span class="role-icon">{{ r.icon }}</span>
          <div>
            <strong>{{ r.label }}</strong>
            <p>{{ r.desc }}</p>
          </div>
        </div>
      </div>
      <el-button type="primary" size="large" style="width: 100%; margin-top: 20px" @click="login" :loading="loading">
        Войти как {{ roles.find(r => r.role === selectedRole)?.label }}
      </el-button>
      <p class="login-note">В продакшене вход через корпоративный SSO (Blitz Identity Provider)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const selectedRole = ref('employee')

const roles = [
  { role: 'employee', icon: '👤', label: 'Сотрудник', desc: 'Создаёт наблюдения' },
  { role: 'ecologist', icon: '🔬', label: 'Эколог', desc: 'Валидирует наблюдения' },
  { role: 'admin', icon: '⚙️', label: 'Администратор', desc: 'Управляет системой' },
]

async function login() {
  loading.value = true
  try {
    const { data } = await axios.post('/api/dev/token', null, {
      params: {
        name: `Dev ${selectedRole.value}`,
        email: `${selectedRole.value}@nlmk.com`,
        role: selectedRole.value,
      }
    })
    auth.setToken(data.token)
    auth.setUser({
      id: 0,
      displayName: data.user.name,
      email: data.user.email,
      role: data.user.role,
    })
    router.push('/')
  } catch (e) {
    console.error(e)
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
  background: linear-gradient(135deg, #5C7F86, #6B8E95);
}
.login-card {
  background: var(--white);
  border-radius: 24px;
  padding: 40px;
  width: 420px;
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
.login-roles { display: flex; flex-direction: column; gap: 8px; }
.role-option {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px; border: 1.5px solid var(--slate-wash);
  border-radius: 12px; cursor: pointer; transition: all 0.2s;
}
.role-option:hover { border-color: var(--teal); }
.role-option.selected { border-color: var(--teal); background: rgba(42,122,110,0.06); box-shadow: 0 0 0 3px rgba(42,122,110,0.1); }
.role-icon { font-size: 28px; }
.role-option strong { display: block; font-size: 15px; color: var(--slate-deep); }
.role-option p { font-size: 12px; color: var(--slate-mid); margin-top: 2px; }
.login-note { text-align: center; font-size: 11px; color: var(--slate-light); margin-top: 16px; }
</style>
