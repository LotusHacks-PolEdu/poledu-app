<script setup lang="ts">
import { ref } from 'vue'

export interface TrueFalseQuestionProps {
  question: string
  correctAnswer?: boolean
}

const props = defineProps<TrueFalseQuestionProps>()
const selected = ref<boolean | null>(null)
const submitted = ref(false)

const emit = defineEmits<{
  (e: 'answer', payload: { selected: boolean; correct: boolean }): void
}>()

function handleSubmit(): void {
  submitted.value = true
  if (selected.value === null) {
    return
  }

  emit('answer', {
    selected: selected.value,
    correct: props.correctAnswer !== undefined && selected.value === props.correctAnswer,
  })
}
</script>

<template>
  <div class="true-false">
    <p class="true-false__question"><strong>{{ question }}</strong></p>

    <label class="true-false__choice">
      <input v-model="selected" type="radio" :value="true" :disabled="submitted" />
      <span>True</span>
    </label>

    <label class="true-false__choice">
      <input v-model="selected" type="radio" :value="false" :disabled="submitted" />
      <span>False</span>
    </label>

    <button
      type="button"
      class="true-false__button"
      :disabled="selected === null || submitted"
      @click="handleSubmit"
    >
      Submit
    </button>

    <p v-if="submitted && correctAnswer !== undefined" class="true-false__feedback">
      {{ selected === correctAnswer ? 'Correct.' : `Incorrect. The answer is ${correctAnswer ? 'True' : 'False'}.` }}
    </p>
  </div>
</template>

<style scoped>
.true-false {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 1rem;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.45);
}

.true-false__question {
  margin: 0 0 0.85rem;
}

.true-false__choice {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0.45rem 0;
}

.true-false__button {
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

.true-false__button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.true-false__feedback {
  margin: 0.8rem 0 0;
  color: #dbeafe;
}
</style>
