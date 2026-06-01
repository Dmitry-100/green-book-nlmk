<template>
  <button
    type="button"
    class="filter-chip"
    :class="{ 'filter-chip--active': active, 'filter-chip--sm': small }"
    @click="$emit('toggle')"
  >
    <span class="filter-chip__icon" v-if="icon">{{ icon }}</span>
    <span class="filter-chip__label"><slot>{{ label }}</slot></span>
    <span class="filter-chip__count" v-if="count != null">{{ count }}</span>
  </button>
</template>

<script setup lang="ts">
defineEmits(['toggle'])

withDefaults(
  defineProps<{
    label?: string
    icon?: string
    active?: boolean
    small?: boolean
    count?: number | null
  }>(),
  {
    active: false,
    small: false,
    count: null,
  }
)
</script>

<style scoped>
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: white;
  border: 1.5px solid rgba(42,122,110,0.15);
  color: var(--slate-deep);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.filter-chip--sm { padding: 6px 12px; font-size: 12px; }
.filter-chip:hover { border-color: var(--teal); color: var(--teal-dark); }
.filter-chip--active {
  background: var(--teal);
  border-color: var(--teal);
  color: white;
  box-shadow: 0 2px 8px rgba(42,122,110,0.28);
}
.filter-chip--active:hover { background: var(--teal-dark); border-color: var(--teal-dark); color: white; }
.filter-chip__icon { font-size: 14px; line-height: 1; }
.filter-chip__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(42,122,110,0.12);
  font-size: 11px;
  font-weight: 700;
}
.filter-chip--active .filter-chip__count { background: rgba(255,255,255,0.25); color: white; }
</style>
