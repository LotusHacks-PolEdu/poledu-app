<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const started = ref(false)
const allDone = ref(false)
const textGone = ref(false)
const audioRef = ref<HTMLAudioElement | null>(null)

// --- Voice input segments ---
const segments = [
  { text: 'Teach me about derivatives', delay: 0 },
  { text: ' in very simple terms', delay: 1600 },
  { text: ' and in a calm voice.', delay: 3000 },
]
const segmentVisible = ref<boolean[]>(segments.map(() => false))

// --- Captions for the audio ---
// Each caption has a start time (seconds) and the text to display.
// Adjust these to match your actual derivative.mp3 content.
const captions = ref([
  {
    "start": 0,
    "end": 3.2,
    "text": "A derivative is the exact rate of change at a single moment."
  },
  {
    "start": 3.21,
    "end": 5.28,
    "text": " Just imagine a car's speedometer"
  },
  {
    "start": 5.28,
    "end": 6.75,
    "text": "instead of average speed"
  },
  {
    "start": 6.76,
    "end": 8.57,
    "text": " it shows your exact speed"
  },
  {
    "start": 8.57,
    "end": 10.34,
    "text": "at one frozen millisecond."
  }
])
const activeCaption = ref('')

const timers: ReturnType<typeof setTimeout>[] = []
let animFrame = 0

function begin() {
  if (started.value) return
  started.value = true

  // Reveal text segments
  segments.forEach((seg, i) => {
    timers.push(setTimeout(() => { segmentVisible.value[i] = true }, seg.delay))
  })

  // After last segment: float text away, then play audio
  const lastDelay = segments[segments.length - 1]!.delay
  timers.push(setTimeout(() => {
    allDone.value = true // text starts floating up
  }, lastDelay + 1200))

  timers.push(setTimeout(() => {
    textGone.value = true // text fully gone
    audioRef.value?.play()
    startCaptionSync()
  }, lastDelay + 2400))
}

function startCaptionSync() {
  const audio = audioRef.value
  if (!audio) return

  function tick() {
    const t = audio!.currentTime
    const cap = captions.value.find((c) => t >= c.start && t < c.end)
    activeCaption.value = cap ? cap.text : ''
    if (!audio!.ended && !audio!.paused) {
      animFrame = requestAnimationFrame(tick)
    } else if (audio!.ended) {
      activeCaption.value = ''
    }
  }
  animFrame = requestAnimationFrame(tick)
}

// Load Google Font
onMounted(() => {
  if (!document.querySelector('link[href*="Nunito+Sans"]')) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700&display=swap'
    document.head.appendChild(link)
  }
})

onBeforeUnmount(() => {
  timers.forEach(clearTimeout)
  if (animFrame) cancelAnimationFrame(animFrame)
})
</script>

<template>
  <div class="math-demo" @click="begin">
    <router-link to="/" class="back-link" @click.stop>← Home</router-link>

    <!-- Click prompt -->
    <div v-if="!started" class="click-overlay">
      <div class="click-prompt">
        <div class="click-ring"></div>
        <span>Click anywhere to start</span>
      </div>
    </div>

    <!-- Pulsating blob -->
    <div class="voice-blob" :class="{ idle: !started, pulsing: started && !allDone, done: allDone }"></div>

    <!-- Voice input text — floats up and disappears -->
    <div v-if="started && !textGone" class="voice-text" :class="{ floating: allDone }">
      <span
        v-for="(seg, i) in segments"
        :key="i"
        class="segment"
        :class="{ visible: segmentVisible[i] }"
      >{{ seg.text }}</span>
    </div>

    <!-- Caption text during audio -->
    <transition name="caption-fade">
      <p v-if="textGone && activeCaption" :key="activeCaption" class="caption">
        {{ activeCaption }}
      </p>
    </transition>

    <audio ref="audioRef" src="/derivative.mp3" preload="auto"></audio>
  </div>
</template>

<style scoped>
.math-demo {
  min-height: 100vh;
  background: #0a0a14;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  font-family: 'Nunito Sans', 'Inter', system-ui, sans-serif;
  user-select: none;
}

/* ── Click overlay ── */
.click-overlay {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
}
.click-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 16px;
  letter-spacing: 0.5px;
  animation: fade-pulse 2s ease-in-out infinite;
}
.click-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.15);
  position: relative;
}
.click-ring::after {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.08);
  animation: ring-expand 2s ease-in-out infinite;
}
@keyframes fade-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
@keyframes ring-expand {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.3); opacity: 0; }
}

/* ── Back link ── */
.back-link {
  position: fixed;
  top: 20px;
  left: 24px;
  z-index: 50;
  color: rgba(255, 255, 255, 0.5);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.back-link:hover { color: #fff; }

/* ── Voice blob ── */
.voice-blob {
  position: absolute;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: radial-gradient(circle at 45% 45%,
    rgba(99, 102, 241, 0.9),
    rgba(139, 92, 246, 0.7),
    rgba(6, 182, 212, 0.5)
  );
  filter: blur(8px);
  transition: transform 0.8s ease, filter 1.2s ease, background 1s ease, opacity 0.8s ease;
}
.voice-blob.idle {
  filter: blur(40px);
  opacity: 0.5;
  transform: scale(0.9);
}
.voice-blob.pulsing {
  animation: blob-pulse 0.8s ease-in-out infinite alternate;
}
@keyframes blob-pulse {
  0% {
    transform: scale(1);
    filter: blur(8px);
    background: radial-gradient(circle at 40% 40%,
      rgba(99, 102, 241, 0.9),
      rgba(139, 92, 246, 0.7),
      rgba(6, 182, 212, 0.5)
    );
  }
  100% {
    transform: scale(1.18);
    filter: blur(12px);
    background: radial-gradient(circle at 55% 55%,
      rgba(139, 92, 246, 0.95),
      rgba(99, 102, 241, 0.7),
      rgba(236, 72, 153, 0.4)
    );
  }
}
.voice-blob.done {
  animation: blob-breathe 3s ease-in-out infinite alternate;
  background: radial-gradient(circle at 50% 50%,
    rgba(16, 185, 129, 0.8),
    rgba(6, 182, 212, 0.6),
    rgba(99, 102, 241, 0.35)
  );
}
@keyframes blob-breathe {
  0% { transform: scale(1.05); filter: blur(8px); }
  100% { transform: scale(1.2); filter: blur(14px); }
}

/* ── Voice text ── */
.voice-text {
  position: relative;
  z-index: 20;
  text-align: center;
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 0.2px;
  white-space: nowrap;
  animation: text-fade-in 0.8s ease;
  transition: transform 1.2s ease, opacity 1.2s ease;
}
.voice-text.floating {
  transform: translateY(-220px);
  opacity: 0;
}
@keyframes text-fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.segment {
  opacity: 0;
  transition: opacity 1s ease;
}
.segment.visible {
  opacity: 1;
}

/* ── Caption ── */
.caption {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 20;
  color: rgba(255, 255, 255, 0.95);
  font-size: 32px;
  font-weight: 600;
  text-align: left;
  max-width: 85%;
  line-height: 1.4;
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.5);
}
.caption-fade-enter-active {
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.caption-fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}
.caption-fade-enter-from {
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.8);
}
.caption-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) scale(1.05);
}

/* ── Mobile-first: big text by default, scale down on desktop ── */
.voice-text {
  font-size: 28px;
  text-align: left;
  white-space: normal;
  padding: 0 24px;
}
.caption {
  font-size: 28px;
  max-width: 90%;
  padding: 0 16px;
}

@media (min-width: 641px) {
  .voice-text {
    font-size: 28px;
    text-align: left;
    white-space: nowrap;
    padding: 0;
  }
  .caption {
    font-size: 32px;
    max-width: 85%;
    padding: 0;
  }
}
</style>
