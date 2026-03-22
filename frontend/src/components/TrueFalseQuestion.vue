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
    <div class="true-false__choices">
      <label
        class="true-false__choice"
        :class="{
          'true-false__choice--selected': selected === true,
          'true-false__choice--correct': submitted && correctAnswer === true,
          'true-false__choice--wrong': submitted && selected === true && correctAnswer !== true,
        }"
      >
        <input v-model="selected" type="radio" :value="true" :disabled="submitted" />
        <span>True</span>
      </label>

      <label
        class="true-false__choice"
        :class="{
          'true-false__choice--selected': selected === false,
          'true-false__choice--correct': submitted && correctAnswer === false,
          'true-false__choice--wrong': submitted && selected === false && correctAnswer !== false,
        }"
      >
        <input v-model="selected" type="radio" :value="false" :disabled="submitted" />
        <span>False</span>
      </label>
    </div>

    <div class="true-false__row">
      <button
        type="button"
        class="true-false__button"
        :disabled="selected === null || submitted"
        @click="handleSubmit"
      >
        Submit
      </button>
      <p v-if="submitted && correctAnswer !== undefined" class="true-false__feedback" :class="{ correct: selected === correctAnswer }">
        {{ selected === correctAnswer ? 'Correct!' : `Incorrect. The answer is ${correctAnswer ? 'True' : 'False'}.` }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.true-false {
  display: grid;
  gap: 0.65rem;
}

.true-false__choices {
  display: flex;
  gap: 0.5rem;
}

.true-false__choice {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  cursor: pointer;
  font-size: 0.93rem;
  color: var(--color-text);
  transition: border-color 0.1s;
}

.true-false__choice--selected {
  border-color: var(--color-primary);
}

.true-false__choice--correct {
  border-color: var(--color-green);
  color: var(--color-green);
  font-weight: 700;
}

.true-false__choice--wrong {
  border-color: #c0392b;
  color: #c0392b;
  text-decoration: line-through;
}

.true-false__row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.true-false__button {
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

.true-false__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.true-false__row p {
  margin: 0;
  font-size: 0.88rem;
  color: #c0392b;
}

.true-false__feedback {
  margin: 0;
  font-size: 0.88rem;
  color: #c0392b;
}

.true-false__feedback.correct {
  color: var(--color-green);
}
</style>
