<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <div class="empty-state__icon" v-if="icon">{{ icon }}</div>
    <h3 class="empty-state__title" v-if="title">{{ title }}</h3>
    <p class="empty-state__text" v-if="text">{{ text }}</p>
    <slot />
    <router-link
      v-if="ctaTo"
      :to="ctaTo"
      class="empty-state__cta"
    >{{ ctaLabel }}</router-link>
    <button
      v-else-if="ctaLabel"
      type="button"
      class="empty-state__cta"
      @click="$emit('cta')"
    >{{ ctaLabel }}</button>
  </div>
</template>

<script setup lang="ts">
defineEmits(['cta'])

withDefaults(
  defineProps<{
    icon?: string
    title?: string
    text?: string
    ctaLabel?: string
    ctaTo?: string
    compact?: boolean
  }>(),
  {
    icon: '🌿',
    compact: false,
  }
)
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56px 32px;
  background: #F7FAFA;
  border: 1px dashed rgba(42,122,110,0.22);
  border-radius: 14px;
  color: var(--slate-mid);
}
.empty-state--compact { padding: 28px 20px; }
.empty-state__icon {
  font-size: 48px;
  line-height: 1;
  margin-bottom: 14px;
  filter: drop-shadow(0 2px 6px rgba(27,77,79,0.15));
}
.empty-state--compact .empty-state__icon { font-size: 36px; margin-bottom: 10px; }
.empty-state__title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--teal-dark);
  margin: 0 0 6px;
}
.empty-state__text {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  max-width: 380px;
  color: var(--slate-mid);
}
.empty-state__cta {
  margin-top: 18px;
  padding: 10px 22px;
  border: 0;
  border-radius: 8px;
  background: var(--teal);
  color: white;
  font: inherit;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.empty-state__cta:hover { background: var(--teal-dark); transform: translateY(-1px); }
</style>
