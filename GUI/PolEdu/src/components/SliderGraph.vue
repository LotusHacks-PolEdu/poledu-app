<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import type { SliderParam } from '../types/lessons'

const props = defineProps<{
  expressionTemplate: string
  paramA: SliderParam
  paramB: SliderParam
  xMin?: number
  xMax?: number
  yMin?: number
  yMax?: number
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const valueA = ref(props.paramA.default)
const valueB = ref(props.paramB.default)

function buildFn(a: number, b: number): ((x: number) => number) | null {
  try {
    const prepared = props.expressionTemplate
      .replace(/\^/g, '**')
      .replace(/(\d)(x)/g, '$1*x')
      .replace(/(x)(\d)/g, 'x*$2')
      .replace(/\)(x)/g, ')*x')
      .replace(/(x)\(/g, 'x*(')
      .replace(/\bsin\b/g, 'Math.sin')
      .replace(/\bcos\b/g, 'Math.cos')
      .replace(/\btan\b/g, 'Math.tan')
      .replace(/\bsqrt\b/g, 'Math.sqrt')
      .replace(/\babs\b/g, 'Math.abs')
      .replace(/\blog\b/g, 'Math.log')
      .replace(/\bpi\b/gi, 'Math.PI')

    // eslint-disable-next-line no-new-func
    const fn = new Function('x', 'A', 'B', `"use strict"; return (${prepared});`) as (x: number, a: number, b: number) => number
    fn(0, a, b)
    return (x: number) => fn(x, a, b)
  } catch {
    return null
  }
}

function draw(): void {
  const canvas = canvasRef.value
  if (!canvas || !canvas.parentElement) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = canvas.parentElement.clientWidth
  canvas.height = 200

  const w = canvas.width
  const h = canvas.height
  const xMin = props.xMin ?? -6.3
  const xMax = props.xMax ?? 6.3
  const yMin = props.yMin ?? -4
  const yMax = props.yMax ?? 4
  const xRange = xMax - xMin
  const yRange = yMax - yMin

  const toPixelX = (x: number) => ((x - xMin) / xRange) * w
  const toPixelY = (y: number) => h - ((y - yMin) / yRange) * h

  // Background
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, w, h)

  // Grid
  ctx.strokeStyle = '#e5e5e5'
  ctx.lineWidth = 1
  for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x++) {
    const px = toPixelX(x)
    ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, h); ctx.stroke()
  }
  for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y++) {
    const py = toPixelY(y)
    ctx.beginPath(); ctx.moveTo(0, py); ctx.lineTo(w, py); ctx.stroke()
  }

  // Axes
  ctx.strokeStyle = '#aaa'
  ctx.lineWidth = 1.5
  if (yMin <= 0 && yMax >= 0) {
    const py = toPixelY(0)
    ctx.beginPath(); ctx.moveTo(0, py); ctx.lineTo(w, py); ctx.stroke()
  }
  if (xMin <= 0 && xMax >= 0) {
    const px = toPixelX(0)
    ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, h); ctx.stroke()
  }

  // Plot
  const fn = buildFn(valueA.value, valueB.value)
  if (!fn) return

  ctx.strokeStyle = '#00BAFF'
  ctx.lineWidth = 2.5
  ctx.beginPath()
  let penDown = false
  const steps = w * 2
  for (let i = 0; i <= steps; i++) {
    const x = xMin + (i / steps) * xRange
    let y: number
    try { y = fn(x) } catch { penDown = false; continue }
    if (!isFinite(y)) { penDown = false; continue }
    const px = toPixelX(x)
    const py = toPixelY(y)
    if (!penDown) { ctx.moveTo(px, py); penDown = true }
    else ctx.lineTo(px, py)
  }
  ctx.stroke()

  // Label
  ctx.fillStyle = '#00BAFF'
  ctx.font = 'bold 12px monospace'
  ctx.textAlign = 'left'
  const label = props.expressionTemplate
    .replace(/\bA\b/g, valueA.value.toFixed(1))
    .replace(/\bB\b/g, valueB.value.toFixed(1))
  ctx.fillText(`y = ${label}`, 8, 16)
}

watch([valueA, valueB], draw)

onMounted(() => {
  draw()
  window.addEventListener('resize', draw)
})
</script>

<template>
  <div class="slider-graph">
    <canvas ref="canvasRef" class="slider-graph__canvas" />

    <div class="slider-graph__controls">
      <label class="slider-graph__slider">
        <span class="slider-graph__slider-label">
          {{ paramA.label }}
          <strong>{{ valueA.toFixed(1) }}</strong>
        </span>
        <input
          v-model.number="valueA"
          type="range"
          :min="paramA.min"
          :max="paramA.max"
          :step="paramA.step"
        />
      </label>

      <label class="slider-graph__slider">
        <span class="slider-graph__slider-label">
          {{ paramB.label }}
          <strong>{{ valueB.toFixed(1) }}</strong>
        </span>
        <input
          v-model.number="valueB"
          type="range"
          :min="paramB.min"
          :max="paramB.max"
          :step="paramB.step"
        />
      </label>
    </div>
  </div>
</template>

<style scoped>
.slider-graph {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
}

.slider-graph__canvas {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
}

.slider-graph__controls {
  display: grid;
  gap: 0.6rem;
}

.slider-graph__slider {
  display: grid;
  gap: 0.3rem;
}

.slider-graph__slider-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.82rem;
  color: var(--color-text-muted);
  font-family: var(--font-body);
}

.slider-graph__slider-label strong {
  color: var(--color-primary);
  font-weight: 700;
  min-width: 2rem;
  text-align: right;
}

input[type='range'] {
  width: 100%;
  accent-color: var(--color-primary);
  cursor: pointer;
}
</style>
