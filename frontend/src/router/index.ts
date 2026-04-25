import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/HomeView.vue'),
        },
        {
          path: 'species',
          name: 'species-list',
          component: () => import('../views/SpeciesListView.vue'),
        },
        {
          path: 'species/:id',
          name: 'species-detail',
          component: () => import('../views/SpeciesDetailView.vue'),
        },
        {
          path: 'observe',
          name: 'observe',
          component: () => import('../views/ObserveView.vue'),
        },
        {
          path: 'my',
          name: 'my-observations',
          component: () => import('../views/MyObservationsView.vue'),
        },
        {
          path: 'observations/:id',
          name: 'observation-detail',
          component: () => import('../views/ObservationDetailView.vue'),
        },
        {
          path: 'expert',
          name: 'expert-queue',
          component: () => import('../views/ExpertQueueView.vue'),
        },
        {
          path: 'identify',
          name: 'identify',
          component: () => import('../views/IdentifyView.vue'),
        },
        {
          path: 'map',
          name: 'map',
          component: () => import('../views/MapView.vue'),
        },
        {
          path: 'help',
          name: 'help',
          component: () => import('../views/HelpView.vue'),
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('../views/AdminView.vue'),
        },
        {
          path: 'passport',
          name: 'passport',
          component: () => import('../views/EcoPassportView.vue'),
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('../views/ProfileView.vue'),
        },
        {
          path: 'quiz',
          name: 'quiz',
          component: () => import('../views/QuizView.vue'),
        },
        {
          path: 'routes',
          name: 'routes',
          component: () => import('../views/RoutesView.vue'),
        },
        {
          path: 'exhibition',
          name: 'exhibition',
          component: () => import('../views/ExhibitionView.vue'),
        },
      ],
    },
  ],
})

const authRequiredNames = new Set([
  'observe',
  'my-observations',
  'profile',
  'expert-queue',
  'admin',
])

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.name === 'login') {
    return true
  }

  if (to.name && authRequiredNames.has(to.name.toString()) && !auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'expert-queue' && !auth.isEcologist()) {
    return { name: 'home' }
  }

  if (to.name === 'admin' && !auth.isAdmin()) {
    return { name: 'home' }
  }

  return true
})

export default router
