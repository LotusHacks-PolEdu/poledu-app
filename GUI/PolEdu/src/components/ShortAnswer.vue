<script setup lang="ts">
import { ref } from 'vue'

export interface ShortAnswerProps {
  /** The question / prompt text */
  question: string
  /** Accepted correct answers (case-insensitive match), optional — used for auto-grading */
  acceptedAnswers?: string[]
}

const props = defineProps<ShortAnswerProps>()
const answer = ref('')
const submitted = ref(false)
const isCorrect = ref(false)

const emit = defineEmits<{
  (e: 'answer', payload: { answer: string; correct: boolean }): void
}>()

function handleSubmit() {
  submitted.value = true
  if (props.acceptedAnswers && props.acceptedAnswers.length > 0) {
    isCorrect.value = props.acceptedAnswers.some(
      (a) => a.trim().toLowerCase() === answer.value.trim().toLowerCase(),
    )
  }
  emit('answer', { answer: answer.value, correct: isCorrect.value })
}
</script>

<template>
  <div class="sa-block">
    <p class="sa-question"><strong>{{ question }}</strong></p>

    <input
      type="text"
      v-model="answer"
      placeholder="Type your answer…"
      :disabled="submitted"
      class="sa-input"
    />

    <button @click="handleSubmit" :disabled="answer.trim() === '' || submitted">Submit</button>

    <p v-if="submitted && acceptedAnswers && acceptedAnswers.length > 0" class="sa-feedback">
      {{ isCorrect ? '✅ Correct!' : '❌ Incorrect. Accepted answers: ' + acceptedAnswers.join(', ') }}
    </p>
  </div>
</template>

<style scoped>
.sa-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}
.sa-input {
  display: block;
  margin: 8px 0;
  padding: 6px;
  width: 100%;
  max-width: 400px;
  box-sizing: border-box;
}
.sa-feedback {
  margin-top: 8px;
}
</style>
