import { defineStore } from 'pinia'
import { login, register } from '@/api/auth'
import axios from 'axios'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.user && state.user.role === 'admin'
  },

  actions: {
    // 登录
    async login(credentials) {
      const { token, user } = await login(credentials)
      this.token = token
      this.user = user

      // 保存到本地存储
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))

      return user
    },

    // 注册
    async register(userData) {
      const data = await register(userData)
      return data.user
    },

    // 登出
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },

    // 获取用户信息
    async fetchUserInfo() {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/user/profile', {
          headers: { 'Authorization': token }
        })
        this.user = response.data.user
        localStorage.setItem('user', JSON.stringify(response.data.user))
        return response.data.user
      } catch (error) {
        console.error('获取用户信息失败', error)
        throw error
      }
    }
  }
})
