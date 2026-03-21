<script setup lang="ts">
import { ref } from 'vue'

export interface OrderingQuestionProps {
  /** Instruction text */
  question: string
  /** Items displayed in shuffled order */
  items: string[]
  /** Correct order as array of original indices, optional — used for grading */
  correctOrder?: number[]
}

const props = defineProps<OrderingQuestionProps>()

// Build a mutable ordering (indices into `items`)
const order = ref<number[]>(props.items.map((_, i) => i))
const submitted = ref(false)

function moveUp(index: number) {
  if (index === 0) return
  const arr = [...order.value]
  ;[arr[index - 1], arr[index]] = [arr[index], arr[index - 1]]
  order.value = arr
}

function moveDown(index: number) {
  if (index === order.value.length - 1) return
  const arr = [...order.value]
  ;[arr[index], arr[index + 1]] = [arr[index + 1], arr[index]]
  order.value = arr
}

const emit = defineEmits<{
  (e: 'answer', payload: { order: number[]; correct: boolean }): void
}>()

function handleSubmit() {
  submitted.value = true
  const correct =
    props.correctOrder !== undefined &&
    JSON.stringify(order.value) === JSON.stringify(props.correctOrder)
  emit('answer', { order: order.value, correct })
}
</script>

<template>
  <div class="order-block">
    <p><strong>{{ question }}</strong></p>

    <ol>
      <li v-for="(idx, pos) in order" :key="idx" class="order-item">
        <span>{{ items[idx] }}</span>
        <button @click="moveUp(pos)" :disabled="pos === 0 || submitted">▲</button>
        <button @click="moveDown(pos)" :disabled="pos === order.length - 1 || submitted">▼</button>
      </li>
    </ol>

    <button @click="handleSubmit" :disabled="submitted">Submit</button>

    <p v-if="submitted && correctOrder !== undefined" class="order-feedback">
      {{ JSON.stringify(order) === JSON.stringify(correctOrder) ? '✅ Correct order!' : '❌ Incorrect order.' }}
    </p>
  </div>
</template>

<style scoped>
.order-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}
.order-item {
  margin: 4px 0;
}
.order-item button {
  margin-left: 6px;
  cursor: pointer;
}
.order-feedback {
  margin-top: 8px;
}
</style>
