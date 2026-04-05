import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
          path: 'expert',
          name: 'expert-queue',
          component: () => import('../views/ExpertQueueView.vue'),
        },
      ],
    },
  ],
})

export default router
