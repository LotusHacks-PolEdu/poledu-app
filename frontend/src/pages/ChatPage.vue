<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import logoUrl from '../assets/logo.png'
import OnboardingWizard from '../components/OnboardingWizard.vue'
import {
  createLearnerProfile,
  fetchLearnerProfile,
  fetchLessonPayload,
  fetchLessonStatus,
  fetchTestStatus,
  sendAssistantMessage,
} from '../lib/poledu-api'
import type { TestStatusResponse } from '../types/ielts'
import type {
  LearnerOnboardRequest,
  LearnerProfile,
  LessonStatusResponse,
  MathLessonPayload,
} from '../types/lessons'
import InlineLessonCard from '../components/InlineLessonCard.vue'

interface DemoPersona {
  key: string
  label: string
  description: string
  request: LearnerOnboardRequest
}

const DEMO_PERSONAS: DemoPersona[] = [
  {
    key: 'demo-alex',
    label: 'Alex',
    description: 'Learns by doing · Swimming & gaming',
    request: {
      name: 'Alex',
      learning_by_doing: true,
      learning_by_listening: false,
      learning_by_reading: false,
      hobbies: ['swimming', 'gaming'],
      favorite_food: 'pizza',
    },
  },
  {
    key: 'demo-jamie',
    label: 'Jamie',
    description: 'Learns by listening · Soccer & music',
    request: {
      name: 'Jamie',
      learning_by_doing: false,
      learning_by_listening: true,
      learning_by_reading: false,
      hobbies: ['soccer', 'music'],
      favorite_food: 'sushi',
    },
  },
]

type MessageRole = 'user' | 'assistant'
type JobType = 'lesson' | 'ielts' | null

interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: string
  lessonPayload?: MathLessonPayload
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
const demoPersonaBusy = ref<string | null>(null)
const sidebarOpen = ref(false)

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

function addMessage(role: MessageRole, content: string, lessonPayload?: MathLessonPayload): void {
  messages.value.push({
    id: createId(role),
    role,
    content,
    timestamp: new Date().toISOString(),
    lessonPayload,
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

async function switchToPersona(persona: DemoPersona): Promise<void> {
  demoPersonaBusy.value = persona.key
  const cacheKey = `poledu-demo-v2-${persona.key}`
  const cached = localStorage.getItem(cacheKey)
  if (cached) {
    try {
      const profile = JSON.parse(cached) as LearnerProfile
      saveLearnerProfile(profile)
      showOnboarding.value = false
      demoPersonaBusy.value = null
      return
    } catch {
      localStorage.removeItem(cacheKey)
    }
  }
  try {
    const response = await createLearnerProfile(persona.request)
    localStorage.setItem(cacheKey, JSON.stringify(response.profile))
    saveLearnerProfile(response.profile)
    showOnboarding.value = false
  } catch (err) {
    addMessage('assistant', `Could not create profile for ${persona.label}: ${err instanceof Error ? err.message : 'Unknown error'}`)
  } finally {
    demoPersonaBusy.value = null
  }
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
      if (autoOpenJobKey.value === jobKey) autoOpenJobKey.value = null
      try {
        const payload = await fetchLessonPayload(code)
        addMessage(
          'assistant',
          `Here's your lesson on "${payload.topic}", ${payload.learner_profile.display_name}!`,
          payload,
        )
      } catch {
        addMessage(
          'assistant',
          `Lesson ${code.toUpperCase()} is ready! Tap "Open lesson page" in the menu to view it.`,
        )
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
  <div class="chat-page" :class="{ 'sidebar-open': sidebarOpen }">

    <!-- Mobile top bar -->
    <header class="chat-page__topbar">
      <div class="chat-page__topbar-brand">
        <img :src="logoUrl" alt="PolEdu logo" />
        <strong>PolEdu</strong>
      </div>
      <button type="button" class="chat-page__hamburger" @click="sidebarOpen = !sidebarOpen" aria-label="Menu">
        ☰
      </button>
    </header>

    <!-- Backdrop (mobile) -->
    <div v-if="sidebarOpen" class="chat-page__backdrop" @click="sidebarOpen = false" />

    <!-- Sidebar -->
    <aside class="chat-page__sidebar">
      <div class="chat-page__sidebar-head">
        <div class="chat-page__brand">
          <img :src="logoUrl" alt="PolEdu logo" />
          <div>
            <strong>PolEdu</strong>
            <span>Personalized tutor</span>
          </div>
        </div>
        <button type="button" class="chat-page__close-btn" @click="sidebarOpen = false" aria-label="Close menu">✕</button>
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
              ? 'IELTS can run without onboarding.'
              : 'Pick a demo persona below or create your own profile.'
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

      <section class="chat-page__panel chat-page__demo-panel">
        <p class="chat-page__panel-label">Demo personas</p>
        <button
          v-for="persona in DEMO_PERSONAS"
          :key="persona.key"
          type="button"
          class="chat-page__persona-btn"
          :class="{ active: learnerProfile?.display_name === persona.label }"
          :disabled="demoPersonaBusy !== null"
          @click="switchToPersona(persona)"
        >
          <strong>{{ persona.label }}</strong>
          <span>{{ persona.description }}</span>
          <span v-if="demoPersonaBusy === persona.key" class="chat-page__persona-loading">Loading…</span>
        </button>
      </section>

      <RouterLink class="chat-page__home-link" :to="{ name: 'landing' }">
        Back to landing page
      </RouterLink>
    </aside>

    <!-- Main chat -->
    <main class="chat-page__main">
      <header class="chat-page__header">
        <div>
          <p class="chat-page__eyebrow">{{ entryMode === 'ielts' ? 'IELTS mode' : 'Personalized tutor' }}</p>
          <h1>
            {{
              entryMode === 'ielts'
                ? 'Generate IELTS practice tests.'
                : 'Your lesson, your way.'
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
          <h2>{{ entryMode === 'ielts' ? 'IELTS tools are ready.' : 'What do you want to learn?' }}</h2>
          <p class="chat-page__welcome-copy">
            {{
              entryMode === 'ielts'
                ? 'Ask for an IELTS mock test, or switch back to Tutor for personalized lessons.'
                : learnerProfile
                  ? `Hi ${learnerProfile.display_name}! Ask me any math topic.`
                  : 'Pick a demo persona on the left, or tap Menu and choose one.'
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
          <InlineLessonCard
            v-if="message.lessonPayload"
            :payload="message.lessonPayload"
            class="chat-page__lesson-card"
          />
        </div>

        <!-- Thinking (initial API call) -->
        <div v-if="busy" class="chat-page__message-row chat-page__message-row--assistant">
          <div class="chat-page__message">
            <span class="chat-page__message-role">PolEdu</span>
            <span class="chat-page__dots" aria-label="Thinking">
              <span /><span /><span />
            </span>
          </div>
        </div>

        <!-- Generating (background job polling) -->
        <div v-else-if="autoOpenJobKey" class="chat-page__message-row chat-page__message-row--assistant">
          <div class="chat-page__message">
            <span class="chat-page__message-role">PolEdu</span>
            <span class="chat-page__generating-label">
              {{ latestJobType === 'ielts' ? 'Generating IELTS test' : 'Generating lesson' }}
            </span>
            <span class="chat-page__dots" aria-label="Generating">
              <span /><span /><span />
            </span>
          </div>
        </div>
      </section>

      <footer class="chat-page__composer">
        <p v-if="onboardingError" class="chat-page__error">{{ onboardingError }}</p>
        <form class="chat-page__composer-form" @submit.prevent="sendMessage(input)">
          <textarea
            v-model="input"
            rows="1"
            placeholder="Ask about any math topic…"
            :disabled="busy || (showOnboarding && !learnerProfile && entryMode !== 'ielts')"
          ></textarea>
          <button
            type="submit"
            :disabled="!input.trim() || busy || (showOnboarding && !learnerProfile && entryMode !== 'ielts')"
          >
            Send
          </button>
        </form>
      </footer>
    </main>
  </div>
</template>

<style scoped>
/* ── Layout ───────────────────────────────────────────────────────────────── */

.chat-page {
  min-height: 100dvh;
  background: var(--color-bg);
  color: var(--color-text);
  display: flex;
  flex-direction: column;
}

/* Mobile top bar — always dark regardless of page theme */
.chat-page__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  background: #1A1A1A;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: sticky;
  top: 0;
  z-index: 10;
}

.chat-page__topbar-brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.chat-page__topbar-brand img {
  width: 2rem;
  height: 2rem;
  border-radius: 0.6rem;
  object-fit: cover;
}

.chat-page__topbar-brand strong {
  font-family: var(--font-heading);
  font-size: 1.1rem;
  color: var(--color-primary);
}

.chat-page__hamburger {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 1.4rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

/* Backdrop */
.chat-page__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 20;
}

/* Sidebar — mobile: fixed drawer */
.chat-page__sidebar {
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  width: min(18rem, 80vw);
  z-index: 30;
  display: grid;
  align-content: start;
  gap: 1rem;
  padding: 1rem;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  transform: translateX(-100%);
  transition: transform 0.25s ease;
}

.sidebar-open .chat-page__sidebar {
  transform: translateX(0);
}

.chat-page__sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.chat-page__close-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.25rem;
  flex-shrink: 0;
}

.chat-page__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chat-page__brand img {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  object-fit: cover;
}

.chat-page__brand strong {
  display: block;
  font-family: var(--font-heading);
  font-size: 1rem;
  color: var(--color-primary);
}

.chat-page__brand span {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

/* Main area */
.chat-page__main {
  flex: 1;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-height: 0;
}

/* ── Sidebar internals ────────────────────────────────────────────────────── */

.chat-page__mode-switch {
  display: flex;
  gap: 0.5rem;
}

.chat-page__mode-button {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 0.65rem 0.8rem;
  background: transparent;
  color: var(--color-text-muted);
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.chat-page__mode-button.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #1A1A1A;
}

.chat-page__panel {
  display: grid;
  gap: 0.6rem;
  padding: 0.9rem;
  border-radius: 1rem;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
}

.chat-page__panel-label,
.chat-page__eyebrow {
  margin: 0;
  font-family: var(--font-body);
  font-weight: 700;
  color: var(--color-primary);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.chat-page__panel h2 {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 1.1rem;
}

.chat-page__panel p,
.chat-page__preferences {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.chat-page__preferences {
  padding-left: 1rem;
}

.chat-page__status-pill {
  justify-self: start;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  background: var(--color-primary-dim);
  color: var(--color-primary);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: capitalize;
}

.chat-page__sidebar-button,
.chat-page__sidebar-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.7rem 0.9rem;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text);
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.85rem;
  text-decoration: none;
  cursor: pointer;
  transition: border-color 0.15s;
}

.chat-page__sidebar-button:hover,
.chat-page__sidebar-link:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Demo personas */
.chat-page__demo-panel { gap: 0.45rem; }

.chat-page__persona-btn {
  display: grid;
  gap: 0.15rem;
  width: 100%;
  padding: 0.75rem 0.9rem;
  border-radius: 0.9rem;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text);
  font-family: var(--font-body);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.chat-page__persona-btn.active {
  border-color: var(--color-primary);
  background: var(--color-primary-dim);
}

.chat-page__persona-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.chat-page__persona-btn strong { font-size: 0.95rem; font-weight: 700; }

.chat-page__persona-btn span {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.chat-page__persona-btn.active span { color: var(--color-primary); }

.chat-page__persona-loading { color: var(--color-primary) !important; }

.chat-page__home-link {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  text-decoration: none;
}

/* ── Main chat area ───────────────────────────────────────────────────────── */

.chat-page__header,
.chat-page__welcome,
.chat-page__messages,
.chat-page__composer {
  width: min(960px, calc(100% - 1rem));
  margin: 0 auto;
}

.chat-page__header {
  padding: 1.25rem 0 0.75rem;
}

.chat-page__eyebrow {
  font-size: 0.72rem;
  margin-bottom: 0.3rem;
}

.chat-page__header h1 {
  margin: 0;
  font-family: var(--font-heading);
  font-size: clamp(1.8rem, 5vw, 2.8rem);
  line-height: 1.1;
  color: var(--color-text);
}

.chat-page__welcome {
  display: grid;
  align-content: center;
  padding: 1rem 0 2rem;
}

.chat-page__welcome-shell {
  display: grid;
  gap: 1rem;
  padding: 1.4rem;
  border-radius: 1.5rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.chat-page__welcome-shell h2 {
  margin: 0;
  font-family: var(--font-heading);
  font-size: clamp(1.4rem, 4vw, 1.9rem);
}

.chat-page__welcome-copy {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--color-text-muted);
}

.chat-page__suggestions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.65rem;
}

.chat-page__suggestion {
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  border: 1px solid var(--color-border);
  background: var(--color-surface-2);
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 0.92rem;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s;
}

.chat-page__suggestion:hover { border-color: var(--color-primary); }

/* Messages */
.chat-page__messages {
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 1rem;
}

.chat-page__message-row {
  padding: 0.7rem 0;
  min-width: 0;
  overflow: hidden;
}

.chat-page__message {
  max-width: 36rem;
  padding: 0.9rem 1rem;
  border-radius: 1.2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: 0.95rem;
}

.chat-page__message-row--assistant .chat-page__message {
  background: var(--color-surface-2);
}

.chat-page__message-role {
  display: inline-block;
  margin-bottom: 0.4rem;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.chat-page__message p { margin: 0; line-height: 1.65; }

.chat-page__message time {
  display: inline-block;
  margin-top: 0.5rem;
  font-size: 0.72rem;
  color: var(--color-text-muted);
}

/* Inline lesson card — sits outside the 36rem bubble */
.chat-page__lesson-card {
  margin-top: 0.75rem;
  width: 100%;
}

/* Composer */
.chat-page__composer { padding: 0.75rem 0 1rem; }

.chat-page__composer-form {
  display: flex;
  gap: 0.65rem;
  align-items: flex-end;
  padding: 0.6rem 0.65rem;
  border-radius: 1.2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.chat-page__composer-form textarea {
  flex: 1;
  min-height: 2.8rem;
  max-height: 10rem;
  resize: vertical;
  border: none;
  background: transparent;
  color: var(--color-text);
  outline: none;
  font-family: var(--font-body);
  font-size: 0.95rem;
  line-height: 1.6;
}

.chat-page__composer-form textarea::placeholder { color: var(--color-text-muted); }

.chat-page__composer-form button {
  border: none;
  border-radius: 999px;
  padding: 0.8rem 1.3rem;
  background: var(--color-primary);
  color: #1A1A1A;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s;
}

.chat-page__composer-form button:disabled { opacity: 0.45; cursor: not-allowed; }

.chat-page__error { color: #ff6b6b; font-size: 0.88rem; margin: 0; }

/* Three-dot loading indicator */
.chat-page__dots {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.chat-page__dots span {
  display: inline-block;
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: dot-bounce 1.2s ease-in-out infinite;
}

.chat-page__dots span:nth-child(2) { animation-delay: 0.2s; }
.chat-page__dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
  40% { transform: translateY(-0.35rem); opacity: 1; }
}

.chat-page__generating-label {
  display: block;
  font-size: 0.82rem;
  color: var(--color-text-muted);
  margin-bottom: 0.4rem;
}

/* ── Desktop: sidebar always visible ─────────────────────────────────────── */

@media (min-width: 768px) {
  .chat-page {
    display: grid;
    grid-template-columns: 18rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }

  /* Hide mobile top bar on desktop */
  .chat-page__topbar { display: none; }

  /* Sidebar always visible, not a drawer */
  .chat-page__sidebar {
    position: static;
    height: auto;
    transform: none !important;
    width: auto;
    border-right: 1px solid var(--color-border);
    overflow-y: auto;
  }

  /* Hide drawer close button on desktop */
  .chat-page__close-btn { display: none; }

  /* No backdrop needed on desktop */
  .chat-page__backdrop { display: none; }

  .chat-page__main {
    grid-column: 2;
    min-height: 100dvh;
  }

  .chat-page__suggestions {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
