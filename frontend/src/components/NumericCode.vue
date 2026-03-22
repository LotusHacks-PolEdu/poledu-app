<script setup lang="ts">
import { ref, computed } from 'vue'

export interface NumericCodeProps {
  /** The question / prompt text */
  question: string
  /** How many digit boxes to show (default 4) */
  length?: number
  /** The correct code as a string, e.g. "1234", "-3.2". Optional — used for grading. */
  correctCode?: string
}

const props = withDefaults(defineProps<NumericCodeProps>(), {
  length: 4,
})

const digits = ref<string[]>(Array.from({ length: props.length }, () => ''))
const submitted = ref(false)
const inputRefs = ref<(HTMLInputElement | null)[]>([])

const code = computed(() => digits.value.join(''))
const anyFilled = computed(() => digits.value.some((d) => d !== ''))

function setRef(el: any, i: number) {
  inputRefs.value[i] = el as HTMLInputElement | null
}

/** Check whether `char` is allowed at 0-based `index`. */
function isAllowed(char: string, index: number): boolean {
  // Digits are always allowed
  if (/^\d$/.test(char)) return true

  // Minus sign: allowed at positions 0, 1, 2 (user's "position 1, 2, 3")
  // Only one minus across all boxes
  if (char === '-' && index <= 2) {
    const hasMinus = digits.value.some((d, i) => d === '-' && i !== index)
    return !hasMinus
  }

  // Decimal point: allowed at positions 1, 2 (user's "position 2, 3")
  // Only one decimal across all boxes
  if (char === '.' && index >= 1 && index <= 2) {
    const hasDot = digits.value.some((d, i) => d === '.' && i !== index)
    return !hasDot
  }

  return false
}

function handleInput(event: Event, index: number) {
  const target = event.target as HTMLInputElement
  const raw = target.value.slice(-1) // take last typed character

  // Empty means the user deleted — allow clearing the box
  if (!raw) {
    digits.value[index] = ''
    target.value = ''
    return
  }

  if (isAllowed(raw, index)) {
    digits.value[index] = raw
    target.value = raw

    // Auto-advance to next box
    if (index < props.length - 1) {
      inputRefs.value[index + 1]?.focus()
    }
  } else {
    // Reject — restore previous value
    target.value = digits.value[index] ?? ''
  }
}

function handleKeydown(event: KeyboardEvent, index: number) {
  if (event.key === 'Backspace') {
    if (digits.value[index]) {
      // Clear current box
      digits.value[index] = ''
    } else if (index > 0) {
      // Already empty — move focus back
      inputRefs.value[index - 1]?.focus()
    }
  }
}

function handlePaste(event: ClipboardEvent) {
  event.preventDefault()
  const pasted = (event.clipboardData?.getData('text') ?? '').slice(0, props.length)
  // Validate each pasted character positionally
  for (let i = 0; i < props.length; i++) {
    digits.value[i] = '' // clear first so isAllowed can re-check uniqueness
  }
  for (let i = 0; i < props.length; i++) {
    const ch = pasted[i] ?? ''
    digits.value[i] = isAllowed(ch, i) ? ch : ''
  }
  // Focus the next empty box or the last one
  const nextEmpty = digits.value.findIndex((d) => d === '')
  const focusIdx = nextEmpty === -1 ? props.length - 1 : nextEmpty
  inputRefs.value[focusIdx]?.focus()
}

const emit = defineEmits<{
  (e: 'answer', payload: { code: string; correct: boolean }): void
}>()

function handleSubmit() {
  submitted.value = true
  emit('answer', {
    code: code.value,
    correct: props.correctCode !== undefined && code.value === props.correctCode,
  })
}
</script>

<template>
  <div class="nc-block">
    <p><strong>{{ question }}</strong></p>

    <div class="nc-digits" @paste="handlePaste">
      <input
        v-for="(_, i) in length"
        :key="i"
        :ref="(el) => setRef(el, i)"
        type="text"
        inputmode="numeric"
        maxlength="1"
        class="nc-box"
        :value="digits[i]"
        @input="handleInput($event, i)"
        @keydown="handleKeydown($event, i)"
        :disabled="submitted"
      />
    </div>

    <button @click="handleSubmit" :disabled="!anyFilled || submitted">Submit</button>

    <p v-if="submitted && correctCode !== undefined" class="nc-feedback">
      {{ code === correctCode ? '✅ Correct!' : '❌ Incorrect. The answer is: ' + correctCode }}
    </p>
  </div>
</template>

<style scoped>
.nc-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}
.nc-digits {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}
.nc-box {
  width: 48px;
  height: 56px;
  text-align: center;
  font-size: 24px;
  font-weight: bold;
  border: 2px solid #aaa;
  border-radius: 6px;
  outline: none;
}
.nc-box:focus {
  border-color: #2563eb;
}
.nc-feedback {
  margin-top: 8px;
}
</style>
