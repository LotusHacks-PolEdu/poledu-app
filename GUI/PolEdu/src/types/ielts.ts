export interface Question {
  question_number: number
  question_text: string
  options: string[] | null
  answer: string
}

export interface QuestionSet {
  questions_range: string
  question_type: string
  instruction: string
  questions: Question[]
}

export interface ListeningPart {
  part_number: number
  context: string
  audio_script: string
  question_sets: QuestionSet[]
}

export interface ReadingPassage {
  passage_number: number
  title: string
  content: string
  question_sets: QuestionSet[]
}

export interface WritingTaskData {
  task_number: number
  instruction: string
  prompt?: string
  data_description?: string
}

export interface SpeakingPart {
  topic: string
  questions?: string[]
  cue_card_topic?: string
  bullet_points?: string[]
  instruction?: string
}

export interface IeltsTest {
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

export interface CreateTestRequest {
  model?: string
  temperature?: number
  max_completion_tokens?: number | null
  max_attempts?: number
  seed?: number | null
  test_title?: string
  generate_audio?: boolean
}

export interface MinibotRequestOptions extends CreateTestRequest {
  previous_messages?: string[]
}

export interface CreateTestResponse {
  name_code: string
  folder: string
  state: string
  log_file: string
  test_json: string | null
  audio_files: string[]
  audio_access_code: string
  audio_base_url: string
}

export interface LogEntry {
  timestamp: string
  state: string
  message: string
}

export interface TestStatusResponse {
  name_code: string
  folder: string
  state: string
  log_file: string
  test_json: string | null
  test_json_exists: boolean
  audio_access_code: string
  audio_files: string[]
  audio_urls: string[]
  logs: LogEntry[]
}

export interface MinibotResponse {
  reply: string
  intent: string
  will_create_test: boolean
  test: CreateTestResponse | null
}
