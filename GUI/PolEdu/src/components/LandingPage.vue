<script setup lang="ts">
import logoUrl from '../assets/logo.png'
</script>

<template>
  <div class="landing">
    <!-- Hexagonal pattern background -->
    <div class="hex-bg">
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="hexagons" width="100" height="87" patternUnits="userSpaceOnUse" patternTransform="scale(1.5)">
            <path
              d="M25,0 L75,0 L100,43.5 L75,87 L25,87 L0,43.5 Z"
              fill="none"
              stroke="url(#hex-gradient)"
              stroke-width="1.5"
            />
          </pattern>
          <linearGradient id="hex-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#10b981" stop-opacity="1" />
            <stop offset="50%" stop-color="#06b6d4" stop-opacity="1" />
            <stop offset="100%" stop-color="#10b981" stop-opacity="1" />
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#hexagons)" />
      </svg>
    </div>

    <!-- Animated gradient overlay -->
    <div class="gradient-overlay"></div>

    <!-- Fixed logo top-left -->
    <div class="logo-bar">
      <div class="logo-icon">
        <img :src="logoUrl" alt="PolEdu Logo" />
      </div>
      <span class="logo-text">PolEdu</span>
    </div>

    <!-- Hero section -->
    <div class="hero">
      <div class="hero-inner">
        <div class="hero-text">
          <h1>
            <span class="gradient-text">Learn</span><span class="white-text">, in your way,</span>
            <br />
            <span class="white-text">at your </span><span class="gradient-text-alt">pace</span>
          </h1>
          <p class="hero-subtitle">Your personal AI tutor, ready to help you master any subject</p>
        </div>

        <!-- CTA button -->
        <div class="cta-wrap">
          <router-link to="/sample_test" class="cta-btn">Enter PolEdu Tutor</router-link>
        </div>

        <!-- Feature cards -->
        <div class="features">
          <div class="feature-card">
            <div class="feature-icon icon-green-cyan">
              <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h3>Personalized Learning</h3>
            <p>Adapt to your unique learning style and pace</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon icon-cyan-green">
              <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3>AI-Powered Insights</h3>
            <p>Smart assistance that grows with you</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon icon-green-cyan">
              <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3>24/7 Availability</h3>
            <p>Learn anytime, anywhere, at your convenience</p>
          </div>
        </div>
      </div>
    </div>

    <!-- White "Coming Soon" section -->
    <div class="coming-soon">
      <div class="coming-soon-inner">
        <div class="coming-soon-header">
          <h2>Coming Soon</h2>
          <p>More features and content will be added here</p>
        </div>
        <div class="placeholder-grid">
          <div class="placeholder-box">Content Area 1</div>
          <div class="placeholder-box">Content Area 2</div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="footer">
      <p>© 2026 PolEdu. All rights reserved.</p>
    </div>
  </div>
</template>

<style scoped>
/* ── Reset & base ── */
.landing {
  min-height: 100vh;
  background: #000;
  color: #fff;
  position: relative;
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}

/* ── Hexagonal SVG background ── */
.hex-bg {
  position: absolute;
  inset: 0;
  opacity: 0.10;
  pointer-events: none;
}

/* ── Pulsing gradient overlay ── */
.gradient-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom right, rgba(16,185,129,0.05), rgba(6,182,212,0.05), rgba(16,185,129,0.05));
  animation: pulse-overlay 4s ease-in-out infinite;
  pointer-events: none;
}
@keyframes pulse-overlay {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* ── Logo bar ── */
.logo-bar {
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 8px 16px 8px 8px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  flex-shrink: 0;
}
.logo-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.logo-text {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}

/* ── Hero ── */
.hero {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 16px;
}
.hero-inner {
  max-width: 960px;
  margin: 0 auto;
  text-align: center;
}
.hero-text h1 {
  font-size: clamp(2.5rem, 6vw, 5rem);
  font-weight: 700;
  line-height: 1.15;
  margin: 0 0 24px;
}
.white-text {
  color: #fff;
}
.gradient-text {
  background: linear-gradient(to right, #34d399, #22d3ee, #34d399);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradient-shift 3s ease infinite;
}
.gradient-text-alt {
  background: linear-gradient(to right, #22d3ee, #34d399, #22d3ee);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradient-shift 3s ease infinite;
}
@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.hero-subtitle {
  font-size: clamp(1rem, 2vw, 1.5rem);
  color: #9ca3af;
  max-width: 640px;
  margin: 0 auto;
}

/* ── CTA ── */
.cta-wrap {
  padding-top: 32px;
}
.cta-btn {
  display: inline-block;
  padding: 16px 48px;
  font-size: 18px;
  font-weight: 600;
  border-radius: 16px;
  border: none;
  cursor: pointer;
  text-decoration: none;
  background: linear-gradient(to right, #fff, #f3f4f6);
  color: #000;
  box-shadow: 0 8px 32px rgba(16,185,129,0.15);
  transition: transform 0.3s, box-shadow 0.3s;
}
.cta-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 40px rgba(16,185,129,0.25);
}

/* ── Feature cards ── */
.features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
  padding-top: 64px;
}
@media (max-width: 768px) {
  .features { grid-template-columns: 1fr; }
}
.feature-card {
  position: relative;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid rgba(16,185,129,0.3);
  backdrop-filter: blur(8px);
  text-align: center;
  transition: transform 0.3s;
}
.feature-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 24px;
  background: linear-gradient(to bottom right, rgba(16,185,129,0.15), rgba(6,182,212,0.15));
  z-index: -1;
  transition: transform 0.3s;
}
.feature-card:hover {
  transform: scale(1.05);
}
.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #fff;
}
.feature-card p {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

/* ── Feature icons ── */
.feature-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.icon-green-cyan {
  background: linear-gradient(to bottom right, #10b981, #06b6d4);
}
.icon-cyan-green {
  background: linear-gradient(to bottom right, #06b6d4, #10b981);
}

/* ── Coming Soon (white) ── */
.coming-soon {
  position: relative;
  z-index: 10;
  background: #fff;
  padding: 128px 16px;
  margin-top: 128px;
}
.coming-soon-inner {
  max-width: 1152px;
  margin: 0 auto;
}
.coming-soon-header {
  text-align: center;
  margin-bottom: 64px;
}
.coming-soon-header h2 {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  color: #000;
  margin: 0 0 16px;
}
.coming-soon-header p {
  font-size: 20px;
  color: #4b5563;
  margin: 0;
}
.placeholder-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 48px;
}
@media (max-width: 768px) {
  .placeholder-grid { grid-template-columns: 1fr; }
}
.placeholder-box {
  background: #f9fafb;
  border: 2px dashed #d1d5db;
  border-radius: 24px;
  padding: 48px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #9ca3af;
}

/* ── Footer ── */
.footer {
  position: relative;
  z-index: 10;
  background: #fff;
  padding: 64px 16px;
  text-align: center;
}
.footer p {
  color: #6b7280;
  margin: 0;
}
</style>
