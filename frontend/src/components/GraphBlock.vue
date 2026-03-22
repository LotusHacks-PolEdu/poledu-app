<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

export interface GraphBlockProps {
  /** Instruction / question text shown above the graph */
  question?: string
  /**
   * A JS math expression using variable `x`, e.g. "2*x+4", "Math.sin(x)", "x**2 - 3*x + 1".
   * Evaluated for each x value to produce y.
   */
  expression: string
  /** Minimum x value (default -10) */
  xMin?: number
  /** Maximum x value (default 10) */
  xMax?: number
  /** Minimum y value (default -10) */
  yMin?: number
  /** Maximum y value (default 10) */
  yMax?: number
  /** Canvas width in pixels (default 500) */
  width?: number
  /** Canvas height in pixels (default 400) */
  height?: number
  /** Line colour (default '#2563eb') */
  color?: string
}

const props = withDefaults(defineProps<GraphBlockProps>(), {
  xMin: -10,
  xMax: 10,
  yMin: -10,
  yMax: 10,
  width: 500,
  height: 400,
  color: '#2563eb',
})

const canvas = ref<HTMLCanvasElement | null>(null)
const error = ref<string | null>(null)

/**
 * Build a function from the expression string.
 * We inject `x` as the parameter and also expose Math helpers as bare names
 * so users can write `sin(x)` instead of `Math.sin(x)`.
 */
function buildFn(expr: string): ((x: number) => number) | null {
  try {
    // Provide common math helpers as local variables
    const body = `
      "use strict";
      const { sin, cos, tan, abs, sqrt, log, log2, log10, exp, floor, ceil, round, PI, E, pow, min, max } = Math;
      return (${expr});
    `
    // eslint-disable-next-line no-new-func
    const factory = new Function('x', body)
    // Quick sanity-check
    const test = factory(0)
    if (typeof test !== 'number') throw new Error('Expression did not return a number')
    return factory as (x: number) => number
  } catch (e: any) {
    error.value = `Bad expression: ${e.message}`
    return null
  }
}

function draw() {
  const cvs = canvas.value
  if (!cvs) return
  const ctx = cvs.getContext('2d')
  if (!ctx) return

  const { width: w, height: h, xMin, xMax, yMin, yMax, color } = props

  cvs.width = w
  cvs.height = h

  const xRange = xMax - xMin
  const yRange = yMax - yMin

  // Map math coords → pixel coords
  const toPixelX = (x: number) => ((x - xMin) / xRange) * w
  const toPixelY = (y: number) => h - ((y - yMin) / yRange) * h

  // --- clear ---
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, w, h)

  // --- grid lines ---
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

  // --- axes ---
  ctx.strokeStyle = '#888'
  ctx.lineWidth = 1.5
  // x-axis
  if (yMin <= 0 && yMax >= 0) {
    const py = toPixelY(0)
    ctx.beginPath(); ctx.moveTo(0, py); ctx.lineTo(w, py); ctx.stroke()
  }
  // y-axis
  if (xMin <= 0 && xMax >= 0) {
    const px = toPixelX(0)
    ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, h); ctx.stroke()
  }

  // --- axis labels ---
  ctx.fillStyle = '#666'
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'center'
  for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x++) {
    if (x === 0) continue
    const px = toPixelX(x)
    const py = toPixelY(0)
    ctx.fillText(String(x), px, Math.min(py + 14, h - 2))
  }
  ctx.textAlign = 'right'
  for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y++) {
    if (y === 0) continue
    const px = toPixelX(0)
    const py = toPixelY(y)
    ctx.fillText(String(y), Math.max(px - 4, 20), py + 4)
  }

  // --- plot function ---
  const fn = buildFn(props.expression)
  if (!fn) return
  error.value = null

  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.beginPath()
  let penDown = false
  const steps = w * 2 // 2 samples per pixel for smoothness
  for (let i = 0; i <= steps; i++) {
    const x = xMin + (i / steps) * xRange
    let y: number
    try {
      y = fn(x)
    } catch {
      penDown = false
      continue
    }
    if (!isFinite(y)) {
      penDown = false
      continue
    }
    const px = toPixelX(x)
    const py = toPixelY(y)
    if (!penDown) {
      ctx.moveTo(px, py)
      penDown = true
    } else {
      ctx.lineTo(px, py)
    }
  }
  ctx.stroke()

  // --- expression label ---
  ctx.fillStyle = color
  ctx.font = 'bold 13px monospace'
  ctx.textAlign = 'left'
  ctx.fillText(`y = ${props.expression}`, 8, 18)
}

onMounted(draw)
watch(() => [props.expression, props.xMin, props.xMax, props.yMin, props.yMax, props.width, props.height, props.color], draw)
</script>

<template>
  <div class="graph-block">
    <p v-if="question"><strong>{{ question }}</strong></p>
    <canvas ref="canvas"></canvas>
    <p v-if="error" class="graph-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.graph-block {
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 0.5rem;
  overflow: hidden;
  min-width: 0;
}
canvas {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
}
.graph-error {
  color: red;
  margin-top: 4px;
}
</style>
