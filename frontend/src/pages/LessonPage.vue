<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import {
  fetchLessonPayload,
  fetchLessonStatus,
} from '../lib/poledu-api'
import type {
  LessonAnswerKeyItem,
  LessonQuestion,
  LessonStatusResponse,
  MathLessonPayload,
} from '../types/lessons'
import GraphBlock from '../components/GraphBlock.vue'
import LatexFormula from '../components/LatexFormula.vue'
import LessonBlockRenderer from '../components/LessonBlockRenderer.vue'
import MultipleChoice from '../components/MultipleChoice.vue'
import NumberAnswer from '../components/NumberAnswer.vue'
import TrueFalseQuestion from '../components/TrueFalseQuestion.vue'

const route = useRoute()

const lesson = ref<MathLessonPayload | null>(null)
const status = ref<LessonStatusResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const info = ref<string | null>(null)

let pollTimer: number | null = null

const lessonCode = computed(() => String(route.params.lessonCode || '').trim())

const answerKeyMap = computed(() => {
  const map = new Map<string, LessonAnswerKeyItem>()
  for (const entry of lesson.value?.answer_key || []) {
    map.set(entry.question_id, entry)
  }
  return map
})

const questionMap = computed(() => {
  const map = new Map<string, LessonQuestion>()
  for (const question of lesson.value?.mini_test || []) {
    map.set(question.id, question)
  }
  return map
})

function stopPolling(): void {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function isTerminalState(state: string | undefined): boolean {
  return state === 'completed' || state === 'failed'
}

async function refreshStatus(code: string): Promise<void> {
  status.value = await fetchLessonStatus(code)
  if (status.value.lesson_json_exists && !lesson.value) {
    lesson.value = await fetchLessonPayload(code)
    info.value = null
  }
  if (isTerminalState(status.value.state)) {
    stopPolling()
  }
}

async function loadLesson(code: string): Promise<void> {
  if (!code) {
    lesson.value = null
    status.value = null
    return
  }

  loading.value = true
  error.value = null
  info.value = null

  try {
    await refreshStatus(code)
    if (!status.value?.lesson_json_exists) {
      lesson.value = null
      info.value = `Lesson ${code.toUpperCase()} is still ${status.value?.state || 'processing'}.`
      return
    }

    lesson.value = await fetchLessonPayload(code)
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load the lesson.'
    lesson.value = null
  } finally {
    loading.value = false
  }
}

function startPolling(code: string): void {
  stopPolling()
  pollTimer = window.setInterval(() => {
    void refreshStatus(code).catch((pollError) => {
      error.value = pollError instanceof Error ? pollError.message : 'Unable to refresh lesson status.'
      stopPolling()
    })
  }, 4000)
}

function answerKeyFor(questionId: string): LessonAnswerKeyItem | undefined {
  return answerKeyMap.value.get(questionId)
}

function answerSummary(answer: LessonAnswerKeyItem): string {
  const question = questionMap.value.get(answer.question_id)

  if ('correct_option_index' in answer) {
    if (question?.type === 'multiple-choice') {
      return question.options[answer.correct_option_index] || `Option ${answer.correct_option_index + 1}`
    }
    return `Option ${answer.correct_option_index + 1}`
  }

  if ('accepted_answers' in answer) {
    return answer.accepted_answers.join(', ')
  }

  if ('correct_answer' in answer) {
    return answer.correct_answer ? 'True' : 'False'
  }

  return ''
}

function graphTitle(question: LessonQuestion): string {
  return question.type === 'true-false' && question.statement ? question.statement : question.prompt
}

function multipleChoiceIndex(questionId: string): number | undefined {
  const key = answerKeyFor(questionId)
  if (key && 'correct_option_index' in key) {
    return key.correct_option_index
  }
  return undefined
}

function numberAnswers(questionId: string): string[] | undefined {
  const key = answerKeyFor(questionId)
  if (key && 'accepted_answers' in key) {
    return key.accepted_answers
  }
  return undefined
}

function trueFalseAnswer(questionId: string): boolean | undefined {
  const key = answerKeyFor(questionId)
  if (key && 'correct_answer' in key) {
    return key.correct_answer
  }
  return undefined
}

const isNarrating = ref(false)

function toggleNarration(): void {
  if (isNarrating.value) {
    window.speechSynthesis.cancel()
    isNarrating.value = false
    return
  }
  const script = lesson.value?.narration_script
  if (!script) return
  const utterance = new SpeechSynthesisUtterance(script)
  utterance.onend = () => { isNarrating.value = false }
  utterance.onerror = () => { isNarrating.value = false }
  window.speechSynthesis.speak(utterance)
  isNarrating.value = true
}

watch(
  lessonCode,
  async (code) => {
    stopPolling()
    await loadLesson(code)
    if (code && status.value && !isTerminalState(status.value.state)) {
      startPolling(code)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopPolling()
  window.speechSynthesis.cancel()
})
</script>

<template>
  <div class="lesson-page">
    <header class="lesson-page__header">
      <div>
        <RouterLink class="lesson-page__back" :to="{ name: 'chat' }">Back to tutor</RouterLink>
        <p class="lesson-page__eyebrow">Personalized math lesson</p>
        <h1>{{ lesson?.topic || status?.topic || 'Math lesson' }}</h1>
        <p class="lesson-page__introline">
          {{ lesson?.learner_profile.display_name || 'Learner' }} ·
          {{ lesson?.subject || status?.subject || 'math' }}
        </p>
      </div>

      <div class="lesson-page__meta">
        <div class="lesson-page__meta-card">
          <span>Lesson code</span>
          <strong>{{ lessonCode.toUpperCase() }}</strong>
        </div>
        <div class="lesson-page__meta-card">
          <span>Status</span>
          <strong>{{ status?.state || (loading ? 'loading' : 'unknown') }}</strong>
        </div>
      </div>
    </header>

    <p v-if="info" class="lesson-page__info">{{ info }}</p>
    <p v-if="error" class="lesson-page__error">{{ error }}</p>

    <div v-if="status?.logs?.length" class="lesson-page__logs">
      <div v-for="log in status.logs.slice(-4)" :key="`${log.timestamp}-${log.message}`" class="lesson-page__log">
        <strong>{{ log.state }}</strong>
        <span>{{ log.message }}</span>
      </div>
    </div>

    <template v-if="lesson">
      <section class="lesson-hero">
        <div class="lesson-hero__copy">
          <h2>Small, digestible overview</h2>
          <p>{{ lesson.intro }}</p>
        </div>

        <div class="lesson-hero__profile">
          <p><strong>Learning by doing:</strong> {{ lesson.learner_profile.learning_by_doing ? 'Yes' : 'No' }}</p>
          <p><strong>Learning by listening:</strong> {{ lesson.learner_profile.learning_by_listening ? 'Yes' : 'No' }}</p>
          <p><strong>Learning by reading:</strong> {{ lesson.learner_profile.learning_by_reading ? 'Yes' : 'No' }}</p>
          <p><strong>Hobbies:</strong> {{ lesson.learner_profile.hobbies.join(', ') || 'Not provided' }}</p>
          <p><strong>Favorite food:</strong> {{ lesson.learner_profile.favorite_food || 'Not provided' }}</p>
        </div>
      </section>

      <LessonBlockRenderer
        v-for="section in lesson.sections"
        :key="section.id"
        :section="section"
      />

      <section class="lesson-mini-test">
        <header class="lesson-mini-test__header">
          <div>
            <p class="lesson-page__eyebrow">Mini test</p>
            <h2>Check your understanding</h2>
          </div>
          <span>10 questions</span>
        </header>

        <div class="lesson-mini-test__list">
          <article
            v-for="(question, index) in lesson.mini_test"
            :key="question.id"
            class="lesson-mini-test__item"
          >
            <div class="lesson-mini-test__title">
              <span>Q{{ index + 1 }}</span>
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
            />

            <NumberAnswer
              v-else-if="question.type === 'number-answer'"
              :question="question.prompt"
              :placeholder="question.placeholder"
              :acceptedAnswers="numberAnswers(question.id)"
            />

            <TrueFalseQuestion
              v-else
              :question="question.statement || question.prompt"
              :correctAnswer="trueFalseAnswer(question.id)"
            />

            <p v-if="answerKeyFor(question.id)" class="lesson-mini-test__explanation">
              {{ answerKeyFor(question.id)?.explanation }}
            </p>
          </article>
        </div>
      </section>

      <section v-if="lesson.narration_script" class="lesson-narration">
        <p class="lesson-page__eyebrow">Audio narration</p>
        <h2>Listen to the lesson</h2>
        <p class="lesson-narration__hint">This lesson was designed for listening. Press play to hear it read aloud.</p>
        <div class="lesson-narration__controls">
          <button type="button" class="lesson-narration__play-btn" @click="toggleNarration">
            {{ isNarrating ? '⏹ Stop' : '▶ Play narration' }}
          </button>
          <span v-if="isNarrating" class="lesson-narration__status">Speaking...</span>
        </div>
      </section>

      <details class="lesson-page__details">
        <summary>Answer key</summary>
        <div class="lesson-page__answer-key">
          <article
            v-for="answer in lesson.answer_key"
            :key="answer.question_id"
            class="lesson-page__answer-item"
          >
            <strong>{{ answer.question_id.toUpperCase() }}</strong>
            <p class="lesson-page__answer-summary">Answer: {{ answerSummary(answer) }}</p>
            <p>{{ answer.explanation }}</p>
          </article>
        </div>
      </details>

      <section class="lesson-sources">
        <header>
          <p class="lesson-page__eyebrow">Research packet</p>
          <h2>Sources used to shape the lesson</h2>
        </header>

        <article
          v-for="source in lesson.research_sources"
          :key="source.url"
          class="lesson-sources__item"
        >
          <p class="lesson-sources__query">{{ source.query }}</p>
          <a :href="source.url" target="_blank" rel="noreferrer">{{ source.title }}</a>
          <p>{{ source.snippet }}</p>
        </article>
      </section>
    </template>
  </div>
</template>

<style scoped>
.lesson-page {
  min-height: 100dvh;
  padding: clamp(1rem, 2vw, 2rem);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-body);
}

.lesson-page__header,
.lesson-hero,
.lesson-mini-test,
.lesson-sources,
.lesson-page__details,
.lesson-page__logs {
  max-width: 1100px;
  margin: 0 auto 1.5rem;
}

.lesson-page__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.lesson-page__back {
  color: var(--color-primary);
  text-decoration: none;
}

.lesson-page__eyebrow {
  margin: 0.45rem 0 0.3rem;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.8rem;
}

.lesson-page__header h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.4rem);
}

.lesson-page__introline {
  margin: 0.4rem 0 0;
  color: var(--color-text-muted);
}

.lesson-page__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.lesson-page__meta-card {
  min-width: 9rem;
  padding: 1rem;
  border-radius: 1.2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.lesson-page__meta-card span {
  display: block;
  margin-bottom: 0.35rem;
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.lesson-page__info,
.lesson-page__error {
  max-width: 1100px;
  margin: 0 auto 1rem;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
}

.lesson-page__info {
  background: var(--color-primary-dim);
  color: var(--color-primary);
}

.lesson-page__error {
  background: rgba(255, 80, 80, 0.15);
  color: #ff6b6b;
}

.lesson-page__logs {
  display: grid;
  gap: 0.65rem;
}

.lesson-page__log {
  display: grid;
  gap: 0.25rem;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.lesson-page__log strong {
  color: var(--color-primary);
  text-transform: uppercase;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
}

.lesson-hero {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 1rem;
}

.lesson-hero__copy,
.lesson-hero__profile {
  padding: 1.25rem;
  border-radius: 1.45rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.lesson-hero__copy h2,
.lesson-mini-test__header h2,
.lesson-sources h2 {
  margin: 0 0 0.6rem;
}

.lesson-hero__copy p,
.lesson-hero__profile p,
.lesson-sources__item p {
  margin: 0;
  line-height: 1.7;
  color: var(--color-text-muted);
}

.lesson-hero__profile {
  display: grid;
  gap: 0.6rem;
}

.lesson-mini-test {
  padding: 1.25rem;
  border-radius: 1.5rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.lesson-mini-test__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.lesson-mini-test__header span {
  padding: 0.45rem 0.7rem;
  border-radius: 999px;
  background: var(--color-primary-dim);
  color: var(--color-primary);
}

.lesson-mini-test__list {
  display: grid;
  gap: 1rem;
}

.lesson-mini-test__item {
  padding: 1rem;
  border-radius: 1.1rem;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
}

.lesson-mini-test__title {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 0.9rem;
}

.lesson-mini-test__title span {
  color: var(--color-primary);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.lesson-mini-test__title h3,
.lesson-sources__item a {
  margin: 0;
}

.lesson-mini-test__explanation {
  margin: 0.85rem 0 0;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.lesson-narration {
  max-width: 1100px;
  margin: 0 auto 1.5rem;
  padding: 1.25rem;
  border-radius: 1.45rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: grid;
  gap: 0.75rem;
}

.lesson-narration h2 {
  margin: 0;
}

.lesson-narration__hint {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.lesson-narration__controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.lesson-narration__play-btn {
  padding: 0.8rem 1.4rem;
  border: none;
  border-radius: 0.95rem;
  background: var(--color-primary);
  color: #1A1A1A;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
}

.lesson-narration__status {
  color: var(--color-primary);
  font-size: 0.9rem;
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

.lesson-page__details {
  padding: 1rem 1.1rem;
  border-radius: 1.2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.lesson-page__details summary {
  cursor: pointer;
  color: var(--color-primary);
  font-weight: 700;
}

.lesson-page__details pre {
  margin: 1rem 0 0;
  white-space: pre-wrap;
  line-height: 1.7;
  color: var(--color-text-muted);
}

.lesson-page__answer-key {
  display: grid;
  gap: 0.85rem;
  margin-top: 1rem;
}

.lesson-page__answer-item {
  padding: 0.95rem;
  border-radius: 1rem;
  background: var(--color-surface-2);
}

.lesson-page__answer-item p {
  margin: 0.45rem 0 0;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.lesson-page__answer-summary {
  color: var(--color-primary);
}

.lesson-sources {
  display: grid;
  gap: 1rem;
}

.lesson-sources__item {
  padding: 1rem 1.05rem;
  border-radius: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.lesson-sources__query {
  color: var(--color-primary);
  font-size: 0.85rem;
}

.lesson-sources__item a {
  color: var(--color-primary);
}

@media (max-width: 900px) {
  .lesson-page__header,
  .lesson-hero,
  .lesson-mini-test__header {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .lesson-page__meta {
    width: 100%;
  }
}
</style>
