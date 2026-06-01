<template>
  <div ref="host" class="shader-host" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ShaderMount,
  ShaderFitOptions,
  defaultPatternSizing,
  getShaderColorFromString,
  meshGradientFragmentShader,
} from '@paper-design/shaders'

const props = withDefaults(
  defineProps<{
    colors?: string[]
    distortion?: number
    swirl?: number
    speed?: number
    offsetX?: number
    offsetY?: number
  }>(),
  {
    colors: () => ['#5C7F86', '#6B8E95', '#8FB8B8', '#3F7C82', '#A8D3D3', '#2A7A6E'],
    distortion: 0.8,
    swirl: 0.6,
    speed: 0.42,
    offsetX: 0.08,
    offsetY: 0,
  }
)

const host = ref<HTMLDivElement | null>(null)
let mount: ShaderMount | null = null

function colorVecs() {
  return props.colors.map((c) => getShaderColorFromString(c))
}

onMounted(() => {
  if (!host.value) return
  const cs = colorVecs()
  mount = new ShaderMount(
    host.value,
    meshGradientFragmentShader,
    {
      u_colors: cs,
      u_colorsCount: cs.length,
      u_distortion: props.distortion,
      u_swirl: props.swirl,
      u_grainMixer: 0,
      u_grainOverlay: 0,
      u_fit: ShaderFitOptions.cover,
      u_scale: defaultPatternSizing.scale,
      u_rotation: defaultPatternSizing.rotation,
      u_originX: defaultPatternSizing.originX,
      u_originY: defaultPatternSizing.originY,
      u_offsetX: props.offsetX,
      u_offsetY: props.offsetY,
      u_worldWidth: defaultPatternSizing.worldWidth,
      u_worldHeight: defaultPatternSizing.worldHeight,
    },
    undefined,
    props.speed
  )
})

onBeforeUnmount(() => {
  mount?.dispose()
  mount = null
})

watch(
  () => props.speed,
  (v) => mount?.setSpeed(v)
)

watch(
  () => [props.colors, props.distortion, props.swirl, props.offsetX, props.offsetY],
  () => {
    if (!mount) return
    const cs = colorVecs()
    mount.setUniforms({
      u_colors: cs,
      u_colorsCount: cs.length,
      u_distortion: props.distortion,
      u_swirl: props.swirl,
      u_offsetX: props.offsetX,
      u_offsetY: props.offsetY,
    })
  },
  { deep: true }
)
</script>

<style scoped>
.shader-host {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.shader-host :deep(canvas) {
  display: block;
  width: 100% !important;
  height: 100% !important;
}
</style>
