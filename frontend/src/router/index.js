import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: false }  // 允许未登录访问
  },
  {
    path: '/operation-log',
    name: 'OperationLog',
    component: () => import('@/views/OperationLog.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/recycle-bin',
    name: 'RecycleBin',
    component: () => import('@/views/RecycleBin.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/user-profile',
    name: 'UserProfile',
    component: () => import('@/views/UserProfile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/preview-window/:drawingId',
    name: 'PreviewWindow',
    component: () => import('@/views/PreviewWindow.vue'),
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
