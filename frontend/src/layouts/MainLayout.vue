<template>
  <div class="layout">
    <nav class="portal-nav">
      <div class="portal-nav__logo">
        <span class="nlmk-badge">НЛМК</span>
        Корпоративный портал
      </div>
      <ul class="portal-nav__links">
        <li><span class="disabled" title="Раздел корпоративного портала">Новости</span></li>
        <li><router-link to="/" class="active">Природа</router-link></li>
        <li><span class="disabled" title="Раздел корпоративного портала">Сервисы</span></li>
      </ul>
      <div class="portal-nav__right">
        <div class="notification-bell" @click="$router.push('/my')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
        </div>
        <div class="user-avatar" @click="$router.push('/login')" style="cursor:pointer" title="Сменить роль">ДС</div>
      </div>
    </nav>

    <div class="section-nav">
      <router-link to="/" exact-active-class="active">Главная</router-link>
      <router-link to="/map" active-class="active">Карта</router-link>
      <router-link to="/species" active-class="active">Виды</router-link>
      <router-link to="/identify" active-class="active">Определитель</router-link>
      <router-link to="/my" active-class="active">Мои наблюдения</router-link>
      <router-link to="/help" active-class="active">Правила</router-link>
      <router-link to="/expert" active-class="active">Эколог</router-link>
      <router-link to="/admin" active-class="active">Админ</router-link>
    </div>

    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const unreadCount = ref(3)
</script>

<style scoped>
.portal-nav__links .disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
