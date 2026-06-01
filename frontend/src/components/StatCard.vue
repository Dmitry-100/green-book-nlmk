<template>
  <div class="stat-card" :class="{ 'stat-card--glass': glass }">
    <div class="stat-card__icon" v-if="icon">{{ icon }}</div>
    <div class="stat-card__body">
      <div class="stat-card__number">{{ display }}<span v-if="suffix" class="stat-card__suffix">{{ suffix }}</span></div>
      <div class="stat-card__label">{{ label }}</div>
      <div class="stat-card__hint" v-if="hint">{{ hint }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useCountUp } from '../composables/useCountUp'

const props = withDefaults(
  defineProps<{
    value: number
    label: string
    hint?: string
    icon?: string
    suffix?: string
    glass?: boolean
    animate?: boolean
  }>(),
  {
    animate: true,
    glass: false,
  }
)

const valueRef = toRef(props, 'value')
const animated = useCountUp(valueRef)
const display = computed(() => (props.animate ? animated.value : props.value))
</script>

<style scoped>
.stat-card {
  display: flex;
  gap: 14px;
  align-items: center;
  background: white;
  border: 1px solid rgba(42,122,110,0.12);
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: 0 2px 10px rgba(27,77,79,0.06);
  transition: transform 0.25s cubic-bezier(0.4,0,0.2,1), box-shadow 0.25s ease;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(27,77,79,0.12); }
.stat-card--glass {
  background: rgba(255,255,255,0.08);
  border-color: rgba(255,255,255,0.18);
  color: white;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 4px 24px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.18);
}
.stat-card__icon {
  font-size: 28px;
  line-height: 1;
}
.stat-card__body { flex: 1; min-width: 0; }
.stat-card__number {
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  color: var(--teal-dark);
}
.stat-card--glass .stat-card__number { color: white; text-shadow: 0 1px 8px rgba(0,0,0,0.15); }
.stat-card__suffix { font-size: 18px; margin-left: 4px; opacity: 0.7; }
.stat-card__label {
  margin-top: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--slate-mid);
}
.stat-card--glass .stat-card__label { color: rgba(255,255,255,0.78); }
.stat-card__hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--slate-mid);
}
.stat-card--glass .stat-card__hint { color: rgba(255,255,255,0.68); }
</style>
