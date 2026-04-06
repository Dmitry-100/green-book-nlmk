<template>
  <div class="profile-page">
    <div v-if="authError" class="auth-error">
      <p>Для просмотра профиля необходимо войти в систему.</p>
      <router-link to="/login" class="auth-error__link">Войти</router-link>
    </div>
    <div class="profile-header" v-else>
      <div class="profile-avatar">{{ profile?.display_name?.charAt(0) || 'У' }}</div>
      <div class="profile-info">
        <h1>{{ profile?.display_name || 'Загрузка...' }}</h1>
        <div class="profile-stats-row">
          <div class="profile-stat">
            <span class="profile-stat__number">{{ profile?.total_points || 0 }}</span>
            <span class="profile-stat__label">Баллов</span>
          </div>
          <div class="profile-stat">
            <span class="profile-stat__number">{{ profile?.confirmed_observations || 0 }}</span>
            <span class="profile-stat__label">Наблюдений</span>
          </div>
          <div class="profile-stat">
            <span class="profile-stat__number">{{ profile?.species_collected || 0 }}</span>
            <span class="profile-stat__label">Видов</span>
          </div>
          <div class="profile-stat">
            <span class="profile-stat__number">{{ profile?.first_discoveries || 0 }}</span>
            <span class="profile-stat__label">Открытий</span>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <h2 class="section-title">Достижения</h2>
      <div class="achievements-grid" v-if="profile?.achievements?.length">
        <div v-for="a in profile.achievements" :key="a.code" class="achievement-card">
          <span class="achievement-icon">{{ a.icon }}</span>
          <strong>{{ a.name }}</strong>
          <p>{{ a.description }}</p>
        </div>
      </div>
      <p v-else class="empty-hint">Пока нет достижений. Создайте первое наблюдение!</p>
    </div>

    <div class="section">
      <div class="section-header">
        <h2 class="section-title">Лидерборд</h2>
        <div class="period-tabs">
          <button v-for="p in [{key:'month',label:'Месяц'},{key:'quarter',label:'Квартал'},{key:'year',label:'Год'},{key:'all',label:'Все время'}]"
                  :key="p.key"
                  class="period-tab"
                  :class="{ active: leaderboardPeriod === p.key }"
                  @click="fetchLeaderboard(p.key)">
            {{ p.label }}
          </button>
        </div>
      </div>
      <div class="leaderboard">
        <div v-for="(l, i) in leaders" :key="l.user_id" class="leader-item">
          <span class="leader-rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">{{ i + 1 }}</span>
          <div class="leader-avatar">{{ l.display_name?.charAt(0) || '?' }}</div>
          <span class="leader-name">{{ l.display_name }}</span>
          <span class="leader-points">{{ l.total_points }} баллов</span>
        </div>
        <p v-if="leaders.length === 0" class="empty-hint">Пока нет данных</p>
      </div>
    </div>

    <div class="section" v-if="fact">
      <h2 class="section-title">Факт дня</h2>
      <div class="fact-card" :style="fact.photo_url ? { backgroundImage: `linear-gradient(to right, rgba(27,77,79,0.9) 0%, rgba(27,77,79,0.7) 50%, transparent 100%), url(${fact.photo_url})` } : {}">
        <div class="fact-content">
          <h3>{{ fact.name_ru }}</h3>
          <div class="fact-latin">{{ fact.name_latin }}</div>
          <p>{{ fact.description }}</p>
          <router-link :to="`/species/${fact.species_id}`" class="fact-link">Подробнее &rarr;</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

const profile = ref<any>(null)
const leaders = ref<any[]>([])
const fact = ref<any>(null)
const leaderboardPeriod = ref('all')
const authError = ref(false)

async function fetchLeaderboard(period: string) {
  leaderboardPeriod.value = period
  try {
    const { data } = await api.get(`/gamification/leaderboard?period=${period}`)
    leaders.value = data.leaders || []
  } catch {}
}

onMounted(async () => {
  // Profile (requires auth)
  try {
    const { data } = await api.get('/gamification/profile')
    profile.value = data
  } catch (e: any) {
    if (e.response?.status === 401) authError.value = true
  }
  // Leaderboard + fact (no auth needed)
  try {
    const [l, f] = await Promise.all([
      api.get('/gamification/leaderboard'),
      api.get('/gamification/fact-of-day'),
    ])
    leaders.value = l.data.leaders || []
    fact.value = f.data.fact !== null ? f.data : null
  } catch {}
})
</script>

<style scoped>
.profile-page { max-width: 900px; margin: 0 auto; padding: 32px; }
.profile-header { display: flex; align-items: center; gap: 28px; margin-bottom: 36px; }
.profile-avatar {
  width: 80px; height: 80px; border-radius: 50%; background: var(--teal);
  color: white; font-size: 32px; font-weight: 700; display: flex;
  align-items: center; justify-content: center; flex-shrink: 0;
}
.profile-info h1 { font-family: var(--font-display); font-size: 30px; color: var(--teal-dark); margin-bottom: 12px; }
.profile-stats-row { display: flex; gap: 24px; }
.profile-stat { text-align: center; }
.profile-stat__number { display: block; font-family: var(--font-display); font-size: 28px; font-weight: 700; color: var(--teal); }
.profile-stat__label { font-size: 11px; color: var(--slate-mid); text-transform: uppercase; letter-spacing: 0.5px; }

.section { margin-bottom: 32px; }
.section-title { font-family: var(--font-display); font-size: 24px; color: var(--teal-dark); margin-bottom: 16px; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.section-header .section-title { margin-bottom: 0; }
.period-tabs { display: flex; gap: 4px; background: var(--slate-wash, #E8EEF0); border-radius: 8px; padding: 3px; }
.period-tab { padding: 6px 14px; border: none; background: transparent; border-radius: 6px; font-size: 12px; font-weight: 600; color: var(--slate-mid, #8FA5AB); cursor: pointer; transition: all 0.2s; }
.period-tab:hover { color: var(--teal, #2A7A6E); }
.period-tab.active { background: white; color: var(--teal, #2A7A6E); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }

.achievements-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.achievement-card {
  background: var(--white); border-radius: 12px; padding: 20px; text-align: center;
  box-shadow: var(--shadow-card); transition: transform 0.2s;
}
.achievement-card:hover { transform: translateY(-2px); }
.achievement-icon { font-size: 36px; display: block; margin-bottom: 8px; }
.achievement-card strong { font-size: 14px; color: var(--slate-deep); display: block; margin-bottom: 4px; }
.achievement-card p { font-size: 12px; color: var(--slate-mid); }

.leaderboard { background: var(--white); border-radius: 16px; padding: 4px; box-shadow: var(--shadow-card); }
.leader-item {
  display: flex; align-items: center; gap: 14px; padding: 14px 20px;
  border-bottom: 1px solid var(--slate-wash); transition: background 0.2s;
}
.leader-item:last-child { border-bottom: none; }
.leader-item:hover { background: var(--slate-bg); }
.leader-rank { font-family: var(--font-display); font-size: 22px; font-weight: 700; color: var(--slate-light); width: 32px; text-align: center; }
.leader-rank.gold { color: #FFC107; }
.leader-rank.silver { color: #90A4AE; }
.leader-rank.bronze { color: #CD7F32; }
.leader-avatar {
  width: 36px; height: 36px; border-radius: 50%; background: var(--slate-wash);
  color: var(--slate-mid); font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.leader-name { flex: 1; font-weight: 600; color: var(--slate-deep); }
.leader-points { font-family: var(--font-display); font-size: 18px; color: var(--teal); font-weight: 700; }

.fact-card {
  border-radius: 16px; overflow: hidden; min-height: 200px;
  background-size: cover; background-position: center right;
  background-color: var(--teal-dark); display: flex; align-items: center;
}
.fact-content { padding: 32px; max-width: 500px; }
.fact-content h3 { font-family: var(--font-display); font-size: 26px; color: white; }
.fact-latin { font-family: var(--font-display); font-style: italic; color: rgba(255,255,255,0.7); margin-bottom: 12px; }
.fact-content p { font-size: 14px; color: rgba(255,255,255,0.85); line-height: 1.7; margin-bottom: 16px; }
.fact-link { color: white; font-weight: 600; text-decoration: none; border-bottom: 1px solid rgba(255,255,255,0.4); }

.empty-hint { color: var(--slate-light); font-size: 14px; }
.auth-error { text-align: center; padding: 60px 20px; }
.auth-error p { font-size: 16px; color: var(--slate-mid, #8FA5AB); margin-bottom: 16px; }
.auth-error__link { display: inline-block; padding: 10px 28px; background: var(--teal, #2A7A6E); color: white; border-radius: 8px; text-decoration: none; font-weight: 600; }
.auth-error__link:hover { opacity: 0.9; }
</style>
