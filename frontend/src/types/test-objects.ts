/**
 * Shared TypeScript interfaces for test question objects.
 * These mirror the props of each Vue component so that API / JSON
 * metadata can be typed consistently throughout the app.
 */

/** A rich-media content block (reading passage, image, audio). */
export interface MediaBlock {
  type: 'media'
  text?: string
  imageUrl?: string
  audioUrl?: string
}

/** A multiple-choice question. */
export interface MultipleChoiceQuestion {
  type: 'multiple-choice'
  question: string
  options: string[]
  /** 0-based index of the correct option */
  correctIndex?: number
}

/** A short-answer (fill-in) question. */
export interface ShortAnswerQuestion {
  type: 'short-answer'
  question: string
  /** All accepted correct answers (case-insensitive) */
  acceptedAnswers?: string[]
}

/** True / False / Not Given (IELTS reading staple). */
export interface TrueFalseNotGivenQuestion {
  type: 'true-false-not-given'
  statement: string
  correctAnswer?: 'true' | 'false' | 'not-given'
}

/** Matching – pair prompts with choices. */
export interface MatchingQuestion {
  type: 'matching'
  question: string
  prompts: string[]
  choices: string[]
  /** correctMap[i] = index of the correct choice for prompts[i] */
  correctMap?: number[]
}

/** Ordering – arrange items in the correct sequence. */
export interface OrderingQuestion {
  type: 'ordering'
  question: string
  /** Items shown in (shuffled) display order */
  items: string[]
  /** Correct order expressed as indices into `items` */
  correctOrder?: number[]
}

/** Graph – renders a JS math expression on a canvas. */
export interface GraphBlock {
  type: 'graph'
  question?: string
  /** JS expression using variable `x`, e.g. "2*x+4", "Math.sin(x)" */
  expression: string
  xMin?: number
  xMax?: number
  yMin?: number
  yMax?: number
}

/** Numeric code input – OTP-style individual digit boxes. */
export interface NumericCodeQuestion {
  type: 'numeric-code'
  question: string
  /** Number of digit boxes (default 4) */
  length?: number
  /** Correct code as a string, e.g. "1234" */
  correctCode?: string
}

/** Union of all test-object types. */
export type TestObject =
  | MediaBlock
  | MultipleChoiceQuestion
  | ShortAnswerQuestion
  | TrueFalseNotGivenQuestion
  | MatchingQuestion
  | OrderingQuestion
  | GraphBlock
  | NumericCodeQuestion
