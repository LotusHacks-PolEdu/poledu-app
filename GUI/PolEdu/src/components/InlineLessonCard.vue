<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type {
  LessonAnswerKeyItem,
  LessonQuestion,
  MathLessonPayload,
} from '../types/lessons'
import GraphBlock from './GraphBlock.vue'
import LatexFormula from './LatexFormula.vue'
import LessonBlockRenderer from './LessonBlockRenderer.vue'
import MultipleChoice from './MultipleChoice.vue'
import NumberAnswer from './NumberAnswer.vue'
import TrueFalseQuestion from './TrueFalseQuestion.vue'

const props = defineProps<{
  payload: MathLessonPayload
}>()

// ── Mini-test toggle ──────────────────────────────────────────────────────────
const showMiniTest = ref(false)
const answeredQuestions = ref(new Set<string>())

function markAnswered(questionId: string): void {
  answeredQuestions.value = new Set([...answeredQuestions.value, questionId])
}

// ── Narration ─────────────────────────────────────────────────────────────────
const isNarrating = ref(false)

function toggleNarration(): void {
  if (isNarrating.value) {
    window.speechSynthesis.cancel()
    isNarrating.value = false
    return
  }
  const script = props.payload.narration_script
  if (!script) return
  const utterance = new SpeechSynthesisUtterance(script)
  utterance.onend = () => { isNarrating.value = false }
  utterance.onerror = () => { isNarrating.value = false }
  window.speechSynthesis.speak(utterance)
  isNarrating.value = true
}

onBeforeUnmount(() => {
  window.speechSynthesis.cancel()
})

// ── Answer key helpers (mirrors LessonPage.vue) ───────────────────────────────
const answerKeyMap = computed(() => {
  const map = new Map<string, LessonAnswerKeyItem>()
  for (const entry of props.payload.answer_key) {
    map.set(entry.question_id, entry)
  }
  return map
})

const questionMap = computed(() => {
  const map = new Map<string, LessonQuestion>()
  for (const question of props.payload.mini_test) {
    map.set(question.id, question)
  }
  return map
})

function answerKeyFor(questionId: string): LessonAnswerKeyItem | undefined {
  return answerKeyMap.value.get(questionId)
}

function multipleChoiceIndex(questionId: string): number | undefined {
  const key = answerKeyFor(questionId)
  if (key && 'correct_option_index' in key) return key.correct_option_index
  return undefined
}

function numberAnswers(questionId: string): string[] | undefined {
  const key = answerKeyFor(questionId)
  if (key && 'accepted_answers' in key) return key.accepted_answers
  return undefined
}

function trueFalseAnswer(questionId: string): boolean | undefined {
  const key = answerKeyFor(questionId)
  if (key && 'correct_answer' in key) return key.correct_answer
  return undefined
}

function graphTitle(question: LessonQuestion): string {
  return question.type === 'true-false' && question.statement
    ? question.statement
    : question.prompt
}
</script>

<template>
  <div class="ilc">

    <!-- Header -->
    <header class="ilc__header">
      <p class="ilc__eyebrow">Personalized for {{ payload.learner_profile.display_name }}</p>
      <h2 class="ilc__topic">{{ payload.topic }}</h2>
      <div class="ilc__tags">
        <span v-if="payload.learner_profile.learning_by_doing" class="ilc__tag ilc__tag--green">Hands-on</span>
        <span v-if="payload.learner_profile.learning_by_listening" class="ilc__tag ilc__tag--blue">Listening</span>
        <span v-if="payload.learner_profile.learning_by_reading" class="ilc__tag ilc__tag--yellow">Reading</span>
        <span
          v-for="hobby in payload.learner_profile.hobbies.slice(0, 2)"
          :key="hobby"
          class="ilc__tag ilc__tag--neutral"
        >{{ hobby }}</span>
      </div>
      <div class="ilc__header-actions">
        <button
          v-if="payload.narration_script"
          type="button"
          class="ilc__narration-btn"
          @click="toggleNarration"
        >
          {{ isNarrating ? '⏹ Stop' : '▶ Play narration' }}
          <span v-if="isNarrating" class="ilc__narration-live">Speaking…</span>
        </button>
        <RouterLink
          class="ilc__full-link"
          :to="{ name: 'lesson-viewer', params: { lessonCode: payload.lesson_code } }"
          target="_blank"
        >
          Full page ↗
        </RouterLink>
      </div>
    </header>

    <!-- Intro -->
    <p class="ilc__intro">{{ payload.intro }}</p>

    <!-- Sections (LessonBlockRenderer handles graph / graph-playground / text) -->
    <LessonBlockRenderer
      v-for="section in payload.sections"
      :key="section.id"
      :section="section"
    />

    <!-- Mini-test toggle -->
    <div class="ilc__test-toggle">
      <button type="button" class="ilc__toggle-btn" @click="showMiniTest = !showMiniTest">
        {{ showMiniTest ? 'Hide mini-test' : 'Take the mini-test' }}
        <span class="ilc__badge">{{ payload.mini_test.length }} questions</span>
      </button>
    </div>

    <!-- Mini-test questions -->
    <div v-if="showMiniTest" class="ilc__mini-test">
      <article
        v-for="(question, index) in payload.mini_test"
        :key="question.id"
        class="ilc__question"
      >
        <div class="ilc__question-title">
          <span class="ilc__question-num">Q{{ index + 1 }}</span>
          <h3>{{ question.prompt }}</h3>
        </div>

        <GraphBlock
          v-if="question.graph"
          :expression="question.graph?.expression || 'x'"
          :xMin="question.graph?.xMin"
          :xMax="question.graph?.xMax"
          :yMin="question.graph?.yMin"
          :yMax="question.graph?.yMax"
          :color="question.graph?.color"
          :question="graphTitle(question)"
        />

        <LatexFormula
          v-for="expression in question.latex || []"
          :key="`${question.id}-${expression}`"
          :expression="expression"
        />

        <MultipleChoice
          v-if="question.type === 'multiple-choice'"
          :question="question.prompt"
          :options="question.options"
          :correctIndex="multipleChoiceIndex(question.id)"
          @answer="markAnswered(question.id)"
        />

        <NumberAnswer
          v-else-if="question.type === 'number-answer'"
          :question="question.prompt"
          :placeholder="question.placeholder"
          :acceptedAnswers="numberAnswers(question.id)"
          @answer="markAnswered(question.id)"
        />

        <TrueFalseQuestion
          v-else
          :question="question.statement || question.prompt"
          :correctAnswer="trueFalseAnswer(question.id)"
          @answer="markAnswered(question.id)"
        />

        <p v-if="answeredQuestions.has(question.id) && answerKeyFor(question.id)" class="ilc__explanation">
          {{ answerKeyFor(question.id)?.explanation }}
        </p>
      </article>
    </div>

  </div>
</template>

<style scoped>
.ilc {
  display: grid;
  gap: 0.75rem;
  padding: 0.85rem;
  border-radius: 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  min-width: 0;
  overflow: hidden;
}

/* Header */
.ilc__header {
  display: grid;
  gap: 0.45rem;
  min-width: 0;
}

.ilc__eyebrow {
  margin: 0;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.ilc__topic {
  margin: 0;
  font-family: var(--font-heading);
  font-size: clamp(1.3rem, 4vw, 1.75rem);
  line-height: 1.1;
  color: var(--color-text);
}

.ilc__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.ilc__tag {
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.72rem;
}

.ilc__tag--green  { background: var(--color-green-dim);  color: var(--color-green); }
.ilc__tag--blue   { background: var(--color-primary-dim); color: var(--color-primary); }
.ilc__tag--yellow { background: var(--color-yellow-dim); color: var(--color-yellow); }
.ilc__tag--neutral {
  background: var(--color-border);
  color: var(--color-text-muted);
}

.ilc__header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.3rem;
}

.ilc__narration-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: none;
  border-radius: 999px;
  padding: 0.7rem 1.2rem;
  background: var(--color-primary);
  color: #1A1A1A;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: nowrap;
}

.ilc__narration-live {
  color: #1A1A1A;
  font-size: 0.75rem;
  opacity: 0.75;
  animation: ilc-pulse 1.4s ease-in-out infinite;
}

@keyframes ilc-pulse {
  0%, 100% { opacity: 0.75; }
  50% { opacity: 0.3; }
}

.ilc__full-link {
  font-family: var(--font-body);
  font-size: 0.82rem;
  color: var(--color-text-muted);
  text-decoration: none;
  white-space: nowrap;
}

.ilc__full-link:hover {
  color: var(--color-primary);
}

/* Intro */
.ilc__intro {
  margin: 0;
  padding: 0.75rem;
  border-radius: 0.85rem;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  font-family: var(--font-body);
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--color-text-muted);
  word-break: break-word;
  overflow-wrap: break-word;
}

/* Mini-test toggle */
.ilc__test-toggle {
  display: flex;
  align-items: center;
}

.ilc__toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  border: 2px solid var(--color-border);
  border-radius: 999px;
  padding: 0.75rem 1.2rem;
  background: transparent;
  color: var(--color-text);
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: border-color 0.15s;
}

.ilc__toggle-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.ilc__badge {
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: var(--color-primary-dim);
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: 700;
}

/* Mini-test questions */
.ilc__mini-test {
  display: grid;
  gap: 0.85rem;
}

.ilc__question {
  padding: 1rem;
  border-radius: 1.1rem;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  display: grid;
  gap: 0.85rem;
}

.ilc__question-title {
  display: grid;
  gap: 0.3rem;
}

.ilc__question-num {
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.ilc__question-title h3 {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 1rem;
  line-height: 1.5;
  color: var(--color-text);
}

.ilc__explanation {
  margin: 0;
  font-family: var(--font-body);
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--color-text-muted);
}
</style>
