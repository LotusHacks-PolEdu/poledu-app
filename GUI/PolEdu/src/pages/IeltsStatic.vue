<script setup lang="ts">
import ShortAnswer from '../components/ShortAnswer.vue'
import MultipleChoice from '../components/MultipleChoice.vue'
import TrueFalseNotGiven from '../components/TrueFalseNotGiven.vue'
import YesNoNotGiven from '../components/YesNoNotGiven.vue'
import WritingTask from '../components/WritingTask.vue'
import SpeakingTask from '../components/SpeakingTask.vue'
import testJson from '../data/ielts_test.json'
import { ref } from 'vue'

// --- types matching the JSON shape ---
interface Question {
  question_number: number
  question_text: string
  options: string[] | null
  answer: string
}
interface QuestionSet {
  questions_range: string
  question_type: string
  instruction: string
  questions: Question[]
}
interface ListeningPart {
  part_number: number
  context: string
  audio_script: string
  question_sets: QuestionSet[]
}
interface ReadingPassage {
  passage_number: number
  title: string
  content: string
  question_sets: QuestionSet[]
}
interface WritingTaskData {
  task_number: number
  instruction: string
  prompt?: string
  data_description?: string
}
interface SpeakingPart {
  topic: string
  questions?: string[]
  cue_card_topic?: string
  bullet_points?: string[]
  instruction?: string
}
interface IeltsTest {
  test_title: string
  listening: { parts: ListeningPart[] }
  reading: { passages: ReadingPassage[] }
  writing: { tasks: WritingTaskData[] }
  speaking: {
    part_1: SpeakingPart
    part_2: SpeakingPart
    part_3: SpeakingPart
  }
}

const testData = testJson as unknown as IeltsTest
const activeSection = ref<'listening' | 'reading' | 'writing' | 'speaking'>('listening')

// Track which parts failed to load audio (key = part_number)
const audioFailed = ref<Record<number, boolean>>({})
function onAudioError(partNumber: number) {
  audioFailed.value[partNumber] = true
}

function answerToIndex(answer: string, options: string[]): number {
  if (/^[A-Z]$/.test(answer)) {
    return answer.charCodeAt(0) - 65
  }
  const idx = options.findIndex(
    (o) =>
      o.trim().toLowerCase() === answer.trim().toLowerCase() ||
      o.startsWith(answer + '.') ||
      o.startsWith(answer + ' '),
  )
  return idx >= 0 ? idx : 0
}

function mapTFNG(answer: string): 'true' | 'false' | 'not-given' {
  const a = answer.toUpperCase()
  if (a === 'TRUE') return 'true'
  if (a === 'FALSE') return 'false'
  return 'not-given'
}

function mapYNNG(answer: string): 'yes' | 'no' | 'not-given' {
  const a = answer.toUpperCase()
  if (a === 'YES') return 'yes'
  if (a === 'NO') return 'no'
  return 'not-given'
}

const sections = [
  { key: 'listening' as const, label: '🎧 Listening' },
  { key: 'reading' as const, label: '📖 Reading' },
  { key: 'writing' as const, label: '✏️ Writing' },
  { key: 'speaking' as const, label: '🗣️ Speaking' },
]
</script>

<template>
  <div class="exam-page">
    <div class="exam-header">
      <router-link to="/" class="back-link">← Home</router-link>
      <h1>{{ testData.test_title }}</h1>
    </div>

    <!-- Section tabs -->
    <nav class="section-tabs">
      <button
        v-for="s in sections"
        :key="s.key"
        :class="['tab', { active: activeSection === s.key }]"
        @click="activeSection = s.key"
      >
        {{ s.label }}
      </button>
    </nav>

    <!-- ═══════ LISTENING ═══════ -->
    <div v-if="activeSection === 'listening'" class="section-body">
      <div v-for="part in testData.listening.parts" :key="part.part_number" class="part-block">
        <h2>Part {{ part.part_number }}</h2>
        <p class="context"><em>{{ part.context }}</em></p>

        <!-- Audio player: tries /1.mp3, /2.mp3, etc. -->
        <div v-if="!audioFailed[part.part_number]" class="audio-player">
          <audio controls :src="'/' + part.part_number + '.mp3'" @error="onAudioError(part.part_number)" style="width:100%"></audio>
        </div>

        <!-- Fallback: transcript (shown if no mp3 found) -->
        <details v-else class="script-toggle">
          <summary>Show Audio Script</summary>
          <pre class="audio-script">{{ part.audio_script }}</pre>
        </details>

        <div v-for="qs in part.question_sets" :key="qs.questions_range" class="question-set">
          <p class="qs-instruction"><strong>Questions {{ qs.questions_range }}:</strong> {{ qs.instruction }}</p>

          <div v-for="q in qs.questions" :key="q.question_number" class="question-item">
            <span class="q-num">Q{{ q.question_number }}.</span>

            <ShortAnswer
              v-if="!q.options && ['fill_in_the_blanks','short_answer','summary_completion'].includes(qs.question_type)"
              :question="q.question_text"
              :acceptedAnswers="[q.answer]"
            />

            <MultipleChoice
              v-else-if="q.options"
              :question="q.question_text"
              :options="q.options"
              :correctIndex="answerToIndex(q.answer, q.options)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════ READING ═══════ -->
    <div v-if="activeSection === 'reading'" class="section-body">
      <div v-for="passage in testData.reading.passages" :key="passage.passage_number" class="part-block">
        <h2>Passage {{ passage.passage_number }}: {{ passage.title }}</h2>
        <details class="passage-toggle" open>
          <summary>Reading Passage</summary>
          <div class="passage-content">{{ passage.content }}</div>
        </details>

        <div v-for="qs in passage.question_sets" :key="qs.questions_range" class="question-set">
          <p class="qs-instruction"><strong>Questions {{ qs.questions_range }}:</strong> {{ qs.instruction }}</p>

          <div v-for="q in qs.questions" :key="q.question_number" class="question-item">
            <span class="q-num">Q{{ q.question_number }}.</span>

            <TrueFalseNotGiven
              v-if="qs.question_type === 'true_false_not_given'"
              :statement="q.question_text"
              :correctAnswer="mapTFNG(q.answer)"
            />

            <YesNoNotGiven
              v-else-if="qs.question_type === 'yes_no_not_given'"
              :statement="q.question_text"
              :correctAnswer="mapYNNG(q.answer)"
            />

            <ShortAnswer
              v-else-if="!q.options"
              :question="q.question_text"
              :acceptedAnswers="[q.answer]"
            />

            <MultipleChoice
              v-else
              :question="q.question_text"
              :options="q.options"
              :correctIndex="answerToIndex(q.answer, q.options)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════ WRITING ═══════ -->
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

    <!-- ═══════ SPEAKING ═══════ -->
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
  </div>
</template>

<style scoped>
.exam-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}
.exam-header { margin-bottom: 24px; }
.back-link {
  display: inline-block;
  margin-bottom: 12px;
  color: #2563eb;
  text-decoration: none;
}
.back-link:hover { text-decoration: underline; }

/* Section tabs */
.section-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 2px solid #e5e7eb;
}
.tab {
  padding: 10px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.2s, border-color 0.2s;
}
.tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}
.tab:hover { color: #111; }

/* Parts */
.part-block {
  margin-bottom: 48px;
  padding-bottom: 32px;
  border-bottom: 1px solid #e5e7eb;
}
.context { color: #555; margin-bottom: 12px; }

/* Audio script */
.script-toggle { margin-bottom: 16px; }
.script-toggle summary {
  cursor: pointer;
  font-weight: 600;
  color: #2563eb;
  margin-bottom: 8px;
}
.audio-script {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}

/* Reading passage */
.passage-toggle { margin-bottom: 16px; }
.passage-toggle summary {
  cursor: pointer;
  font-weight: 600;
  color: #2563eb;
  margin-bottom: 8px;
}
.passage-content {
  background: #f9fafb;
  padding: 20px;
  border-radius: 8px;
  white-space: pre-wrap;
  font-size: 15px;
  line-height: 1.7;
  max-height: 500px;
  overflow-y: auto;
}

/* Question sets */
.question-set { margin-top: 20px; margin-bottom: 24px; }
.qs-instruction {
  background: #eef2ff;
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
}
.question-item { margin-bottom: 8px; }
.q-num {
  font-weight: 700;
  color: #2563eb;
  margin-right: 4px;
}

.section-body {
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
