<script setup lang="ts">
import InteractiveDerivativeActivity from '../components/InteractiveDerivativeActivity.vue'

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

function formatNumber(value: number) {
  if (Math.abs(value) < 0.0001) {
    return '0'
  }

  const rounded = Number(value.toFixed(2))
  return Number.isInteger(rounded) ? String(rounded) : String(rounded)
}

function formatSigned(value: number) {
  return value >= 0 ? `+ ${formatNumber(value)}` : `- ${formatNumber(Math.abs(value))}`
}

function getParam(params: Record<string, number>, key: string) {
  return params[key] ?? 0
}

const activities: ActivityProps[] = [
  {
    title: 'Activity 1',
    prompt: 'Set a = 3. Then move b only.',
    note: 'See: one slider changes the steepness. The other only moves the graph.',
    sliders: [
      { key: 'a', label: 'a', min: -5, max: 5, step: 1, initial: 2 },
      { key: 'b', label: 'b', min: -6, max: 6, step: 1, initial: 1 },
    ],
    xMin: -6,
    xMax: 6,
    yMin: -10,
    yMax: 10,
    formulaLabel: (params) => `f(x) = ${formatNumber(getParam(params, 'a'))}x ${formatSigned(getParam(params, 'b'))}`,
    derivativeLabel: (params) => `f'(x) = ${formatNumber(getParam(params, 'a'))}`,
    curve: (x, params) => getParam(params, 'a') * x + getParam(params, 'b'),
    status: (params) => {
      if (getParam(params, 'a') === 3) {
        return {
          tone: 'success',
          title: 'Challenge met',
          body: 'You set the constant derivative to 3. Changing b still moves the graph without changing the derivative.',
        }
      }

      return {
        tone: 'info',
        title: 'Interact and learn',
        body: 'Try moving b after you choose a. Watch what stays exactly the same.',
      }
    },
    focusX: () => 0,
    focusLabel: () => 'y-intercept',
  },
  {
    title: 'Activity 2',
    prompt: 'Make the graph reach a maximum at (2, 4).',
    note: 'See: one slider flips the shape, and the others guide the peak into place.',
    sliders: [
      { key: 'a', label: 'a', min: -4, max: 4, step: 1, initial: -1 },
      { key: 'c', label: 'c', min: -4, max: 4, step: 1, initial: 0 },
      { key: 'd', label: 'd', min: -1, max: 6, step: 1, initial: 2 },
    ],
    xMin: -6,
    xMax: 6,
    yMin: -8,
    yMax: 8,
    formulaLabel: (params) => {
      const a = getParam(params, 'a')
      const c = getParam(params, 'c')
      const d = getParam(params, 'd')
      return `f(x) = ${formatNumber(a)}(x ${c >= 0 ? `- ${formatNumber(c)}` : `+ ${formatNumber(Math.abs(c))}`})^2 ${formatSigned(d)}`
    },
    derivativeLabel: (params) => {
      const a = getParam(params, 'a')
      const c = getParam(params, 'c')
      return `f'(x) = ${formatNumber(2 * a)}(x ${c >= 0 ? `- ${formatNumber(c)}` : `+ ${formatNumber(Math.abs(c))}`})`
    },
    curve: (x, params) => {
      const a = getParam(params, 'a')
      const c = getParam(params, 'c')
      const d = getParam(params, 'd')
      return a * (x - c) ** 2 + d
    },
    status: (params) => {
      const a = getParam(params, 'a')
      const c = getParam(params, 'c')
      const d = getParam(params, 'd')

      if (a < 0 && c === 2 && d === 4) {
        return {
          tone: 'success',
          title: 'Maximum placed',
          body: 'The vertex is now at (2, 4), and because a is negative the vertex is a maximum instead of a minimum.',
        }
      }

      if (a >= 0) {
        return {
          tone: 'warning',
          title: 'Interact and learn',
          body: 'Start by flipping the curve the other way. The peak appears after that.',
        }
      }

      return {
        tone: 'info',
        title: 'Interact and learn',
        body: 'Slide the peak across, then lift it into place. One slider still decides its direction.',
      }
    },
    focusX: (params) => getParam(params, 'c'),
    focusLabel: (params) => `vertex (${formatNumber(getParam(params, 'c'))}, ${formatNumber(getParam(params, 'd'))})`,
  },
  {
    title: 'Activity 3',
    prompt: 'Set the slope at x = c to -2. Then change a.',
    note: 'See: one slider locks the slope at the center, while another reshapes everything around it.',
    sliders: [
      { key: 'a', label: 'a', min: -1, max: 1, step: 0.25, initial: 0.5 },
      { key: 'b', label: 'b', min: -4, max: 4, step: 1, initial: 1 },
      { key: 'c', label: 'c', min: -3, max: 3, step: 1, initial: 0 },
      { key: 'd', label: 'd', min: -4, max: 4, step: 1, initial: 0 },
    ],
    xMin: -6,
    xMax: 6,
    yMin: -8,
    yMax: 8,
    formulaLabel: (params) => {
      const a = getParam(params, 'a')
      const b = getParam(params, 'b')
      const c = getParam(params, 'c')
      const d = getParam(params, 'd')
      return `f(x) = ${formatNumber(a)}(x ${c >= 0 ? `- ${formatNumber(c)}` : `+ ${formatNumber(Math.abs(c))}`})^3 ${formatSigned(b)}(x ${c >= 0 ? `- ${formatNumber(c)}` : `+ ${formatNumber(Math.abs(c))}`}) ${formatSigned(d)}`
    },
    derivativeLabel: (params) => {
      const a = getParam(params, 'a')
      const b = getParam(params, 'b')
      const c = getParam(params, 'c')
      return `f'(x) = ${formatNumber(3 * a)}(x ${c >= 0 ? `- ${formatNumber(c)}` : `+ ${formatNumber(Math.abs(c))}`})^2 ${formatSigned(b)}`
    },
    curve: (x, params) => {
      const a = getParam(params, 'a')
      const b = getParam(params, 'b')
      const c = getParam(params, 'c')
      const d = getParam(params, 'd')
      return a * (x - c) ** 3 + b * (x - c) + d
    },
    status: (params) => {
      const b = getParam(params, 'b')

      if (b === -2) {
        return {
          tone: 'success',
          title: 'Center slope matched',
          body: 'At x = c, the derivative is now -2. Changing a bends the graph more or less, but the slope right at the center stays tied to b.',
        }
      }

      return {
        tone: 'info',
        title: 'Interact and learn',
        body: `Hover near the center and compare the slope there with b = ${formatNumber(b)}.`,
      }
    },
    focusX: (params) => getParam(params, 'c'),
    focusLabel: (params) => `center x = ${formatNumber(getParam(params, 'c'))}`,
  },
]
</script>

<template>
  <div class="derivative-page">
    <div class="derivative-page__glow derivative-page__glow--left"></div>
    <div class="derivative-page__glow derivative-page__glow--right"></div>

    <main class="derivative-layout">
      <section class="hero-panel">
        <router-link to="/" class="back-link">Back home</router-link>

        <p class="hero-panel__eyebrow">Interactive Lab</p>
        <h1>Derivative.</h1>
        <p class="hero-panel__summary">
          A derivative tells us how fast a graph is changing at one exact point. On a graph, that means the slope at that location. Here, every slider changes the function in real time so the idea stays visual.
        </p>

        <div class="concept-strip concept-strip--four">
          <div>
            <strong>Derivative</strong>
            <span>The slope of the graph at one exact point.</span>
          </div>
          <div>
            <strong>Constant derivative</strong>
            <span>The slope stays the same everywhere, like a straight line.</span>
          </div>
          <div>
            <strong>Maximum</strong>
            <span>A highest nearby point, where the graph changes from rising to falling.</span>
          </div>
          <div>
            <strong>Hover readout</strong>
            <span>Move across the graph to inspect coordinates and estimated slope.</span>
          </div>
        </div>
      </section>

      <section class="coach-panel">
        <h2>Interact and learn</h2>
        <p>Move a slider, watch the graph shift, then hover to inspect the point and slope. Learn each idea by doing one small task at a time.</p>

        <div class="coach-panel__steps">
          <div>
            <span>1</span>
            <p>Drag sliders and watch how each coefficient changes the graph.</p>
          </div>
          <div>
            <span>2</span>
            <p>Hover over the graph to inspect the point and the local slope.</p>
          </div>
          <div>
            <span>3</span>
            <p>Use the status box to connect what you see to derivative vocabulary.</p>
          </div>
        </div>
      </section>

      <section class="quiz-grid">
        <InteractiveDerivativeActivity
          v-for="activity in activities"
          :key="activity.title"
          v-bind="activity"
        />
      </section>
    </main>
  </div>
</template>

<style scoped>
.derivative-page {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at top, rgba(255, 206, 161, 0.32), transparent 32%),
    linear-gradient(180deg, #f8f1e6 0%, #eef3f9 48%, #f9f6ef 100%);
  color: #18314c;
  font-family: 'Avenir Next', 'Trebuchet MS', 'Segoe UI', sans-serif;
}

.derivative-page__glow {
  position: absolute;
  width: 32rem;
  height: 32rem;
  border-radius: 999px;
  filter: blur(60px);
  opacity: 0.5;
  pointer-events: none;
}

.derivative-page__glow--left {
  top: -10rem;
  left: -12rem;
  background: rgba(255, 177, 122, 0.42);
}

.derivative-page__glow--right {
  right: -10rem;
  top: 16rem;
  background: rgba(57, 139, 164, 0.22);
}

.derivative-layout {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
  padding: 3rem 1.25rem 4rem;
}

.hero-panel,
.coach-panel {
  border-radius: 34px;
  border: 1px solid rgba(25, 58, 92, 0.1);
  box-shadow: 0 24px 60px rgba(24, 50, 79, 0.09);
}

.hero-panel {
  padding: 1.5rem;
  background:
    linear-gradient(135deg, rgba(255, 251, 245, 0.95), rgba(255, 243, 232, 0.92)),
    #fff;
}

.back-link {
  display: inline-flex;
  align-items: center;
  margin-bottom: 1rem;
  color: #1d7c78;
  text-decoration: none;
  font-weight: 700;
}

.back-link:hover {
  text-decoration: underline;
}

.hero-panel__eyebrow {
  margin: 0 0 0.8rem;
  color: #c7642c;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 0.8rem;
  font-weight: 700;
}

h1 {
  max-width: 12ch;
  margin: 0;
  font-size: clamp(2.4rem, 5vw, 4.8rem);
  line-height: 0.98;
  color: #193a5c;
}

.hero-panel__summary {
  max-width: 58rem;
  margin: 1.1rem 0 0;
  font-size: 1.08rem;
  line-height: 1.75;
}

.concept-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1.6rem;
}

.concept-strip--four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.concept-strip div {
  padding: 1rem 1.1rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(25, 58, 92, 0.1);
}

.concept-strip strong,
.concept-strip span {
  display: block;
}

.concept-strip strong {
  margin-bottom: 0.35rem;
  color: #193a5c;
}

.concept-strip span {
  color: #355674;
  line-height: 1.5;
}

.coach-panel {
  margin-top: 1.4rem;
  padding: 1.4rem 1.5rem;
  background: rgba(24, 49, 76, 0.94);
  color: #eff7ff;
}

.coach-panel h2 {
  margin: 0 0 0.6rem;
  font-size: 1.35rem;
}

.coach-panel p {
  margin: 0;
  max-width: 54rem;
  line-height: 1.7;
}

.coach-panel__steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}

.coach-panel__steps div {
  padding: 1rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.coach-panel__steps span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  margin-bottom: 0.7rem;
  border-radius: 999px;
  background: rgba(255, 185, 137, 0.18);
  color: #ffd2b3;
  font-weight: 800;
}

.coach-panel__steps p {
  font-size: 0.97rem;
}

.quiz-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  margin-top: 1.5rem;
}

@media (max-width: 900px) {
  .concept-strip,
  .coach-panel__steps,
  .quiz-grid {
    grid-template-columns: 1fr;
  }

  .derivative-layout {
    padding-top: 1.5rem;
  }
}
</style>
