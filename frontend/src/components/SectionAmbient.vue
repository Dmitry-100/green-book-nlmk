<template>
  <HeroShaderBackground
    class="section-ambient"
    :colors="colors"
    :distortion="distortion"
    :swirl="swirl"
    :speed="speed"
    :offset-x="offsetX"
  />
</template>

<script setup lang="ts">
import HeroShaderBackground from './HeroShaderBackground.vue'

withDefaults(
  defineProps<{
    colors?: string[]
    distortion?: number
    swirl?: number
    speed?: number
    offsetX?: number
  }>(),
  {
    colors: () => ['#2A7A6E', '#3F7C82', '#1B4D4F', '#A8D3D3', '#5C7F86', '#DDE5B6'],
    distortion: 0.7,
    swirl: 0.5,
    speed: 0.22,
    offsetX: 0,
  }
)
</script>

<style scoped>
.section-ambient {
  position: absolute;
  inset: -24px;
  z-index: 0;
  border-radius: 28px;
  filter: blur(28px);
  opacity: 0.55;
  pointer-events: none;
}
</style>
