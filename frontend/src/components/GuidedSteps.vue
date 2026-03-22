<script setup lang="ts">
import { ref } from 'vue'

import type { GuidedStep } from '../types/lessons'
import LatexFormula from './LatexFormula.vue'

defineProps<{
  prompt: string
  steps: GuidedStep[]
}>()

const revealed = ref<Set<number>>(new Set())

function reveal(index: number): void {
  revealed.value = new Set([...revealed.value, index])
}
</script>

<template>
  <div class="guided-steps">
    <p class="guided-steps__prompt">{{ prompt }}</p>

    <ol class="guided-steps__list">
      <li
        v-for="(step, i) in steps"
        :key="i"
        class="guided-steps__step"
        :class="{ 'guided-steps__step--revealed': revealed.has(i) }"
      >
        <div class="guided-steps__instruction">
          <span class="guided-steps__num">{{ i + 1 }}</span>
          <p>{{ step.instruction }}</p>
        </div>

        <div v-if="revealed.has(i)" class="guided-steps__reveal">
          <p>{{ step.reveal }}</p>
          <LatexFormula v-if="step.latex" :expression="step.latex" />
        </div>

        <button
          v-if="!revealed.has(i)"
          type="button"
          class="guided-steps__reveal-btn"
          @click="reveal(i)"
        >
          Reveal →
        </button>
        <span v-else class="guided-steps__done">✓ Got it</span>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.guided-steps {
  display: grid;
  gap: 0.75rem;
}

.guided-steps__prompt {
  margin: 0;
  font-size: 0.88rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.guided-steps__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.6rem;
}

.guided-steps__step {
  border: 1px solid var(--color-border);
  border-radius: 0.85rem;
  padding: 0.75rem;
  background: var(--color-bg);
  display: grid;
  gap: 0.5rem;
  transition: border-color 0.15s;
  min-width: 0;
  overflow: hidden;
}

.guided-steps__step--revealed {
  border-color: var(--color-primary);
  background: var(--color-primary-dim);
}

.guided-steps__instruction {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  min-width: 0;
}

.guided-steps__num {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-primary);
  color: #1A1A1A;
  font-weight: 700;
  font-size: 0.72rem;
  font-family: var(--font-body);
}

.guided-steps__instruction p {
  margin: 0;
  font-size: 0.93rem;
  color: var(--color-text);
  line-height: 1.5;
  word-break: break-word;
  overflow-wrap: break-word;
  min-width: 0;
}

.guided-steps__reveal {
  padding: 0.5rem 0.75rem;
  border-left: 3px solid var(--color-primary);
  margin-left: 2.15rem;
  min-width: 0;
  overflow: hidden;
}

.guided-steps__reveal p {
  margin: 0 0 0.3rem;
  font-size: 0.88rem;
  color: var(--color-text);
  font-weight: 600;
  word-break: break-word;
  overflow-wrap: break-word;
}

/* LaTeX inside steps scrolls horizontally instead of overflowing */
:deep(.katex-display),
:deep(.katex) {
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
}

.guided-steps__reveal-btn {
  justify-self: start;
  margin-left: 2.15rem;
  border: 1px solid var(--color-primary);
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  background: transparent;
  color: var(--color-primary);
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
}

.guided-steps__reveal-btn:hover {
  background: var(--color-primary-dim);
}

.guided-steps__done {
  justify-self: start;
  margin-left: 2.15rem;
  font-size: 0.8rem;
  color: var(--color-green);
  font-weight: 700;
  font-family: var(--font-body);
}
</style>
