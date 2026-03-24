import request from './index'

// 获取分类列表
export const getCategories = () => {
  return request({
    url: '/categories',
    method: 'GET'
  })
}

// 创建分类
export const createCategory = (data) => {
  return request({
    url: '/categories',
    method: 'POST',
    data
  })
}

// 更新分类
export const updateCategory = (categoryId, data) => {
  return request({
    url: `/categories/${categoryId}`,
    method: 'PUT',
    data
  })
}

// 删除分类
export const deleteCategory = (categoryId) => {
  return request({
    url: `/categories/${categoryId}`,
    method: 'DELETE'
  })
}

// 获取图纸列表
export const getDrawings = (params) => {
  return request({
    url: '/drawings',
    method: 'GET',
    params
  })
}

// 上传图纸
export const uploadDrawing = (formData) => {
  return request({
    url: '/drawings',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 更新图纸（修改目录）
export const updateDrawing = (drawingId, data) => {
  return request({
    url: `/drawings/${drawingId}`,
    method: 'PUT',
    data
  })
}

// 删除图纸
export const deleteDrawing = (drawingId) => {
  return request({
    url: `/drawings/${drawingId}`,
    method: 'DELETE'
  })
}

// 下载图纸
export const downloadDrawing = (drawingId) => {
  return `/api/drawings/${drawingId}/download`
}

// 预览图纸
export const previewDrawing = (drawingId) => {
  return `/api/drawings/${drawingId}/preview`
}

// 获取预览图片（将 PDF/Word/Excel/OFD/CEB 转换为图片）
export const getPreviewImages = (drawingId) => {
  return request({
    url: `/drawings/${drawingId}/preview-images`,
    method: 'GET'
  })
}

// 获取 kkFileView 预览链接
export const getKkPreviewUrl = (drawingId) => {
  return request({
    url: `/drawings/${drawingId}/preview-url`,
    method: 'GET'
  })
}
