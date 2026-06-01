<template>
  <div class="marquee" :style="cssVars">
    <div class="marquee__track">
      <div class="marquee__lane">
        <slot />
      </div>
      <div class="marquee__lane" aria-hidden="true">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    durationSec?: number
    reverse?: boolean
    gap?: string
    fade?: boolean
  }>(),
  {
    durationSec: 40,
    reverse: false,
    gap: '14px',
    fade: true,
  }
)

const cssVars = computed(() => ({
  '--marquee-duration': `${props.durationSec}s`,
  '--marquee-direction': props.reverse ? 'reverse' : 'normal',
  '--marquee-gap': props.gap,
  '--marquee-mask': props.fade
    ? 'linear-gradient(to right, transparent 0, black 6%, black 94%, transparent 100%)'
    : 'none',
}))
</script>

<style scoped>
.marquee {
  position: relative;
  overflow: hidden;
  width: 100%;
  -webkit-mask-image: var(--marquee-mask);
  mask-image: var(--marquee-mask);
}
.marquee__track {
  display: flex;
  width: max-content;
  animation: marquee-scroll var(--marquee-duration) linear infinite;
  animation-direction: var(--marquee-direction);
  gap: var(--marquee-gap);
}
.marquee:hover .marquee__track {
  animation-play-state: paused;
}
.marquee__lane {
  display: flex;
  gap: var(--marquee-gap);
  flex-shrink: 0;
}
@keyframes marquee-scroll {
  from { transform: translateX(0); }
  to { transform: translateX(calc(-50% - (var(--marquee-gap) / 2))); }
}
</style>
