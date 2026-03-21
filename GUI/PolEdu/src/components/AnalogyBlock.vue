<script setup lang="ts">
defineProps<{
  analogy: string
  connection: string
}>()
</script>

<template>
  <div class="analogy">
    <div class="analogy__icon">💡</div>
    <div class="analogy__body">
      <p class="analogy__text">"{{ analogy }}"</p>
      <p class="analogy__connection">{{ connection }}</p>
    </div>
  </div>
</template>

<style scoped>
.analogy {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.85rem;
  border-radius: 0.85rem;
  background: var(--color-yellow-dim);
  border-left: 3px solid var(--color-yellow);
}

.analogy__icon {
  font-size: 1.2rem;
  flex-shrink: 0;
  line-height: 1;
  margin-top: 0.1rem;
}

.analogy__body {
  display: grid;
  gap: 0.3rem;
  min-width: 0;
}

.analogy__text {
  margin: 0;
  font-family: var(--font-body);
  font-size: 0.93rem;
  font-style: italic;
  line-height: 1.6;
  color: var(--color-text);
  word-break: break-word;
}

.analogy__connection {
  margin: 0;
  font-family: var(--font-body);
  font-size: 0.82rem;
  color: var(--color-yellow);
  font-weight: 700;
  word-break: break-word;
}
</style>
