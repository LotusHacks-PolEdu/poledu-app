<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

interface SliderSpec {
  key: string
  label: string
  min: number
  max: number
  step: number
  initial: number
}

interface StatusMessage {
  tone: 'info' | 'success' | 'warning'
  title: string
  body: string
}

interface ActivityProps {
  title: string
  prompt: string
  note: string
  sliders: SliderSpec[]
  xMin: number
  xMax: number
  yMin: number
  yMax: number
  formulaLabel: (params: Record<string, number>) => string
  derivativeLabel: (params: Record<string, number>) => string
  curve: (x: number, params: Record<string, number>) => number
  status: (params: Record<string, number>) => StatusMessage
  focusX?: (params: Record<string, number>) => number | undefined
  focusLabel?: (params: Record<string, number>) => string
}

const props = defineProps<ActivityProps>()

const svgRef = ref<SVGSVGElement | null>(null)
const hoverPoint = ref<{ x: number; y: number; slope: number } | null>(null)

const params = reactive<Record<string, number>>(
  Object.fromEntries(props.sliders.map((slider) => [slider.key, slider.initial])),
)

const graphWidth = 420
const graphHeight = 250
const padding = 24

const xRange = computed(() => props.xMax - props.xMin)
const yRange = computed(() => props.yMax - props.yMin)

function formatNumber(value: number) {
  if (Math.abs(value) < 0.0001) {
    return '0'
  }

  const rounded = Number(value.toFixed(2))
  return Number.isInteger(rounded) ? String(rounded) : String(rounded)
}

function xToSvg(x: number) {
  return padding + ((x - props.xMin) / xRange.value) * (graphWidth - padding * 2)
}

function yToSvg(y: number) {
  return graphHeight - padding - ((y - props.yMin) / yRange.value) * (graphHeight - padding * 2)
}

function niceStep(range: number) {
  const rough = range / 6
  if (rough <= 1) return 1
  if (rough <= 2) return 2
  if (rough <= 5) return 5
  return 10
}

function buildTicks(min: number, max: number, step: number) {
  const values: number[] = []
  const start = Math.ceil(min / step) * step

  for (let value = start; value <= max + 0.0001; value += step) {
    values.push(Number(value.toFixed(3)))
  }

  return values
}

function curveAt(x: number) {
  return props.curve(x, params)
}

function paramValue(key: string) {
  return params[key] ?? 0
}

function estimateSlope(x: number) {
  const h = xRange.value / 800
  const left = curveAt(x - h)
  const right = curveAt(x + h)

  if (!Number.isFinite(left) || !Number.isFinite(right)) {
    return 0
  }

  return (right - left) / (2 * h)
}

const xTicks = computed(() => buildTicks(props.xMin, props.xMax, niceStep(xRange.value)))
const yTicks = computed(() => buildTicks(props.yMin, props.yMax, niceStep(yRange.value)))

const curvePath = computed(() => {
  const commands: string[] = []
  let drawing = false
  const samples = 220

  for (let index = 0; index <= samples; index += 1) {
    const x = props.xMin + (index / samples) * xRange.value
    const y = curveAt(x)

    if (!Number.isFinite(y)) {
      drawing = false
      continue
    }

    commands.push(`${drawing ? 'L' : 'M'} ${xToSvg(x).toFixed(2)} ${yToSvg(y).toFixed(2)}`)
    drawing = true
  }

  return commands.join(' ')
})

const focusPoint = computed(() => {
  if (!props.focusX) {
    return null
  }

  const x = props.focusX(params)

  if (x === undefined) {
    return null
  }

  const y = curveAt(x)

  if (!Number.isFinite(y)) {
    return null
  }

  return {
    x,
    y,
    label: props.focusLabel ? props.focusLabel(params) : 'focus',
  }
})

const statusMessage = computed(() => props.status(params))

function handlePointerMove(event: PointerEvent) {
  if (!svgRef.value) {
    return
  }

  const rect = svgRef.value.getBoundingClientRect()
  const ratio = (event.clientX - rect.left) / rect.width
  const clampedRatio = Math.min(1, Math.max(0, ratio))
  const x = props.xMin + clampedRatio * xRange.value
  const y = curveAt(x)

  if (!Number.isFinite(y) || y < props.yMin || y > props.yMax) {
    hoverPoint.value = null
    return
  }

  hoverPoint.value = {
    x,
    y,
    slope: estimateSlope(x),
  }
}

function clearHover() {
  hoverPoint.value = null
}
</script>

<template>
  <article class="activity-card">
    <div class="activity-card__header">
      <div>
        <p class="activity-card__eyebrow">{{ title }}</p>
        <h3>{{ formulaLabel(params) }}</h3>
      </div>
      <div class="activity-card__formula">
        <span>Derivative</span>
        <strong>{{ derivativeLabel(params) }}</strong>
      </div>
    </div>

    <p class="activity-card__prompt">{{ prompt }}</p>
    <p class="activity-card__note">{{ note }}</p>

    <div class="activity-card__grid">
      <div class="activity-card__controls">
        <label v-for="slider in sliders" :key="slider.key" class="slider-field">
          <div class="slider-field__top">
            <span>{{ slider.label }}</span>
            <strong>{{ formatNumber(paramValue(slider.key)) }}</strong>
          </div>

          <input
            v-model.number="params[slider.key]"
            type="range"
            :min="slider.min"
            :max="slider.max"
            :step="slider.step"
          />

          <div class="slider-field__bounds">
            <span>{{ slider.min }}</span>
            <span>{{ slider.max }}</span>
          </div>
        </label>
      </div>

      <div class="activity-card__graph">
        <svg
          ref="svgRef"
          class="graph-surface"
          :viewBox="`0 0 ${graphWidth} ${graphHeight}`"
          role="img"
          :aria-label="`Interactive graph for ${title}`"
          @pointermove="handlePointerMove"
          @pointerleave="clearHover"
        >
          <rect x="0" y="0" :width="graphWidth" :height="graphHeight" rx="24" class="graph-bg" />

          <g class="graph-grid">
            <line
              v-for="tick in xTicks"
              :key="`x-${tick}`"
              :x1="xToSvg(tick)"
              :x2="xToSvg(tick)"
              :y1="padding"
              :y2="graphHeight - padding"
            />
            <line
              v-for="tick in yTicks"
              :key="`y-${tick}`"
              :x1="padding"
              :x2="graphWidth - padding"
              :y1="yToSvg(tick)"
              :y2="yToSvg(tick)"
            />
          </g>

          <line
            v-if="props.yMin <= 0 && props.yMax >= 0"
            class="graph-axis"
            :x1="padding"
            :x2="graphWidth - padding"
            :y1="yToSvg(0)"
            :y2="yToSvg(0)"
          />
          <line
            v-if="props.xMin <= 0 && props.xMax >= 0"
            class="graph-axis"
            :x1="xToSvg(0)"
            :x2="xToSvg(0)"
            :y1="padding"
            :y2="graphHeight - padding"
          />

          <path :d="curvePath" class="graph-curve" />

          <g v-if="focusPoint" class="graph-focus">
            <circle :cx="xToSvg(focusPoint.x)" :cy="yToSvg(focusPoint.y)" r="5" />
            <text :x="xToSvg(focusPoint.x) + 9" :y="yToSvg(focusPoint.y) - 10">{{ focusPoint.label }}</text>
          </g>

          <g v-if="hoverPoint" class="graph-hover">
            <line
              :x1="xToSvg(hoverPoint.x)"
              :x2="xToSvg(hoverPoint.x)"
              :y1="padding"
              :y2="graphHeight - padding"
            />
            <line
              :x1="padding"
              :x2="graphWidth - padding"
              :y1="yToSvg(hoverPoint.y)"
              :y2="yToSvg(hoverPoint.y)"
            />
            <circle :cx="xToSvg(hoverPoint.x)" :cy="yToSvg(hoverPoint.y)" r="5.5" />
          </g>
        </svg>

        <div class="activity-card__readout">
          <template v-if="hoverPoint">
            <span>Point: ({{ formatNumber(hoverPoint.x) }}, {{ formatNumber(hoverPoint.y) }})</span>
            <span>Estimated slope: {{ formatNumber(hoverPoint.slope) }}</span>
          </template>
          <template v-else>
            <span>Hover the graph to inspect a point.</span>
            <span>The slope readout approximates the derivative there.</span>
          </template>
        </div>
      </div>
    </div>

    <div class="activity-card__status" :class="statusMessage.tone">
      <strong>{{ statusMessage.title }}</strong>
      <span>{{ statusMessage.body }}</span>
    </div>
  </article>
</template>

<style scoped>
.activity-card {
  display: grid;
  gap: 1rem;
  padding: 1.35rem;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(22, 57, 90, 0.1);
  box-shadow: 0 20px 44px rgba(17, 47, 78, 0.1);
}

.activity-card__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.activity-card__eyebrow {
  margin: 0 0 0.35rem;
  color: #d06d34;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

h3 {
  margin: 0;
  color: #173a5d;
  font-size: 1.4rem;
  line-height: 1.2;
}

.activity-card__formula {
  display: grid;
  gap: 0.2rem;
  min-width: 11rem;
  padding: 0.9rem 1rem;
  border-radius: 20px;
  background: rgba(23, 58, 93, 0.06);
}

.activity-card__formula span {
  color: #4d6986;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.activity-card__formula strong {
  color: #173a5d;
}

.activity-card__prompt,
.activity-card__note {
  margin: 0;
  line-height: 1.65;
}

.activity-card__prompt {
  color: #18314c;
  font-size: 1.02rem;
}

.activity-card__note {
  color: #4c6682;
}

.activity-card__grid {
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  gap: 1rem;
}

.activity-card__controls {
  display: grid;
  gap: 0.9rem;
}

.slider-field {
  display: grid;
  gap: 0.45rem;
  padding: 0.95rem;
  border-radius: 20px;
  background: linear-gradient(180deg, #fff8ef, #f7fbff);
  border: 1px solid rgba(22, 57, 90, 0.08);
}

.slider-field__top,
.slider-field__bounds {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.slider-field__top span {
  color: #2c4e70;
  font-weight: 700;
}

.slider-field__top strong {
  color: #173a5d;
}

.slider-field__bounds {
  color: #6a8098;
  font-size: 0.82rem;
}

input[type='range'] {
  width: 100%;
  accent-color: #1c7f79;
}

.activity-card__graph {
  display: grid;
  gap: 0.8rem;
}

.graph-surface {
  width: 100%;
  height: auto;
  display: block;
  touch-action: none;
}

.graph-bg {
  fill: #fffdf7;
}

.graph-grid line {
  stroke: rgba(26, 60, 93, 0.08);
}

.graph-axis {
  stroke: rgba(23, 58, 93, 0.45);
  stroke-width: 1.7;
}

.graph-curve {
  fill: none;
  stroke: #1c7f79;
  stroke-width: 4;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.graph-focus circle,
.graph-hover circle {
  fill: #d06d34;
}

.graph-focus text {
  fill: #173a5d;
  font-size: 12px;
  font-weight: 700;
}

.graph-hover line {
  stroke: rgba(208, 109, 52, 0.35);
  stroke-dasharray: 6 6;
}

.activity-card__readout {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  padding: 0.95rem 1rem;
  border-radius: 20px;
  background: rgba(23, 58, 93, 0.06);
  color: #24486d;
  font-size: 0.94rem;
}

.activity-card__status {
  display: grid;
  gap: 0.2rem;
  padding: 0.95rem 1rem;
  border-radius: 20px;
}

.activity-card__status.info {
  background: rgba(28, 127, 121, 0.1);
  color: #145f5b;
}

.activity-card__status.success {
  background: rgba(43, 144, 92, 0.13);
  color: #186241;
}

.activity-card__status.warning {
  background: rgba(208, 109, 52, 0.12);
  color: #8a4a20;
}

@media (max-width: 960px) {
  .activity-card__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .activity-card {
    padding: 1rem;
    border-radius: 24px;
  }

  .activity-card__header {
    flex-direction: column;
  }

  .activity-card__formula {
    min-width: 0;
    width: 100%;
  }

  h3 {
    font-size: 1.18rem;
  }
}
</style>
