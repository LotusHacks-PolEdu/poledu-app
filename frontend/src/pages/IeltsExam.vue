<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import MultipleChoice from '../components/MultipleChoice.vue'
import ShortAnswer from '../components/ShortAnswer.vue'
import SpeakingTask from '../components/SpeakingTask.vue'
import TrueFalseNotGiven from '../components/TrueFalseNotGiven.vue'
import WritingTask from '../components/WritingTask.vue'
import YesNoNotGiven from '../components/YesNoNotGiven.vue'
import { fetchTestPayload, fetchTestStatus, toApiUrl } from '../lib/poledu-api'
import bundledSample from '../data/ielts_test.json'
import type { IeltsTest, TestStatusResponse } from '../types/ielts'

const route = useRoute()

const testData = ref<IeltsTest | null>(null)
const testStatus = ref<TestStatusResponse | null>(null)
const error = ref<string | null>(null)
const info = ref<string | null>(null)
const loading = ref(false)
const activeSection = ref<'listening' | 'reading' | 'writing' | 'speaking'>('listening')
const sourceLabel = ref('Bundled sample')
const backendCodeInput = ref('')
const audioErrors = ref<Record<number, boolean>>({})

const queryNameCode = computed(() =>
  typeof route.query.name_code === 'string' ? route.query.name_code.trim() : '',
)

const sections = [
  { key: 'listening' as const, label: 'Listening' },
  { key: 'reading' as const, label: 'Reading' },
  { key: 'writing' as const, label: 'Writing' },
  { key: 'speaking' as const, label: 'Speaking' },
]

function answerToIndex(answer: string, options: string[]): number {
  if (/^[A-Z]$/.test(answer)) {
    return answer.charCodeAt(0) - 65
  }

  const romanNumeralMatch = options.findIndex((option) =>
    option.trim().toLowerCase().startsWith(`${answer.trim().toLowerCase()}.`),
  )
  if (romanNumeralMatch >= 0) {
    return romanNumeralMatch
  }

  const directMatch = options.findIndex((option) => option.trim().toLowerCase() === answer.trim().toLowerCase())
  return directMatch >= 0 ? directMatch : 0
}

function mapTFNG(answer: string): 'true' | 'false' | 'not-given' {
  const normalized = answer.toUpperCase()
  if (normalized === 'TRUE') return 'true'
  if (normalized === 'FALSE') return 'false'
  return 'not-given'
}

function mapYNNG(answer: string): 'yes' | 'no' | 'not-given' {
  const normalized = answer.toUpperCase()
  if (normalized === 'YES') return 'yes'
  if (normalized === 'NO') return 'no'
  return 'not-given'
}

function resetMessages(): void {
  error.value = null
  info.value = null
  audioErrors.value = {}
}

function setTestPayload(payload: IeltsTest, nextSourceLabel: string): void {
  testData.value = payload
  sourceLabel.value = nextSourceLabel
  activeSection.value = 'listening'
  audioErrors.value = {}
}

function getAudioUrl(partNumber: number): string {
  const remoteAudio = testStatus.value?.audio_urls.find((url) => url.endsWith(`/${partNumber}.mp3`))
  if (remoteAudio) {
    return toApiUrl(remoteAudio)
  }

  return `/${partNumber}.mp3`
}

function markAudioError(partNumber: number): void {
  audioErrors.value = {
    ...audioErrors.value,
    [partNumber]: true,
  }
}

function clearAudioError(partNumber: number): void {
  if (!audioErrors.value[partNumber]) {
    return
  }

  const nextErrors = { ...audioErrors.value }
  delete nextErrors[partNumber]
  audioErrors.value = nextErrors
}

async function loadBundledSample(): Promise<void> {
  resetMessages()
  testStatus.value = null
  setTestPayload(bundledSample as IeltsTest, 'Bundled sample')
  info.value = 'Loaded the bundled IELTS sample. Listening audio falls back to files in /public when available.'
}

async function loadFromFile(): Promise<void> {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) {
      return
    }

    resetMessages()
    testStatus.value = null

    try {
      const text = await file.text()
      setTestPayload(JSON.parse(text) as IeltsTest, `Local file: ${file.name}`)
    } catch (parseError) {
      error.value = parseError instanceof Error ? parseError.message : 'Failed to parse the selected JSON file.'
    }
  }
  input.click()
}

async function loadBackendTest(nameCode: string): Promise<void> {
  const trimmedCode = nameCode.trim()
  if (!trimmedCode) {
    error.value = 'Enter a generated test code first.'
    return
  }

  loading.value = true
  resetMessages()

  try {
    const status = await fetchTestStatus(trimmedCode)
    testStatus.value = status

    if (!status.test_json_exists) {
      info.value = `Test ${trimmedCode.toUpperCase()} is still ${status.state}. Open it again once generation is complete.`
      testData.value = null
      return
    }

    const payload = await fetchTestPayload(trimmedCode)
    setTestPayload(payload, `Backend test: ${trimmedCode.toUpperCase()}`)

    if (status.audio_files.length) {
      info.value = `Loaded ${status.audio_files.length} listening audio file(s) from the backend.`
    } else {
      info.value = 'Loaded the backend test, but no listening MP3 files were published for it.'
    }
  } catch (loadError) {
    testData.value = null
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load the backend test.'
  } finally {
    loading.value = false
  }
}

watch(
  queryNameCode,
  async (nameCode) => {
    backendCodeInput.value = nameCode
    if (nameCode) {
      await loadBackendTest(nameCode)
      return
    }

    if (!testData.value) {
      await loadBundledSample()
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="exam-page">
    <div class="exam-header">
      <div>
        <router-link to="/chat" class="back-link">Back to chat</router-link>
        <h1>{{ testData?.test_title ?? 'IELTS Exam' }}</h1>
        <p class="source-label">Source: {{ sourceLabel }}</p>
      </div>

      <div class="loader-panel">
        <button class="utility-button" type="button" @click="loadBundledSample">Bundled sample</button>
        <button class="utility-button" type="button" @click="loadFromFile">Open JSON</button>
        <div class="backend-loader">
          <input
            v-model="backendCodeInput"
            type="text"
            placeholder="Generated code"
            class="backend-input"
          />
          <button class="utility-button primary" type="button" :disabled="loading" @click="loadBackendTest(backendCodeInput)">
            {{ loading ? 'Loading...' : 'Load backend test' }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="info" class="info-banner">{{ info }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <template v-if="testData">
      <div v-if="testStatus" class="status-strip">
        <span class="status-pill">{{ testStatus.state }}</span>
        <span>{{ testStatus.audio_files.length }} audio file(s)</span>
        <span>{{ testStatus.logs.length }} log entries</span>
      </div>

      <nav class="section-tabs">
        <button
          v-for="section in sections"
          :key="section.key"
          class="tab"
          :class="{ active: activeSection === section.key }"
          type="button"
          @click="activeSection = section.key"
        >
          {{ section.label }}
        </button>
      </nav>

      <div v-if="activeSection === 'listening'" class="section-body">
        <div
          v-for="part in testData.listening.parts"
          :key="part.part_number"
          class="part-block"
        >
          <div class="part-header">
            <div>
              <h2>Part {{ part.part_number }}</h2>
              <p class="context">{{ part.context }}</p>
            </div>
            <div class="audio-panel">
              <audio
                class="audio-player"
                controls
                preload="none"
                :src="getAudioUrl(part.part_number)"
                @canplay="clearAudioError(part.part_number)"
                @error="markAudioError(part.part_number)"
              />
              <p class="audio-caption">
                Source:
                <span>{{ getAudioUrl(part.part_number) }}</span>
              </p>
              <p v-if="audioErrors[part.part_number]" class="audio-warning">
                This listening file could not be loaded from the current source.
              </p>
            </div>
          </div>

          <details class="script-toggle">
            <summary>Show audio script</summary>
            <pre class="audio-script">{{ part.audio_script }}</pre>
          </details>

          <div
            v-for="questionSet in part.question_sets"
            :key="`${part.part_number}-${questionSet.questions_range}`"
            class="question-set"
          >
            <p class="qs-instruction">
              <strong>Questions {{ questionSet.questions_range }}:</strong>
              {{ questionSet.instruction }}
            </p>

            <div
              v-for="question in questionSet.questions"
              :key="question.question_number"
              class="question-item"
            >
              <span class="q-num">Q{{ question.question_number }}.</span>

              <ShortAnswer
                v-if="!question.options && ['fill_in_the_blanks', 'short_answer', 'summary_completion'].includes(questionSet.question_type)"
                :question="question.question_text"
                :acceptedAnswers="[question.answer]"
              />

              <MultipleChoice
                v-else-if="question.options"
                :question="question.question_text"
                :options="question.options"
                :correctIndex="answerToIndex(question.answer, question.options)"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeSection === 'reading'" class="section-body">
        <div
          v-for="passage in testData.reading.passages"
          :key="passage.passage_number"
          class="part-block"
        >
          <h2>Passage {{ passage.passage_number }}: {{ passage.title }}</h2>
          <details class="passage-toggle" open>
            <summary>Reading passage</summary>
            <div class="passage-content">{{ passage.content }}</div>
          </details>

          <div
            v-for="questionSet in passage.question_sets"
            :key="`${passage.passage_number}-${questionSet.questions_range}`"
            class="question-set"
          >
            <p class="qs-instruction">
              <strong>Questions {{ questionSet.questions_range }}:</strong>
              {{ questionSet.instruction }}
            </p>

            <div
              v-for="question in questionSet.questions"
              :key="question.question_number"
              class="question-item"
            >
              <span class="q-num">Q{{ question.question_number }}.</span>

              <TrueFalseNotGiven
                v-if="questionSet.question_type === 'true_false_not_given'"
                :statement="question.question_text"
                :correctAnswer="mapTFNG(question.answer)"
              />

              <YesNoNotGiven
                v-else-if="questionSet.question_type === 'yes_no_not_given'"
                :statement="question.question_text"
                :correctAnswer="mapYNNG(question.answer)"
              />

              <ShortAnswer
                v-else-if="!question.options"
                :question="question.question_text"
                :acceptedAnswers="[question.answer]"
              />

              <MultipleChoice
                v-else
                :question="question.question_text"
                :options="question.options"
                :correctIndex="answerToIndex(question.answer, question.options)"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeSection === 'writing'" class="section-body">
        <WritingTask
          v-for="task in testData.writing.tasks"
          :key="task.task_number"
          :taskNumber="task.task_number"
          :instruction="task.instruction"
          :prompt="task.prompt"
          :dataDescription="task.data_description"
        />
      </div>

      <div v-if="activeSection === 'speaking'" class="section-body">
        <SpeakingTask
          partLabel="Part 1"
          :topic="testData.speaking.part_1.topic"
          :questions="testData.speaking.part_1.questions"
        />
        <SpeakingTask
          partLabel="Part 2"
          :topic="testData.speaking.part_2.cue_card_topic ?? testData.speaking.part_2.topic"
          :cueCardTopic="testData.speaking.part_2.cue_card_topic"
          :bulletPoints="testData.speaking.part_2.bullet_points"
          :instruction="testData.speaking.part_2.instruction"
        />
        <SpeakingTask
          partLabel="Part 3"
          :topic="testData.speaking.part_3.topic"
          :questions="testData.speaking.part_3.questions"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.exam-page {
  width: 100%;
  margin: 0;
  padding: clamp(1rem, 2vw, 2rem) clamp(1rem, 3vw, 2.5rem) 4rem;
  font-family: Inter, 'Segoe UI', system-ui, sans-serif;
  color: #e5e7eb;
  background:
    radial-gradient(circle at top left, rgba(16, 185, 129, 0.12), transparent 28rem),
    linear-gradient(180deg, #0f172a 0%, #111827 55%, #0b1120 100%);
  min-height: 100dvh;
  box-sizing: border-box;
}

.exam-header {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.exam-header h1 {
  margin: 0.3rem 0 0.35rem;
  font-size: clamp(2rem, 5vw, 2.8rem);
}

.back-link {
  color: #86efac;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.source-label {
  margin: 0;
  color: #94a3b8;
}

.loader-panel {
  display: grid;
  gap: 0.75rem;
  min-width: min(28rem, 100%);
}

.backend-loader {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
}

.backend-input,
.utility-button {
  border-radius: 0.9rem;
}

.backend-input {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.65);
  color: #f8fafc;
  padding: 0.85rem 1rem;
}

.utility-button {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.06);
  color: #f8fafc;
  padding: 0.85rem 1rem;
  cursor: pointer;
}

.utility-button.primary {
  background: linear-gradient(135deg, #16a34a, #22c55e);
  border-color: transparent;
}

.utility-button:hover {
  background: rgba(255, 255, 255, 0.12);
}

.utility-button.primary:hover {
  background: linear-gradient(135deg, #15803d, #16a34a);
}

.utility-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.info-banner,
.error-banner,
.status-strip,
.qs-instruction,
.audio-panel,
.part-block,
.script-toggle,
.passage-toggle {
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.info-banner,
.error-banner {
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  margin-bottom: 1rem;
}

.info-banner {
  background: rgba(59, 130, 246, 0.12);
  color: #bfdbfe;
}

.error-banner {
  background: rgba(220, 38, 38, 0.14);
  color: #fecaca;
}

.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  margin-bottom: 1.5rem;
  background: rgba(15, 23, 42, 0.45);
  color: #cbd5e1;
}

.status-pill {
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.15);
  color: #86efac;
  text-transform: capitalize;
}

.section-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.section-body {
  width: 100%;
}

.tab {
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  padding: 0.8rem 1.1rem;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.tab.active {
  background: linear-gradient(135deg, #16a34a, #22c55e);
  color: #f8fafc;
}

.part-block {
  margin-bottom: 2rem;
  border-radius: 1.35rem;
  padding: 1.35rem;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(10px);
}

.part-header {
  display: flex;
  justify-content: space-between;
  gap: 1.25rem;
  align-items: flex-start;
}

.part-block h2 {
  margin: 0 0 0.45rem;
}

.context {
  margin: 0;
  color: #cbd5e1;
  line-height: 1.6;
}

.audio-panel {
  width: min(24rem, 100%);
  border-radius: 1rem;
  padding: 0.9rem;
  background: rgba(2, 6, 23, 0.42);
}

.audio-player {
  width: 100%;
}

.audio-caption,
.audio-warning {
  margin: 0.75rem 0 0;
  font-size: 0.9rem;
}

.audio-caption span {
  color: #86efac;
  word-break: break-all;
}

.audio-warning {
  color: #fecaca;
}

.script-toggle,
.passage-toggle {
  margin-top: 1rem;
  border-radius: 1rem;
  background: rgba(2, 6, 23, 0.35);
  padding: 0.9rem 1rem;
}

.script-toggle summary,
.passage-toggle summary {
  cursor: pointer;
  color: #93c5fd;
  font-weight: 600;
}

.audio-script,
.passage-content {
  white-space: pre-wrap;
  line-height: 1.75;
  color: #e2e8f0;
}

.audio-script {
  margin: 1rem 0 0;
}

.passage-content {
  margin-top: 1rem;
}

.question-set {
  margin-top: 1.25rem;
}

.qs-instruction {
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  margin-bottom: 1rem;
  background: rgba(37, 99, 235, 0.14);
  color: #dbeafe;
}

.question-item {
  margin-bottom: 0.75rem;
}

.q-num {
  display: inline-block;
  margin-bottom: 0.45rem;
  color: #86efac;
  font-weight: 700;
}

.section-body :deep(.mc-block),
.section-body :deep(.sa-block),
.section-body :deep(.tfng-block),
.section-body :deep(.ynng-block),
.section-body :deep(.wt-block),
.section-body :deep(.st-block) {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 1rem;
  color: #f8fafc;
}

.section-body :deep(button) {
  border: none;
  border-radius: 0.75rem;
  background: #16a34a;
  color: #ffffff;
  padding: 0.65rem 0.95rem;
  cursor: pointer;
}

.section-body :deep(input),
.section-body :deep(textarea) {
  background: rgba(15, 23, 42, 0.65);
  color: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 0.75rem;
}

@media (max-width: 900px) {
  .exam-header,
  .part-header {
    flex-direction: column;
  }

  .loader-panel,
  .audio-panel {
    min-width: 0;
    width: 100%;
  }

  .backend-loader {
    grid-template-columns: 1fr;
  }
}
</style>
