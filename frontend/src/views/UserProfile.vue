<template>
  <el-container class="user-profile-container">
    <el-header class="page-header">
      <h2>个人中心</h2>
      <el-button @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </el-header>

    <el-main>
      <el-card class="profile-card">
        <!-- 头像区域 -->
        <div class="avatar-section">
          <el-avatar :size="120" :src="userAvatar" class="avatar">
            {{ userInfo.username && userInfo.username.charAt(0).toUpperCase() }}
          </el-avatar>
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            @change="handleAvatarChange"
          >
            <el-button type="primary" size="small" style="margin-top: 15px">
              更换头像
            </el-button>
          </el-upload>
        </div>

        <!-- 用户信息表单 -->
        <el-form :model="userForm" label-width="100px" class="user-form">
          <el-form-item label="用户名">
            <el-input v-model="userInfo.username" disabled />
          </el-form-item>

          <el-form-item label="角色">
            <el-input :value="userInfo.role === 'admin' ? '管理员' : '普通用户'" disabled />
          </el-form-item>

          <el-form-item label="注册时间">
            <el-input v-model="userInfo.create_time" disabled />
          </el-form-item>

          <el-form-item label="手机号">
            <el-input
              v-model="userForm.phone"
              placeholder="请输入手机号"
              clearable
              maxlength="11"
            />
          </el-form-item>

          <el-form-item label="新密码">
            <el-input
              v-model="userForm.new_password"
              type="password"
              placeholder="不修改请留空"
              show-password
              clearable
            />
          </el-form-item>

          <el-form-item label="确认密码">
            <el-input
              v-model="userForm.confirm_password"
              type="password"
              placeholder="不修改请留空"
              show-password
              clearable
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleUpdateProfile" :loading="updating">
              保存修改
            </el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import axios from 'axios'

const router = useRouter()
const userStore = useUserStore()

const updating = ref(false)
const userInfo = ref({
  username: '',
  phone: '',
  role: '',
  create_time: '',
  avatar: null
})

const userForm = reactive({
  phone: '',
  new_password: '',
  confirm_password: '',
  avatar_file: null
})

// 计算头像URL
const userAvatar = computed(() => {
  if (userInfo.value.avatar) {
    return `data:image/jpeg;base64,${userInfo.value.avatar}`
  }
  return null
})

// 加载用户信息
const loadUserInfo = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/user/profile', {
      headers: { 'Authorization': token }
    })

    userInfo.value = response.data.user
    userForm.phone = response.data.user.phone || ''
  } catch (error) {
    console.error('加载用户信息失败', error)
    ElMessage.error('加载用户信息失败')
  }
}

// 头像文件变化
const handleAvatarChange = (file) => {
  const isImage = file.raw.type.startsWith('image/')
  const isLt2M = file.raw.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件！')
    return
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB！')
    return
  }

  userForm.avatar_file = file.raw

  // 预览头像
  const reader = new FileReader()
  reader.onload = (e) => {
    userInfo.value.avatar = e.target.result.split(',')[1]
  }
  reader.readAsDataURL(file.raw)
}

// 更新用户信息
const handleUpdateProfile = async () => {
  // 验证手机号格式
  if (userForm.phone && !/^1[3-9]\d{9}$/.test(userForm.phone)) {
    ElMessage.warning('请输入正确的手机号格式')
    return
  }

  // 验证密码
  if (userForm.new_password || userForm.confirm_password) {
    if (userForm.new_password !== userForm.confirm_password) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
    if (userForm.new_password.length < 6) {
      ElMessage.warning('密码长度不能少于6位')
      return
    }
  }

  updating.value = true
  try {
    const token = localStorage.getItem('token')

    // 构建表单数据
    const formData = new FormData()
    if (userForm.phone !== userInfo.value.phone) {
      formData.append('phone', userForm.phone)
    }
    if (userForm.new_password) {
      formData.append('new_password', userForm.new_password)
    }
    if (userForm.avatar_file) {
      formData.append('avatar', userForm.avatar_file)
    }

    await axios.put('/api/user/profile', formData, {
      headers: {
        'Authorization': token,
        'Content-Type': 'multipart/form-data'
      }
    })

    ElMessage.success('修改成功')
    await loadUserInfo()
    // 更新store中的用户信息
    await userStore.fetchUserInfo()
  } catch (error) {
    console.error('更新用户信息失败', error)
    ElMessage.error(error.response && error.response.data && error.response.data.error || '更新失败')
  } finally {
    updating.value = false
  }
}

// 重置表单
const resetForm = () => {
  userForm.phone = userInfo.value.phone || ''
  userForm.new_password = ''
  userForm.confirm_password = ''
  userForm.avatar_file = null
}

onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped>
.user-profile-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header h2 {
  margin: 0;
  color: #333;
}

.el-main {
  padding: 20px;
  background-color: #f5f5f5;
  display: flex;
  justify-content: center;
}

.profile-card {
  max-width: 600px;
  width: 100%;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 0;
  border-bottom: 1px solid #e6e6e6;
  margin-bottom: 30px;
}

.avatar {
  border: 3px solid #409eff;
}

.user-form {
  max-width: 400px;
  margin: 0 auto;
}
</style>
