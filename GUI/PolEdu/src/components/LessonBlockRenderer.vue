<script setup lang="ts">
import { ref } from 'vue'

import type {
  LessonGraphBlock,
  LessonGraphPlaygroundBlock,
  LessonSection,
  LessonTextBlock,
} from '../types/lessons'
import GraphBlock from './GraphBlock.vue'
import GraphPlayground from './GraphPlayground.vue'
import LatexFormula from './LatexFormula.vue'

defineProps<{
  section: LessonSection
}>()

const activePlayground = ref<LessonGraphPlaygroundBlock | null>(null)

function openPlayground(block: LessonGraphPlaygroundBlock): void {
  activePlayground.value = block
}

function closePlayground(): void {
  activePlayground.value = null
}

function isTextBlock(block: LessonSection['blocks'][number]): block is LessonTextBlock {
  return block.type === 'text'
}

function isGraphBlock(block: LessonSection['blocks'][number]): block is LessonGraphBlock {
  return block.type === 'graph'
}

function isGraphPlaygroundBlock(
  block: LessonSection['blocks'][number],
): block is LessonGraphPlaygroundBlock {
  return block.type === 'graph-playground'
}
</script>

<template>
  <section class="lesson-section">
    <header class="lesson-section__header">
      <h2>{{ section.title }}</h2>
    </header>

    <div class="lesson-section__blocks">
      <article
        v-for="block in section.blocks"
        :key="block.id"
        class="lesson-block"
        :class="`lesson-block--${block.type}`"
      >
        <template v-if="isTextBlock(block)">
          <h3>{{ block.title }}</h3>
          <p>{{ block.content }}</p>
          <LatexFormula
            v-for="expression in block.latex || []"
            :key="`${block.id}-${expression}`"
            :expression="expression"
          />
        </template>

        <template v-else-if="isGraphBlock(block)">
          <h3>{{ block.title }}</h3>
          <p class="lesson-block__prompt">{{ block.prompt }}</p>
          <GraphBlock
            :expression="block.expression"
            :xMin="block.xMin"
            :xMax="block.xMax"
            :yMin="block.yMin"
            :yMax="block.yMax"
            :color="block.color"
          />
        </template>

        <template v-else-if="isGraphPlaygroundBlock(block)">
          <h3>{{ block.title }}</h3>
          <p class="lesson-block__prompt">{{ block.prompt }}</p>
          <div class="lesson-block__playground-card">
            <strong>Challenge</strong>
            <p>{{ block.challenge }}</p>
            <button type="button" @click="openPlayground(block)">Open graph playground</button>
          </div>
        </template>
      </article>
    </div>

    <GraphPlayground
      :visible="activePlayground !== null"
      :title="activePlayground?.title"
      :hint="activePlayground ? `${activePlayground.prompt} ${activePlayground.challenge}` : ''"
      :initial-expression="activePlayground?.initial_expression || 'x^2'"
      @close="closePlayground"
    />
  </section>
</template>

<style scoped>
.lesson-section {
  display: grid;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 1.5rem;
  background: rgba(15, 23, 42, 0.52);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.lesson-section__header h2 {
  margin: 0;
  font-size: 1.35rem;
}

.lesson-section__blocks {
  display: grid;
  gap: 1rem;
}

.lesson-block {
  padding: 1rem;
  border-radius: 1.15rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.lesson-block h3 {
  margin: 0 0 0.55rem;
}

.lesson-block p {
  margin: 0;
  line-height: 1.7;
  color: #dbeafe;
}

.lesson-block__prompt {
  margin-bottom: 0.85rem;
}

.lesson-block__playground-card {
  display: grid;
  gap: 0.55rem;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(15, 118, 110, 0.14);
}

.lesson-block__playground-card strong {
  color: #99f6e4;
}

.lesson-block__playground-card button {
  justify-self: start;
  border: none;
  border-radius: 0.85rem;
  padding: 0.75rem 1rem;
  background: #14b8a6;
  color: #022c22;
  cursor: pointer;
  font-weight: 700;
}
</style>
