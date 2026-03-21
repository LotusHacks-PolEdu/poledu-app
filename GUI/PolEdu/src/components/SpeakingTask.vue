<script setup lang="ts">
export interface SpeakingTaskProps {
  partLabel: string
  topic: string
  questions?: string[]
  cueCardTopic?: string
  bulletPoints?: string[]
  instruction?: string
}

defineProps<SpeakingTaskProps>()
</script>

<template>
  <div class="st-block">
    <h4>{{ partLabel }}</h4>
    <p class="st-topic"><strong>Topic:</strong> {{ topic }}</p>
    <p v-if="instruction" class="st-instruction"><em>{{ instruction }}</em></p>

    <div v-if="cueCardTopic" class="st-cue">
      <p><strong>{{ cueCardTopic }}</strong></p>
      <ul v-if="bulletPoints">
        <li v-for="(bp, i) in bulletPoints" :key="i">{{ bp }}</li>
      </ul>
    </div>

    <ol v-if="questions && questions.length">
      <li v-for="(q, i) in questions" :key="i">{{ q }}</li>
    </ol>
  </div>
</template>

<style scoped>
.st-block { border: 1px solid #ccc; padding: 16px; margin-bottom: 16px; }
.st-topic { margin-bottom: 8px; }
.st-instruction { color: #555; margin-bottom: 8px; }
.st-cue { background: #f9f9f9; padding: 12px; border-radius: 6px; margin-bottom: 12px; }
</style>
