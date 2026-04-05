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
      ],
    },
  ],
})

export default router
