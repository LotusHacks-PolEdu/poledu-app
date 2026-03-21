<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import logoUrl from '../assets/logo.png'
import OnboardingWizard from '../components/OnboardingWizard.vue'
import {
  createLearnerProfile,
  fetchLearnerProfile,
  fetchLessonStatus,
  fetchTestStatus,
  sendAssistantMessage,
} from '../lib/poledu-api'
import type { TestStatusResponse } from '../types/ielts'
import type {
  LearnerOnboardRequest,
  LearnerProfile,
  LessonStatusResponse,
} from '../types/lessons'

type MessageRole = 'user' | 'assistant'
type JobType = 'lesson' | 'ielts' | null

interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: string
}

const route = useRoute()
const router = useRouter()

const LEARNER_STORAGE_KEY = 'poledu-learner-profile'

const messages = ref<ChatMessage[]>([])
const input = ref('')
const busy = ref(false)
const onboardingBusy = ref(false)
const onboardingError = ref<string | null>(null)
const jobError = ref<string | null>(null)
const learnerProfile = ref<LearnerProfile | null>(null)
const showOnboarding = ref(false)

const latestJobType = ref<JobType>(null)
const latestLessonCode = ref<string | null>(null)
const latestLessonStatus = ref<LessonStatusResponse | null>(null)
const latestTestCode = ref<string | null>(null)
const latestTestStatus = ref<TestStatusResponse | null>(null)

const messageViewport = ref<HTMLElement | null>(null)

let pollTimer: number | null = null
const autoOpenJobKey = ref<string | null>(null)
const announcedJobs = new Set<string>()

const entryMode = computed(() => (route.query.entry === 'ielts' ? 'ielts' : 'tutor'))

const suggestions = computed(() =>
  entryMode.value === 'ielts'
    ? [
        'Create an IELTS academic mock test.',
        'Generate an IELTS practice test with listening audio.',
        'What can PolEdu do for IELTS right now?',
      ]
    : [
        'Teach me maths',
        'Teach me derivatives',
        'Explain quadratic functions with a mini test',
        'Create an IELTS academic mock test',
      ],
)

const currentStatusLabel = computed(() => {
  if (latestJobType.value === 'lesson') {
    return latestLessonStatus.value?.state || 'queued'
  }
  if (latestJobType.value === 'ielts') {
    return latestTestStatus.value?.state || 'queued'
  }
  return ''
})

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function stopPolling(): void {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function isTerminalState(state: string | undefined): boolean {
  return state === 'completed' || state === 'failed'
}

function addMessage(role: MessageRole, content: string): void {
  messages.value.push({
    id: createId(role),
    role,
    content,
    timestamp: new Date().toISOString(),
  })
}

function getPreviousUserMessages(): string[] {
  return messages.value
    .filter((message) => message.role === 'user')
    .map((message) => message.content.trim())
    .filter(Boolean)
    .slice(-2)
}

function saveLearnerProfile(profile: LearnerProfile | null): void {
  learnerProfile.value = profile
  if (!profile) {
    localStorage.removeItem(LEARNER_STORAGE_KEY)
    return
  }

  localStorage.setItem(LEARNER_STORAGE_KEY, JSON.stringify(profile))
}

function loadStoredLearnerProfile(): LearnerProfile | null {
  const raw = localStorage.getItem(LEARNER_STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as LearnerProfile
  } catch {
    localStorage.removeItem(LEARNER_STORAGE_KEY)
    return null
  }
}

async function hydrateLearnerProfile(): Promise<void> {
  const stored = loadStoredLearnerProfile()
  if (!stored) {
    showOnboarding.value = entryMode.value !== 'ielts'
    return
  }

  try {
    const profile = await fetchLearnerProfile(stored.learner_id)
    saveLearnerProfile(profile)
    showOnboarding.value = false
  } catch {
    saveLearnerProfile(null)
    showOnboarding.value = entryMode.value !== 'ielts'
  }
}

async function handleOnboardingSubmit(payload: LearnerOnboardRequest): Promise<void> {
  onboardingBusy.value = true
  onboardingError.value = null

  try {
    const response = await createLearnerProfile(payload)
    saveLearnerProfile(response.profile)
    showOnboarding.value = false
    addMessage(
      'assistant',
      `Profile saved for ${response.display_name}. Tell me what math topic you want to learn next.`,
    )
    if (route.query.entry === 'ielts') {
      await router.replace({ name: 'chat' })
    }
  } catch (error) {
    onboardingError.value =
      error instanceof Error ? error.message : 'Unable to save the learner profile.'
  } finally {
    onboardingBusy.value = false
  }
}

async function refreshLessonStatus(code: string): Promise<void> {
  try {
    const status = await fetchLessonStatus(code)
    latestLessonStatus.value = status
    jobError.value = null

    if (!isTerminalState(status.state)) {
      return
    }

    stopPolling()
    const jobKey = `lesson:${code}`
    if (announcedJobs.has(jobKey)) {
      return
    }

    announcedJobs.add(jobKey)
    if (status.state === 'completed') {
      addMessage('assistant', `Your math lesson ${code.toUpperCase()} is ready. Opening it now.`)
      if (autoOpenJobKey.value === jobKey) {
        autoOpenJobKey.value = null
        await router.push({ name: 'lesson-viewer', params: { lessonCode: code } })
      }
    } else {
      addMessage('assistant', `The math lesson job ${code.toUpperCase()} failed. Check the latest log message.`)
    }
  } catch (error) {
    jobError.value = error instanceof Error ? error.message : 'Unable to refresh lesson status.'
  }
}

async function refreshTestStatus(code: string): Promise<void> {
  try {
    const status = await fetchTestStatus(code)
    latestTestStatus.value = status
    jobError.value = null

    if (!isTerminalState(status.state)) {
      return
    }

    stopPolling()
    const jobKey = `ielts:${code}`
    if (announcedJobs.has(jobKey)) {
      return
    }

    announcedJobs.add(jobKey)
    if (status.state === 'completed') {
      addMessage('assistant', `Your IELTS test ${code.toUpperCase()} is ready. Opening the exam now.`)
      if (autoOpenJobKey.value === jobKey) {
        autoOpenJobKey.value = null
        await router.push({ name: 'ielts-exam', query: { name_code: code } })
      }
    } else {
      addMessage('assistant', `The IELTS test job ${code.toUpperCase()} failed. Check the latest log message.`)
    }
  } catch (error) {
    jobError.value = error instanceof Error ? error.message : 'Unable to refresh IELTS test status.'
  }
}

function startPolling(jobType: Exclude<JobType, null>, code: string): void {
  stopPolling()
  if (jobType === 'lesson') {
    void refreshLessonStatus(code)
    pollTimer = window.setInterval(() => {
      void refreshLessonStatus(code)
    }, 4000)
    return
  }

  void refreshTestStatus(code)
  pollTimer = window.setInterval(() => {
    void refreshTestStatus(code)
  }, 5000)
}

async function refreshCurrentJob(): Promise<void> {
  if (latestJobType.value === 'lesson' && latestLessonCode.value) {
    await refreshLessonStatus(latestLessonCode.value)
  }

  if (latestJobType.value === 'ielts' && latestTestCode.value) {
    await refreshTestStatus(latestTestCode.value)
  }
}

async function sendMessage(rawMessage: string): Promise<void> {
  const message = rawMessage.trim()
  if (!message) {
    return
  }

  const previousMessages = getPreviousUserMessages()
  input.value = ''
  addMessage('user', message)
  busy.value = true
  onboardingError.value = null
  jobError.value = null

  try {
    const response = await sendAssistantMessage(message, {
      learner_id: learnerProfile.value?.learner_id ?? null,
      previous_messages: previousMessages,
    })

    addMessage('assistant', response.reply)

    if (response.requires_onboarding) {
      showOnboarding.value = true
    }

    if (response.lesson) {
      latestJobType.value = 'lesson'
      latestLessonCode.value = response.lesson.lesson_code
      latestLessonStatus.value = {
        lesson_code: response.lesson.lesson_code,
        folder: response.lesson.folder,
        state: response.lesson.state,
        log_file: response.lesson.log_file,
        lesson_json: response.lesson.lesson_json,
        lesson_json_exists: false,
        learner_id: response.lesson.learner_id,
        topic: response.lesson.topic,
        subject: response.lesson.subject,
        logs: [],
      }
      autoOpenJobKey.value = `lesson:${response.lesson.lesson_code}`
      startPolling('lesson', response.lesson.lesson_code)
    }

    if (response.test) {
      latestJobType.value = 'ielts'
      latestTestCode.value = response.test.name_code
      latestTestStatus.value = {
        name_code: response.test.name_code,
        folder: response.test.folder,
        state: response.test.state,
        log_file: response.test.log_file,
        test_json: response.test.test_json,
        test_json_exists: false,
        audio_access_code: response.test.audio_access_code,
        audio_files: response.test.audio_files,
        audio_urls: [],
        logs: [],
      }
      autoOpenJobKey.value = `ielts:${response.test.name_code}`
      startPolling('ielts', response.test.name_code)
    }
  } catch (error) {
    const messageText = error instanceof Error ? error.message : 'Unable to reach the backend.'
    addMessage('assistant', `I could not reach the backend at localhost:8000. ${messageText}`)
  } finally {
    busy.value = false
  }
}

function switchToIeltsMode(): void {
  void router.replace({ name: 'chat', query: { entry: 'ielts' } })
}

function switchToTutorMode(): void {
  void router.replace({ name: 'chat' })
}

watch(
  () => entryMode.value,
  (mode) => {
    if (mode === 'ielts') {
      showOnboarding.value = false
      return
    }

    if (!learnerProfile.value) {
      showOnboarding.value = true
    }
  },
)

watch(
  () => [messages.value.length, busy.value, latestLessonStatus.value?.state, latestTestStatus.value?.state],
  async () => {
    await nextTick()
    if (messageViewport.value) {
      messageViewport.value.scrollTop = messageViewport.value.scrollHeight
    }
  },
)

onMounted(() => {
  void hydrateLearnerProfile()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="chat-page">
    <aside class="chat-page__sidebar">
      <div class="chat-page__brand">
        <img :src="logoUrl" alt="PolEdu logo" />
        <div>
          <strong>PolEdu</strong>
          <span>Math-first tutor</span>
        </div>
      </div>

      <div class="chat-page__mode-switch">
        <button
          type="button"
          class="chat-page__mode-button"
          :class="{ active: entryMode === 'tutor' }"
          @click="switchToTutorMode"
        >
          Tutor
        </button>
        <button
          type="button"
          class="chat-page__mode-button"
          :class="{ active: entryMode === 'ielts' }"
          @click="switchToIeltsMode"
        >
          IELTS
        </button>
      </div>

      <section v-if="learnerProfile" class="chat-page__panel">
        <p class="chat-page__panel-label">Learner profile</p>
        <h2>{{ learnerProfile.display_name }}</h2>
        <p>{{ learnerProfile.hobbies.join(', ') || 'No hobbies added yet.' }}</p>
        <ul class="chat-page__preferences">
          <li>Doing: {{ learnerProfile.learning_by_doing ? 'On' : 'Off' }}</li>
          <li>Listening: {{ learnerProfile.learning_by_listening ? 'On' : 'Off' }}</li>
          <li>Reading: {{ learnerProfile.learning_by_reading ? 'On' : 'Off' }}</li>
        </ul>
      </section>

      <section v-else class="chat-page__panel">
        <p class="chat-page__panel-label">Quick start</p>
        <h2>{{ entryMode === 'ielts' ? 'IELTS tools ready' : 'Tutor setup needed' }}</h2>
        <p>
          {{
            entryMode === 'ielts'
              ? 'IELTS can run without onboarding. Switch back to Tutor when you want personalized math lessons.'
              : 'Create a learner profile to unlock personalized math lessons.'
          }}
        </p>
        <button
          v-if="entryMode !== 'ielts'"
          type="button"
          class="chat-page__sidebar-button"
          @click="showOnboarding = true"
        >
          Open onboarding
        </button>
      </section>

      <section v-if="latestJobType" class="chat-page__panel">
        <p class="chat-page__panel-label">Current job</p>
        <h2>{{ latestJobType === 'lesson' ? 'Math lesson' : 'IELTS test' }}</h2>
        <p>
          {{
            latestJobType === 'lesson'
              ? latestLessonCode?.toUpperCase()
              : latestTestCode?.toUpperCase()
          }}
        </p>
        <span class="chat-page__status-pill">{{ currentStatusLabel }}</span>
        <button type="button" class="chat-page__sidebar-button" @click="refreshCurrentJob">
          Refresh status
        </button>
        <RouterLink
          v-if="latestJobType === 'lesson' && latestLessonCode"
          class="chat-page__sidebar-link"
          :to="{ name: 'lesson-viewer', params: { lessonCode: latestLessonCode } }"
        >
          Open lesson page
        </RouterLink>
        <RouterLink
          v-if="latestJobType === 'ielts' && latestTestCode"
          class="chat-page__sidebar-link"
          :to="{ name: 'ielts-exam', query: { name_code: latestTestCode } }"
        >
          Open IELTS exam
        </RouterLink>
        <p v-if="jobError" class="chat-page__error">{{ jobError }}</p>
      </section>

      <RouterLink class="chat-page__home-link" :to="{ name: 'landing' }">
        Back to landing page
      </RouterLink>
    </aside>

    <main class="chat-page__main">
      <header class="chat-page__header">
        <div>
          <p class="chat-page__eyebrow">{{ entryMode === 'ielts' ? 'IELTS mode' : 'Personalized tutor' }}</p>
          <h1>
            {{
              entryMode === 'ielts'
                ? 'Generate IELTS practice tests when you ask for them.'
                : 'Ask for a math topic and PolEdu will build a short lesson around you.'
            }}
          </h1>
        </div>
      </header>

      <section v-if="messages.length === 0" class="chat-page__welcome">
        <OnboardingWizard
          v-if="showOnboarding && !learnerProfile && entryMode !== 'ielts'"
          :submitting="onboardingBusy"
          @submit="handleOnboardingSubmit"
          @skip-ielts="switchToIeltsMode"
        />

        <div v-else class="chat-page__welcome-shell">
          <h2>{{ entryMode === 'ielts' ? 'IELTS tools are ready.' : 'Start with a question.' }}</h2>
          <p class="chat-page__welcome-copy">
            {{
              entryMode === 'ielts'
                ? 'Ask for an IELTS mock test, or switch back to Tutor for personalized math lessons.'
                : learnerProfile
                  ? `Profile loaded for ${learnerProfile.display_name}. Ask for a math topic to begin.`
                  : 'Create a learner profile first, or switch to IELTS mode if you only want test generation.'
            }}
          </p>

          <div class="chat-page__suggestions">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion"
              type="button"
              class="chat-page__suggestion"
              @click="sendMessage(suggestion)"
            >
              {{ suggestion }}
            </button>
          </div>

          <p v-if="onboardingError" class="chat-page__error">{{ onboardingError }}</p>
        </div>
      </section>

      <section v-else ref="messageViewport" class="chat-page__messages">
        <div
          v-for="message in messages"
          :key="message.id"
          class="chat-page__message-row"
          :class="{ 'chat-page__message-row--assistant': message.role === 'assistant' }"
        >
          <div class="chat-page__message">
            <span class="chat-page__message-role">{{ message.role === 'user' ? 'You' : 'PolEdu' }}</span>
            <p>{{ message.content }}</p>
            <time>{{ formatTime(message.timestamp) }}</time>
          </div>
        </div>

        <div v-if="busy" class="chat-page__message-row chat-page__message-row--assistant">
          <div class="chat-page__message">
            <span class="chat-page__message-role">PolEdu</span>
            <p>Thinking...</p>
          </div>
        </div>
      </section>

      <footer class="chat-page__composer">
        <p v-if="onboardingError" class="chat-page__error">{{ onboardingError }}</p>
        <form class="chat-page__composer-form" @submit.prevent="sendMessage(input)">
          <textarea
            v-model="input"
            rows="1"
            placeholder="Message PolEdu"
            :disabled="busy || (showOnboarding && !learnerProfile && entryMode !== 'ielts')"
          ></textarea>
          <button
            type="submit"
            :disabled="!input.trim() || busy || (showOnboarding && !learnerProfile && entryMode !== 'ielts')"
          >
            Send
          </button>
        </form>
        <p class="chat-page__footnote">
          Math-first tutoring is personalized. IELTS remains available as a secondary feature.
        </p>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.chat-page {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: 20rem minmax(0, 1fr);
  background: #020617;
  color: #f8fafc;
}

.chat-page__sidebar {
  display: grid;
  align-content: start;
  gap: 1rem;
  padding: 1.2rem;
  background: rgba(15, 23, 42, 0.92);
  border-right: 1px solid rgba(148, 163, 184, 0.14);
}

.chat-page__brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.chat-page__brand img {
  width: 3rem;
  height: 3rem;
  border-radius: 0.95rem;
  object-fit: cover;
}

.chat-page__brand strong,
.chat-page__panel h2,
.chat-page__header h1 {
  display: block;
}

.chat-page__brand span {
  color: #cbd5e1;
  font-size: 0.9rem;
}

.chat-page__mode-switch {
  display: flex;
  gap: 0.6rem;
}

.chat-page__mode-button {
  flex: 1;
  border: none;
  border-radius: 0.95rem;
  padding: 0.8rem 0.95rem;
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
  cursor: pointer;
}

.chat-page__mode-button.active {
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #ffffff;
}

.chat-page__panel {
  display: grid;
  gap: 0.65rem;
  padding: 1rem;
  border-radius: 1.25rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.chat-page__panel-label,
.chat-page__eyebrow {
  margin: 0;
  color: #67e8f9;
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.chat-page__panel h2 {
  margin: 0;
  font-size: 1.25rem;
}

.chat-page__panel p,
.chat-page__welcome-copy,
.chat-page__message p,
.chat-page__preferences {
  margin: 0;
  line-height: 1.7;
  color: #cbd5e1;
}

.chat-page__preferences {
  padding-left: 1rem;
}

.chat-page__status-pill {
  justify-self: start;
  padding: 0.38rem 0.72rem;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.16);
  color: #99f6e4;
  text-transform: capitalize;
}

.chat-page__sidebar-button,
.chat-page__sidebar-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.8rem 0.95rem;
  border-radius: 0.95rem;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: #f8fafc;
  text-decoration: none;
  cursor: pointer;
}

.chat-page__home-link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.92rem;
}

.chat-page__main {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-height: 100dvh;
}

.chat-page__header,
.chat-page__welcome,
.chat-page__messages,
.chat-page__composer {
  width: min(980px, calc(100% - 2rem));
  margin: 0 auto;
}

.chat-page__header {
  padding: 1.4rem 0 1rem;
}

.chat-page__header h1 {
  margin: 0.5rem 0 0;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.08;
  max-width: 16ch;
}

.chat-page__welcome {
  display: grid;
  align-content: center;
  padding: 1rem 0 2rem;
}

.chat-page__welcome-shell {
  display: grid;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 1.5rem;
  background:
    radial-gradient(circle at top right, rgba(20, 184, 166, 0.14), transparent 16rem),
    rgba(15, 23, 42, 0.62);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.chat-page__welcome-shell h2 {
  margin: 0;
  font-size: 1.8rem;
}

.chat-page__suggestions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.chat-page__suggestion {
  padding: 1rem;
  border-radius: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.04);
  color: #f8fafc;
  text-align: left;
  cursor: pointer;
}

.chat-page__messages {
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 1rem;
}

.chat-page__message-row {
  padding: 0.8rem 0;
}

.chat-page__message-row--assistant .chat-page__message {
  background: rgba(15, 23, 42, 0.62);
}

.chat-page__message {
  max-width: 48rem;
  padding: 1rem 1.1rem;
  border-radius: 1.2rem;
  background: rgba(30, 41, 59, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.chat-page__message-role {
  display: inline-block;
  margin-bottom: 0.45rem;
  color: #99f6e4;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.chat-page__message time {
  display: inline-block;
  margin-top: 0.6rem;
  color: #94a3b8;
  font-size: 0.75rem;
}

.chat-page__composer {
  padding: 1rem 0 1.3rem;
}

.chat-page__composer-form {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
  padding: 0.7rem;
  border-radius: 1.2rem;
  background: rgba(15, 23, 42, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.chat-page__composer-form textarea {
  flex: 1;
  min-height: 3rem;
  max-height: 12rem;
  resize: vertical;
  border: none;
  background: transparent;
  color: #f8fafc;
  outline: none;
  line-height: 1.6;
}

.chat-page__composer-form button {
  border: none;
  border-radius: 0.95rem;
  padding: 0.9rem 1.2rem;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #ffffff;
  cursor: pointer;
}

.chat-page__composer-form button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.chat-page__footnote {
  margin: 0.65rem 0 0;
  color: #94a3b8;
  font-size: 0.84rem;
  text-align: center;
}

.chat-page__error {
  color: #fca5a5;
}

@media (max-width: 980px) {
  .chat-page {
    grid-template-columns: 1fr;
  }

  .chat-page__sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  }

  .chat-page__suggestions {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .chat-page__composer-form {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
