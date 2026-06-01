<template>
  <section class="page-hero" :class="{ 'page-hero--compact': compact }">
    <SectionAmbient v-if="ambient" class="page-hero__ambient" :colors="ambientColors" :speed="0.18" />
    <div class="page-hero__inner">
      <router-link v-if="back" :to="back" class="page-hero__back">&larr; {{ backLabel }}</router-link>
      <div class="page-hero__row">
        <div class="page-hero__icon" v-if="icon">{{ icon }}</div>
        <div class="page-hero__text">
          <div class="page-hero__kicker" v-if="kicker">{{ kicker }}</div>
          <h1 class="page-hero__title">{{ title }}</h1>
          <p class="page-hero__subtitle" v-if="subtitle">{{ subtitle }}</p>
        </div>
        <div class="page-hero__aside" v-if="$slots.aside">
          <slot name="aside" />
        </div>
      </div>
      <div class="page-hero__bottom" v-if="$slots.bottom">
        <slot name="bottom" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import SectionAmbient from './SectionAmbient.vue'

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    kicker?: string
    icon?: string
    back?: string
    backLabel?: string
    compact?: boolean
    ambient?: boolean
    ambientColors?: string[]
  }>(),
  {
    backLabel: 'Назад',
    compact: false,
    ambient: false,
    ambientColors: () => ['#2A7A6E', '#1B4D4F', '#3F7C82', '#A8D3D3', '#DDE5B6'],
  }
)
</script>

<style scoped>
.page-hero {
  position: relative;
  background: linear-gradient(135deg, #1B4D4F 0%, #2A7A6E 60%, #3F7C82 100%);
  color: white;
  padding: 36px 32px 32px;
  border-radius: 0 0 16px 16px;
  isolation: isolate;
  overflow: hidden;
}
.page-hero--compact { padding: 24px 32px 20px; }
.page-hero__ambient {
  inset: -40px;
  filter: blur(36px);
  opacity: 0.5;
}
.page-hero__inner {
  position: relative;
  z-index: 1;
  max-width: 1200px;
  margin: 0 auto;
}
.page-hero__back {
  display: inline-block;
  color: rgba(255,255,255,0.78);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  margin-bottom: 12px;
  transition: color 0.2s;
}
.page-hero__back:hover { color: white; }
.page-hero__row {
  display: flex;
  gap: 20px;
  align-items: center;
}
.page-hero__icon {
  font-size: 44px;
  line-height: 1;
  flex-shrink: 0;
}
.page-hero__text { flex: 1; min-width: 0; }
.page-hero__kicker {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.75);
  margin-bottom: 6px;
}
.page-hero__title {
  font-family: var(--font-display);
  font-size: 34px;
  font-weight: 700;
  line-height: 1.1;
  margin: 0;
  text-shadow: 0 2px 16px rgba(0,0,0,0.18);
}
.page-hero--compact .page-hero__title { font-size: 26px; }
.page-hero__subtitle {
  margin: 6px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.78);
  line-height: 1.5;
  max-width: 720px;
}
.page-hero__aside { flex-shrink: 0; }
.page-hero__bottom { margin-top: 18px; }

@media (max-width: 720px) {
  .page-hero { padding: 24px 18px; }
  .page-hero__title { font-size: 24px; }
  .page-hero__row { gap: 14px; }
  .page-hero__icon { font-size: 32px; }
}
</style>
