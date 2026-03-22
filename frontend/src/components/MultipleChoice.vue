<script setup lang="ts">
import { ref } from 'vue'

export interface MultipleChoiceProps {
  question: string
  options: string[]
  correctIndex?: number
}

const props = defineProps<MultipleChoiceProps>()
const selected = ref<number | null>(null)
const submitted = ref(false)

const emit = defineEmits<{
  (e: 'answer', payload: { selected: number; correct: boolean }): void
}>()

function handleSubmit() {
  submitted.value = true
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
    <div class="mc-options">
      <label
        v-for="(opt, i) in options"
        :key="i"
        class="mc-option"
        :class="{
          'mc-option--correct': submitted && correctIndex !== undefined && i === correctIndex,
          'mc-option--wrong': submitted && selected === i && correctIndex !== undefined && i !== correctIndex,
          'mc-option--selected': selected === i,
        }"
      >
        <input
          type="radio"
          :name="'mc-' + question"
          :value="i"
          v-model="selected"
          :disabled="submitted"
        />
        <span>{{ opt }}</span>
      </label>
    </div>

    <div class="mc-row">
      <button
        type="button"
        class="mc-button"
        :disabled="selected === null || submitted"
        @click="handleSubmit"
      >
        Submit
      </button>
      <p v-if="submitted && correctIndex !== undefined" class="mc-feedback" :class="{ correct: selected === correctIndex }">
        {{ selected === correctIndex ? 'Correct!' : 'Incorrect. The correct answer is: ' + options[correctIndex] }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.mc-block {
  display: grid;
  gap: 0.65rem;
}

.mc-options {
  display: grid;
  gap: 0.4rem;
}

.mc-option {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.85rem;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  cursor: pointer;
  font-size: 0.93rem;
  color: var(--color-text);
  transition: border-color 0.1s;
}

.mc-option--selected {
  border-color: var(--color-primary);
}

.mc-option--correct {
  border-color: var(--color-green);
  color: var(--color-green);
  font-weight: 700;
}

.mc-option--wrong {
  border-color: #c0392b;
  color: #c0392b;
  text-decoration: line-through;
}

.mc-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.mc-button {
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

.mc-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.mc-feedback {
  margin: 0;
  font-size: 0.88rem;
  color: #c0392b;
}

.mc-feedback.correct {
  color: var(--color-green);
}
</style>
