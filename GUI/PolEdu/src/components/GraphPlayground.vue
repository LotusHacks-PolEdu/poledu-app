<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    visible: boolean
    title?: string
    hint?: string
    initialExpression?: string
  }>(),
  {
    title: 'Graph Playground',
    hint: 'Scroll to zoom, drag to pan, and hover for coordinates.',
    initialExpression: 'x^2',
  },
)

const emit = defineEmits<{
  (e: 'close'): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const funcInput = ref(props.initialExpression)
const errorMsg = ref('')
const hoverCoords = ref<{ x: number; y: number } | null>(null)

const viewCenterX = ref(0)
const viewCenterY = ref(0)
const viewScale = ref(40)

function parseMathExpr(expr: string): ((x: number) => number) | null {
  try {
    const prepared = expr
      .replace(/\^/g, '**')
      .replace(/(\d)(x)/g, '$1*x')
      .replace(/(x)(\d)/g, 'x*$2')
      .replace(/\)(x)/g, ')*x')
      .replace(/(x)\(/g, 'x*(')
      .replace(/sin/g, 'Math.sin')
      .replace(/cos/g, 'Math.cos')
      .replace(/tan/g, 'Math.tan')
      .replace(/sqrt/g, 'Math.sqrt')
      .replace(/abs/g, 'Math.abs')
      .replace(/log/g, 'Math.log')
      .replace(/pi/gi, 'Math.PI')
      .replace(/e(?![a-zA-Z])/g, 'Math.E')

    const fn = new Function('x', `"use strict"; return (${prepared});`) as (x: number) => number
    fn(1)
    return fn
  } catch {
    return null
  }
}

function draw(): void {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }

  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }

  const width = canvas.width
  const height = canvas.height
  const scale = viewScale.value
  const centerX = width / 2 + viewCenterX.value * scale
  const centerY = height / 2 - viewCenterY.value * scale

  ctx.fillStyle = '#07111f'
  ctx.fillRect(0, 0, width, height)

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)'
  ctx.lineWidth = 1
  const step = scale >= 20 ? 1 : scale >= 10 ? 2 : 5

  const xStart = Math.floor(-centerX / scale / step) * step
  const xEnd = Math.ceil((width - centerX) / scale / step) * step
  for (let x = xStart; x <= xEnd; x += step) {
    const px = centerX + x * scale
    ctx.beginPath()
    ctx.moveTo(px, 0)
    ctx.lineTo(px, height)
    ctx.stroke()
  }

  const yStart = Math.floor((centerY - height) / scale / step) * step
  const yEnd = Math.ceil(centerY / scale / step) * step
  for (let y = yStart; y <= yEnd; y += step) {
    const py = centerY - y * scale
    ctx.beginPath()
    ctx.moveTo(0, py)
    ctx.lineTo(width, py)
    ctx.stroke()
  }

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.28)'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(centerX, 0)
  ctx.lineTo(centerX, height)
  ctx.stroke()

  ctx.fillStyle = 'rgba(255, 255, 255, 0.42)'
  ctx.font = '11px ui-sans-serif, system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  for (let x = xStart; x <= xEnd; x += step) {
    if (x === 0) {
      continue
    }
    ctx.fillText(String(x), centerX + x * scale, centerY + 4)
  }

  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  for (let y = yStart; y <= yEnd; y += step) {
    if (y === 0) {
      continue
    }
    ctx.fillText(String(y), centerX - 6, centerY - y * scale)
  }

  const fn = parseMathExpr(funcInput.value)
  if (!fn) {
    errorMsg.value = 'Invalid function'
    return
  }

  errorMsg.value = ''
  ctx.strokeStyle = '#5eead4'
  ctx.lineWidth = 2.5
  ctx.beginPath()
  let started = false
  for (let px = 0; px < width; px += 1) {
    const x = (px - centerX) / scale
    try {
      const y = fn(x)
      if (!Number.isFinite(y)) {
        started = false
        continue
      }
      const py = centerY - y * scale
      if (!started) {
        ctx.moveTo(px, py)
        started = true
      } else {
        ctx.lineTo(px, py)
      }
    } catch {
      started = false
    }
  }
  ctx.stroke()

  if (hoverCoords.value) {
    const hoverX = centerX + hoverCoords.value.x * scale
    const hoverY = centerY - hoverCoords.value.y * scale

    ctx.strokeStyle = 'rgba(45, 212, 191, 0.35)'
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(hoverX, 0)
    ctx.lineTo(hoverX, height)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, hoverY)
    ctx.lineTo(width, hoverY)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.fillStyle = '#f9a8d4'
    ctx.beginPath()
    ctx.arc(hoverX, hoverY, 5, 0, Math.PI * 2)
    ctx.fill()
  }
}

function resizeCanvas(): void {
  const canvas = canvasRef.value
  if (!canvas || !canvas.parentElement) {
    return
  }

  canvas.width = canvas.parentElement.clientWidth
  canvas.height = canvas.parentElement.clientHeight
  draw()
}

function onMouseMove(event: MouseEvent): void {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }

  const rect = canvas.getBoundingClientRect()
  const mouseX = event.clientX - rect.left
  const scale = viewScale.value
  const centerX = canvas.width / 2 + viewCenterX.value * scale
  const centerY = canvas.height / 2 - viewCenterY.value * scale
  const x = (mouseX - centerX) / scale

  const fn = parseMathExpr(funcInput.value)
  if (!fn) {
    return
  }

  try {
    const y = fn(x)
    if (!Number.isFinite(y)) {
      hoverCoords.value = null
    } else {
      hoverCoords.value = {
        x: Number(x.toFixed(3)),
        y: Number(y.toFixed(3)),
      }
    }
  } catch {
    hoverCoords.value = null
  }

  draw()
}

function onMouseLeave(): void {
  hoverCoords.value = null
  draw()
}

function zoomIn(): void {
  viewScale.value = Math.min(200, viewScale.value * 1.3)
  draw()
}

function zoomOut(): void {
  viewScale.value = Math.max(5, viewScale.value / 1.3)
  draw()
}

function resetView(): void {
  viewCenterX.value = 0
  viewCenterY.value = 0
  viewScale.value = 40
  draw()
}

function onWheel(event: WheelEvent): void {
  event.preventDefault()
  if (event.deltaY < 0) {
    zoomIn()
  } else {
    zoomOut()
  }
}

let isPanning = false
let panStartX = 0
let panStartY = 0
let panOriginX = 0
let panOriginY = 0

function onPanStart(event: MouseEvent): void {
  if (event.button !== 0) {
    return
  }

  isPanning = true
  panStartX = event.clientX
  panStartY = event.clientY
  panOriginX = viewCenterX.value
  panOriginY = viewCenterY.value
}

function onPanMove(event: MouseEvent): void {
  if (!isPanning) {
    return
  }

  const deltaX = event.clientX - panStartX
  const deltaY = event.clientY - panStartY
  viewCenterX.value = panOriginX + deltaX / viewScale.value
  viewCenterY.value = panOriginY - deltaY / viewScale.value
  draw()
}

function onPanEnd(): void {
  isPanning = false
}

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) {
      return
    }

    funcInput.value = props.initialExpression
    hoverCoords.value = null
    await nextTick()
    resizeCanvas()
  },
)

watch(
  () => props.initialExpression,
  (value) => {
    if (props.visible) {
      funcInput.value = value
      draw()
    }
  },
)

watch(funcInput, () => {
  draw()
})

onMounted(() => {
  window.addEventListener('resize', resizeCanvas)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="graph-playground" @click.self="emit('close')">
      <div class="graph-playground__modal">
        <header class="graph-playground__header">
          <div>
            <p class="graph-playground__eyebrow">Interactive graph</p>
            <h3>{{ title }}</h3>
          </div>
          <button type="button" class="graph-playground__close" @click="emit('close')">
            Close
          </button>
        </header>

        <div class="graph-playground__controls">
          <label class="graph-playground__input">
            <span>f(x) =</span>
            <input
              v-model="funcInput"
              type="text"
              spellcheck="false"
              placeholder="e.g. x^2, sin(x), 2*x+1"
            />
          </label>

          <div class="graph-playground__buttons">
            <button type="button" @click="zoomIn">Zoom in</button>
            <button type="button" @click="zoomOut">Zoom out</button>
            <button type="button" @click="resetView">Reset</button>
          </div>
        </div>

        <p v-if="errorMsg" class="graph-playground__error">{{ errorMsg }}</p>

        <div class="graph-playground__canvas-wrap">
          <canvas
            ref="canvasRef"
            @mousemove="onMouseMove"
            @mouseleave="onMouseLeave"
            @wheel="onWheel"
            @mousedown="onPanStart"
            @mousemove.capture="onPanMove"
            @mouseup="onPanEnd"
            @mouseleave.capture="onPanEnd"
          ></canvas>
          <div v-if="hoverCoords" class="graph-playground__coords">
            ({{ hoverCoords.x }}, {{ hoverCoords.y }})
          </div>
        </div>

        <p class="graph-playground__hint">{{ hint }}</p>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.graph-playground {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(2, 6, 23, 0.72);
  backdrop-filter: blur(8px);
}

.graph-playground__modal {
  width: min(92vw, 760px);
  height: min(85vh, 640px);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 1.5rem;
  background: linear-gradient(180deg, #07111f 0%, #0f172a 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 28px 70px rgba(2, 6, 23, 0.55);
}

.graph-playground__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.graph-playground__eyebrow {
  margin: 0 0 0.25rem;
  color: #67e8f9;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
}

.graph-playground__header h3 {
  margin: 0;
  font-size: 1.35rem;
}

.graph-playground__close,
.graph-playground__buttons button {
  border: none;
  border-radius: 0.85rem;
  padding: 0.75rem 0.9rem;
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  cursor: pointer;
}

.graph-playground__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  align-items: center;
}

.graph-playground__input {
  flex: 1;
  display: grid;
  gap: 0.35rem;
  min-width: 16rem;
}

.graph-playground__input span {
  color: #99f6e4;
  font-weight: 600;
}

.graph-playground__input input {
  width: 100%;
  padding: 0.8rem 0.95rem;
  border-radius: 0.95rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(15, 23, 42, 0.85);
  color: #f8fafc;
}

.graph-playground__buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.graph-playground__error {
  margin: 0;
  color: #fca5a5;
}

.graph-playground__canvas-wrap {
  position: relative;
  flex: 1;
  min-height: 18rem;
  border-radius: 1.2rem;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.graph-playground__canvas-wrap canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.graph-playground__coords {
  position: absolute;
  top: 0.85rem;
  right: 0.85rem;
  padding: 0.4rem 0.65rem;
  border-radius: 0.75rem;
  background: rgba(2, 6, 23, 0.78);
  color: #f9a8d4;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 0.82rem;
}

.graph-playground__hint {
  margin: 0;
  color: #cbd5e1;
  line-height: 1.6;
}

@media (max-width: 720px) {
  .graph-playground__modal {
    width: 100%;
    height: 100%;
    max-height: none;
    border-radius: 0;
  }

  .graph-playground__header {
    flex-direction: column;
  }
}
</style>
