<script setup lang="ts">
import { computed, ref } from 'vue'

export interface NumberAnswerProps {
  question: string
  placeholder?: string
  acceptedAnswers?: string[]
}

const props = defineProps<NumberAnswerProps>()
const answer = ref('')
const submitted = ref(false)
const isCorrect = ref(false)

const emit = defineEmits<{
  (e: 'answer', payload: { answer: string; correct: boolean }): void
}>()

function compareAnswers(input: string, acceptedAnswers: string[]): boolean {
  const normalizedInput = input.trim()
  if (!normalizedInput) {
    return false
  }

  const numericInput = Number(normalizedInput)
  const inputIsNumeric = !Number.isNaN(numericInput)

  return acceptedAnswers.some((accepted) => {
    const normalizedAccepted = accepted.trim()
    if (normalizedAccepted.toLowerCase() === normalizedInput.toLowerCase()) {
      return true
    }

    const numericAccepted = Number(normalizedAccepted)
    const acceptedIsNumeric = !Number.isNaN(numericAccepted)
    return inputIsNumeric && acceptedIsNumeric && Math.abs(numericInput - numericAccepted) < 1e-9
  })
}

function handleSubmit(): void {
  submitted.value = true
  if (props.acceptedAnswers && props.acceptedAnswers.length > 0) {
    isCorrect.value = compareAnswers(answer.value, props.acceptedAnswers)
  }

  emit('answer', { answer: answer.value, correct: isCorrect.value })
}

const feedbackText = computed(() => {
  if (!submitted.value || !props.acceptedAnswers || props.acceptedAnswers.length === 0) {
    return ''
  }

  return isCorrect.value
    ? 'Correct!'
    : `Incorrect. Accepted: ${props.acceptedAnswers.join(', ')}`
})
</script>

<template>
  <div class="number-answer">
    <input
      v-model="answer"
      type="text"
      class="number-answer__input"
      :placeholder="placeholder || 'Enter your answer'"
      :disabled="submitted"
    />
    <div class="number-answer__row">
      <button
        type="button"
        class="number-answer__button"
        :disabled="answer.trim() === '' || submitted"
        @click="handleSubmit"
      >
        Submit
      </button>
      <p v-if="feedbackText" class="number-answer__feedback" :class="{ correct: isCorrect }">
        {{ feedbackText }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.number-answer {
  display: grid;
  gap: 0.65rem;
}

.number-answer__input {
  width: 100%;
  padding: 0.7rem 0.9rem;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 0.95rem;
}

.number-answer__input:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 0;
}

.number-answer__row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.number-answer__button {
  border: none;
  border-radius: 999px;
  padding: 0.6rem 1.2rem;
  background: var(--color-primary);
  color: #1A1A1A;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
}

.number-answer__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.number-answer__feedback {
  margin: 0;
  font-size: 0.88rem;
  color: #c0392b;
}

.number-answer__feedback.correct {
  color: var(--color-green);
}
</style>
