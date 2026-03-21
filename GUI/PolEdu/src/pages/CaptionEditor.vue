<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'

interface Caption {
  start: number
  end: number
  text: string
}

const audioRef = ref<HTMLAudioElement | null>(null)
const captions = ref<Caption[]>([])
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const audioSrc = ref('')
const exportJson = ref('')
const showExport = ref(false)
const editingIndex = ref<number | null>(null)

let animFrame = 0

// Load audio file from picker
function loadAudio() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'audio/*'
  input.onchange = () => {
    const file = input.files?.[0]
    if (!file) return
    audioSrc.value = URL.createObjectURL(file)
    captions.value = []
    showExport.value = false
  }
  input.click()
}

function onAudioLoaded() {
  duration.value = audioRef.value?.duration ?? 0
}

function togglePlay() {
  const a = audioRef.value
  if (!a) return
  if (a.paused) {
    a.play()
    isPlaying.value = true
    tickTime()
  } else {
    a.pause()
    isPlaying.value = false
    cancelAnimationFrame(animFrame)
  }
}

function tickTime() {
  const a = audioRef.value
  if (!a) return
  currentTime.value = a.currentTime
  if (!a.paused && !a.ended) {
    animFrame = requestAnimationFrame(tickTime)
  } else {
    isPlaying.value = false
  }
}

function seekTo(e: MouseEvent) {
  const a = audioRef.value
  const bar = e.currentTarget as HTMLElement
  if (!a || !bar) return
  const rect = bar.getBoundingClientRect()
  const pct = (e.clientX - rect.left) / rect.width
  a.currentTime = pct * duration.value
  currentTime.value = a.currentTime
}

// Mark a new caption at current time
function markCaption() {
  const t = currentTime.value

  // Close previous caption's end time
  if (captions.value.length > 0) {
    const last = captions.value[captions.value.length - 1]!
    if (last.end === 0 || last.end > t) {
      last.end = parseFloat(t.toFixed(2))
    }
  }

  captions.value.push({
    start: parseFloat(t.toFixed(2)),
    end: 0,
    text: '',
  })

  // Focus the new text input
  nextTick(() => {
    const inputs = document.querySelectorAll<HTMLInputElement>('.cap-text-input')
    const lastInput = inputs[inputs.length - 1]
    lastInput?.focus()
  })
}

// Add a caption manually
function addCaption() {
  const lastEnd = captions.value.length > 0
    ? captions.value[captions.value.length - 1]!.end || currentTime.value
    : 0
  captions.value.push({
    start: parseFloat(lastEnd.toFixed(2)),
    end: 0,
    text: '',
  })
}

function deleteCaption(i: number) {
  captions.value.splice(i, 1)
}

function finalizeAndExport() {
  // Set last caption's end to audio duration if unset
  if (captions.value.length > 0) {
    const last = captions.value[captions.value.length - 1]!
    if (last.end === 0) {
      last.end = parseFloat(duration.value.toFixed(2))
    }
  }
  exportJson.value = JSON.stringify(captions.value, null, 2)
  showExport.value = true
}

function copyExport() {
  navigator.clipboard.writeText(exportJson.value)
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  const ms = Math.floor((s % 1) * 100)
  return `${m}:${String(sec).padStart(2, '0')}.${String(ms).padStart(2, '0')}`
}

// Keyboard shortcut: Space = mark caption, P = play/pause
function handleKey(e: KeyboardEvent) {
  // Don't intercept when typing in an input
  if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return

  if (e.code === 'Space') {
    e.preventDefault()
    markCaption()
  } else if (e.code === 'KeyP') {
    e.preventDefault()
    togglePlay()
  }
}

onMounted(() => window.addEventListener('keydown', handleKey))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKey)
  cancelAnimationFrame(animFrame)
})
</script>

<template>
  <div class="editor-page">
    <router-link to="/" class="back-link">← Home</router-link>
    <h1>🎬 Caption Timing Editor</h1>

    <!-- Load audio -->
    <div v-if="!audioSrc" class="load-area">
      <button class="btn primary" @click="loadAudio">📂 Load Audio File</button>
      <p class="hint">Load an MP3 or audio file to start creating captions.</p>
    </div>

    <template v-if="audioSrc">
      <audio ref="audioRef" :src="audioSrc" @loadedmetadata="onAudioLoaded" preload="auto"></audio>

      <!-- Player controls -->
      <div class="player">
        <button class="btn play-btn" @click="togglePlay">
          {{ isPlaying ? '⏸ Pause' : '▶ Play' }}
        </button>
        <span class="time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
        <div class="seek-bar" @click="seekTo">
          <div class="seek-fill" :style="{ width: (duration ? (currentTime / duration) * 100 : 0) + '%' }"></div>
          <div class="seek-head" :style="{ left: (duration ? (currentTime / duration) * 100 : 0) + '%' }"></div>
        </div>
      </div>

      <!-- Instructions -->
      <div class="shortcuts">
        <kbd>Space</kbd> Mark caption at current time &nbsp;|&nbsp;
        <kbd>P</kbd> Play / Pause
      </div>

      <!-- Mark + Add buttons -->
      <div class="action-row">
        <button class="btn primary" @click="markCaption">⏱ Mark Caption Here</button>
        <button class="btn" @click="addCaption">+ Add Caption Manually</button>
      </div>

      <!-- Captions list -->
      <div v-if="captions.length" class="captions-list">
        <div v-for="(cap, i) in captions" :key="i" class="cap-row">
          <span class="cap-num">#{{ i + 1 }}</span>

          <div class="cap-times">
            <label>
              Start
              <input type="number" v-model.number="cap.start" step="0.1" min="0" class="time-input" />
            </label>
            <label>
              End
              <input type="number" v-model.number="cap.end" step="0.1" min="0" class="time-input" />
            </label>
          </div>

          <input
            type="text"
            v-model="cap.text"
            placeholder="Type caption text…"
            class="cap-text-input"
          />

          <button class="btn-icon delete" @click="deleteCaption(i)" title="Delete">✕</button>
        </div>
      </div>

      <!-- Export -->
      <div class="export-row">
        <button class="btn primary" @click="finalizeAndExport" :disabled="captions.length === 0">
          📋 Export JSON
        </button>
      </div>

      <div v-if="showExport" class="export-block">
        <div class="export-header">
          <strong>Paste this into your captions array:</strong>
          <button class="btn small" @click="copyExport">📋 Copy</button>
        </div>
        <pre class="export-code">{{ exportJson }}</pre>
      </div>
    </template>
  </div>
</template>

<style scoped>
.editor-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  font-family: 'Nunito Sans', 'Inter', system-ui, sans-serif;
  color: #e5e7eb;
  background: #0f0f1a;
  min-height: 100vh;
}
.back-link {
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  font-size: 14px;
}
.back-link:hover { color: #fff; }
h1 { margin: 12px 0 24px; color: #fff; font-size: 24px; }

/* ── Buttons ── */
.btn {
  padding: 8px 18px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
  color: #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}
.btn:hover { background: rgba(255,255,255,0.1); }
.btn.primary {
  background: #4f46e5;
  border-color: #6366f1;
  color: #fff;
}
.btn.primary:hover { background: #4338ca; }
.btn.primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn.small { padding: 4px 12px; font-size: 12px; }

.btn-icon {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #9ca3af;
  transition: background 0.2s, color 0.2s;
}
.btn-icon.delete:hover { background: rgba(239,68,68,0.15); color: #ef4444; }

/* ── Load area ── */
.load-area {
  text-align: center;
  padding: 48px 16px;
  border: 2px dashed rgba(255,255,255,0.12);
  border-radius: 16px;
  margin-top: 24px;
}
.hint { color: #6b7280; margin-top: 12px; font-size: 14px; }

/* ── Player ── */
.player {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0 12px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.04);
  border-radius: 12px;
}
.play-btn { min-width: 90px; }
.time { font-size: 13px; color: #9ca3af; white-space: nowrap; min-width: 110px; }
.seek-bar {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  position: relative;
  cursor: pointer;
}
.seek-fill {
  height: 100%;
  background: #6366f1;
  border-radius: 3px;
}
.seek-head {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  background: #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 6px rgba(0,0,0,0.4);
}

/* ── Shortcuts hint ── */
.shortcuts {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 16px;
}
kbd {
  display: inline-block;
  padding: 2px 6px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 4px;
  font-size: 12px;
  color: #d1d5db;
}

/* ── Action row ── */
.action-row {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

/* ── Captions list ── */
.captions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
.cap-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
}
.cap-num {
  font-size: 13px;
  font-weight: 700;
  color: #6366f1;
  min-width: 28px;
}
.cap-times {
  display: flex;
  gap: 6px;
}
.cap-times label {
  font-size: 11px;
  color: #6b7280;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.time-input {
  width: 70px;
  padding: 4px 6px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  color: #e5e7eb;
  font-size: 13px;
}
.cap-text-input {
  flex: 1;
  padding: 6px 10px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
}
.cap-text-input::placeholder { color: #4b5563; }

/* ── Export ── */
.export-row { margin-bottom: 16px; }
.export-block {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}
.export-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  color: #d1d5db;
  font-size: 14px;
}
.export-code {
  background: #1a1a2e;
  padding: 14px;
  border-radius: 8px;
  font-size: 13px;
  color: #a5b4fc;
  overflow-x: auto;
  white-space: pre;
  max-height: 300px;
  overflow-y: auto;
}
</style>
