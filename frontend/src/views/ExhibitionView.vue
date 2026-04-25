<template>
  <div class="exhibition-page">
    <section
      class="exhibition-hero"
      :style="{ backgroundImage: `linear-gradient(to right, rgba(27,77,79,0.92), rgba(27,77,79,0.56), rgba(27,77,79,0.18)), url(${heroImage})` }"
    >
      <div class="exhibition-hero__content">
        <div class="exhibition-hero__eyebrow">Онлайн-экспозиция</div>
        <h1>Живая природа промышленной площадки</h1>
        <p>
          Черновая подборка для будущей выставки. Когда появятся архивные материалы и подписи, этот раздел станет витриной лучших наблюдений сотрудников.
        </p>
      </div>
    </section>

    <section class="exhibition-section">
      <div class="exhibition-section__header">
        <div>
          <h2>Первые сюжеты</h2>
          <p>Временные фотографии из открытых интернет-источников помогают увидеть будущий формат раздела.</p>
        </div>
        <router-link to="/observe" class="exhibition-section__action">Добавить наблюдение</router-link>
      </div>

      <div class="exhibition-grid">
        <article
          v-for="item in exhibitionItems"
          :key="item.id"
          class="exhibition-card"
          :class="{ 'exhibition-card--wide': item.wide }"
        >
          <img :src="item.image" :alt="item.alt" loading="lazy" />
          <div class="exhibition-card__body">
            <div class="exhibition-card__kicker">{{ item.kicker }}</div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.description }}</p>
            <a :href="item.sourceUrl" target="_blank" rel="noreferrer" class="exhibition-card__source">
              {{ item.sourceLabel }}
            </a>
          </div>
        </article>
      </div>
    </section>

    <section class="exhibition-note">
      <div>
        <h2>Следующий шаг</h2>
        <p>
          После получения материалов выставки сюда можно перенести реальные фотографии, подписи, авторов, даты наблюдений и ссылки на публикации.
        </p>
      </div>
      <router-link to="/species" class="exhibition-note__link">К справочнику видов</router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
const heroImage = 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1800&q=85'

const exhibitionItems = [
  {
    id: 1,
    wide: true,
    kicker: 'Водные биотопы',
    title: 'Утренний свет у воды',
    description: 'Спокойные водоемы становятся точками наблюдений за птицами, земноводными и сезонными миграциями.',
    image: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1400&q=85',
    alt: 'Озеро и горный пейзаж в утреннем свете',
    sourceLabel: 'Unsplash',
    sourceUrl: 'https://unsplash.com/',
  },
  {
    id: 2,
    kicker: 'Лесополоса',
    title: 'Тихие укрытия',
    description: 'Древесные и кустарниковые зоны дают место для гнездования, кормления и коротких наблюдений по маршруту.',
    image: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1000&q=85',
    alt: 'Лесная тропа среди высоких деревьев',
    sourceLabel: 'Unsplash',
    sourceUrl: 'https://unsplash.com/',
  },
  {
    id: 3,
    kicker: 'Насекомые',
    title: 'Малые открытия',
    description: 'Небольшие детали чаще всего становятся первым поводом достать камеру и открыть карточку вида.',
    image: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=85',
    alt: 'Солнечный природный пейзаж у берега',
    sourceLabel: 'Unsplash',
    sourceUrl: 'https://unsplash.com/',
  },
  {
    id: 4,
    kicker: 'Сезонные находки',
    title: 'После дождя',
    description: 'Грибы, мхи и влажные участки маршрутов хорошо показывают, как быстро меняется природная среда.',
    image: 'https://images.unsplash.com/photo-1473773508845-188df298d2d1?auto=format&fit=crop&w=1000&q=85',
    alt: 'Зеленый лесной мох крупным планом',
    sourceLabel: 'Unsplash',
    sourceUrl: 'https://unsplash.com/',
  },
  {
    id: 5,
    wide: true,
    kicker: 'Панорама площадки',
    title: 'Природа в рабочем ландшафте',
    description: 'Будущая выставка поможет собрать лучшие фотографии сотрудников и показать биоразнообразие как часть корпоративной культуры.',
    image: 'https://images.unsplash.com/photo-1518173946687-a4c8892bbd9f?auto=format&fit=crop&w=1400&q=85',
    alt: 'Лесной массив с высоты',
    sourceLabel: 'Unsplash',
    sourceUrl: 'https://unsplash.com/',
  },
]
</script>

<style scoped>
.exhibition-page {
  color: var(--slate-deep);
}

.exhibition-hero {
  min-height: 360px;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
}

.exhibition-hero__content {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 56px 32px;
}

.exhibition-hero__eyebrow {
  color: rgba(255,255,255,0.74);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.exhibition-hero h1 {
  max-width: 620px;
  font-family: var(--font-display);
  font-size: 44px;
  line-height: 1.08;
  color: white;
  margin-bottom: 18px;
}

.exhibition-hero p {
  max-width: 560px;
  color: rgba(255,255,255,0.82);
  font-size: 15px;
  line-height: 1.7;
}

.exhibition-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 36px 32px 24px;
}

.exhibition-section__header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  margin-bottom: 20px;
}

.exhibition-section__header h2,
.exhibition-note h2 {
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1.1;
  color: var(--teal-dark);
  margin-bottom: 6px;
}

.exhibition-section__header p,
.exhibition-note p {
  color: var(--slate-mid);
  font-size: 14px;
  line-height: 1.7;
  max-width: 620px;
}

.exhibition-section__action,
.exhibition-note__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 10px 18px;
  border-radius: 6px;
  background: var(--teal);
  color: white;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  transition: background 0.2s, transform 0.2s;
}

.exhibition-section__action:hover,
.exhibition-note__link:hover {
  background: var(--teal-light);
  transform: translateY(-1px);
}

.exhibition-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.exhibition-card {
  min-width: 0;
  overflow: hidden;
  border-radius: 8px;
  background: var(--white);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s, transform 0.2s;
}

.exhibition-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-3px);
}

.exhibition-card--wide {
  grid-column: span 2;
}

.exhibition-card img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  display: block;
  background: var(--slate-wash);
}

.exhibition-card__body {
  padding: 18px 18px 20px;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 7px;
}

.exhibition-card__kicker {
  color: var(--teal);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}

.exhibition-card h3 {
  color: var(--slate-deep);
  font-size: 17px;
  line-height: 1.25;
}

.exhibition-card p {
  color: var(--slate-mid);
  font-size: 13px;
  line-height: 1.65;
  flex: 1;
}

.exhibition-card__source {
  color: var(--slate-light);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  width: fit-content;
}

.exhibition-card__source:hover {
  color: var(--teal);
}

.exhibition-note {
  max-width: 1136px;
  margin: 12px auto 40px;
  padding: 24px;
  border-radius: 8px;
  background: rgba(42,122,110,0.08);
  border: 1px solid rgba(42,122,110,0.14);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

@media (max-width: 900px) {
  .exhibition-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .exhibition-card--wide {
    grid-column: span 1;
  }
}

@media (max-width: 640px) {
  .exhibition-hero {
    min-height: 320px;
  }

  .exhibition-hero__content {
    padding: 40px 20px;
  }

  .exhibition-hero h1 {
    font-size: 32px;
  }

  .exhibition-section {
    padding: 28px 20px 20px;
  }

  .exhibition-section__header,
  .exhibition-note {
    align-items: stretch;
    flex-direction: column;
  }

  .exhibition-grid {
    grid-template-columns: 1fr;
  }

  .exhibition-section__action,
  .exhibition-note__link {
    width: 100%;
  }
}
</style>
