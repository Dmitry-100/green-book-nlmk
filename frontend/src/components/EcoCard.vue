<template>
  <component
    :is="tag"
    class="eco-card"
    :class="{
      'eco-card--interactive': interactive,
      'eco-card--flat': flat,
      'eco-card--tint': tint,
    }"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    tag?: string
    interactive?: boolean
    flat?: boolean
    tint?: boolean
  }>(),
  {
    tag: 'div',
    interactive: false,
    flat: false,
    tint: false,
  }
)
</script>

<style scoped>
.eco-card {
  display: block;
  background: white;
  border: 1px solid rgba(42,122,110,0.12);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(27,77,79,0.06);
  padding: 20px;
  transition: transform 0.25s cubic-bezier(0.4,0,0.2,1),
              box-shadow 0.25s cubic-bezier(0.4,0,0.2,1),
              border-color 0.25s ease;
  text-decoration: none;
  color: inherit;
}
.eco-card--tint { background: #F7FAFA; }
.eco-card--flat { box-shadow: none; }
.eco-card--interactive { cursor: pointer; }
.eco-card--interactive:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(27,77,79,0.14);
  border-color: rgba(42,122,110,0.28);
}
</style>
