<template>
  <div class="preview-panel">
    <div v-if="showHeader" class="header">
      <div class="title">{{ drawingName }}</div>
      <div class="meta">{{ fileTypeUpper }}</div>
    </div>

    <div v-if="loading" class="loading">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <p>{{ loadingText }}</p>
    </div>

    <div v-else-if="error" class="error">
      <el-result icon="warning" :title="errorMessage">
        <template #extra>
          <el-button type="primary" @click="loadPreview">重试</el-button>
        </template>
      </el-result>
    </div>

    <div v-else-if="mode === 'html'" :class="['html-container', { 'excel-html-container': isExcel }]">
      <div v-if="isExcel" class="toolbar html-toolbar">
        <el-button-group>
          <el-button :type="excelHtmlMode === 'fast' ? 'primary' : 'default'" @click="switchExcelHtmlMode('fast')">
            快速模式
          </el-button>
          <el-button :type="excelHtmlMode === 'full' ? 'primary' : 'default'" @click="switchExcelHtmlMode('full')">
            完整模式
          </el-button>
        </el-button-group>
        <span class="mode-tip">
          {{ excelHtmlMode === 'fast' ? '1000 行 × 100 列（更快）' : '5000 行 × 300 列（更完整）' }}
        </span>
      </div>
      <iframe
        v-if="iframeUrl"
        :src="iframeUrl"
        :class="['preview-iframe', { 'excel-preview-iframe': isExcel }]"
      ></iframe>
    </div>

    <div v-else-if="mode === 'images'" class="image-container">
      <div class="toolbar">
        <el-button-group>
          <el-button :disabled="currentPage <= 1" @click="currentPage--">上一页</el-button>
          <el-button disabled>{{ currentPage }} / {{ totalPages }}</el-button>
          <el-button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</el-button>
        </el-button-group>

        <el-divider direction="vertical" />

        <el-button size="small" @click="zoomOut" :disabled="scale <= 0.25">-</el-button>
        <el-slider v-model="scalePercent" :min="25" :max="300" :step="5" style="width: 120px" />
        <el-button size="small" @click="zoomIn" :disabled="scale >= 3">+</el-button>
        <span class="scale-text">{{ scalePercent }}%</span>
      </div>

      <div class="image-content" @wheel="onWheel">
        <img
          v-if="currentImage"
          :src="currentImage"
          class="preview-image"
          :style="{ transform: `scale(${scale})` }"
          draggable="false"
        />
        <div v-else class="page-loading">正在加载第 {{ currentPage }} 页...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getPreviewImages } from '@/api/file'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  drawingId: { type: Number, required: true },
  fileType: { type: String, required: true },
  drawingName: { type: String, default: '文件预览' },
  showHeader: { type: Boolean, default: false }
})

const token = localStorage.getItem('token') || ''

const loading = ref(true)
const error = ref(false)
const errorMessage = ref('')
const mode = ref('')
const iframeUrl = ref('')
const images = ref([])
const totalPages = ref(0)
const currentPage = ref(1)
const scale = ref(1)
const excelHtmlMode = ref('fast')
const lazyImageMode = ref(false)

const normalizedFileType = computed(() => String(props.fileType || '').toLowerCase())
const fileTypeUpper = computed(() => normalizedFileType.value.toUpperCase())
const isExcel = computed(() => ['xls', 'xlsx'].includes(normalizedFileType.value))
const currentImage = computed(() => images.value[currentPage.value - 1] || '')
const imageDpi = computed(() => (normalizedFileType.value === 'pdf' ? 120 : 140))
const scalePercent = computed({
  get: () => Math.round(scale.value * 100),
  set: (v) => { scale.value = Math.max(0.25, Math.min(3, v / 100)) }
})
const loadingText = computed(() => {
  if (['doc', 'docx'].includes(normalizedFileType.value)) return '正在转换 Word 文档...'
  if (['xls', 'xlsx'].includes(normalizedFileType.value)) return '正在加载 Excel 预览...'
  if (normalizedFileType.value === 'pdf') return '正在加载 PDF...'
  if (normalizedFileType.value === 'ofd') return '正在转换 OFD 文档...'
  if (normalizedFileType.value === 'ceb') return '正在转换 CEB 文档...'
  return '正在加载预览...'
})

const buildApiUrl = (path) => {
  if (!token) return path
  const joiner = path.includes('?') ? '&' : '?'
  return `${path}${joiner}token=${encodeURIComponent(token)}`
}

const tryHtmlPreview = async () => {
  const htmlParams = excelHtmlMode.value === 'full'
    ? '?full=1&max_rows=5000&max_cols=300'
    : '?max_rows=1000&max_cols=100'
  const htmlUrl = buildApiUrl(`/api/drawings/${props.drawingId}/preview-html${isExcel.value ? htmlParams : ''}`)
  const res = await fetch(htmlUrl, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  const ct = res.headers.get('content-type') || ''
  if (!res.ok || !ct.includes('text/html')) {
    let msg = 'HTML 预览不可用'
    try {
      const data = await res.json()
      if (data?.error) msg = data.error
    } catch {}
    throw new Error(msg)
  }
  mode.value = 'html'
  iframeUrl.value = htmlUrl
}

const switchExcelHtmlMode = async (nextMode) => {
  if (!isExcel.value || excelHtmlMode.value === nextMode) return
  excelHtmlMode.value = nextMode
  await loadPreview()
}

const loadImagePreview = async () => {
  const meta = await getPreviewImages(props.drawingId, { lazy: 1, meta: 1, dpi: imageDpi.value })
  if (!meta.success || !meta.page_count) {
    throw new Error(meta.error || '图片预览失败')
  }
  mode.value = 'images'
  lazyImageMode.value = true
  totalPages.value = meta.page_count
  images.value = Array(meta.page_count).fill('')
  currentPage.value = 1
  await loadImagePage(1)
}

const loadImagePage = async (page) => {
  if (page < 1 || page > totalPages.value) return
  if (!lazyImageMode.value) return
  if (images.value[page - 1]) return

  const data = await getPreviewImages(props.drawingId, { lazy: 1, page, dpi: imageDpi.value })
  if (!data.success || !data.image) {
    throw new Error(data.error || `第 ${page} 页加载失败`)
  }
  images.value[page - 1] = data.image
}

const loadPreview = async () => {
  loading.value = true
  error.value = false
  errorMessage.value = ''
  mode.value = ''
  iframeUrl.value = ''
  images.value = []
  totalPages.value = 0
  currentPage.value = 1
  scale.value = 1
  lazyImageMode.value = false

  try {
    if (['pdf', 'doc', 'docx', 'ofd', 'ceb'].includes(normalizedFileType.value)) {
      await loadImagePreview()
    } else if (['xls', 'xlsx'].includes(normalizedFileType.value)) {
      await tryHtmlPreview()
    } else {
      await loadImagePreview()
    }
  } catch (e) {
    error.value = true
    errorMessage.value = e.message || '预览失败'
  } finally {
    loading.value = false
  }
}

const zoomIn = () => { if (scale.value < 3) scale.value = Math.min(3, scale.value + 0.1) }
const zoomOut = () => { if (scale.value > 0.25) scale.value = Math.max(0.25, scale.value - 0.1) }
const onWheel = (e) => {
  if (mode.value !== 'images') return
  if (e.ctrlKey) {
    if (e.deltaY < 0) zoomIn()
    else zoomOut()
    return
  }
  if (e.deltaY > 0 && currentPage.value < totalPages.value) currentPage.value++
  if (e.deltaY < 0 && currentPage.value > 1) currentPage.value--
}

onMounted(loadPreview)

watch(currentPage, async (page) => {
  if (mode.value !== 'images' || !lazyImageMode.value) return
  try {
    await loadImagePage(page)
    if (page + 1 <= totalPages.value) {
      loadImagePage(page + 1).catch(() => {})
    }
  } catch (e) {
    error.value = true
    errorMessage.value = e.message || '分页加载失败'
  }
})
</script>

<style scoped>
.preview-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafafa;
}

.title {
  font-size: 14px;
  color: #303133;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  color: #909399;
  font-size: 12px;
  margin-left: 12px;
}

.loading, .error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.html-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.preview-iframe {
  width: 100%;
  flex: 1;
  min-height: 0;
  border: none;
}

.excel-html-container {
  min-height: 980px;
}

.excel-preview-iframe {
  min-height: 980px;
}

.image-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #e8e8e8;
  background: #f7f7f7;
}

.html-toolbar {
  border-bottom: 1px solid #e8e8e8;
}

.mode-tip {
  color: #606266;
  font-size: 12px;
}

.scale-text {
  width: 52px;
  color: #606266;
  font-size: 12px;
}

.image-content {
  flex: 1;
  overflow: auto;
  background: #efefef;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 20px;
}

.preview-image {
  max-width: 100%;
  height: auto;
  transform-origin: top center;
}

.page-loading {
  color: #606266;
  font-size: 13px;
  padding-top: 24px;
}
</style>
