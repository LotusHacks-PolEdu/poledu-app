<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

import type {
  LessonAnalogyBlock,
  LessonGraphBlock,
  LessonGraphPlaygroundBlock,
  LessonGuidedStepsBlock,
  LessonSection,
  LessonSliderGraphBlock,
  LessonTextBlock,
} from '../types/lessons'
import AnalogyBlock from './AnalogyBlock.vue'
import GraphBlock from './GraphBlock.vue'
import GraphPlayground from './GraphPlayground.vue'
import GuidedSteps from './GuidedSteps.vue'
import LatexFormula from './LatexFormula.vue'
import SliderGraph from './SliderGraph.vue'

const props = defineProps<{
  section: LessonSection
}>()

const activePlayground = ref<LessonGraphPlaygroundBlock | null>(null)

function openPlayground(block: LessonGraphPlaygroundBlock): void {
  activePlayground.value = block
}

function closePlayground(): void {
  activePlayground.value = null
}

// ── Per-section narration ─────────────────────────────────────────────────────
const isNarrating = ref(false)

function toggleNarration(): void {
  if (isNarrating.value) {
    window.speechSynthesis.cancel()
    isNarrating.value = false
    return
  }
  if (!props.section.narration) return
  const utterance = new SpeechSynthesisUtterance(props.section.narration)
  utterance.onend = () => { isNarrating.value = false }
  utterance.onerror = () => { isNarrating.value = false }
  window.speechSynthesis.speak(utterance)
  isNarrating.value = true
}

onBeforeUnmount(() => {
  window.speechSynthesis.cancel()
})

// ── Type guards ───────────────────────────────────────────────────────────────
type AnyBlock = LessonSection['blocks'][number]

function isTextBlock(b: AnyBlock): b is LessonTextBlock { return b.type === 'text' }
function isGraphBlock(b: AnyBlock): b is LessonGraphBlock { return b.type === 'graph' }
function isGraphPlaygroundBlock(b: AnyBlock): b is LessonGraphPlaygroundBlock { return b.type === 'graph-playground' }
function isSliderGraphBlock(b: AnyBlock): b is LessonSliderGraphBlock { return b.type === 'slider-graph' }
function isGuidedStepsBlock(b: AnyBlock): b is LessonGuidedStepsBlock { return b.type === 'guided-steps' }
function isAnalogyBlock(b: AnyBlock): b is LessonAnalogyBlock { return b.type === 'analogy' }
</script>

<template>
  <section class="lesson-section">
    <header class="lesson-section__header">
      <h2>{{ section.title }}</h2>
      <button
        v-if="section.narration"
        type="button"
        class="lesson-section__narration-btn"
        :class="{ 'lesson-section__narration-btn--active': isNarrating }"
        @click="toggleNarration"
      >
        {{ isNarrating ? '⏹' : '▶' }}
        <span>{{ isNarrating ? 'Stop' : 'Listen' }}</span>
      </button>
    </header>

    <div class="lesson-section__blocks">
      <article
        v-for="block in section.blocks"
        :key="block.id"
        class="lesson-block"
        :class="`lesson-block--${block.type}`"
      >
        <!-- Text block -->
        <template v-if="isTextBlock(block)">
          <h3>{{ block.title }}</h3>
          <p>{{ block.content }}</p>
          <LatexFormula
            v-for="expression in block.latex || []"
            :key="`${block.id}-${expression}`"
            :expression="expression"
          />
        </template>

        <!-- Static graph -->
        <template v-else-if="isGraphBlock(block)">
          <h3>{{ block.title }}</h3>
          <p class="lesson-block__prompt">{{ block.prompt }}</p>
          <GraphBlock
            :expression="block.expression"
            :xMin="block.xMin"
            :xMax="block.xMax"
            :yMin="block.yMin"
            :yMax="block.yMax"
            :color="block.color"
          />
        </template>

        <!-- Graph playground (challenge) -->
        <template v-else-if="isGraphPlaygroundBlock(block)">
          <h3>{{ block.title }}</h3>
          <p class="lesson-block__prompt">{{ block.prompt }}</p>
          <div class="lesson-block__playground-card">
            <strong>Challenge</strong>
            <p>{{ block.challenge }}</p>
            <button type="button" @click="openPlayground(block)">Open graph playground</button>
          </div>
        </template>

        <!-- Slider graph (doing learners) -->
        <template v-else-if="isSliderGraphBlock(block)">
          <h3>{{ block.title }}</h3>
          <p class="lesson-block__prompt">{{ block.prompt }}</p>
          <SliderGraph
            :expressionTemplate="block.expression_template"
            :paramA="block.param_a"
            :paramB="block.param_b"
            :xMin="block.xMin"
            :xMax="block.xMax"
            :yMin="block.yMin"
            :yMax="block.yMax"
          />
        </template>

        <!-- Guided steps (doing learners) -->
        <template v-else-if="isGuidedStepsBlock(block)">
          <h3>{{ block.title }}</h3>
          <GuidedSteps :prompt="block.prompt" :steps="block.steps" />
        </template>

        <!-- Analogy (listening learners) -->
        <template v-else-if="isAnalogyBlock(block)">
          <AnalogyBlock :analogy="block.analogy" :connection="block.connection" />
        </template>
      </article>
    </div>

    <GraphPlayground
      :visible="activePlayground !== null"
      :title="activePlayground?.title"
      :hint="activePlayground ? `${activePlayground.prompt} ${activePlayground.challenge}` : ''"
      :initial-expression="activePlayground?.initial_expression || 'x^2'"
      @close="closePlayground"
    />
  </section>
</template>

<style scoped>
.lesson-section {
  display: grid;
  gap: 0.75rem;
  padding: 0.85rem;
  border-radius: 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  min-width: 0;
  overflow: hidden;
}

.lesson-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.lesson-section__header h2 {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 1.2rem;
  word-break: break-word;
}

.lesson-section__narration-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 0.3rem 0.75rem;
  background: transparent;
  color: var(--color-text-muted);
  font-family: var(--font-body);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s, color 0.15s;
}

.lesson-section__narration-btn--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.lesson-section__blocks {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
}

.lesson-block {
  padding: 0.75rem;
  border-radius: 1rem;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  min-width: 0;
  overflow: hidden;
}

/* Analogy block has its own card style — remove double-card */
.lesson-block--analogy {
  padding: 0;
  background: transparent;
  border: none;
}

.lesson-block h3 {
  margin: 0 0 0.55rem;
  font-family: var(--font-heading);
  font-size: 1rem;
  word-break: break-word;
}

.lesson-block p {
  margin: 0;
  line-height: 1.7;
  color: var(--color-text-muted);
  word-break: break-word;
  overflow-wrap: break-word;
  font-size: 0.92rem;
}

.lesson-block__prompt {
  margin-bottom: 0.75rem;
}

/* LaTeX horizontal scroll */
:deep(.katex-display),
:deep(.katex) {
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
}

.lesson-block__playground-card {
  display: grid;
  gap: 0.55rem;
  padding: 0.85rem;
  border-radius: 0.85rem;
  background: var(--color-primary-dim);
  border: 1px solid rgba(0, 186, 255, 0.2);
}

.lesson-block__playground-card strong {
  font-family: var(--font-body);
  font-weight: 700;
  color: var(--color-primary);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.lesson-block__playground-card p {
  color: var(--color-text-muted);
}

.lesson-block__playground-card button {
  justify-self: start;
  border: none;
  border-radius: 999px;
  padding: 0.65rem 1.1rem;
  background: var(--color-primary);
  color: #1A1A1A;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.88rem;
  cursor: pointer;
}
</style>
