<script setup lang="ts">
export interface MediaBlockProps {
  /** Long-form text / passage to display */
  text?: string
  /** URL to an image */
  imageUrl?: string
  /** URL to an audio file */
  audioUrl?: string
}

defineProps<MediaBlockProps>()
</script>

<template>
  <div class="media-block">
    <div v-if="text" class="media-text">
      <p style="white-space: pre-wrap;">{{ text }}</p>
    </div>

    <div v-if="imageUrl" class="media-image">
      <img :src="imageUrl" alt="Media image" />
    </div>

    <div v-if="audioUrl" class="media-audio">
      <audio controls :src="audioUrl">Your browser does not support audio.</audio>
    </div>
  </div>
</template>

<style scoped>
.media-block {
  border: 1px solid #ccc;
  padding: 12px;
  margin-bottom: 16px;
}
.media-image img {
  max-width: 100%;
  height: auto;
}
.media-audio {
  margin-top: 8px;
}
</style>
