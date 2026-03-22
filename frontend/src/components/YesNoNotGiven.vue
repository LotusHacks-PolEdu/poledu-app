<script setup lang="ts">
import { ref } from 'vue'

export interface YesNoNotGivenProps {
  statement: string
  correctAnswer?: 'yes' | 'no' | 'not-given'
}

const props = defineProps<YesNoNotGivenProps>()
const selected = ref<string | null>(null)
const submitted = ref(false)

const choices = ['yes', 'no', 'not-given'] as const
const labels: Record<string, string> = {
  yes: 'Yes',
  no: 'No',
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
  <div class="ynng-block">
    <p class="ynng-statement"><strong>{{ statement }}</strong></p>
    <div v-for="c in choices" :key="c" class="ynng-option">
      <label
        :class="{
          correct: submitted && correctAnswer !== undefined && c === correctAnswer,
          wrong: submitted && selected === c && correctAnswer !== undefined && c !== correctAnswer,
        }"
      >
        <input type="radio" :name="'ynng-' + statement" :value="c" v-model="selected" :disabled="submitted" />
        {{ labels[c] }}
      </label>
    </div>
    <button @click="handleSubmit" :disabled="selected === null || submitted">Submit</button>
    <p v-if="submitted && correctAnswer !== undefined" class="ynng-feedback">
      {{ selected === correctAnswer ? '✅ Correct!' : '❌ Incorrect. The answer is: ' + labels[correctAnswer] }}
    </p>
  </div>
</template>

<style scoped>
.ynng-block { border: 1px solid #ccc; padding: 12px; margin-bottom: 16px; }
.ynng-option { margin: 4px 0; }
.correct { color: green; font-weight: bold; }
.wrong { color: red; text-decoration: line-through; }
.ynng-feedback { margin-top: 8px; }
</style>
