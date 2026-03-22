<script setup lang="ts">
import { ref } from 'vue'

export interface TrueFalseNotGivenProps {
  /** The statement to evaluate */
  statement: string
  /** The correct answer: 'true' | 'false' | 'not-given', optional */
  correctAnswer?: 'true' | 'false' | 'not-given'
}

const props = defineProps<TrueFalseNotGivenProps>()
const selected = ref<string | null>(null)
const submitted = ref(false)

const choices = ['true', 'false', 'not-given'] as const
const labels: Record<string, string> = {
  true: 'True',
  false: 'False',
  'not-given': 'Not Given',
}

const emit = defineEmits<{
  (e: 'answer', payload: { selected: string; correct: boolean }): void
}>()

function handleSubmit() {
  submitted.value = true
  if (selected.value) {
    emit('answer', {
      selected: selected.value,
      correct: props.correctAnswer !== undefined && selected.value === props.correctAnswer,
    })
  }
}
</script>

<template>
  <div class="tfng-block">
    <p class="tfng-statement"><strong>{{ statement }}</strong></p>

    <div v-for="c in choices" :key="c" class="tfng-option">
      <label
        :class="{
          correct: submitted && correctAnswer !== undefined && c === correctAnswer,
          wrong: submitted && selected === c && correctAnswer !== undefined && c !== correctAnswer,
        }"
      >
        <input
          type="radio"
          :name="'tfng-' + statement"
          :value="c"
          v-model="selected"
          :disabled="submitted"
        />
        {{ labels[c] }}
      </label>
    </div>

    <button @click="handleSubmit" :disabled="selected === null || submitted">Submit</button>

    <p v-if="submitted && correctAnswer !== undefined" class="tfng-feedback">
      {{ selected === correctAnswer ? '✅ Correct!' : '❌ Incorrect. The answer is: ' + labels[correctAnswer] }}
    </p>
  </div>
</template>

<style scoped>
.tfng-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}
.tfng-option {
  margin: 4px 0;
}
.correct {
  color: green;
  font-weight: bold;
}
.wrong {
  color: red;
  text-decoration: line-through;
}
.tfng-feedback {
  margin-top: 8px;
}
</style>
