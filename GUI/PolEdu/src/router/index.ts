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
      path: '/sample_test',
      name: 'sample-test',
      component: () => import('../pages/SampleTest.vue'),
    },
  ],
})

export default router
