import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../components/LandingPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingPage,
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../pages/ChatPage.vue'),
    },
    {
      path: '/lessons/:lessonCode',
      name: 'lesson-viewer',
      component: () => import('../pages/LessonPage.vue'),
    },
    {
      path: '/sample_test',
      name: 'sample-test',
      component: () => import('../pages/SampleTest.vue'),
    },
    {
      path: '/ielts_exam',
      name: 'ielts-exam',
      component: () => import('../pages/IeltsExam.vue'),
    },
    {
      path: '/ielts_demo1',
      name: 'ielts-demo1',
      component: () => import('../pages/IeltsStatic.vue'),
    },
    {
      path: '/math_demo1',
      name: 'math-demo1',
      component: () => import('../pages/MathDemo1.vue'),
    },
    {
      path: '/derivative-quiz',
      name: 'derivative-quiz',
      component: () => import('../pages/DerivativeLesson.vue'),
    },
    {
      path: '/caption_editor',
      name: 'caption-editor',
      component: () => import('../pages/CaptionEditor.vue'),
    },
  ],
})

export default router
