<template>
  <el-container class="recycle-bin-container">
    <el-header class="page-header">
      <h2>回收站</h2>
    </el-header>

    <el-main>
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="filters.file_name"
          placeholder="文件名称"
          clearable
          @clear="loadDeletedFiles"
          @keyup.enter="loadDeletedFiles"
          style="width: 200px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="filters.file_type" placeholder="文件类型" clearable @change="loadDeletedFiles" style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="doc" />
          <el-option label="Word" value="docx" />
        </el-select>

        <el-button type="primary" @click="loadDeletedFiles">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>

        <el-button @click="handleBatchRestore" :disabled="selectedFiles.length === 0">
          <el-icon><RefreshLeft /></el-icon>
          批量还原
        </el-button>

        <el-button type="danger" @click="handleBatchDelete" :disabled="selectedFiles.length === 0">
          <el-icon><Delete /></el-icon>
          批量彻底删除
        </el-button>
      </div>

      <!-- 文件列表 -->
      <el-card>
        <el-table
          :data="deletedFiles"
          v-loading="loading"
          stripe
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="drawing_name" label="文件名称" min-width="200" />
          <el-table-column prop="file_type" label="文件类型" width="100">
            <template #default="{ row }">
              <el-tag>{{ row.file_type.toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="deleted_at" label="删除时间" width="180" />
          <el-table-column prop="days_left" label="剩余天数" width="100">
            <template #default="{ row }">
              <el-tag :type="getDaysColor(row.days_left)">{{ row.days_left }}天</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="upload_username" label="上传用户" width="120" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="handleRestore(row)">
                还原
              </el-button>
              <el-button type="danger" size="small" @click="handlePermanentDelete(row)">
                彻底删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadDeletedFiles"
            @current-change="loadDeletedFiles"
          />
        </div>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Delete } from '@element-plus/icons-vue'
import axios from 'axios'

const loading = ref(false)
const deletedFiles = ref([])
const selectedFiles = ref([])

// 筛选条件
const filters = reactive({
  file_name: '',
  file_type: ''
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 加载已删除文件
const loadDeletedFiles = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/recycle-bin', {
      headers: { 'Authorization': token },
      params: {
        page: pagination.page,
        size: pagination.size,
        ...filters
      }
    })

    deletedFiles.value = response.data.files || []
    pagination.total = response.data.total || 0
  } catch (error) {
    console.error('加载回收站失败', error)
    ElMessage.error('加载回收站失败')
  } finally {
    loading.value = false
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedFiles.value = selection
}

// 获取剩余天数颜色
const getDaysColor = (days) => {
  if (days <= 1) return 'danger'
  if (days <= 3) return 'warning'
  return 'success'
}

// 还原文件
const handleRestore = async (row) => {
  try {
    await ElMessageBox.confirm('确定要还原此文件吗？', '提示', {
      type: 'info'
    })

    const token = localStorage.getItem('token')
    await axios.put(`/api/recycle-bin/${row.drawing_id}/restore`, {}, {
      headers: { 'Authorization': token }
    })

    ElMessage.success('还原成功')
    loadDeletedFiles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('还原失败', error)
      ElMessage.error('还原失败')
    }
  }
}

// 彻底删除
const handlePermanentDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要彻底删除此文件吗？删除后将无法恢复！', '警告', {
      type: 'warning'
    })

    const token = localStorage.getItem('token')
    await axios.delete(`/api/recycle-bin/${row.drawing_id}`, {
      headers: { 'Authorization': token }
    })

    ElMessage.success('删除成功')
    loadDeletedFiles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败', error)
      ElMessage.error('删除失败')
    }
  }
}

// 批量还原
const handleBatchRestore = async () => {
  if (selectedFiles.value.length === 0) return

  try {
    await ElMessageBox.confirm(`确定要还原选中的 ${selectedFiles.value.length} 个文件吗？`, '提示', {
      type: 'info'
    })

    const token = localStorage.getItem('token')
    const drawingIds = selectedFiles.value.map(f => f.drawing_id)

    await axios.put('/api/recycle-bin/batch-restore', { drawing_ids: drawingIds }, {
      headers: { 'Authorization': token }
    })

    ElMessage.success('批量还原成功')
    selectedFiles.value = []
    loadDeletedFiles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量还原失败', error)
      ElMessage.error('批量还原失败')
    }
  }
}

// 批量彻底删除
const handleBatchDelete = async () => {
  if (selectedFiles.value.length === 0) return

  try {
    await ElMessageBox.confirm(`确定要彻底删除选中的 ${selectedFiles.value.length} 个文件吗？删除后将无法恢复！`, '警告', {
      type: 'warning'
    })

    const token = localStorage.getItem('token')
    const drawingIds = selectedFiles.value.map(f => f.drawing_id)

    await axios.delete('/api/recycle-bin/batch', {
      headers: { 'Authorization': token },
      data: { drawing_ids: drawingIds }
    })

    ElMessage.success('批量删除成功')
    selectedFiles.value = []
    loadDeletedFiles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败', error)
      ElMessage.error('批量删除失败')
    }
  }
}

onMounted(() => {
  loadDeletedFiles()
})
</script>

<style scoped>
.recycle-bin-container {
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
}

.page-header h2 {
  margin: 0;
  color: #333;
}

.el-main {
  padding: 20px;
  background-color: #f5f5f5;
}

.filter-bar {
  background-color: #fff;
  padding: 15px;
  margin-bottom: 15px;
  border: 1px solid #e6e6e6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
