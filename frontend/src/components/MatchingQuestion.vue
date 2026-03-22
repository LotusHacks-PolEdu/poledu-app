<script setup lang="ts">
import { ref } from 'vue'

export interface MatchingQuestionProps {
  question: string
  prompts: string[]
  choices: string[]
  correctMap?: number[]
}

const props = defineProps<MatchingQuestionProps>()
const answers = ref<(number | null)[]>(props.prompts.map(() => null))
const submitted = ref(false)

const emit = defineEmits<{
  (e: 'answer', payload: { answers: (number | null)[]; score: number; total: number }): void
}>()

function correctChoiceLabel(index: number) {
  if (!props.correctMap) {
    return ''
  }

  const choiceIndex = props.correctMap[index]
  return typeof choiceIndex === 'number' ? props.choices[choiceIndex] ?? '' : ''
}

function handleSubmit() {
  submitted.value = true
  let score = 0

  if (props.correctMap) {
    props.correctMap.forEach((correct, index) => {
      if (answers.value[index] === correct) {
        score += 1
      }
    })
  }

  emit('answer', { answers: answers.value, score, total: props.prompts.length })
}
</script>

<template>
  <div class="match-block">
    <p><strong>{{ question }}</strong></p>

    <table>
      <thead>
        <tr>
          <th>Prompt</th>
          <th>Your Match</th>
          <th v-if="submitted && correctMap">Result</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(prompt, i) in prompts" :key="i">
          <td>{{ prompt }}</td>
          <td>
            <select v-model="answers[i]" :disabled="submitted">
              <option :value="null" disabled>-- select --</option>
              <option v-for="(choice, choiceIndex) in choices" :key="choiceIndex" :value="choiceIndex">
                {{ choice }}
              </option>
            </select>
          </td>
          <td v-if="submitted && correctMap">
            {{ answers[i] === correctMap[i] ? 'Correct' : `Incorrect -> ${correctChoiceLabel(i)}` }}
          </td>
        </tr>
      </tbody>
    </table>

    <button @click="handleSubmit" :disabled="submitted">Submit</button>

    <p v-if="submitted && correctMap" class="match-feedback">
      Score: {{ correctMap.filter((choiceIndex, i) => answers[i] === choiceIndex).length }} / {{ prompts.length }}
    </p>
  </div>
</template>

<style scoped>
.match-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}

table {
  border-collapse: collapse;
  margin: 8px 0;
}

th,
td {
  border: 1px solid #ddd;
  padding: 6px 10px;
  text-align: left;
}

.match-feedback {
  margin-top: 8px;
}
</style>
