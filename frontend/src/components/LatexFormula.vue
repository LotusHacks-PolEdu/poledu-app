<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

declare global {
  interface Window {
    katex?: {
      renderToString: (
        expression: string,
        options?: { throwOnError?: boolean; displayMode?: boolean },
      ) => string
    }
  }
}

const props = withDefaults(
  defineProps<{
    expression: string
    displayMode?: boolean
  }>(),
  {
    displayMode: true,
  },
)

let katexLoader: Promise<void> | null = null

const renderedHtml = ref('')

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function ensureStylesheet(): void {
  if (document.querySelector('link[data-katex-styles="true"]')) {
    return
  }

  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css'
  link.dataset.katexStyles = 'true'
  document.head.appendChild(link)
}

function ensureKatex(): Promise<void> {
  if (window.katex) {
    return Promise.resolve()
  }

  if (katexLoader) {
    return katexLoader
  }

  katexLoader = new Promise((resolve, reject) => {
    ensureStylesheet()

    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js'
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load KaTeX'))
    document.head.appendChild(script)
  })

  return katexLoader
}

async function renderExpression(): Promise<void> {
  const expression = props.expression.trim()
  if (!expression) {
    renderedHtml.value = ''
    return
  }

  try {
    await ensureKatex()
    if (!window.katex) {
      renderedHtml.value = `<code>${escapeHtml(expression)}</code>`
      return
    }

    renderedHtml.value = window.katex.renderToString(expression, {
      throwOnError: false,
      displayMode: props.displayMode,
    })
  } catch {
    renderedHtml.value = `<code>${escapeHtml(expression)}</code>`
  }
}

const wrapperClass = computed(() => ({
  'latex-formula': true,
  'latex-formula--inline': !props.displayMode,
}))

watch(
  () => [props.expression, props.displayMode],
  () => {
    void renderExpression()
  },
)

onMounted(() => {
  void renderExpression()
})
</script>

<template>
  <div :class="wrapperClass" v-html="renderedHtml"></div>
</template>

<style scoped>
.latex-formula {
  padding: 0.35rem 0;
  overflow-x: auto;
}

.latex-formula--inline {
  display: inline-block;
  padding: 0;
}

.latex-formula :deep(.katex-display) {
  margin: 0;
}
</style>
