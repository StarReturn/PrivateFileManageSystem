<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="上传文件"
    width="600px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="选择文件" prop="file" required  >
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
          accept=".pdf,.doc,.docx,.xlsx,.xls,.ofd,.ceb"
          drag
          style="width: 410px"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击选择</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              仅支持上传 PDF、Word、Excel、OFD、CEB 文件
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item label="文件名称" prop="drawing_name">
        <el-input v-model="form.drawing_name" placeholder="请输入文件名称" style="width: 410px"/>
      </el-form-item>

      <el-form-item label="所属目录" prop="category_id">
        <el-cascader
          v-model="form.category_path"
          :options="categoryTree"
          :props="cascaderProps"
          placeholder="请选择目录"
          clearable
          style="width: 410px"
          @change="handleCategoryChange"
        >
          <template #default="{ node, data }">
            <el-tooltip :content="data.label" placement="top" :show-after="500">
              <span class="cascader-node-label">{{ data.label }}</span>
            </el-tooltip>
          </template>
        </el-cascader>
      </el-form-item>

      <el-form-item label="访问权限" prop="visibility">
        <el-radio-group v-model="form.visibility">
          <el-radio value="public">全站可见</el-radio>
          <el-radio value="login">登录可见</el-radio>
          <el-radio value="private">仅我可见</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="uploading" @click="handleUpload">
        上传
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadDrawing } from '@/api/file'

const props = defineProps({
  modelValue: Boolean,
  categories: Array,
  defaultCategoryId: Number  // 预选目录ID
})

const emit = defineEmits(['update:modelValue', 'success'])

const formRef = ref()
const uploadRef = ref()
const uploading = ref(false)
const selectedFile = ref(null)

const form = reactive({
  file: null,
  drawing_name: '',
  category_id: null,
  category_path: [],
  visibility: 'login'  // 默认为登录可见
})

const rules = {
  drawing_name: [{ required: true, message: '请输入文件名称', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择目录', trigger: 'change' }],
  file: [{
    validator: (rule, value, callback) => {
      if (!form.file) {
        callback(new Error('请选择文件'))
      } else {
        callback()
      }
    },
    trigger: 'change'
  }]
}

// 构建目录树结构
const categoryTree = computed(() => {
  const buildTree = (parentId = null) => {
    return props.categories
      .filter(c => {
        // 处理根目录：parent_id 为 0 或 null
        if (parentId === null) {
          return c.parent_id === 0 || c.parent_id === null
        }
        return c.parent_id === parentId
      })
      .map(c => ({
        value: c.category_id,
        label: c.category_name,
        children: buildTree(c.category_id)
      }))
  }
  return buildTree()
})

// Cascader 配置
const cascaderProps = {
  value: 'value',
  label: 'label',
  children: 'children',
  checkStrictly: true,  // 允许选择任意一级
  emitPath: false       // 只返回最后一级的值
}

// 目录选择改变
const handleCategoryChange = (value) => {
  form.category_id = value
}

// 获取目录节点的完整路径（从根到当前节点）
const getCategoryPath = (categoryId, tree, path = []) => {
  for (const node of tree) {
    const currentPath = [...path, node.value]
    if (node.value === categoryId) {
      return currentPath
    }
    if (node.children && node.children.length > 0) {
      const found = getCategoryPath(categoryId, node.children, currentPath)
      if (found) {
        return found
      }
    }
  }
  return null
}

// 监听对话框打开，设置默认目录
watch(() => props.modelValue, async (newValue) => {
  if (newValue) {
    // 等待 DOM 更新和 categoryTree 准备好
    await nextTick()
    // 等待更长时间确保 categoryTree 已计算
    setTimeout(() => {
      if (props.defaultCategoryId) {
        console.log('设置默认目录:', props.defaultCategoryId)
        console.log('categoryTree:', categoryTree.value)
        // 设置选中的目录ID
        form.category_id = props.defaultCategoryId
        // 获取完整路径并设置
        const fullPath = getCategoryPath(props.defaultCategoryId, categoryTree.value)
        console.log('获取到的完整路径:', fullPath)
        if (fullPath) {
          form.category_path = fullPath
          console.log('设置的 category_path:', form.category_path)
        } else {
          console.warn('未找到路径，使用 ID:', props.defaultCategoryId)
          form.category_path = [props.defaultCategoryId]
        }
      }
    }, 100)
  }
})

// 文件选择改变
const handleFileChange = (file) => {
  selectedFile.value = file
  form.file = file
  formRef.value && formRef.value.validateField('file')
  // 自动填充文件名称
  if (!form.drawing_name) {
    const fileName = file.name
    const nameWithoutExt = fileName.substring(0, fileName.lastIndexOf('.'))
    form.drawing_name = nameWithoutExt
  }
}

// 文件超出限制
const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

// 上传文件
const handleUpload = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  if (!form.category_id) {
    ElMessage.warning('请选择目录')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value.raw)
    formData.append('drawing_name', form.drawing_name)
    formData.append('category_id', form.category_id)
    formData.append('visibility', form.visibility)

    await uploadDrawing(formData)

    ElMessage.success('上传成功')
    emit('success')
    handleClose()
  } catch (error) {
    console.error('上传失败', error)
  } finally {
    uploading.value = false
  }
}

// 关闭对话框
const handleClose = () => {
  formRef.value && formRef.value.resetFields()
  uploadRef.value && uploadRef.value.clearFiles()
  selectedFile.value = null
  form.file = null
  form.drawing_name = ''
  form.category_id = null
  form.category_path = []
  form.visibility = 'login'  // 重置为默认值
  emit('update:modelValue', false)
}
</script>

<style scoped>
:deep(.el-upload-dragger) {
  width: 100%;
}

.cascader-node-label {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}
</style>
