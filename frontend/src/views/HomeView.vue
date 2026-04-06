<template>
  <div class="home">
    <!-- Hero with swan -->
    <div class="hero">
      <div class="hero__bg" :style="{ backgroundImage: 'url(/img/swan-hero.png)' }"></div>
      <div class="hero__gradient-left"></div>
      <div class="hero__nlmk-badge">НЛМК</div>
      <div class="hero-content">
        <div class="hero-text">
          <h1>Зелёная книга<br>ПАО &laquo;НЛМК&raquo;</h1>
          <div class="hero-subtitle">Растительный и животный мир</div>
          <p>Наблюдайте, фиксируйте, помогайте изучать биоразнообразие промышленной площадки. Каждое ваше наблюдение вносит вклад в Зелёную книгу.</p>
          <div class="hero-actions">
            <router-link to="/observe" class="btn btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
              Сообщить наблюдение
            </router-link>
            <router-link to="/observe?incident=1" class="btn btn-secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              Инцидент
            </router-link>
          </div>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <div class="hero-stat__number">{{ stats.species }}</div>
            <div class="hero-stat__label">Видов</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat__number">{{ stats.confirmed }}</div>
            <div class="hero-stat__label">Подтверждено</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat__number">{{ stats.on_review }}</div>
            <div class="hero-stat__label">На проверке</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat__number">{{ stats.total_obs }}</div>
            <div class="hero-stat__label">Наблюдений</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="section">
      <div class="quick-grid">
        <router-link v-for="g in groups" :key="g.value" :to="`/species?group=${g.value}`" class="quick-card" :style="{ backgroundImage: `linear-gradient(to top, rgba(27,77,79,0.85) 0%, rgba(27,77,79,0.4) 50%, transparent 100%), url(${g.photo})` }">
          <div class="quick-card__content">
            <div class="quick-card__title">{{ g.label }}</div>
            <div class="quick-card__desc">{{ g.count }} видов</div>
          </div>
        </router-link>
      </div>
    </div>

    <!-- Species of the Month + Challenge -->
    <div class="section" v-if="challenge">
      <div class="section-header">
        <h2 class="section-title">Вид месяца</h2>
      </div>
      <div class="spotlight" :style="{ backgroundImage: challenge.species.photo_url ? `linear-gradient(to right, rgba(27,77,79,0.92) 0%, rgba(27,77,79,0.75) 45%, rgba(27,77,79,0.2) 100%), url(${challenge.species.photo_url})` : '' }">
        <div class="spotlight__body">
          <span class="spotlight__label">{{ challenge.month }} {{ challenge.year }}</span>
          <h3 class="spotlight__name">{{ challenge.species.name_ru }}</h3>
          <div class="spotlight__latin">{{ challenge.species.name_latin }}</div>
          <p class="spotlight__desc" v-if="challenge.species.conservation_status">{{ challenge.species.conservation_status }}</p>
          <div v-if="challenge.found" class="spotlight__challenge spotlight__challenge--found">
            Найден! Первым обнаружил: <strong>{{ challenge.finder.display_name }}</strong>
          </div>
          <div v-else class="spotlight__challenge spotlight__challenge--active">
            Челлендж: кто первый найдёт этот вид — получит спецбейдж!
          </div>
          <router-link :to="`/species/${challenge.species.id}`" class="btn btn-spotlight">Подробнее о виде &rarr;</router-link>
        </div>
      </div>
    </div>

    <!-- Fact of Day -->
    <div class="section" v-if="factOfDay">
      <div class="section-header">
        <h2 class="section-title">Факт дня</h2>
      </div>
      <div class="fact-banner" :style="factOfDay.photo_url ? { backgroundImage: `linear-gradient(to right, rgba(27,77,79,0.92) 0%, rgba(27,77,79,0.7) 50%, transparent 100%), url(${factOfDay.photo_url})` } : {}">
        <div class="fact-banner__body">
          <h3>{{ factOfDay.name_ru }}</h3>
          <div class="fact-banner__latin">{{ factOfDay.name_latin }}</div>
          <p>{{ factOfDay.description?.slice(0, 200) }}{{ factOfDay.description?.length > 200 ? '...' : '' }}</p>
          <router-link :to="`/species/${factOfDay.species_id}`" class="btn-spotlight">Подробнее &rarr;</router-link>
        </div>
      </div>
    </div>

    <!-- Recent species -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">Каталог видов</h2>
        <router-link to="/species" class="section-link">Все виды &rarr;</router-link>
      </div>
      <div class="species-grid">
        <div v-for="s in recentSpecies" :key="s.id" class="species-card" @click="$router.push(`/species/${s.id}`)">
          <div class="species-card__img" :style="s.photo_urls?.length ? { backgroundImage: `url(${s.photo_urls[0]})` } : {}">
            <div v-if="!s.photo_urls?.length" class="species-card__no-photo">{{ groupIcon(s.group) }}</div>
            <div class="species-card__status" :class="statusClass(s.category)"></div>
            <div v-if="s.is_poisonous" class="species-card__poison">&#9888;</div>
          </div>
          <div class="species-card__body">
            <div class="species-card__name-ru">{{ s.name_ru }}</div>
            <div class="species-card__name-lat">{{ s.name_latin }}</div>
            <div class="species-card__tags">
              <span class="tag tag--group">{{ groupLabel(s.group) }}</span>
              <span v-if="s.category === 'red_book'" class="tag tag--redbook">Красная книга</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- News Feed -->
    <div class="section" v-if="recentObs.length">
      <div class="section-header">
        <h2 class="section-title">Последние находки</h2>
        <router-link to="/map" class="section-link">На карте &rarr;</router-link>
      </div>
      <div class="news-feed">
        <router-link v-for="o in recentObs" :key="o.id" :to="`/observations/${o.id}`" class="news-item">
          <div class="news-item__icon">{{ groupIcon(o.group) }}</div>
          <div class="news-item__body">
            <div class="news-item__title">{{ groupLabel(o.group) }}</div>
            <div class="news-item__comment" v-if="o.comment">{{ o.comment.slice(0, 80) }}{{ o.comment.length > 80 ? '...' : '' }}</div>
            <div class="news-item__date">{{ formatNewsDate(o.observed_at) }}</div>
          </div>
          <span class="news-item__badge">Подтверждено</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '../api/client'

const stats = reactive({ species: 0, confirmed: 0, on_review: 0, total_obs: 0 })
const recentSpecies = ref<any[]>([])
const factOfDay = ref<any>(null)
const challenge = ref<any>(null)
const recentObs = ref<any[]>([])

const groups = [
  { value: 'plants', icon: '🌿', label: 'Растения', count: 0, photo: '/api/media/species-pdf/page05_img02.png' },
  { value: 'fungi', icon: '🍄', label: 'Грибы', count: 0, photo: '/api/media/species-pdf/page12_img00.png' },
  { value: 'insects', icon: '🐛', label: 'Насекомые', count: 0, photo: '/api/media/species-pdf/page20_img04.png' },
  { value: 'birds', icon: '🐦', label: 'Птицы', count: 0, photo: '/api/media/species-pdf/page23_img07.png' },
  { value: 'herpetofauna', icon: '🐍', label: 'Герпетофауна', count: 0, photo: '/api/media/species-pdf/page21_img03.png' },
  { value: 'mammals', icon: '🦔', label: 'Млекопитающие', count: 0, photo: '/api/media/species-pdf/page29_img00.png' },
]

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }

function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }
function groupLabel(g: string) { return GROUP_LABELS[g] || g }
function statusClass(cat: string) {
  if (cat === 'red_book') return 'species-card__status--reference'
  if (cat === 'rare') return 'species-card__status--potential'
  return 'species-card__status--confirmed'
}
function formatNewsDate(iso: string) {
  const d = new Date(iso)
  const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}, ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

onMounted(async () => {
  try {
    const { data } = await api.get('/species', { params: { limit: 200 } })
    stats.species = data.total
    recentSpecies.value = data.items.slice(0, 8)
    for (const g of groups) {
      g.count = data.items.filter((s: any) => s.group === g.value).length
    }
  } catch {}
  try {
    const { data } = await api.get('/observations', { params: { limit: 1 } })
    stats.total_obs = data.total
  } catch {}
  try {
    const { data } = await api.get('/observations', { params: { status: 'confirmed', limit: 1 } })
    stats.confirmed = data.total
  } catch {}
  try {
    const { data } = await api.get('/observations', { params: { status: 'on_review', limit: 1 } })
    stats.on_review = data.total
  } catch {}
  try {
    const { data } = await api.get('/gamification/fact-of-day')
    if (data.species_id) factOfDay.value = data
  } catch {}
  try {
    const { data } = await api.get('/gamification/challenge')
    if (data.species) challenge.value = data
  } catch {}
  try {
    const { data } = await api.get('/observations', { params: { status: 'confirmed', limit: 5 } })
    recentObs.value = data.items || []
  } catch {}
})
</script>

<style scoped>
/* === HERO === */
.hero {
  position: relative;
  background: #6B8E95;
  min-height: 420px;
  display: flex;
  align-items: stretch;
  overflow: hidden;
}
.hero__bg {
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 65%;
  background-size: cover;
  background-position: center right;
  z-index: 1;
  animation: heroBgReveal 1.2s ease-out;
}
.hero__bg::before {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 60%;
  background: linear-gradient(to right, #6B8E95 0%, rgba(107,142,149,0.7) 50%, transparent 100%);
  z-index: 2;
}
.hero__gradient-left {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 50%;
  background: linear-gradient(135deg, #5C7F86 0%, #6B8E95 40%, rgba(107,142,149,0.85) 100%);
  z-index: 2;
}
.hero__nlmk-badge {
  position: absolute;
  top: 24px; right: 28px;
  z-index: 10;
  width: 56px; height: 40px;
  border: 2px solid rgba(255,255,255,0.6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.8);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1px;
}
.hero-content {
  position: relative;
  z-index: 5;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 56px 48px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  align-items: center;
}
.hero-text {
  animation: heroSlideIn 0.8s ease-out;
}
.hero h1 {
  font-family: var(--font-display);
  font-size: 46px;
  font-weight: 700;
  color: white;
  line-height: 1.1;
  margin-bottom: 8px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.15);
}
.hero-subtitle {
  font-size: 16px;
  color: white;
  opacity: 0.85;
  margin-bottom: 20px;
}
.hero p {
  font-size: 14px;
  color: rgba(255,255,255,0.7);
  line-height: 1.7;
  margin-bottom: 28px;
  max-width: 420px;
}
.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
  text-decoration: none;
}
.btn-primary {
  background: var(--teal);
  color: white;
  box-shadow: 0 2px 8px rgba(42,122,110,0.3);
}
.btn-primary:hover { background: var(--teal-light); transform: translateY(-1px); }
.btn-secondary {
  background: rgba(255,255,255,0.12);
  color: white;
  border: 1px solid rgba(255,255,255,0.2);
}
.btn-secondary:hover { background: rgba(255,255,255,0.2); }
.btn-outline-dark {
  background: transparent;
  color: var(--teal);
  border: 1.5px solid var(--teal);
  padding: 10px 20px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
}
.btn-outline-dark:hover { background: var(--teal); color: white; }

/* Stats */
.hero-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: rgba(255,255,255,0.15);
  border-radius: var(--radius-md);
  overflow: hidden;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.2);
  animation: statsReveal 0.8s ease-out 0.3s both;
}
.hero-stat {
  padding: 22px 16px;
  background: rgba(255,255,255,0.06);
  text-align: center;
  transition: background 0.3s;
}
.hero-stat:hover { background: rgba(255,255,255,0.15); }
.hero-stat__number {
  font-family: var(--font-display);
  font-size: 38px;
  font-weight: 700;
  color: white;
  line-height: 1;
  text-shadow: 0 1px 8px rgba(0,0,0,0.15);
}
.hero-stat__label {
  font-size: 10px;
  font-weight: 700;
  color: rgba(255,255,255,0.7);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 6px;
}

/* Sections */
.section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.section-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 600;
  color: var(--teal-dark);
}
.section-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--teal);
  text-decoration: none;
}

/* Quick Actions */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.quick-card {
  border-radius: var(--radius-md);
  padding: 0;
  text-align: center;
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
  overflow: hidden;
  background-size: cover;
  background-position: center;
  aspect-ratio: 1.2;
  display: flex;
  align-items: flex-end;
  position: relative;
}
.quick-card:hover { box-shadow: var(--shadow-hover); transform: translateY(-4px); }
.quick-card__content {
  width: 100%;
  padding: 16px;
  text-align: left;
}
.quick-card__title { font-size: 15px; font-weight: 700; color: white; margin-bottom: 2px; }
.quick-card__desc { font-size: 12px; color: rgba(255,255,255,0.75); }

/* Spotlight */
.spotlight {
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-hover);
  background-size: cover;
  background-position: center;
  min-height: 280px;
  display: flex;
  align-items: center;
  position: relative;
  transition: transform 0.3s;
}
.spotlight:hover { transform: scale(1.005); }
.spotlight__body {
  padding: 40px 48px;
  max-width: 550px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.spotlight__label {
  display: inline-block;
  width: fit-content;
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.9);
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 12px;
  backdrop-filter: blur(4px);
}
.spotlight__name { font-family: var(--font-display); font-size: 34px; font-weight: 700; color: white; text-shadow: 0 2px 12px rgba(0,0,0,0.2); }
.spotlight__latin { font-family: var(--font-display); font-style: italic; font-size: 18px; color: rgba(255,255,255,0.75); margin-bottom: 8px; }
.spotlight__desc { font-size: 14px; color: rgba(255,255,255,0.8); line-height: 1.6; margin-bottom: 12px; }
.btn-spotlight {
  display: inline-flex; width: fit-content;
  padding: 10px 22px; border-radius: 6px;
  background: rgba(255,255,255,0.15); color: white;
  border: 1px solid rgba(255,255,255,0.3);
  font-size: 14px; font-weight: 600;
  text-decoration: none; backdrop-filter: blur(4px);
  transition: all 0.2s; margin-top: 8px;
}
.btn-spotlight:hover { background: rgba(255,255,255,0.25); }
.spotlight__challenge { font-size: 13px; margin-bottom: 8px; padding: 8px 14px; border-radius: 8px; }
.spotlight__challenge--active { background: rgba(255,152,0,0.2); color: #FFE0B2; font-weight: 600; }
.spotlight__challenge--found { background: rgba(76,175,80,0.2); color: #C8E6C9; }

/* Fact Banner */
.fact-banner {
  border-radius: var(--radius-lg); overflow: hidden; min-height: 200px;
  background-size: cover; background-position: center right;
  background-color: var(--teal-dark, #1B4D4F); display: flex; align-items: center;
  box-shadow: var(--shadow-hover); transition: transform 0.3s;
}
.fact-banner:hover { transform: scale(1.003); }
.fact-banner__body { padding: 32px 40px; max-width: 520px; }
.fact-banner__body h3 { font-family: var(--font-display); font-size: 26px; color: white; margin-bottom: 2px; }
.fact-banner__latin { font-family: var(--font-display); font-style: italic; color: rgba(255,255,255,0.7); margin-bottom: 12px; }
.fact-banner__body p { font-size: 14px; color: rgba(255,255,255,0.85); line-height: 1.7; margin-bottom: 16px; }

/* Species Grid */
.species-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.species-card {
  background: var(--white);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: fadeIn 0.5s ease-out both;
}
.species-card:nth-child(1) { animation-delay: 0.1s; }
.species-card:nth-child(2) { animation-delay: 0.15s; }
.species-card:nth-child(3) { animation-delay: 0.2s; }
.species-card:nth-child(4) { animation-delay: 0.25s; }
.species-card:hover { box-shadow: var(--shadow-hover); transform: translateY(-4px); }
.species-card__img { height: 160px; background-size: cover; background-position: center; position: relative; background-color: #D6E0E3; }
.species-card__no-photo { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 48px; opacity: 0.3; }
.species-card__status { position: absolute; bottom: 8px; left: 8px; width: 22px; height: 22px; border-radius: 50%; border: 2px solid white; box-shadow: 0 1px 4px rgba(0,0,0,0.2); }
.species-card__status--confirmed { background: var(--teal); }
.species-card__status--potential { background: var(--yellow-potential); }
.species-card__status--reference { background: var(--red-reference); }
.species-card__poison { position: absolute; top: 8px; right: 8px; background: var(--orange-warning); color: white; width: 24px; height: 24px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 13px; }
.species-card__body { padding: 12px 14px; }
.species-card__name-ru { font-weight: 700; font-size: 13px; color: var(--slate-deep); margin-bottom: 2px; }
.species-card__name-lat { font-style: italic; font-size: 11px; color: var(--slate-mid); font-family: var(--font-display); }
.species-card__tags { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.tag { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase; }
.tag--group { background: rgba(42,122,110,0.1); color: var(--teal); }
.tag--redbook { background: rgba(229,57,53,0.1); color: var(--red-reference); }

/* News Feed */
.news-feed { display: flex; flex-direction: column; gap: 8px; }
.news-item {
  display: grid; grid-template-columns: 48px 1fr auto; gap: 14px; align-items: center;
  padding: 14px 18px; background: var(--white, #FAFBFC); border-radius: 12px;
  box-shadow: 0 2px 8px rgba(44,62,74,0.06); text-decoration: none; transition: all 0.2s;
}
.news-item:hover { box-shadow: 0 4px 16px rgba(44,62,74,0.12); transform: translateX(4px); }
.news-item__icon { font-size: 28px; text-align: center; }
.news-item__title { font-size: 14px; font-weight: 700; color: #2C3E4A; }
.news-item__comment { font-size: 13px; color: #4A6572; margin-top: 2px; }
.news-item__date { font-size: 11px; color: #8FA5AB; margin-top: 4px; }
.news-item__badge { padding: 3px 10px; border-radius: 12px; font-size: 10px; font-weight: 700; background: rgba(76,175,80,0.12); color: #2E7D32; white-space: nowrap; }

/* Challenge Banner */
.challenge-banner {
  display: grid; grid-template-columns: 200px 1fr; border-radius: var(--radius-lg, 16px);
  overflow: hidden; box-shadow: 0 4px 24px rgba(44,62,74,0.1); background: #FAFBFC;
}
.challenge-banner__photo { background-size: cover; background-position: center; background-color: #D6E0E3; min-height: 180px; }
.challenge-banner__body { padding: 24px 28px; display: flex; flex-direction: column; justify-content: center; }
.challenge-badge {
  display: inline-block; width: fit-content; padding: 4px 12px; border-radius: 12px;
  background: rgba(255,152,0,0.12); color: #E65100; font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
}
.challenge-banner h3 { font-family: var(--font-display, 'Cormorant Garamond', serif); font-size: 22px; color: #1B4D4F; margin: 0; }
.challenge-latin { font-style: italic; font-size: 14px; color: #8FA5AB; margin-bottom: 10px; }
.challenge-found { font-size: 13px; color: #2E7D32; margin-bottom: 10px; }
.challenge-active { font-size: 13px; color: #E65100; font-weight: 600; margin-bottom: 10px; }
.challenge-link { font-size: 13px; color: #2A7A6E; font-weight: 600; text-decoration: none; }
.challenge-link:hover { text-decoration: underline; }

/* Animations */
@keyframes heroSlideIn { from { opacity: 0; transform: translateX(-30px); } to { opacity: 1; transform: translateX(0); } }
@keyframes heroBgReveal { from { opacity: 0; transform: scale(1.05); } to { opacity: 1; transform: scale(1); } }
@keyframes statsReveal { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* Responsive */
@media (max-width: 768px) {
  .hero-content { grid-template-columns: 1fr; padding: 32px 20px; }
  .hero h1 { font-size: 34px; }
  .hero-stats { grid-template-columns: repeat(2, 1fr); }
  .hero__bg { width: 100%; opacity: 0.3; }
  .hero__gradient-left { width: 100%; }
  .quick-grid { grid-template-columns: repeat(3, 1fr); }
  .spotlight { grid-template-columns: 1fr; }
  .challenge-banner { grid-template-columns: 1fr; }
  .species-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .hero h1 { font-size: 28px; }
  .quick-grid { grid-template-columns: repeat(2, 1fr); }
  .species-grid { grid-template-columns: 1fr; }
}
</style>
