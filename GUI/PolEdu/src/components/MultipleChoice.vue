<script setup lang="ts">
import { ref } from 'vue'

export interface MultipleChoiceProps {
  /** The question text */
  question: string
  /** Array of option strings */
  options: string[]
  /** Index of the correct answer (0-based), optional — used for grading */
  correctIndex?: number
}

const props = defineProps<MultipleChoiceProps>()
const selected = ref<number | null>(null)
const submitted = ref(false)

function submit() {
  submitted.value = true
}

const emit = defineEmits<{
  (e: 'answer', payload: { selected: number; correct: boolean }): void
}>()

function handleSubmit() {
  submit()
  if (selected.value !== null) {
    emit('answer', {
      selected: selected.value,
      correct: props.correctIndex !== undefined && selected.value === props.correctIndex,
    })
  }
}
</script>

<template>
  <div class="mc-block">
    <p class="mc-question"><strong>{{ question }}</strong></p>

    <div v-for="(opt, i) in options" :key="i" class="mc-option">
      <label
        :class="{
          'correct': submitted && correctIndex !== undefined && i === correctIndex,
          'wrong': submitted && selected === i && correctIndex !== undefined && i !== correctIndex,
        }"
      >
        <input
          type="radio"
          :name="'mc-' + question"
          :value="i"
          v-model="selected"
          :disabled="submitted"
        />
        {{ opt }}
      </label>
    </div>

    <button @click="handleSubmit" :disabled="selected === null || submitted">Submit</button>

    <p v-if="submitted && correctIndex !== undefined" class="mc-feedback">
      {{ selected === correctIndex ? '✅ Correct!' : '❌ Incorrect. The correct answer is: ' + options[correctIndex] }}
    </p>
  </div>
</template>

<style scoped>
.mc-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}
.mc-option {
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
.mc-feedback {
  margin-top: 8px;
}
</style>
