<script setup lang="ts">
import { ref } from 'vue'

export interface WritingTaskProps {
  taskNumber: number
  instruction: string
  prompt?: string
  dataDescription?: string
}

defineProps<WritingTaskProps>()
const answer = ref('')
</script>

<template>
  <div class="wt-block">
    <h4>Writing Task {{ taskNumber }}</h4>
    <p class="wt-instruction"><em>{{ instruction }}</em></p>
    <p v-if="dataDescription" class="wt-data">{{ dataDescription }}</p>
    <p v-if="prompt" class="wt-prompt"><strong>{{ prompt }}</strong></p>
    <textarea v-model="answer" rows="12" placeholder="Write your answer here…" class="wt-textarea"></textarea>
    <p class="wt-count">Word count: {{ answer.trim() ? answer.trim().split(/\s+/).length : 0 }}</p>
  </div>
</template>

<style scoped>
.wt-block { border: 1px solid #ccc; padding: 16px; margin-bottom: 16px; }
.wt-instruction { color: #555; margin-bottom: 8px; }
.wt-data { background: #f9f9f9; padding: 12px; border-radius: 6px; white-space: pre-wrap; margin-bottom: 12px; font-size: 14px; }
.wt-prompt { margin-bottom: 12px; }
.wt-textarea { width: 100%; padding: 10px; font-size: 15px; border: 1px solid #ccc; border-radius: 6px; resize: vertical; box-sizing: border-box; }
.wt-count { margin-top: 4px; font-size: 13px; color: #888; }
</style>
