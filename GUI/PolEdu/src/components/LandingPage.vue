<script setup lang="ts">
import logoUrl from '../assets/logo.png'
</script>

<template>
  <div class="landing">
    <div class="landing__glow landing__glow--left"></div>
    <div class="landing__glow landing__glow--right"></div>

    <header class="landing__header">
      <div class="landing__brand">
        <img :src="logoUrl" alt="PolEdu logo" />
        <span>PolEdu</span>
      </div>
      <nav class="landing__nav">
        <RouterLink :to="{ name: 'chat' }">Tutor</RouterLink>
        <RouterLink :to="{ name: 'chat', query: { entry: 'ielts' } }">IELTS</RouterLink>
      </nav>
    </header>

    <main class="landing__hero">
      <section class="landing__copy">
        <p class="landing__eyebrow">Math-first AI tutor</p>
        <h1>Learn math your way, then keep IELTS tools close by.</h1>
        <p class="landing__summary">
          PolEdu now starts with a personalized tutoring flow that adapts to how you like to
          learn. Tell it who you are, pick a math topic, and it builds a short lesson with
          explanations, graphs, interactive practice, and a mini test.
        </p>

        <div class="landing__actions">
          <RouterLink class="landing__primary" :to="{ name: 'chat' }">
            Enter personalized tutor
          </RouterLink>
          <RouterLink class="landing__secondary" :to="{ name: 'chat', query: { entry: 'ielts' } }">
            Use IELTS tools
          </RouterLink>
        </div>
      </section>

      <section class="landing__cards">
        <article class="landing__card landing__card--feature">
          <p class="landing__card-label">Core flow</p>
          <h2>Personalized math lessons</h2>
          <p>
            Onboarding captures learning style, hobbies, and a few small preferences so each
            lesson feels more tailored instead of generic.
          </p>
        </article>

        <article class="landing__card">
          <p class="landing__card-label">Interactive blocks</p>
          <h2>Graphs and playgrounds</h2>
          <p>
            Generated lessons can include graph visualizations, graph playground challenges, and
            a 10-question mini test with answer explanations.
          </p>
        </article>

        <article class="landing__card">
          <p class="landing__card-label">Secondary feature</p>
          <h2>IELTS remains available</h2>
          <p>
            Mock IELTS generation, listening audio, and the exam viewer still work inside the same
            PolEdu app when you explicitly ask for them.
          </p>
        </article>
      </section>
    </main>
  </div>
</template>

<style scoped>
.landing {
  position: relative;
  min-height: 100dvh;
  overflow: hidden;
  background:
    radial-gradient(circle at top, rgba(20, 184, 166, 0.2), transparent 26rem),
    linear-gradient(180deg, #020617 0%, #0f172a 52%, #111827 100%);
  color: #f8fafc;
}

.landing__glow {
  position: absolute;
  width: 28rem;
  height: 28rem;
  border-radius: 999px;
  filter: blur(70px);
  opacity: 0.3;
  pointer-events: none;
}

.landing__glow--left {
  top: -10rem;
  left: -10rem;
  background: rgba(45, 212, 191, 0.38);
}

.landing__glow--right {
  right: -8rem;
  bottom: 4rem;
  background: rgba(34, 211, 238, 0.2);
}

.landing__header,
.landing__hero {
  position: relative;
  z-index: 1;
  width: min(1180px, calc(100% - 2rem));
  margin: 0 auto;
}

.landing__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 0;
}

.landing__brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  font-weight: 700;
}

.landing__brand img {
  width: 3rem;
  height: 3rem;
  border-radius: 0.9rem;
  object-fit: cover;
}

.landing__nav {
  display: flex;
  gap: 1rem;
}

.landing__nav a {
  color: #cbd5e1;
  text-decoration: none;
}

.landing__hero {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 1.5rem;
  align-items: center;
  padding: 3rem 0 4rem;
}

.landing__eyebrow,
.landing__card-label {
  margin: 0;
  color: #67e8f9;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.landing__copy h1 {
  margin: 0.75rem 0 1rem;
  font-size: clamp(2.8rem, 6vw, 5rem);
  line-height: 0.98;
  max-width: 12ch;
}

.landing__summary {
  margin: 0;
  max-width: 60ch;
  color: #cbd5e1;
  line-height: 1.8;
  font-size: 1.05rem;
}

.landing__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  margin-top: 1.5rem;
}

.landing__primary,
.landing__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.95rem 1.2rem;
  border-radius: 1rem;
  text-decoration: none;
  font-weight: 700;
}

.landing__primary {
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #f8fafc;
}

.landing__secondary {
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
}

.landing__cards {
  display: grid;
  gap: 1rem;
}

.landing__card {
  padding: 1.3rem;
  border-radius: 1.5rem;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 22px 40px rgba(2, 6, 23, 0.3);
}

.landing__card--feature {
  background:
    radial-gradient(circle at top right, rgba(45, 212, 191, 0.15), transparent 14rem),
    rgba(15, 23, 42, 0.68);
}

.landing__card h2 {
  margin: 0.6rem 0 0.5rem;
  font-size: 1.45rem;
}

.landing__card p:last-child {
  margin: 0;
  color: #cbd5e1;
  line-height: 1.7;
}

@media (max-width: 900px) {
  .landing__hero {
    grid-template-columns: 1fr;
    padding-top: 2rem;
  }

  .landing__header {
    flex-direction: column;
    gap: 0.9rem;
    align-items: flex-start;
  }
}
</style>
