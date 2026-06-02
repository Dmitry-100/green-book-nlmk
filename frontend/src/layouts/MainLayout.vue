<template>
  <div class="layout">
    <nav class="portal-nav">
      <div class="portal-nav__logo">
        <img src="/logo-nlmk-white.svg" alt="НЛМК" class="nlmk-logo" />
        <span>Зелёная книга</span>
      </div>
      <ul class="portal-nav__links">
        <li><router-link to="/" class="active">Природа</router-link></li>
        <li><router-link to="/species">Виды</router-link></li>
        <li><router-link to="/exhibition">Выставка</router-link></li>
      </ul>
      <div class="portal-nav__right">
        <div v-if="auth.token" class="notification-bell" @click="$router.push('/my')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
        </div>
        <button v-if="auth.token" type="button" class="session-button" @click="logout">
          Выйти
        </button>
        <button v-else type="button" class="session-button" @click="$router.push('/login')">
          Войти
        </button>
        <div
          v-if="auth.token"
          class="user-avatar"
          @click="$router.push('/profile')"
          style="cursor:pointer"
          title="Мой профиль"
        >
          {{ userInitials }}
        </div>
      </div>
    </nav>

    <div class="section-nav">
      <router-link to="/" exact-active-class="active">Главная</router-link>
      <router-link to="/map" active-class="active">Карта</router-link>
      <router-link to="/species" active-class="active">Виды</router-link>
      <router-link to="/identify" active-class="active">Определитель</router-link>
      <router-link to="/my" active-class="active">Мои наблюдения</router-link>
      <router-link to="/quiz" active-class="active">Викторина</router-link>
      <router-link to="/passport" active-class="active">Экопаспорт</router-link>
      <router-link to="/routes" active-class="active">Маршруты</router-link>
      <router-link to="/exhibition" active-class="active">Выставка</router-link>
      <router-link to="/help" active-class="active">Правила</router-link>
      <router-link v-if="auth.isEcologist()" to="/expert" active-class="active">Эколог</router-link>
      <router-link v-if="auth.isAdmin()" to="/admin" active-class="active">Админ</router-link>
      <router-link v-else-if="auth.isEcologist()" to="/admin" active-class="active">Заявки</router-link>
    </div>

    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'
import { buildUserInitials, normalizeDemoDisplayName } from '../utils/userInitials'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const unreadCount = ref(0)
const userInitials = computed(() => (
  auth.user?.publicName || buildUserInitials(normalizeDemoDisplayName(auth.user?.displayName), '?')
))
let pollTimer: number | null = null
let unreadRequest: Promise<void> | null = null
let lastUnreadFetchAt = 0
const MIN_UNREAD_REFRESH_MS = 5000

async function fetchUnreadCount(force = false) {
  if (!auth.token) {
    unreadCount.value = 0
    lastUnreadFetchAt = 0
    return
  }
  const now = Date.now()
  if (!force && now - lastUnreadFetchAt < MIN_UNREAD_REFRESH_MS) {
    return
  }
  if (unreadRequest) {
    return unreadRequest
  }

  unreadRequest = (async () => {
    try {
      const { data } = await api.get('/notifications/unread-count')
      unreadCount.value = data.count || 0
    } catch {
      unreadCount.value = 0
    } finally {
      lastUnreadFetchAt = Date.now()
      unreadRequest = null
    }
  })()
  await unreadRequest
}

async function logout() {
  const redirect = route.name === 'login' ? '/' : route.fullPath || '/'
  try {
    await api.post('/auth/logout')
  } catch {
    // Local session cleanup is enough for this stateless token flow.
  }
  auth.clearSession()
  unreadCount.value = 0
  lastUnreadFetchAt = 0
  router.push({ name: 'login', query: { redirect } })
}

onMounted(async () => {
  await fetchUnreadCount(true)
  pollTimer = window.setInterval(fetchUnreadCount, 30000)
})

onUnmounted(() => {
  if (pollTimer) {
    window.clearInterval(pollTimer)
  }
})

watch(
  () => auth.token,
  () => {
    fetchUnreadCount(true)
  }
)
</script>

<style scoped>
.nlmk-logo {
  width: 54px;
  height: auto;
  display: block;
}

.session-button {
  min-height: 32px;
  border: 1px solid rgba(250, 251, 252, 0.34);
  border-radius: 8px;
  padding: 0 12px;
  background: rgba(250, 251, 252, 0.08);
  color: var(--slate-pale);
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  white-space: nowrap;
}

.session-button:hover {
  background: rgba(250, 251, 252, 0.14);
  border-color: rgba(250, 251, 252, 0.55);
}

@media (max-width: 768px) {
  .session-button {
    padding: 0 10px;
    font-size: 11px;
  }
}
</style>
