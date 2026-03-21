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
    ? 'Correct.'
    : `Incorrect. Accepted answers: ${props.acceptedAnswers.join(', ')}`
})
</script>

<template>
  <div class="number-answer">
    <p class="number-answer__question"><strong>{{ question }}</strong></p>
    <input
      v-model="answer"
      type="text"
      class="number-answer__input"
      :placeholder="placeholder || 'Enter a numeric answer'"
      :disabled="submitted"
    />
    <button
      type="button"
      class="number-answer__button"
      :disabled="answer.trim() === '' || submitted"
      @click="handleSubmit"
    >
      Submit
    </button>
    <p v-if="feedbackText" class="number-answer__feedback">{{ feedbackText }}</p>
  </div>
</template>

<style scoped>
.number-answer {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 1rem;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.45);
}

.number-answer__question {
  margin: 0 0 0.85rem;
}

.number-answer__input {
  width: 100%;
  max-width: 20rem;
  padding: 0.75rem 0.9rem;
  border-radius: 0.85rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.85);
  color: #f8fafc;
}

.number-answer__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.8rem;
  padding: 0.7rem 1rem;
  border: none;
  border-radius: 0.85rem;
  background: #0f766e;
  color: #ffffff;
  cursor: pointer;
}

.number-answer__button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.number-answer__feedback {
  margin: 0.8rem 0 0;
  color: #dbeafe;
}
</style>
