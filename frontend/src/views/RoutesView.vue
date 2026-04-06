<template>
  <div class="routes-page">
    <h1>Маршруты наблюдений</h1>
    <p class="subtitle">Рекомендованные маршруты для наблюдений за природой на территории площадки</p>

    <div class="routes-grid">
      <div v-for="route in routes" :key="route.id" class="route-card" :class="{ expanded: expandedRoute === route.id }" @click="toggleRoute(route.id)">
        <div class="route-card__header">
          <div class="route-card__icon">{{ route.icon }}</div>
          <div class="route-card__info">
            <h3>{{ route.name }}</h3>
            <div class="route-card__meta">
              <span>{{ route.distance }}</span>
              <span>{{ route.duration }}</span>
              <span :class="'difficulty-' + route.difficulty">{{ difficultyLabel[route.difficulty] }}</span>
            </div>
          </div>
          <div class="route-card__arrow" :class="{ rotated: expandedRoute === route.id }">&#9660;</div>
        </div>
        <div v-if="expandedRoute === route.id" class="route-card__body" @click.stop>
          <p>{{ route.description }}</p>
          <div class="route-card__species">
            <strong>Что можно встретить:</strong>
            <div class="route-tags">
              <span v-for="s in route.species" :key="s" class="route-tag">{{ s }}</span>
            </div>
          </div>
          <div class="route-card__tips">
            <strong>Советы:</strong>
            <ul>
              <li v-for="tip in route.tips" :key="tip">{{ tip }}</li>
            </ul>
          </div>
          <div class="route-card__best-time">
            <strong>Лучшее время:</strong> {{ route.bestTime }}
          </div>
        </div>
      </div>
    </div>

    <div class="safety-reminder">
      <span class="safety-icon">&#9888;</span>
      <div>
        <strong>Техника безопасности</strong>
        <p>Все маршруты проходят по безопасным зонам площадки. Соблюдайте правила ТБ, носите СИЗ, не приближайтесь к диким животным. При обнаружении раненого животного — сообщите экологу.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const expandedRoute = ref<number | null>(null)

function toggleRoute(id: number) {
  expandedRoute.value = expandedRoute.value === id ? null : id
}

const difficultyLabel: Record<string, string> = { easy: 'Лёгкий', medium: 'Средний', hard: 'Сложный' }

const routes = [
  {
    id: 1,
    name: 'Пруд-охладитель',
    icon: '🦢',
    distance: '2.1 км',
    duration: '45 мин',
    difficulty: 'easy',
    description: 'Маршрут вдоль пруда-охладителя — главная точка наблюдения за водоплавающими птицами. Здесь были замечены лебеди-шипуны, серые цапли, утки и кулики. Весной и осенью — лучшее место для наблюдения за пролётом.',
    species: ['Лебедь-шипун', 'Серая цапля', 'Кряква', 'Озёрная лягушка', 'Ондатра'],
    tips: ['Возьмите бинокль — птицы держатся на расстоянии', 'Весной здесь гнездятся утки — не тревожьте', 'Лучшие точки — северный и восточный берега'],
    bestTime: 'Раннее утро (6:00–8:00), апрель–октябрь',
  },
  {
    id: 2,
    name: 'Лесополоса восточная',
    icon: '🌳',
    distance: '1.8 км',
    duration: '40 мин',
    difficulty: 'easy',
    description: 'Защитная лесополоса вдоль восточной границы площадки. Берёзы, тополя, клёны создают укрытия для мелких птиц и млекопитающих. Весной здесь цветут первоцветы, летом — богатая энтомофауна.',
    species: ['Большая синица', 'Обыкновенный соловей', 'Заяц-русак', 'Махаон', 'Прыткая ящерица'],
    tips: ['Идите медленно и тихо — здесь много мелких птиц', 'Осматривайте кору деревьев — можно найти насекомых', 'Весной ищите первоцветы у опушки'],
    bestTime: 'Утро (7:00–10:00), май–сентябрь',
  },
  {
    id: 3,
    name: 'Степной участок',
    icon: '🌾',
    distance: '1.5 км',
    duration: '35 мин',
    difficulty: 'medium',
    description: 'Сохранившийся участок степной растительности на южной окраине площадки. Ковыль перистый, полынь, разнотравье. Место обитания степных насекомых, ящериц и грызунов. Один из самых ценных биотопов площадки.',
    species: ['Ковыль перистый', 'Крапчатый суслик', 'Прыткая ящерица', 'Пчела-плотник', 'Коромысло зелёное'],
    tips: ['Осторожно — здесь могут встретиться гадюки', 'Лучше наблюдать в тёплую солнечную погоду', 'Не рвите ковыль — он в Красной книге'],
    bestTime: 'Полдень (11:00–14:00), июнь–август',
  },
  {
    id: 4,
    name: 'Шлакоотвал (рекультивация)',
    icon: '🔬',
    distance: '2.5 км',
    duration: '60 мин',
    difficulty: 'medium',
    description: 'Рекультивированный участок бывшего шлакоотвала — уникальная возможность наблюдать сукцессию. Пионерные виды растений, рудеральная флора, насекомые-первопоселенцы. Важен для мониторинга восстановления экосистем.',
    species: ['Иван-чай', 'Мать-и-мачеха', 'Бодяк полевой', 'Жук-плавунец', 'Полевой лунь'],
    tips: ['Носите закрытую обувь — неровная поверхность', 'Фиксируйте все виды — здесь каждое наблюдение ценно', 'Сравнивайте с прошлыми данными — видна динамика'],
    bestTime: 'Любое время дня, май–октябрь',
  },
  {
    id: 5,
    name: 'Ночной маршрут',
    icon: '🌙',
    distance: '1.2 км',
    duration: '30 мин',
    difficulty: 'hard',
    description: 'Короткий маршрут для вечерних и ночных наблюдений. Летучие мыши вылетают на кормёжку, совы охотятся, ёжи выходят на промысел. Только с сопровождением и разрешения охраны.',
    species: ['Ночница Брандта', 'Малая вечерница', 'Ёж обыкновенный', 'Обыкновенный уж', 'Серая неясыть'],
    tips: ['Обязательно — фонарь с красным фильтром (не слепит животных)', 'Только в сопровождении сотрудника охраны', 'Тишина — главное правило ночных наблюдений'],
    bestTime: 'Сумерки и ночь (21:00–23:00), июнь–август',
  },
]
</script>

<style scoped>
.routes-page { max-width: 800px; margin: 0 auto; padding: 32px; }
.routes-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 24px; }

.routes-grid { display: flex; flex-direction: column; gap: 12px; }
.route-card {
  background: #FAFBFC; border-radius: 16px; overflow: hidden;
  box-shadow: 0 2px 12px rgba(44,62,74,0.08); cursor: pointer; transition: all 0.3s;
}
.route-card:hover { box-shadow: 0 4px 20px rgba(44,62,74,0.12); }
.route-card.expanded { box-shadow: 0 6px 28px rgba(44,62,74,0.14); }

.route-card__header { display: flex; align-items: center; gap: 16px; padding: 20px 24px; }
.route-card__icon { font-size: 32px; flex-shrink: 0; }
.route-card__info { flex: 1; }
.route-card__info h3 { font-size: 16px; font-weight: 700; color: #2C3E4A; margin-bottom: 4px; }
.route-card__meta { display: flex; gap: 12px; font-size: 12px; color: #8FA5AB; font-weight: 600; }
.route-card__meta .difficulty-easy { color: #4CAF50; }
.route-card__meta .difficulty-medium { color: #FF9800; }
.route-card__meta .difficulty-hard { color: #EF5350; }
.route-card__arrow { font-size: 12px; color: #8FA5AB; transition: transform 0.3s; }
.route-card__arrow.rotated { transform: rotate(180deg); }

.route-card__body { padding: 0 24px 24px; border-top: 1px solid #E8EEF0; padding-top: 16px; cursor: default; }
.route-card__body p { font-size: 14px; color: #4A6572; line-height: 1.7; margin-bottom: 16px; }

.route-card__species { margin-bottom: 14px; }
.route-card__species strong { font-size: 13px; color: #2C3E4A; display: block; margin-bottom: 8px; }
.route-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.route-tag { padding: 4px 10px; background: rgba(42,122,110,0.1); color: #2A7A6E; border-radius: 6px; font-size: 12px; font-weight: 600; }

.route-card__tips { margin-bottom: 14px; }
.route-card__tips strong { font-size: 13px; color: #2C3E4A; display: block; margin-bottom: 6px; }
.route-card__tips ul { margin: 0; padding-left: 18px; }
.route-card__tips li { font-size: 13px; color: #4A6572; line-height: 1.6; }

.route-card__best-time { font-size: 13px; color: #2A7A6E; font-weight: 600; }
.route-card__best-time strong { color: #2C3E4A; }

.safety-reminder {
  display: flex; gap: 14px; align-items: flex-start;
  margin-top: 24px; padding: 20px; border-radius: 12px;
  background: rgba(255,152,0,0.06); border: 1px solid rgba(255,152,0,0.15);
}
.safety-icon { font-size: 24px; flex-shrink: 0; }
.safety-reminder strong { font-size: 14px; color: #E65100; display: block; margin-bottom: 4px; }
.safety-reminder p { font-size: 13px; color: #4A6572; line-height: 1.6; margin: 0; }
</style>
