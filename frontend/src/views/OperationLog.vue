<template>
  <el-container class="operation-log-container">
    <el-header class="page-header">
      <h2>操作记录</h2>
    </el-header>

    <el-main>
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filters.operation_type" placeholder="操作类型" clearable @change="loadLogs" style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="上传" value="upload" />
          <el-option label="预览" value="preview" />
          <el-option label="下载" value="download" />
          <el-option label="删除" value="delete" />
          <el-option label="修改" value="modify" />
        </el-select>

        <el-input
          v-model="filters.username"
          placeholder="用户名"
          clearable
          @clear="loadLogs"
          @keyup.enter="loadLogs"
          style="width: 200px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button type="primary" @click="loadLogs">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
      </div>

      <!-- 操作记录列表 -->
      <el-card>
        <el-table :data="logs" v-loading="loading" stripe>
          <el-table-column prop="operation_time" label="操作时间" width="180" sortable />
          <el-table-column prop="username" label="操作用户" width="120" />
          <el-table-column prop="operation_type" label="操作类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getOperationTypeColor(row.operation_type)">
                {{ getOperationTypeName(row.operation_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="drawing_name" label="文件名称" min-width="200">
            <template #default="{ row }">
              {{ row.drawing_name || '-' }}
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
            @size-change="loadLogs"
            @current-change="loadLogs"
          />
        </div>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import axios from 'axios'

const loading = ref(false)
const logs = ref([])

// 筛选条件
const filters = reactive({
  operation_type: '',
  username: ''
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 获取操作类型名称
const getOperationTypeName = (type) => {
  const typeMap = {
    'upload': '上传',
    'preview': '预览',
    'download': '下载',
    'delete': '删除',
    'modify': '修改'
  }
  return typeMap[type] || type
}

// 获取操作类型颜色
const getOperationTypeColor = (type) => {
  const colorMap = {
    'upload': 'success',
    'preview': 'primary',
    'download': 'info',
    'delete': 'danger',
    'modify': 'warning'
  }
  return colorMap[type] || ''
}

// 加载操作记录
const loadLogs = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/operation-logs', {
      headers: { 'Authorization': token },
      params: {
        page: pagination.page,
        size: pagination.size,
        ...filters
      }
    })

    logs.value = response.data.logs || []
    pagination.total = response.data.total || 0
  } catch (error) {
    console.error('加载操作记录失败', error)
    ElMessage.error('加载操作记录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.operation-log-container {
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
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
