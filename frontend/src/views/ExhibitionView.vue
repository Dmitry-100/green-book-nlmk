<template>
  <div class="exhibition-page">
    <section
      class="exhibition-hero"
      :style="{ backgroundImage: `linear-gradient(to right, rgba(27,77,79,0.92), rgba(27,77,79,0.56), rgba(27,77,79,0.18)), url(${heroImage})` }"
    >
      <div class="exhibition-hero__content">
        <div class="exhibition-hero__eyebrow">Фотовыставка 2025</div>
        <h1>Птицы прудов-отстойников НЛМК</h1>
        <p>
          Работы сотрудников и партнеров о водоемах, тростниковых зарослях, сезонных миграциях и редких встречах на промышленной площадке.
        </p>
      </div>
    </section>

    <section class="exhibition-section">
      <div class="exhibition-section__header">
        <div>
          <h2>Фотоистории</h2>
          <p>22 фотографии из подборки «Фото птицы НЛМК 2025» с авторскими подписями из выставочного файла.</p>
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
          <img :src="item.image" :alt="item.alt" loading="lazy" decoding="async" />
          <div class="exhibition-card__body">
            <div class="exhibition-card__meta">
              <span>Фото №{{ item.photoNumber }}</span>
              <span>{{ item.author }}</span>
            </div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.description }}</p>
            <div class="exhibition-card__credit">{{ item.credit }}</div>
          </div>
        </article>
      </div>
    </section>

    <section class="exhibition-note">
      <div>
        <h2>Пруды как точка притяжения</h2>
        <p>
          Незамерзающие участки, отмели и прибрежные тростники создают условия для зимовок, гнездования и остановок во время миграций.
        </p>
      </div>
      <router-link to="/species" class="exhibition-note__link">К справочнику видов</router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
import { exhibitionHeroImage, exhibitionPhotos } from '../data/exhibitionBirds2025'

const heroImage = exhibitionHeroImage
const exhibitionItems = exhibitionPhotos
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

.exhibition-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.exhibition-card__meta span {
  display: inline-flex;
  width: fit-content;
  border-radius: 6px;
  background: rgba(42,122,110,0.08);
  padding: 4px 8px;
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

.exhibition-card__credit {
  color: var(--slate-light);
  font-size: 12px;
  font-weight: 700;
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
