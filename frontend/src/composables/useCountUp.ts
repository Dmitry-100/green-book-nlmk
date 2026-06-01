import { ref, watch, type Ref } from 'vue'

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)

export function useCountUp(source: Ref<number>, durationMs = 900): Ref<number> {
  const display = ref(0)
  let raf = 0
  let startTs = 0
  let from = 0
  let to = 0

  function step(ts: number) {
    if (!startTs) startTs = ts
    const t = Math.min(1, (ts - startTs) / durationMs)
    display.value = Math.round(from + (to - from) * easeOutCubic(t))
    if (t < 1) raf = requestAnimationFrame(step)
  }

  watch(
    source,
    (next) => {
      cancelAnimationFrame(raf)
      from = display.value
      to = next
      startTs = 0
      raf = requestAnimationFrame(step)
    },
    { immediate: true }
  )

  return display
}
