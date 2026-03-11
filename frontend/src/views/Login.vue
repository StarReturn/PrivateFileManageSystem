<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>文件管理系统</h2>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 登录 -->
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef">
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                prefix-icon="User"
                size="large"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                prefix-icon="Lock"
                size="large"
                @keyup.enter="handleLogin"
              >
                <template #suffix>
                  <el-icon
                    class="password-icon"
                    @click="showPassword = !showPassword"
                  >
                    <component :is="showPassword ? 'Hide' : 'View'" />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>

            <div class="login-options">
              <el-checkbox v-model="loginForm.rememberMe">记住我</el-checkbox>
              <el-link type="primary" @click="showForgotDialog = true">
                忘记密码？
              </el-link>
            </div>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                style="width: 100%"
                :loading="loading"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef">
            <el-form-item prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="请输入用户名"
                prefix-icon="User"
                size="large"
              />
            </el-form-item>

            <el-form-item prop="phone">
              <el-input
                v-model="registerForm.phone"
                placeholder="请输入手机号"
                prefix-icon="Phone"
                size="large"
                maxlength="11"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                :type="showRegisterPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                prefix-icon="Lock"
                size="large"
              >
                <template #suffix>
                  <el-icon
                    class="password-icon"
                    @click="showRegisterPassword = !showRegisterPassword"
                  >
                    <component :is="showRegisterPassword ? 'Hide' : 'View'" />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                :type="showRegisterConfirmPassword ? 'text' : 'password'"
                placeholder="请确认密码"
                prefix-icon="Lock"
                size="large"
                @keyup.enter="handleRegister"
              >
                <template #suffix>
                  <el-icon
                    class="password-icon"
                    @click="showRegisterConfirmPassword = !showRegisterConfirmPassword"
                  >
                    <component :is="showRegisterConfirmPassword ? 'Hide' : 'View'" />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                style="width: 100%"
                :loading="loading"
                @click="handleRegister"
              >
                注册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 忘记密码对话框 -->
    <el-dialog v-model="showForgotDialog" title="忘记密码" width="400px">
      <el-form :model="forgotForm" :rules="forgotRules" ref="forgotFormRef">
        <!-- 步骤1：验证用户名和手机号 -->
        <template v-if="forgotStep === 1">
          <el-form-item prop="username">
            <el-input
              v-model="forgotForm.username"
              placeholder="请输入用户名"
              prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="phone">
            <el-input
              v-model="forgotForm.phone"
              placeholder="请输入注册时的手机号"
              prefix-icon="Phone"
              maxlength="11"
            />
          </el-form-item>

          <el-button type="primary" style="width: 100%" @click="handleVerifyPhone" :loading="verifying">
            验证手机号
          </el-button>
        </template>

        <!-- 步骤2：输入新密码 -->
        <template v-if="forgotStep === 2">
          <el-alert
            title="验证成功"
            type="success"
            :closable="false"
            show-icon
            style="margin-bottom: 20px"
          >
            手机号验证通过，请设置新密码
          </el-alert>

          <el-form-item prop="newPassword">
            <el-input
              v-model="forgotForm.newPassword"
              type="password"
              placeholder="请输入新密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input
              v-model="forgotForm.confirmPassword"
              type="password"
              placeholder="请确认新密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="handleCancelForgot">取消</el-button>
        <el-button v-if="forgotStep === 2" type="primary" :loading="resetting" @click="handleResetPassword">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref()
const registerFormRef = ref()
const forgotFormRef = ref()
const showPassword = ref(false)
const showRegisterPassword = ref(false)
const showRegisterConfirmPassword = ref(false)
const showForgotDialog = ref(false)
const resetting = ref(false)
const verifying = ref(false)
const forgotStep = ref(1) // 1: 验证手机号, 2: 输入新密码

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 注册表单
const registerForm = reactive({
  username: '',
  phone: '',
  password: '',
  confirmPassword: ''
})

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 忘记密码表单
const forgotForm = reactive({
  username: '',
  phone: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== forgotForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const forgotRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 初始化 - 加载记住的用户名
onMounted(() => {
  const savedUsername = localStorage.getItem('rememberedUsername')
  if (savedUsername) {
    loginForm.username = savedUsername
    loginForm.rememberMe = true
  }
})

// 登录
const handleLogin = async () => {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login(loginForm)
    ElMessage.success('登录成功')

    // 处理记住我
    if (loginForm.rememberMe) {
      localStorage.setItem('rememberedUsername', loginForm.username)
    } else {
      localStorage.removeItem('rememberedUsername')
    }

    router.push('/')
  } catch (error) {
    console.error('登录失败', error)
    // 显示错误信息给用户
    const errorMsg = error.response && error.response.data && error.response.data.error || error.message || '登录失败，请检查用户名和密码'
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

// 注册
const handleRegister = async () => {
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.register(registerForm)
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    // 清空注册表单
    registerForm.username = ''
    registerForm.phone = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
  } catch (error) {
    console.error('注册失败', error)
    // 显示错误信息给用户
    const errorMsg = error.response && error.response.data && error.response.data.error || error.message || '注册失败'
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

// 验证手机号
const handleVerifyPhone = async () => {
  // 验证表单
  const valid = await forgotFormRef.value.validate(['username', 'phone']).catch(() => false)
  if (!valid) return

  verifying.value = true
  try {
    await axios.post('/api/auth/verify-phone', {
      username: forgotForm.username,
      phone: forgotForm.phone
    })
    ElMessage.success('验证成功')
    // 进入下一步
    forgotStep.value = 2
  } catch (error) {
    console.error('验证失败', error)
    ElMessage.error(error.response && error.response.data && error.response.data.error || '用户名与手机号不匹配')
  } finally {
    verifying.value = false
  }
}

// 取消忘记密码
const handleCancelForgot = () => {
  showForgotDialog.value = false
  // 重置表单和状态
  forgotStep.value = 1
  forgotForm.username = ''
  forgotForm.phone = ''
  forgotForm.newPassword = ''
  forgotForm.confirmPassword = ''
  forgotFormRef.value && forgotFormRef.value.clearValidate()
}

// 重置密码
const handleResetPassword = async () => {
  const valid = await forgotFormRef.value.validate(['newPassword', 'confirmPassword']).catch(() => false)
  if (!valid) return

  resetting.value = true
  try {
    await axios.post('/api/auth/reset-password', {
      username: forgotForm.username,
      phone: forgotForm.phone,
      new_password: forgotForm.newPassword
    })
    ElMessage.success('密码重置成功，请使用新密码登录')
    showForgotDialog.value = false

    // 重置表单和状态
    forgotStep.value = 1
    forgotForm.username = ''
    forgotForm.phone = ''
    forgotForm.newPassword = ''
    forgotForm.confirmPassword = ''

    // 切换到登录页
    activeTab.value = 'login'
  } catch (error) {
    console.error('重置密码失败', error)
    ElMessage.error(error.response && error.response.data && error.response.data.error || '重置密码失败')
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #333;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.password-icon {
  cursor: pointer;
  font-size: 16px;
}
</style>
