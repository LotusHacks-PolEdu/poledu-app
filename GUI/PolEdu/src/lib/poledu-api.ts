import type {
  CreateTestRequest,
  IeltsTest,
  MinibotRequestOptions,
  MinibotResponse,
  TestStatusResponse,
} from '../types/ielts'
import type {
  AssistantChatRequestOptions,
  AssistantChatResponse,
  LearnerOnboardRequest,
  LearnerProfile,
  LessonStatusResponse,
  MathLessonPayload,
  OnboardLearnerResponse,
} from '../types/lessons'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

export const apiBaseUrl = (configuredApiBaseUrl || 'http://localhost:8000').replace(/\/+$/, '')

export function toApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `${response.status} ${response.statusText}`.trim()

  try {
    const payload = await response.json()
    if (typeof payload?.detail === 'string' && payload.detail.trim()) {
      return payload.detail
    }
    return JSON.stringify(payload)
  } catch {
    return fallback
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(toApiUrl(path), init)

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  return response.json() as Promise<T>
}

export async function sendMinibotMessage(
  message: string,
  testRequest: MinibotRequestOptions = {},
): Promise<MinibotResponse> {
  const { previous_messages = [], ...createTestRequest } = testRequest
  const createTestRequestPayload: CreateTestRequest = createTestRequest

  return requestJson<MinibotResponse>('/minibot', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      previous_messages,
      test_request: createTestRequestPayload,
    }),
  })
}

export async function createLearnerProfile(
  request: LearnerOnboardRequest,
): Promise<OnboardLearnerResponse> {
  return requestJson<OnboardLearnerResponse>('/learners/onboard', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
}

export async function fetchLearnerProfile(learnerId: string): Promise<LearnerProfile> {
  return requestJson<LearnerProfile>(`/learners/${encodeURIComponent(learnerId)}`)
}

export async function sendAssistantMessage(
  message: string,
  options: AssistantChatRequestOptions = {},
): Promise<AssistantChatResponse> {
  const {
    previous_messages = [],
    learner_id = null,
    lesson_request = {},
    test_request = {},
  } = options

  return requestJson<AssistantChatResponse>('/assistant/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      previous_messages,
      learner_id,
      lesson_request,
      test_request,
    }),
  })
}

export async function fetchTestStatus(nameCode: string): Promise<TestStatusResponse> {
  return requestJson<TestStatusResponse>(`/tests/${encodeURIComponent(nameCode)}`)
}

export async function fetchTestPayload(nameCode: string): Promise<IeltsTest> {
  return requestJson<IeltsTest>(`/tests/${encodeURIComponent(nameCode)}/json`)
}

export async function fetchLessonStatus(lessonCode: string): Promise<LessonStatusResponse> {
  return requestJson<LessonStatusResponse>(`/lessons/${encodeURIComponent(lessonCode)}`)
}

export async function fetchLessonPayload(lessonCode: string): Promise<MathLessonPayload> {
  return requestJson<MathLessonPayload>(`/lessons/${encodeURIComponent(lessonCode)}/json`)
}
