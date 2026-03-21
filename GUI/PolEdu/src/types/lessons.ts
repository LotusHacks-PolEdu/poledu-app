import type { CreateTestRequest, CreateTestResponse } from './ielts'

export interface LearnerProfile {
  learner_id: string
  display_name: string
  folder_slug: string
  learning_by_doing: boolean
  learning_by_listening: boolean
  learning_by_reading: boolean
  hobbies: string[]
  favorite_food: string
}

export interface LearnerOnboardRequest {
  name: string
  learning_by_doing: boolean
  learning_by_listening: boolean
  learning_by_reading: boolean
  hobbies: string[]
  favorite_food: string
}

export interface OnboardLearnerResponse {
  learner_id: string
  display_name: string
  folder_slug: string
  profile: LearnerProfile
}

export interface LessonCreateRequest {
  model?: string
  temperature?: number
  max_completion_tokens?: number | null
  max_attempts?: number
  seed?: number | null
}

export interface LessonCreateResponse {
  lesson_code: string
  folder: string
  state: string
  log_file: string
  lesson_json: string | null
  learner_id: string
  topic: string
  subject: string
}

export interface LessonLogEntry {
  timestamp: string
  state: string
  message: string
}

export interface LessonStatusResponse {
  lesson_code: string
  folder: string
  state: string
  log_file: string
  lesson_json: string | null
  lesson_json_exists: boolean
  learner_id: string
  topic: string
  subject: string
  logs: LessonLogEntry[]
}

export interface LessonGraphFigure {
  expression: string
  xMin?: number
  xMax?: number
  yMin?: number
  yMax?: number
  color?: string
}

export interface LessonTextBlock {
  id: string
  type: 'text'
  title: string
  content: string
  latex?: string[]
}

export interface LessonGraphBlock extends LessonGraphFigure {
  id: string
  type: 'graph'
  title: string
  prompt: string
}

export interface LessonGraphPlaygroundBlock {
  id: string
  type: 'graph-playground'
  title: string
  prompt: string
  challenge: string
  initial_expression: string
}

export type LessonBlock = LessonTextBlock | LessonGraphBlock | LessonGraphPlaygroundBlock

export interface LessonSection {
  id: string
  title: string
  blocks: LessonBlock[]
}

export interface LessonQuestionBase {
  id: string
  type: 'multiple-choice' | 'number-answer' | 'true-false'
  prompt: string
  latex?: string[]
  graph?: LessonGraphFigure
}

export interface LessonMultipleChoiceQuestion extends LessonQuestionBase {
  type: 'multiple-choice'
  options: string[]
}

export interface LessonNumberAnswerQuestion extends LessonQuestionBase {
  type: 'number-answer'
  placeholder?: string
}

export interface LessonTrueFalseQuestion extends LessonQuestionBase {
  type: 'true-false'
  statement?: string
}

export type LessonQuestion =
  | LessonMultipleChoiceQuestion
  | LessonNumberAnswerQuestion
  | LessonTrueFalseQuestion

export interface LessonAnswerKeyBase {
  question_id: string
  explanation: string
}

export interface LessonMultipleChoiceAnswerKey extends LessonAnswerKeyBase {
  correct_option_index: number
}

export interface LessonNumberAnswerKey extends LessonAnswerKeyBase {
  accepted_answers: string[]
}

export interface LessonTrueFalseAnswerKey extends LessonAnswerKeyBase {
  correct_answer: boolean
}

export type LessonAnswerKeyItem =
  | LessonMultipleChoiceAnswerKey
  | LessonNumberAnswerKey
  | LessonTrueFalseAnswerKey

export interface ResearchSource {
  query: string
  title: string
  url: string
  snippet: string
}

export interface MathLessonPayload {
  lesson_code: string
  subject: 'math'
  topic: string
  learner_profile: LearnerProfile
  intro: string
  sections: LessonSection[]
  mini_test: LessonQuestion[]
  answer_key: LessonAnswerKeyItem[]
  research_sources: ResearchSource[]
  narration_script: string | null
}

export interface AssistantChatRequestOptions {
  previous_messages?: string[]
  learner_id?: string | null
  lesson_request?: LessonCreateRequest
  test_request?: CreateTestRequest
}

export interface AssistantChatResponse {
  reply: string
  intent:
    | 'collect_profile'
    | 'ask_math_topic'
    | 'create_math_lesson'
    | 'ask_capabilities'
    | 'create_ielts_test'
    | 'unsupported_or_other'
  job_type: 'lesson' | 'ielts' | null
  requires_onboarding: boolean
  lesson: LessonCreateResponse | null
  test: CreateTestResponse | null
}
