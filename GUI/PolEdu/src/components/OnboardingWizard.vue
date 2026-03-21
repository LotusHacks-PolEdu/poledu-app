<script setup lang="ts">
import { reactive } from 'vue'

import type { LearnerOnboardRequest } from '../types/lessons'

defineProps<{
  submitting?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', payload: LearnerOnboardRequest): void
  (e: 'skip-ielts'): void
}>()

const form = reactive({
  name: '',
  learning_by_doing: true,
  learning_by_listening: false,
  learning_by_reading: true,
  hobbies: '',
  favorite_food: '',
})

function parseHobbies(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function handleSubmit(): void {
  emit('submit', {
    name: form.name.trim(),
    learning_by_doing: form.learning_by_doing,
    learning_by_listening: form.learning_by_listening,
    learning_by_reading: form.learning_by_reading,
    hobbies: parseHobbies(form.hobbies),
    favorite_food: form.favorite_food.trim(),
  })
}
</script>

<template>
  <section class="onboarding">
    <div class="onboarding__copy">
      <p class="onboarding__eyebrow">Math Tutor Setup</p>
      <h2>Tell PolEdu how you learn best.</h2>
      <p>
        This quick profile lets the lesson generator shape the math lesson around how you like
        to learn. IELTS tools can still be used without this step.
      </p>
    </div>

    <form class="onboarding__form" @submit.prevent="handleSubmit">
      <label class="onboarding__field">
        <span>Your name</span>
        <input v-model="form.name" type="text" placeholder="Enter a demo learner name" required />
      </label>

      <fieldset class="onboarding__field onboarding__field--preferences">
        <legend>Learning preferences</legend>

        <label>
          <input v-model="form.learning_by_doing" type="checkbox" />
          <span>Learning by doing</span>
        </label>

        <label>
          <input v-model="form.learning_by_listening" type="checkbox" />
          <span>Learning by listening</span>
        </label>

        <label>
          <input v-model="form.learning_by_reading" type="checkbox" />
          <span>Learning by reading</span>
        </label>
      </fieldset>

      <label class="onboarding__field">
        <span>Hobbies</span>
        <input
          v-model="form.hobbies"
          type="text"
          placeholder="Comma separated, for example: chess, football, coding"
        />
      </label>

      <label class="onboarding__field">
        <span>Favorite food</span>
        <input v-model="form.favorite_food" type="text" placeholder="Optional" />
      </label>

      <div class="onboarding__actions">
        <button class="onboarding__submit" type="submit" :disabled="!form.name.trim() || submitting">
          {{ submitting ? 'Saving profile...' : 'Start my tutor' }}
        </button>
        <button class="onboarding__secondary" type="button" @click="$emit('skip-ielts')">
          Use IELTS tools instead
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.onboarding {
  display: grid;
  gap: 1.5rem;
  padding: 1.5rem;
  border-radius: 1.5rem;
  background:
    radial-gradient(circle at top right, rgba(20, 184, 166, 0.18), transparent 18rem),
    rgba(10, 18, 34, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.35);
}

.onboarding__copy h2 {
  margin: 0.4rem 0 0.65rem;
  font-size: clamp(1.7rem, 3vw, 2.2rem);
}

.onboarding__copy p {
  margin: 0;
  color: #cbd5e1;
  line-height: 1.7;
}

.onboarding__eyebrow {
  color: #67e8f9;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.onboarding__form {
  display: grid;
  gap: 1rem;
}

.onboarding__field {
  display: grid;
  gap: 0.45rem;
}

.onboarding__field span,
.onboarding__field legend {
  color: #e2e8f0;
  font-weight: 600;
}

.onboarding__field input {
  width: 100%;
  padding: 0.85rem 0.95rem;
  border-radius: 0.95rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.7);
  color: #f8fafc;
}

.onboarding__field--preferences {
  display: grid;
  gap: 0.65rem;
  padding: 1rem;
  border-radius: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.48);
}

.onboarding__field--preferences label {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  color: #e2e8f0;
}

.onboarding__field--preferences input {
  width: auto;
  margin: 0;
}

.onboarding__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
}

.onboarding__submit,
.onboarding__secondary {
  border: none;
  border-radius: 0.95rem;
  padding: 0.85rem 1.15rem;
  cursor: pointer;
}

.onboarding__submit {
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #ffffff;
}

.onboarding__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.onboarding__secondary {
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
}
</style>
