<template>
  <div class="obs-detail-page" v-if="obs">
    <div class="obs-detail-card">
      <div class="obs-detail-header">
        <span class="obs-group-icon">{{ groupIcons[obs.group] || '🌱' }}</span>
        <div>
          <h1>{{ groupLabels[obs.group] || obs.group }}</h1>
          <div class="obs-meta">
            <span class="obs-status" :class="'obs-status--' + obs.status">{{ statusLabels[obs.status] || obs.status }}</span>
            <span>{{ formatDate(obs.observed_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Photo -->
      <div v-if="photoUrl" class="obs-photo" :style="{ backgroundImage: `url(${photoUrl})` }"></div>

      <p v-if="obs.comment" class="obs-comment">{{ obs.comment }}</p>

      <div class="obs-detail-info">
        <div class="info-item" v-if="speciesName">
          <span class="info-label">Вид</span>
          <span class="info-value">{{ speciesName }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Группа</span>
          <span class="info-value">{{ groupLabels[obs.group] || obs.group }}</span>
        </div>
        <div class="info-item" v-if="obs.is_incident">
          <span class="info-label">Инцидент</span>
          <span class="info-value" style="color: #E53935;">{{ obs.incident_type }} — {{ obs.incident_severity }}</span>
        </div>
      </div>

      <!-- Map -->
      <div v-if="obs.lat && obs.lon" class="obs-map-section">
        <div class="obs-map-label">Место наблюдения: {{ obs.lat.toFixed(4) }}, {{ obs.lon.toFixed(4) }}</div>
        <div id="obs-detail-map" ref="mapEl" class="obs-map"></div>
      </div>

      <!-- Likes -->
      <div class="likes-section">
        <button class="like-btn" :class="{ liked: myLiked }" @click="toggleLike">
          <svg width="18" height="18" viewBox="0 0 24 24" :fill="myLiked ? '#E53935' : 'none'" stroke="currentColor" stroke-width="2">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
          </svg>
          {{ likeCount }}
        </button>
        <span class="like-hint">{{ likeCount === 0 ? 'Будьте первым!' : '' }}</span>
      </div>

      <!-- Comments -->
      <div class="comments-section">
        <h3>Комментарии ({{ comments.length }})</h3>
        <div class="comments-list">
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <div class="comment-avatar">{{ c.user_name?.charAt(0) || '?' }}</div>
            <div class="comment-body">
              <div class="comment-header">
                <strong>{{ c.user_name }}</strong>
                <span class="comment-date">{{ formatDate(c.created_at) }}</span>
              </div>
              <p>{{ c.text }}</p>
            </div>
          </div>
          <p v-if="comments.length === 0" class="empty-comments">Пока нет комментариев</p>
        </div>
        <div class="comment-form">
          <input v-model="newComment" placeholder="Написать комментарий..." @keyup.enter="submitComment" />
          <button @click="submitComment" :disabled="!newComment.trim()">Отправить</button>
        </div>
      </div>
    </div>

    <div class="obs-detail-actions">
      <button @click="$router.back()" class="btn-back">&larr; Назад</button>
    </div>
  </div>
  <div v-else class="obs-loading">Загрузка...</div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const obs = ref<any>(null)
const speciesName = ref('')
const mapEl = ref<HTMLElement>()
const comments = ref<any[]>([])
const newComment = ref('')
const likeCount = ref(0)
const myLiked = ref(false)
const photoUrl = ref('')

const groupIcons: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const groupLabels: Record<string, string> = { plants: 'Растение', fungi: 'Гриб', insects: 'Насекомое', herpetofauna: 'Герпетофауна', birds: 'Птица', mammals: 'Млекопитающее' }
const statusLabels: Record<string, string> = { on_review: 'На проверке', needs_data: 'Нужны данные', confirmed: 'Подтверждено', rejected: 'Отклонено' }

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru') + ' ' + d.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
}

async function fetchComments() {
  try {
    const { data } = await api.get(`/observations/${route.params.id}/comments`)
    comments.value = data.comments || []
  } catch {}
}

async function fetchLikes() {
  try {
    const { data } = await api.get(`/observations/${route.params.id}/likes/me`)
    likeCount.value = data.count
    myLiked.value = data.liked
  } catch {
    // Not authenticated — just get count
    try {
      const { data } = await api.get(`/observations/${route.params.id}/likes`)
      likeCount.value = data.count
    } catch {}
  }
}

async function toggleLike() {
  try {
    const { data } = await api.post(`/observations/${route.params.id}/likes`)
    likeCount.value = data.count
    myLiked.value = data.liked
  } catch {}
}

async function submitComment() {
  if (!newComment.value.trim()) return
  try {
    await api.post(`/observations/${route.params.id}/comments`, { text: newComment.value.trim() })
    newComment.value = ''
    fetchComments()
  } catch {}
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/observations/${route.params.id}`)
    obs.value = data
    // Load species name
    if (data.species_id) {
      try {
        const sp = await api.get(`/species/${data.species_id}`)
        speciesName.value = sp.data.name_ru
      } catch {}
    }
    // Photo from media
    if (data.media?.length) {
      photoUrl.value = `/api/media/${data.media[0].s3_key}`
    }
  } catch {}
  fetchComments()
  fetchLikes()

  // Init map
  await nextTick()
  if (obs.value?.lat && obs.value?.lon && mapEl.value) {
    try {
      const configRes = await api.get('/config/ymaps')
      if (!configRes.data.apiKey) return
      const loadScript = () => new Promise<void>((resolve) => {
        if ((window as any).ymaps) { (window as any).ymaps.ready(() => resolve()); return }
        const s = document.createElement('script')
        s.src = `https://api-maps.yandex.ru/2.1/?apikey=${configRes.data.apiKey}&lang=ru_RU`
        s.async = true
        s.onload = () => (window as any).ymaps.ready(() => resolve())
        document.head.appendChild(s)
      })
      await loadScript()
      const ymaps = (window as any).ymaps
      const map = new ymaps.Map(mapEl.value, { center: [obs.value.lat, obs.value.lon], zoom: 15, controls: ['zoomControl'] })
      map.geoObjects.add(new ymaps.Placemark([obs.value.lat, obs.value.lon], {}, { preset: 'islands#greenDotIcon' }))
    } catch {}
  }
})
</script>

<style scoped>
.obs-detail-page { max-width: 700px; margin: 0 auto; padding: 32px; }
.obs-detail-card { background: #FAFBFC; border-radius: 20px; padding: 32px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.obs-photo { width: 100%; height: 280px; background-size: cover; background-position: center; border-radius: 12px; margin-bottom: 20px; background-color: #D6E0E3; }

.obs-detail-header { display: flex; gap: 16px; align-items: center; margin-bottom: 20px; }
.obs-group-icon { font-size: 40px; }
.obs-detail-header h1 { font-family: 'Cormorant Garamond', serif; font-size: 26px; color: #1B4D4F; margin: 0; }
.obs-meta { display: flex; gap: 12px; align-items: center; font-size: 13px; color: #8FA5AB; margin-top: 4px; }
.obs-status { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }
.obs-status--on_review { background: rgba(255,193,7,0.15); color: #F57F17; }
.obs-status--confirmed { background: rgba(76,175,80,0.12); color: #2E7D32; }
.obs-status--rejected { background: rgba(229,57,53,0.1); color: #E53935; }
.obs-status--needs_data { background: rgba(33,150,243,0.12); color: #1565C0; }

.obs-comment { font-size: 15px; color: #4A6572; line-height: 1.7; margin-bottom: 20px; }

.obs-detail-info { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; margin-bottom: 24px; }
.info-item { background: #E8EEF0; padding: 12px 14px; border-radius: 8px; }
.info-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #8FA5AB; display: block; margin-bottom: 2px; }
.info-value { font-size: 14px; font-weight: 600; color: #2C3E4A; }

.obs-map-section { margin-bottom: 20px; }
.obs-map-label { font-size: 12px; color: #8FA5AB; margin-bottom: 8px; font-weight: 600; }
.obs-map { width: 100%; height: 220px; border-radius: 12px; overflow: hidden; background: #D6E0E3; }

.likes-section { display: flex; align-items: center; gap: 10px; padding-bottom: 20px; border-bottom: 1px solid #E8EEF0; margin-bottom: 20px; }
.like-btn {
  display: flex; align-items: center; gap: 6px; padding: 8px 16px;
  border: 1.5px solid #E8EEF0; border-radius: 20px; background: white;
  font-size: 14px; font-weight: 600; color: #4A6572; cursor: pointer; transition: all 0.2s;
}
.like-btn:hover { border-color: #E53935; color: #E53935; }
.like-btn.liked { border-color: #E53935; color: #E53935; background: rgba(229,57,53,0.05); }
.like-hint { font-size: 12px; color: #8FA5AB; }

.comments-section h3 { font-size: 16px; color: #2C3E4A; margin-bottom: 16px; }
.comments-list { margin-bottom: 16px; }
.comment-item { display: flex; gap: 12px; margin-bottom: 14px; }
.comment-avatar {
  width: 32px; height: 32px; border-radius: 50%; background: #2A7A6E; color: white;
  font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.comment-body { flex: 1; }
.comment-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.comment-header strong { font-size: 13px; color: #2C3E4A; }
.comment-date { font-size: 11px; color: #8FA5AB; }
.comment-body p { font-size: 14px; color: #4A6572; line-height: 1.5; margin: 0; }
.empty-comments { font-size: 13px; color: #8FA5AB; }

.comment-form { display: flex; gap: 8px; }
.comment-form input {
  flex: 1; padding: 10px 14px; border: 1.5px solid #E8EEF0; border-radius: 8px;
  font-size: 14px; outline: none; transition: border-color 0.2s;
}
.comment-form input:focus { border-color: #2A7A6E; }
.comment-form button {
  padding: 10px 20px; background: #2A7A6E; color: white; border: none;
  border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;
}
.comment-form button:disabled { opacity: 0.5; cursor: default; }
.comment-form button:hover:not(:disabled) { background: #1B4D4F; }

.obs-detail-actions { margin-top: 20px; }
.btn-back {
  padding: 8px 16px; background: transparent; border: 1.5px solid #2A7A6E;
  color: #2A7A6E; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;
}
.btn-back:hover { background: #2A7A6E; color: white; }

.obs-loading { text-align: center; padding: 60px; color: #8FA5AB; }
</style>
