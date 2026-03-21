<script setup lang="ts">
import { computed, ref } from 'vue'

interface GraphMarker {
  x: number
  label: string
}

interface DerivativeQuizCardProps {
  title: string
  equationLabel: string
  prompt: string
  hint: string
  explanation: string
  choices: string[]
  correctIndex: number
  curve: (x: number) => number
  xMin: number
  xMax: number
  yMin: number
  yMax: number
  focusX?: number
  tangentSlope?: number
  focusLabel?: string
  tags?: string[]
  markers?: GraphMarker[]
}

const props = withDefaults(defineProps<DerivativeQuizCardProps>(), {
  focusLabel: 'Focus point',
  tags: () => [],
  markers: () => [],
})

const selectedIndex = ref<number | null>(null)
const submitted = ref(false)
const hintVisible = ref(false)

const graphWidth = 320
const graphHeight = 220
const padding = 22

const xRange = computed(() => props.xMax - props.xMin)
const yRange = computed(() => props.yMax - props.yMin)

function xToSvg(x: number) {
  return padding + ((x - props.xMin) / xRange.value) * (graphWidth - padding * 2)
}

function yToSvg(y: number) {
  return graphHeight - padding - ((y - props.yMin) / yRange.value) * (graphHeight - padding * 2)
}

function niceStep(range: number) {
  const rough = range / 5
  if (rough <= 1) return 1
  if (rough <= 2) return 2
  if (rough <= 5) return 5
  return 10
}

function buildTickValues(min: number, max: number, step: number) {
  const values: number[] = []
  const start = Math.ceil(min / step) * step

  for (let value = start; value <= max + 0.0001; value += step) {
    values.push(Number(value.toFixed(4)))
  }

  return values
}

const xTicks = computed(() => buildTickValues(props.xMin, props.xMax, niceStep(xRange.value)))
const yTicks = computed(() => buildTickValues(props.yMin, props.yMax, niceStep(yRange.value)))

const curvePath = computed(() => {
  const commands: string[] = []
  let drawing = false
  const samples = 180

  for (let index = 0; index <= samples; index += 1) {
    const x = props.xMin + (index / samples) * xRange.value
    const y = props.curve(x)

    if (!Number.isFinite(y)) {
      drawing = false
      continue
    }

    const command = `${drawing ? 'L' : 'M'} ${xToSvg(x).toFixed(2)} ${yToSvg(y).toFixed(2)}`
    commands.push(command)
    drawing = true
  }

  return commands.join(' ')
})

const tangentPath = computed(() => {
  if (props.focusX === undefined || props.tangentSlope === undefined) {
    return ''
  }

  const y0 = props.curve(props.focusX)
  const x1 = props.xMin
  const y1 = y0 + props.tangentSlope * (x1 - props.focusX)
  const x2 = props.xMax
  const y2 = y0 + props.tangentSlope * (x2 - props.focusX)

  return `M ${xToSvg(x1).toFixed(2)} ${yToSvg(y1).toFixed(2)} L ${xToSvg(x2).toFixed(2)} ${yToSvg(y2).toFixed(2)}`
})

const focusPoint = computed(() => {
  if (props.focusX === undefined) {
    return null
  }

  return {
    x: props.focusX,
    y: props.curve(props.focusX),
  }
})

const isCorrect = computed(() => submitted.value && selectedIndex.value === props.correctIndex)

function submitAnswer() {
  if (selectedIndex.value === null) {
    return
  }

  submitted.value = true

  if (!isCorrect.value) {
    hintVisible.value = true
  }
}

function resetCard() {
  selectedIndex.value = null
  submitted.value = false
  hintVisible.value = false
}
</script>

<template>
  <article class="quiz-card">
    <div class="quiz-card__top">
      <div>
        <p class="quiz-card__eyebrow">{{ title }}</p>
        <h3>{{ equationLabel }}</h3>
      </div>
      <div class="quiz-card__tags">
        <span v-for="tag in tags" :key="tag">{{ tag }}</span>
      </div>
    </div>

    <div class="graph-shell">
      <svg
        class="graph-shell__svg"
        :viewBox="`0 0 ${graphWidth} ${graphHeight}`"
        role="img"
        :aria-label="`Graph for ${equationLabel}`"
      >
        <rect x="0" y="0" :width="graphWidth" :height="graphHeight" rx="22" class="graph-bg" />

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

        <path v-if="tangentPath" :d="tangentPath" class="graph-tangent" />
        <path :d="curvePath" class="graph-curve" />

        <g v-if="focusPoint" class="graph-focus">
          <circle :cx="xToSvg(focusPoint.x)" :cy="yToSvg(focusPoint.y)" r="5.5" />
          <text :x="xToSvg(focusPoint.x) + 10" :y="yToSvg(focusPoint.y) - 10">{{ focusLabel }}</text>
        </g>

        <g v-for="marker in markers" :key="marker.label" class="graph-marker">
          <circle :cx="xToSvg(marker.x)" :cy="yToSvg(curve(marker.x))" r="4.5" />
          <text :x="xToSvg(marker.x) + 8" :y="yToSvg(curve(marker.x)) - 8">{{ marker.label }}</text>
        </g>
      </svg>
    </div>

    <p class="quiz-card__prompt">{{ prompt }}</p>

    <div class="quiz-card__choices">
      <button
        v-for="(choice, index) in choices"
        :key="choice"
        type="button"
        class="choice"
        :class="{
          selected: selectedIndex === index,
          correct: submitted && index === correctIndex,
          wrong: submitted && selectedIndex === index && index !== correctIndex,
        }"
        @click="selectedIndex = index"
      >
        <span class="choice__index">{{ String.fromCharCode(65 + index) }}</span>
        <span>{{ choice }}</span>
      </button>
    </div>

    <div class="quiz-card__actions">
      <button type="button" class="action action--primary" :disabled="selectedIndex === null" @click="submitAnswer">
        Check answer
      </button>
      <button type="button" class="action" @click="hintVisible = !hintVisible">
        {{ hintVisible ? 'Hide hint' : 'Show hint' }}
      </button>
      <button type="button" class="action" @click="resetCard">
        Reset
      </button>
    </div>

    <p v-if="hintVisible" class="hint-box">
      {{ hint }}
    </p>

    <div v-if="submitted" class="feedback-box" :class="{ success: isCorrect, retry: !isCorrect }">
      <strong>{{ isCorrect ? 'Nice work.' : 'Almost there.' }}</strong>
      <span>{{ explanation }}</span>
    </div>
  </article>
</template>

<style scoped>
.quiz-card {
  display: grid;
  gap: 1rem;
  padding: 1.35rem;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 248, 239, 0.98)),
    #fff;
  border: 1px solid rgba(25, 58, 92, 0.12);
  box-shadow: 0 20px 50px rgba(24, 50, 79, 0.12);
}

.quiz-card__top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.quiz-card__eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #c7642c;
}

h3 {
  margin: 0;
  color: #193a5c;
  font-size: 1.4rem;
  font-family: 'Avenir Next', 'Trebuchet MS', sans-serif;
}

.quiz-card__tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.45rem;
}

.quiz-card__tags span {
  padding: 0.38rem 0.7rem;
  border-radius: 999px;
  background: rgba(25, 58, 92, 0.08);
  color: #234a72;
  font-size: 0.78rem;
  font-weight: 700;
}

.graph-shell {
  padding: 0.5rem;
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(255, 210, 176, 0.45), transparent 42%),
    linear-gradient(180deg, #fffef9, #f5f7fb);
  border: 1px solid rgba(25, 58, 92, 0.08);
}

.graph-shell__svg {
  width: 100%;
  height: auto;
  display: block;
}

.graph-bg {
  fill: #fffdf6;
}

.graph-grid line {
  stroke: rgba(39, 78, 118, 0.09);
  stroke-width: 1;
}

.graph-axis {
  stroke: rgba(25, 58, 92, 0.45);
  stroke-width: 1.8;
}

.graph-curve {
  fill: none;
  stroke: #1d7c78;
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.graph-tangent {
  fill: none;
  stroke: #f08d49;
  stroke-width: 3;
  stroke-dasharray: 8 7;
}

.graph-focus circle,
.graph-marker circle {
  fill: #c7642c;
}

.graph-focus text,
.graph-marker text {
  fill: #193a5c;
  font-size: 12px;
  font-weight: 700;
}

.quiz-card__prompt {
  margin: 0;
  color: #18314c;
  font-size: 1.02rem;
  line-height: 1.6;
}

.quiz-card__choices {
  display: grid;
  gap: 0.75rem;
}

.choice {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  width: 100%;
  padding: 0.9rem 1rem;
  border: 1px solid rgba(25, 58, 92, 0.15);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  color: #18314c;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.choice:hover {
  transform: translateY(-1px);
  border-color: rgba(29, 124, 120, 0.45);
  box-shadow: 0 10px 22px rgba(29, 124, 120, 0.08);
}

.choice.selected {
  border-color: #1d7c78;
  background: rgba(29, 124, 120, 0.08);
}

.choice.correct {
  border-color: #1f8f5f;
  background: rgba(31, 143, 95, 0.1);
}

.choice.wrong {
  border-color: #c7642c;
  background: rgba(199, 100, 44, 0.1);
}

.choice__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  background: rgba(25, 58, 92, 0.08);
  font-weight: 800;
  flex-shrink: 0;
}

.quiz-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.action {
  padding: 0.78rem 1rem;
  border: 1px solid rgba(25, 58, 92, 0.16);
  border-radius: 999px;
  background: transparent;
  color: #193a5c;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.action:hover {
  background: rgba(25, 58, 92, 0.06);
}

.action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.action--primary {
  background: #193a5c;
  color: #fffaf2;
  border-color: #193a5c;
}

.action--primary:hover:not(:disabled) {
  background: #0f2943;
}

.hint-box,
.feedback-box {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  line-height: 1.6;
}

.hint-box {
  background: rgba(240, 141, 73, 0.12);
  color: #7a431d;
  border: 1px solid rgba(240, 141, 73, 0.28);
}

.feedback-box {
  display: grid;
  gap: 0.25rem;
}

.feedback-box.success {
  background: rgba(31, 143, 95, 0.11);
  border: 1px solid rgba(31, 143, 95, 0.22);
  color: #175a3e;
}

.feedback-box.retry {
  background: rgba(25, 58, 92, 0.08);
  border: 1px solid rgba(25, 58, 92, 0.14);
  color: #18314c;
}

@media (max-width: 640px) {
  .quiz-card {
    padding: 1rem;
    border-radius: 22px;
  }

  .quiz-card__top {
    flex-direction: column;
  }

  .quiz-card__tags {
    justify-content: flex-start;
  }

  h3 {
    font-size: 1.18rem;
  }
}
</style>
