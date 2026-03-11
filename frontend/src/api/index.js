import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 添加token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const { status, data } = error.response

      if (status === 401) {
        // 只有当本地存在token但无效时，才提示"登录已过期"
        const hasToken = !!localStorage.getItem('token')
        if (hasToken) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          ElMessage.warning('登录已过期，请重新登录')
          // 刷新页面以更新状态
          setTimeout(() => {
            window.location.reload()
          }, 1000)
        }
        // 如果本来就没有token，说明是未登录访问，不做任何处理
      } else if (data && data.error) {
        ElMessage.error(data.error)
      } else {
        ElMessage.error('请求失败')
      }
    } else {
      ElMessage.error('网络错误')
    }

    return Promise.reject(error)
  }
)

export default request
