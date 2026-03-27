<template>
  <el-container class="home-container">
    <!-- 顶部栏 -->
    <el-header class="header">
      <div class="header-left">
        <h2>{{ interfaceSettings.appTitle }}</h2>
      </div>
      <div class="header-right">
        <!-- 未登录：显示登录按钮 -->
        <template v-if="!userStore.isLoggedIn">
          <el-button type="primary" @click="handleLogin">
            <el-icon><User /></el-icon>
            登录
          </el-button>
        </template>
        <!-- 已登录：显示用户头像 -->
        <template v-else>
          <el-dropdown trigger="hover" class="user-dropdown">
            <div class="user-avatar-wrapper">
              <el-avatar v-if="userAvatar" :src="userAvatar" :size="40" />
              <el-avatar v-else class="username-avatar">{{ userStore.user && userStore.user.username && userStore.user.username.charAt(0).toUpperCase() }}</el-avatar>
              <span class="username-text">{{ userStore.user && userStore.user.username }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showInterfaceDialog = true">
                  <el-icon><Setting /></el-icon>
                  界面调整
                </el-dropdown-item>
                <el-dropdown-item @click="showUserProfileDialog = true">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <!-- 管理员专用的用户管理选项 -->
                <el-dropdown-item v-if="userStore.isAdmin" @click="showUserManageDialog = true">
                  <el-icon><User /></el-icon>
                  用户管理
                </el-dropdown-item>
                <el-dropdown-item :divided="true" @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </el-header>

    <!-- 主内容区 -->
    <el-container class="main-content">
      <!-- 左侧目录树 -->
      <el-aside width="300px" class="sidebar">
        <el-card class="directory-card">
          <template #header>
            <div class="card-header">
              <span>文件目录</span>
              <el-button v-if="userStore.isLoggedIn" type="primary" size="small" @click="handleAddRootCategory">
                <el-icon><FolderAdd /></el-icon>
                新建
              </el-button>
            </div>
          </template>

          <!-- 目录搜索 -->
          <el-input
            v-model="filterText"
            placeholder="输入关键字过滤"
            prefix-icon="Search"
            clearable
            style="margin-bottom: 10px"
          />

          <!-- 目录树 -->
          <div class="tree-container">
            <el-tree
              ref="categoryTreeRef"
              :data="categoryTreeData"
              :props="treeProps"
              :filter-node-method="filterNode"
              node-key="category_id"
              :default-expanded-keys="expandedKeys"
              :expand-on-click-node="false"
              accordion
              @node-click="handleCategoryClick"
              @node-expand="handleNodeExpand"
              @node-collapse="handleNodeCollapse"
            >
              <template #default="{ node, data }">
                <span
                  class="custom-tree-node"
                  @contextmenu.prevent="userStore.isLoggedIn && showContextMenu(data, $event)"
                >
                  <el-tooltip :content="node.label" placement="top" :show-after="500">
                    <span class="tree-node-label">{{ node.label }}</span>
                  </el-tooltip>
                </span>
              </template>
            </el-tree>
          </div>

          <!-- 右键菜单（仅登录时显示） -->
          <div
            v-if="userStore.isLoggedIn && contextMenuVisible"
            class="context-menu"
            :style="{ top: contextMenuY + 'px', left: contextMenuX + 'px' }"
          >
            <div class="context-menu-item" @click="handleUploadToNode">
              <el-icon><Upload /></el-icon>
              上传到此目录
            </div>
            <div class="context-menu-item" @click="handleAddCategory">
              <el-icon><FolderAdd /></el-icon>
              新建子目录
            </div>
            <div class="context-menu-item" @click="handleEditCategory">
              <el-icon><Edit /></el-icon>
              修改
            </div>
            <div class="context-menu-item danger" @click="handleDeleteCategory">
              <el-icon><Delete /></el-icon>
              删除
            </div>
          </div>
        </el-card>

        <!-- 底部按钮区 -->
        <div class="sidebar-buttons">
          <el-tooltip
            content="请先登录"
            placement="top"
            :disabled="userStore.isLoggedIn"
          >
            <el-button
              class="sidebar-btn"
              :disabled="!userStore.isLoggedIn"
              @click="userStore.isLoggedIn && (showOperationLogDialog = true)"
            >
              <el-icon><Document /></el-icon>
              操作记录
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="请先登录"
            placement="top"
            :disabled="userStore.isLoggedIn"
          >
            <el-button
              class="sidebar-btn"
              :disabled="!userStore.isLoggedIn"
              @click="userStore.isLoggedIn && (showRecycleBinDialog = true)"
            >
              <el-icon><DeleteFilled /></el-icon>
              回收站
            </el-button>
          </el-tooltip>
        </div>
      </el-aside>

      <!-- 右侧主内容 -->
      <el-main>
        <!-- 面包屑导航 -->
        <el-breadcrumb separator="/" style="margin-bottom: 15px">
          <el-breadcrumb-item
            v-for="(item, index) in breadcrumbList"
            :key="index"
            @click="handleBreadcrumbClick(item, index)"
            style="cursor: pointer"
          >
            {{ item.name }}
          </el-breadcrumb-item>
        </el-breadcrumb>

        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-select v-model="filters.file_type" placeholder="文件类型" clearable @change="loadDrawings" style="width: 200px">
            <el-option label="全部" value="" />
            <el-option label="PDF" value="pdf" />
            <el-option label="Word (doc)" value="doc" />
            <el-option label="Word (docx)" value="docx" />
            <el-option label="Excel (xls)" value="xls" />
            <el-option label="Excel (xlsx)" value="xlsx" />
            <el-option label="OFD" value="ofd" />
            <el-option label="CEB" value="ceb" />
          </el-select>

          <el-input
            v-model="filters.file_name"
            placeholder="文件名称"
            clearable
            @clear="loadDrawings"
            @keyup.enter="loadDrawings"
            style="width: 500px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-input
            v-model="filters.user_name"
            placeholder="上传用户"
            clearable
            @clear="loadDrawings"
            @keyup.enter="loadDrawings"
            style="width: 400px"
          />

          <!-- 按钮组靠右 -->
          <div class="filter-bar-actions">
            <el-button type="primary" @click="loadDrawings" class="search-btn">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleRefresh">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>

            <!-- 上传按钮（仅登录时显示） -->
            <el-button v-if="userStore.isLoggedIn" type="success" @click="handleUploadFile">
              <el-icon><Upload /></el-icon>
              上传文件
            </el-button>
          </div>
        </div>

        <!-- 文件列表 -->
        <el-card>
          <el-table
            :data="drawings"
            v-loading="loading"
            stripe
            :default-sort="{ prop: 'upload_time', order: 'descending' }"
            @sort-change="handleSortChange"
            border
            :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
          >
            <el-table-column prop="drawing_name" label="文件名称" min-width="150" sortable="custom" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="text-ellipsis">{{ row.drawing_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="file_type" label="文件类型" width="100">
              <template #default="{ row }">
                <el-tag>{{ row.file_type.toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="upload_time" label="上传时间" width="180" sortable="custom" />
            <el-table-column prop="file_size" label="大小" width="120" sortable="custom">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="category_path" label="所属目录" min-width="150" sortable="custom" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="text-ellipsis">{{ getCategoryPath(row.category_id) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="upload_username" label="上传用户" width="120" />
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="handlePreview(row)">预览</el-button>
                <el-button type="success" size="small" @click="handleDownload(row)">下载</el-button>
                <el-button type="warning" size="small" @click="handleModifyCategory(row)" v-if="canModifyFile(row)">修改</el-button>
                <el-button type="danger" size="small" @click="handleDelete(row)" v-if="canDeleteFile(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-main>
    </el-container>

    <!-- 上传对话框 -->
    <UploadDialog
      v-model="showUploadDialog"
      :categories="categories"
      :default-category-id="defaultUploadCategoryId"
      @success="handleUploadSuccess"
    />

    <!-- 新建分类对话框 -->
    <el-dialog v-model="showCategoryDialog" title="新建文件夹" width="400px">
      <el-form :model="categoryForm" label-width="100px">
        <el-form-item label="文件夹名称">
          <el-input v-model="categoryForm.category_name" placeholder="不填则默认为'新建文件夹'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCategoryDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateCategory">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改分类对话框 -->
    <el-dialog v-model="showEditCategoryDialog" title="修改文件夹" width="400px">
      <el-form :model="editCategoryForm" label-width="100px">
        <el-form-item label="文件夹名称">
          <el-input v-model="editCategoryForm.category_name" placeholder="请输入文件夹名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditCategoryDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateCategory">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改文件目录对话框 -->
    <el-dialog v-model="showModifyDialog" title="修改文件目录" width="500px">
      <el-form :model="modifyForm" label-width="100px">
        <el-form-item label="文件名称">
          <el-input v-model="modifyForm.drawing_name" disabled />
        </el-form-item>
        <el-form-item label="所属目录" prop="category_id">
          <el-cascader
            v-model="modifyForm.category_path"
            :options="categoryTreeOptions"
            :props="cascaderProps"
            placeholder="请选择目录"
            clearable
            style="width: 100%"
            @change="handleModifyCategoryChange"
          >
            <template #default="{ node, data }">
              <el-tooltip :content="data.label" placement="top" :show-after="500">
                <span class="cascader-node-label">{{ data.label }}</span>
              </el-tooltip>
            </template>
          </el-cascader>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModifyDialog = false">取消</el-button>
        <el-button type="primary" :loading="modifying" @click="handleSaveModify">保存</el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 - 标签页模式 -->
    <el-dialog
      v-model="showPreviewDialog"
      width="95%"
      class="preview-tabs-dialog"
      :fullscreen="previewFullscreen"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <template #header>
        <div class="preview-dialog-header">
          <span class="preview-dialog-title">文件预览</span>
          <div class="preview-dialog-actions">
            <el-tooltip content="下载当前文件" placement="top">
              <el-button circle size="small" type="primary" @click="handleDownloadCurrent">
                <el-icon><Download /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="最小化" placement="top">
              <el-button circle size="small" @click="minimizePreviewDialog">
                <el-icon><Minus /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip :content="previewFullscreen ? '退出全屏' : '全屏'" placement="top">
              <el-button circle size="small" @click="togglePreviewFullscreen">
                <el-icon><FullScreen /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="全部关闭" placement="top">
              <el-button circle size="small" type="danger" plain @click="closeAllPreviewTabs">
                <el-icon><CloseBold /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>
      </template>

      <el-tabs
        v-model="activePreviewTabId"
        type="card"
        :editable="true"
        @edit="handleCloseTab"
        @tab-change="handleTabChange"
      >
        <el-tab-pane
          v-for="tab in previewTabs"
          :key="tab.id"
          :name="tab.id"
          :label="tab.drawing_name"
        >
          <div class="embedded-preview-container">
            <PreviewPanel
              :drawing-id="tab.drawing_id"
              :file-type="tab.file_type"
              :drawing-name="tab.drawing_name"
              :show-header="false"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-badge
      v-if="showPreviewFab"
      :value="previewBadgeCount"
      :max="99"
      :class="['preview-fab-badge', { 'is-unread': previewUnreadCount > 0 }]"
    >
      <el-button
        :class="['preview-fab', { 'is-unread': previewUnreadCount > 0, 'is-pulse': previewFabPulse }]"
        type="primary"
        circle
        @click="restorePreviewDialog"
      >
        <el-icon><View /></el-icon>
      </el-button>
    </el-badge>

    <!-- 操作记录对话框 -->
    <el-dialog v-model="showOperationLogDialog" title="操作记录" width="80%" class="full-height-dialog">
      <div class="filter-bar">
        <el-select v-model="logFilters.operation_type" placeholder="操作类型" clearable @change="loadLogs" style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="上传" value="upload" />
          <el-option label="预览" value="preview" />
          <el-option label="下载" value="download" />
          <el-option label="删除" value="delete" />
          <el-option label="修改" value="modify" />
        </el-select>

        <el-input
          v-model="logFilters.username"
          placeholder="用户名"
          clearable
          @clear="loadLogs"
          @keyup.enter="loadLogs"
          style="width: 120px"
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

      <el-table :data="logs" v-loading="logsLoading" stripe>
        <el-table-column prop="operation_time" label="操作时间" width="180" />
        <el-table-column prop="username" label="操作用户" width="120" />
        <el-table-column prop="operation_type" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getOperationTypeColor(row.operation_type)">
              {{ getOperationTypeName(row.operation_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation_content" label="操作内容" min-width="200">
          <template #default="{ row }">
            {{ row.operation_content || row.drawing_name || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="logPagination.page"
          v-model:page-size="logPagination.size"
          :total="logPagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-dialog>

    <!-- 回收站对话框 -->
    <el-dialog v-model="showRecycleBinDialog" title="回收站" width="80%" class="full-height-dialog">
      <div class="filter-bar">
        <el-input
          v-model="recycleFilters.file_name"
          placeholder="文件名称"
          clearable
          @clear="loadRecycleBin"
          @keyup.enter="loadRecycleBin"
          style="width: 150px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="recycleFilters.file_type" placeholder="文件类型" clearable @change="loadRecycleBin" style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="PDF" value="pdf" />
          <el-option label="Word (doc)" value="doc" />
          <el-option label="Word (docx)" value="docx" />
          <el-option label="Excel (xls)" value="xls" />
          <el-option label="Excel (xlsx)" value="xlsx" />
          <el-option label="OFD" value="ofd" />
          <el-option label="CEB" value="ceb" />
        </el-select>

        <el-button type="primary" @click="loadRecycleBin">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>

        <el-button @click="handleBatchRestore" :disabled="selectedRecycleFiles.length === 0">
          <el-icon><RefreshLeft /></el-icon>
          批量还原
        </el-button>

        <el-button type="danger" @click="handleBatchDelete" :disabled="selectedRecycleFiles.length === 0">
          <el-icon><Delete /></el-icon>
          批量彻底删除
        </el-button>
      </div>

      <el-table
        :data="recycleFiles"
        v-loading="recycleLoading"
        stripe
        @selection-change="handleRecycleSelectionChange"
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

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="recyclePagination.page"
          v-model:page-size="recyclePagination.size"
          :total="recyclePagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadRecycleBin"
          @current-change="loadRecycleBin"
        />
      </div>
    </el-dialog>

    <!-- 个人中心对话框 -->
    <el-dialog v-model="showUserProfileDialog" title="个人中心" width="600px">
      <div class="avatar-section">
        <el-avatar :size="120" :src="userProfileAvatar" class="avatar">
          {{ userStore.user && userStore.user.username && userStore.user.username.charAt(0).toUpperCase() }}
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

      <el-form :model="userProfileForm" label-width="100px" class="user-form">
        <el-form-item label="用户名">
          <el-input v-model="userProfile.username" disabled />
        </el-form-item>

        <el-form-item label="角色">
          <el-input :value="userProfile.role === 'admin' ? '管理员' : '普通用户'" disabled />
        </el-form-item>

        <el-form-item label="注册时间">
          <el-input v-model="userProfile.create_time" disabled />
        </el-form-item>

        <el-form-item label="手机号">
          <el-input
            v-model="userProfileForm.phone"
            placeholder="请输入手机号"
            clearable
            maxlength="11"
          />
        </el-form-item>

        <el-form-item label="新密码">
          <el-input
            v-model="userProfileForm.new_password"
            type="password"
            placeholder="不修改请留空"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="确认密码">
          <el-input
            v-model="userProfileForm.confirm_password"
            type="password"
            placeholder="不修改请留空"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleUpdateProfile" :loading="updatingProfile">
            保存修改
          </el-button>
          <el-button @click="resetProfileForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 界面调整对话框 -->
    <el-dialog v-model="showInterfaceDialog" title="界面调整" width="650px">
      <el-form :model="interfaceSettings" label-width="140px" class="interface-form">
        <el-form-item label="界面标题">
          <el-input v-model="interfaceSettings.appTitle" placeholder="请输入界面标题" />
        </el-form-item>

        <el-form-item label="标题字号">
          <el-slider
            v-model="interfaceSettings.titleFontSize"
            :min="16"
            :max="30"
            show-input
            :marks="{ 16: '16px', 20: '20px', 24: '24px', 30: '30px' }"
          />
        </el-form-item>

        <el-form-item label="目录节点字号">
          <el-slider
            v-model="interfaceSettings.nodeFontSize"
            :min="14"
            :max="20"
            show-input
            :marks="{ 14: '14px', 16: '16px', 18: '18px', 20: '20px' }"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveInterfaceSettings(); showInterfaceDialog = false">
            保存设置
          </el-button>
          <el-button @click="resetInterfaceSettings">重置为默认</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 用户管理对话框（管理员） -->
    <el-dialog v-model="showUserManageDialog" title="用户管理" width="850px" class="user-manage-dialog">
      <div class="filter-bar">
        <el-input
          v-model="userFilters.username"
          placeholder="用户名"
          clearable
          @clear="loadUsers"
          @keyup.enter="loadUsers"
          style="width: 120px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="loadUsers">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
      </div>

      <el-table :data="users" v-loading="usersLoading" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="create_time" label="注册时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleResetPassword(row)">
              重置密码
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDeleteUser(row)"
              :disabled="row.user_id === (userStore.user && userStore.user.user_id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="userPagination.page"
        v-model:page-size="userPagination.size"
        :page-sizes="[10, 20, 50, 100]"
        :total="userPagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadUsers"
        @current-change="loadUsers"
      />
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import {
  Upload,
  SwitchButton,
  FolderAdd,
  Folder,
  Delete,
  DeleteFilled,
  Document,
  Search,
  Refresh,
  RefreshLeft,
  Download,
  Loading,
  User,
  Edit,
  Setting,
  ZoomIn,
  ZoomOut,
  View,
  Minus,
  FullScreen,
  CloseBold
} from '@element-plus/icons-vue'
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  getDrawings,
  updateDrawing,
  deleteDrawing,
  downloadDrawing
} from '@/api/file'
import UploadDialog from '@/components/UploadDialog.vue'
import PreviewPanel from '@/components/PreviewPanel.vue'

const router = useRouter()
const userStore = useUserStore()

// 对话框状态
const showOperationLogDialog = ref(false)
const showRecycleBinDialog = ref(false)
const showUserProfileDialog = ref(false)
const showUserManageDialog = ref(false)

// 数据
const categories = ref([])
const drawings = ref([])
const loading = ref(false)
const currentCategoryId = ref(null)
const categoryTreeRef = ref()
const expandedKeys = ref([])

// 用户头像（从 store 获取）
const userAvatar = computed(() => {
  if (userStore.user && userStore.user.avatar) {
    return `data:image/jpeg;base64,${userStore.user.avatar}`
  }
  return null
})

// 目录搜索
const filterText = ref('')

// 筛选条件
const filters = reactive({
  file_type: '',
  file_name: '',
  user_name: ''
})

// 面包屑
const breadcrumbList = ref([{ name: '目录', categoryId: null }])

// 对话框状态
const showUploadDialog = ref(false)
const defaultUploadCategoryId = ref(null)
const showCategoryDialog = ref(false)
const showEditCategoryDialog = ref(false)
const showInterfaceDialog = ref(false)

// 界面设置（使用 localStorage 持久化）
const interfaceSettings = reactive({
  appTitle: '文件管理系统',
  titleFontSize: 24,
  nodeFontSize: 16
})

// 预览状态 - 标签页模式
const showPreviewDialog = ref(false)
const previewFullscreen = ref(false)
const previewMinimized = ref(false)
const previewUnreadCount = ref(0)
const previewFabPulse = ref(false)
const MAX_PREVIEW_TABS = 5  // 最多 5 个标签页

// 当前激活的标签页 ID
const activePreviewTabId = ref(null)

// 预览标签页数组
const previewTabs = ref([])

// 获取当前激活的标签页
const currentPreviewTab = computed(() => {
  return previewTabs.value.find(tab => tab.id === activePreviewTabId.value)
})
const showPreviewFab = computed(() => previewMinimized.value && previewTabs.value.length > 0)
const previewBadgeCount = computed(() => {
  return previewUnreadCount.value > 0 ? previewUnreadCount.value : previewTabs.value.length
})

// 缩放百分比计算属性（基于当前标签页）
const scalePercent = computed({
  get: () => {
    const tab = currentPreviewTab.value
    return tab ? Math.round(tab.imageScale * 100) : 100
  },
  set: (value) => {
    const tab = currentPreviewTab.value
    if (tab) {
      tab.imageScale = Math.max(0.25, Math.min(3, value / 100))
    }
  }
})

// 图片拖动状态（基于当前标签页）
const getDragState = () => {
  const tab = currentPreviewTab.value
  if (!tab) return { isDragging: false, dragStart: { x: 0, y: 0 }, imagePosition: { x: 0, y: 0 } }
  return {
    isDragging: tab.isDragging || false,
    dragStart: tab.dragStart || { x: 0, y: 0 },
    imagePosition: tab.imagePosition || { x: 0, y: 0 }
  }
}

// 目录树右键菜单
const contextMenuVisible = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuNode = ref(null)
const currentParentNode = ref(null)

// 分类表单
const categoryForm = reactive({
  category_name: ''
})

// 修改分类表单
const editCategoryForm = reactive({
  category_id: null,
  category_name: ''
})

// 修改文件目录表单
const showModifyDialog = ref(false)
const modifying = ref(false)
const modifyForm = reactive({
  drawing_id: null,
  drawing_name: '',
  category_id: null,
  category_path: []
})

// 排序参数
const sortParams = reactive({
  prop: 'upload_time',
  order: 'descending'
})

// 树形组件配置
const treeProps = {
  children: 'children',
  label: 'category_name'
}

// Cascader 配置
const cascaderProps = {
  value: 'category_id',
  label: 'category_name',
  children: 'children',
  checkStrictly: true,
  emitPath: false
}

// 监听搜索
watch(filterText, (val) => {
  categoryTreeRef.value && categoryTreeRef.value.filter(val)
})

// ==================== 操作记录相关 ====================
const logs = ref([])
const logsLoading = ref(false)
const logFilters = reactive({
  operation_type: '',
  username: ''
})
const logPagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const getOperationTypeName = (type) => {
  const typeMap = {
    'upload': '上传',
    'preview': '预览',
    'download': '下载',
    'delete': '删除',
    'modify': '修改',
    'restore': '还原',
    'login': '登录',
    'update_profile': '修改个人信息',
    'add_folder': '添加文件夹',
    'delete_folder': '删除文件夹',
    'edit_folder': '修改文件夹',
    'delete_user': '删除用户',
    'reset_password': '重置密码'
  }
  return typeMap[type] || type
}

const getOperationTypeColor = (type) => {
  const colorMap = {
    'upload': 'success',
    'preview': 'primary',
    'download': 'info',
    'delete': 'danger',
    'modify': 'warning',
    'restore': 'success',
    'login': 'success',
    'update_profile': 'warning',
    'add_folder': 'primary',
    'delete_folder': 'danger',
    'edit_folder': 'warning',
    'delete_user': 'danger',
    'reset_password': 'warning'
  }
  return colorMap[type] || ''
}

const loadLogs = async () => {
  logsLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/operation-logs', {
      headers: { 'Authorization': token },
      params: {
        page: logPagination.page,
        size: logPagination.size,
        ...logFilters
      }
    })
    logs.value = response.data.logs || []
    logPagination.total = response.data.total || 0
  } catch (error) {
    console.error('加载操作记录失败', error)
    ElMessage.error('加载操作记录失败')
  } finally {
    logsLoading.value = false
  }
}

// ==================== 回收站相关 ====================
const recycleFiles = ref([])
const recycleLoading = ref(false)
const selectedRecycleFiles = ref([])
const recycleFilters = reactive({
  file_name: '',
  file_type: ''
})
const recyclePagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const handleRecycleSelectionChange = (selection) => {
  selectedRecycleFiles.value = selection
}

const getDaysColor = (days) => {
  if (days <= 1) return 'danger'
  if (days <= 3) return 'warning'
  return 'success'
}

const loadRecycleBin = async () => {
  recycleLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/recycle-bin', {
      headers: { 'Authorization': token },
      params: {
        page: recyclePagination.page,
        size: recyclePagination.size,
        ...recycleFilters
      }
    })
    recycleFiles.value = response.data.files || []
    recyclePagination.total = response.data.total || 0
  } catch (error) {
    console.error('加载回收站失败', error)
    ElMessage.error('加载回收站失败')
  } finally {
    recycleLoading.value = false
  }
}

const handleRestore = async (row) => {
  try {
    await ElMessageBox.confirm('确定要还原此文件吗？', '提示', { type: 'info' })
    const token = localStorage.getItem('token')
    await axios.put(`/api/recycle-bin/${row.drawing_id}/restore`, {}, {
      headers: { 'Authorization': token }
    })
    ElMessage.success('还原成功')
    loadRecycleBin()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('还原失败', error)
      ElMessage.error('还原失败')
    }
  }
}

const handlePermanentDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要彻底删除此文件吗？删除后将无法恢复！', '警告', { type: 'warning' })
    const token = localStorage.getItem('token')
    await axios.delete(`/api/recycle-bin/${row.drawing_id}`, {
      headers: { 'Authorization': token }
    })
    ElMessage.success('删除成功')
    loadRecycleBin()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleBatchRestore = async () => {
  if (selectedRecycleFiles.value.length === 0) return
  try {
    await ElMessageBox.confirm(`确定要还原选中的 ${selectedRecycleFiles.value.length} 个文件吗？`, '提示', { type: 'info' })
    const token = localStorage.getItem('token')
    const drawingIds = selectedRecycleFiles.value.map(f => f.drawing_id)
    await axios.put('/api/recycle-bin/batch-restore', { drawing_ids: drawingIds }, {
      headers: { 'Authorization': token }
    })
    ElMessage.success('批量还原成功')
    selectedRecycleFiles.value = []
    loadRecycleBin()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量还原失败', error)
      ElMessage.error('批量还原失败')
    }
  }
}

const handleBatchDelete = async () => {
  if (selectedRecycleFiles.value.length === 0) return
  try {
    await ElMessageBox.confirm(`确定要彻底删除选中的 ${selectedRecycleFiles.value.length} 个文件吗？删除后将无法恢复！`, '警告', { type: 'warning' })
    const token = localStorage.getItem('token')
    const drawingIds = selectedRecycleFiles.value.map(f => f.drawing_id)
    await axios.delete('/api/recycle-bin/batch', {
      headers: { 'Authorization': token },
      data: { drawing_ids: drawingIds }
    })
    ElMessage.success('批量删除成功')
    selectedRecycleFiles.value = []
    loadRecycleBin()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败', error)
      ElMessage.error('批量删除失败')
    }
  }
}

// ==================== 个人中心相关 ====================
const userProfile = ref({
  username: '',
  phone: '',
  role: '',
  create_time: '',
  avatar: null
})
const userProfileForm = reactive({
  phone: '',
  new_password: '',
  confirm_password: '',
  avatar_file: null
})
const updatingProfile = ref(false)

// 用户管理相关
const users = ref([])
const usersLoading = ref(false)
const userFilters = reactive({
  username: ''
})
const userPagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const userProfileAvatar = computed(() => {
  if (userProfile.value.avatar) {
    return `data:image/jpeg;base64,${userProfile.value.avatar}`
  }
  return null
})

const loadUserProfile = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/user/profile', {
      headers: { 'Authorization': token }
    })
    userProfile.value = response.data.user
    userProfileForm.phone = response.data.user.phone || ''
  } catch (error) {
    console.error('加载用户信息失败', error)
    ElMessage.error('加载用户信息失败')
  }
}

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
  userProfileForm.avatar_file = file.raw
  const reader = new FileReader()
  reader.onload = (e) => {
    userProfile.value.avatar = e.target.result.split(',')[1]
  }
  reader.readAsDataURL(file.raw)
}

const handleUpdateProfile = async () => {
  if (userProfileForm.phone && !/^1[3-9]\d{9}$/.test(userProfileForm.phone)) {
    ElMessage.warning('请输入正确的手机号格式')
    return
  }
  if (userProfileForm.new_password || userProfileForm.confirm_password) {
    if (userProfileForm.new_password !== userProfileForm.confirm_password) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
    if (userProfileForm.new_password.length < 6) {
      ElMessage.warning('密码长度不能少于 6 位')
      return
    }
  }
  updatingProfile.value = true
  try {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    if (userProfileForm.phone !== userProfile.value.phone) {
      formData.append('phone', userProfileForm.phone)
    }
    if (userProfileForm.new_password) {
      formData.append('new_password', userProfileForm.new_password)
    }
    if (userProfileForm.avatar_file) {
      formData.append('avatar', userProfileForm.avatar_file)
    }
    await axios.put('/api/user/profile', formData, {
      headers: { 'Authorization': token, 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success('修改成功')
    await loadUserProfile()
    await userStore.fetchUserInfo()
    showUserProfileDialog.value = false
  } catch (error) {
    console.error('更新用户信息失败', error)
    ElMessage.error(error.response && error.response.data && error.response.data.error || '更新失败')
  } finally {
    updatingProfile.value = false
  }
}

const resetProfileForm = () => {
  userProfileForm.phone = userProfile.value.phone || ''
  userProfileForm.new_password = ''
  userProfileForm.confirm_password = ''
  userProfileForm.avatar_file = null
}

// ==================== 用户管理相关 ====================
const loadUsers = async () => {
  usersLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/users', {
      headers: { 'Authorization': token },
      params: {
        page: userPagination.page,
        size: userPagination.size,
        ...userFilters
      }
    })
    users.value = response.data.users || []
    userPagination.total = response.data.total || 0
  } catch (error) {
    console.error('加载用户列表失败', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    usersLoading.value = false
  }
}

const handleDeleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除用户 "${row.username}" 吗？`, '警告', {
      type: 'warning'
    })

    const token = localStorage.getItem('token')
    await axios.delete(`/api/users/${row.user_id}`, {
      headers: { 'Authorization': token }
    })

    ElMessage.success('删除成功')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除用户失败', error)
      ElMessage.error('删除用户失败')
    }
  }
}

const handleResetPassword = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /^.{6,}$/,
      inputErrorMessage: '密码长度不能少于 6 位'
    })

    const token = localStorage.getItem('token')
    await axios.put(`/api/users/${row.user_id}/password`, {
      new_password: value
    }, {
      headers: { 'Authorization': token }
    })

    ElMessage.success('密码重置成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置密码失败', error)
      ElMessage.error('重置密码失败')
    }
  }
}

// 监听对话框打开，加载数据
watch(showOperationLogDialog, (val) => {
  if (val) loadLogs()
})
watch(showRecycleBinDialog, (val) => {
  if (val) loadRecycleBin()
})
watch(showUserProfileDialog, (val) => {
  if (val) loadUserProfile()
})
watch(showUserManageDialog, (val) => {
  if (val) loadUsers()
})

watch(showPreviewDialog, (val) => {
  if (!val && previewTabs.value.length > 0) {
    previewMinimized.value = true
  } else if (val) {
    previewMinimized.value = false
    previewUnreadCount.value = 0
    previewFabPulse.value = false
  }
})

// 监听登录状态变化，重新加载文件列表
watch(() => userStore.isLoggedIn, () => {
  loadDrawings()
})

// 扁平化分类列表
const flatCategories = computed(() => {
  const flatten = (list, level = 0) => {
    let result = []
    list.forEach(item => {
      result.push({
        category_id: item.category_id,
        category_name: '  '.repeat(level) + item.category_name
      })
      if (item.children && item.children.length > 0) {
        result = result.concat(flatten(item.children, level + 1))
      }
    })
    return result
  }
  return flatten(categories.value)
})

// 构建树形数据
const categoryTreeData = computed(() => {
  const buildTree = (parentId = 0) => {
    return categories.value
      .filter(c => {
        if (parentId === 0) {
          return c.parent_id === 0 || c.parent_id === null
        }
        return c.parent_id === parentId
      })
      .map(c => ({
        ...c,
        children: buildTree(c.category_id)
      }))
  }
  return buildTree()
})

// 构建分类树选项
const categoryTreeOptions = computed(() => {
  const buildTree = (parentId = null) => {
    return categories.value
      .filter(c => {
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

// 加载分类
const loadCategories = async () => {
  try {
    const data = await getCategories()
    categories.value = data.categories || []

    if (expandedKeys.value.length === 0) {
      const rootCategories = data.categories && data.categories.filter(c => !c.parent_id || c.parent_id === 0) || []
      expandedKeys.value = rootCategories.map(c => c.category_id)
    }
  } catch (error) {
    console.error('加载分类失败', error)
  }
}

// 节点展开时记录
const handleNodeExpand = (data, node) => {
  if (!expandedKeys.value.includes(data.category_id)) {
    expandedKeys.value.push(data.category_id)
  }
}

// 节点折叠时移除
const handleNodeCollapse = (data, node) => {
  const index = expandedKeys.value.indexOf(data.category_id)
  if (index > -1) {
    expandedKeys.value.splice(index, 1)
  }
}

// 当前选中的目录及其所有子目录 ID 列表
const selectedCategoryIds = ref([])

// 获取目录及其所有子目录的 ID
const getAllChildCategoryIds = (categoryId) => {
  if (categoryId === null || categoryId === undefined) {
    return []
  }

  const ids = [categoryId]

  const collectChildIds = (parentId) => {
    const children = categories.value.filter(c => c.parent_id === parentId)
    children.forEach(child => {
      ids.push(child.category_id)
      collectChildIds(child.category_id)
    })
  }

  collectChildIds(categoryId)
  return ids
}

// 点击分类
const handleCategoryClick = (data) => {
  currentCategoryId.value = data.category_id
  selectedCategoryIds.value = getAllChildCategoryIds(data.category_id)
  updateBreadcrumb(data)
  loadDrawings()
}

// 更新面包屑
const updateBreadcrumb = (categoryData) => {
  const buildPath = (categoryId) => {
    const path = []
    let current = categories.value.find(c => c.category_id === categoryId)

    while (current) {
      path.unshift(current)
      current = categories.value.find(c => c.category_id === current.parent_id)
    }

    return path
  }

  if (!categoryData || categoryData.category_id === null) {
    breadcrumbList.value = [{ name: '目录', categoryId: null }]
  } else {
    const path = buildPath(categoryData.category_id)
    breadcrumbList.value = path.map(c => ({ name: c.category_name, categoryId: c.category_id }))
  }
}

// 面包屑点击
const handleBreadcrumbClick = (item, index) => {
  if (item.categoryId === null) {
    currentCategoryId.value = null
    breadcrumbList.value = [{ name: '目录', categoryId: null }]
  } else {
    currentCategoryId.value = item.categoryId
    const category = categories.value.find(c => c.category_id === item.categoryId)
    updateBreadcrumb(category)
  }
  loadDrawings()
}

// 显示右键菜单
const showContextMenu = (data, event) => {
  currentParentNode.value = data
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  contextMenuNode.value = data
  contextMenuVisible.value = true
}

// 隐藏右键菜单
const hideContextMenu = () => {
  contextMenuVisible.value = false
}

// 新建一级分类
const handleAddRootCategory = () => {
  currentParentNode.value = null
  categoryForm.category_name = ''
  showCategoryDialog.value = true
}

// 新建分类
const handleAddCategory = () => {
  categoryForm.category_name = ''
  showCategoryDialog.value = true
  hideContextMenu()
}

const handleCreateCategory = async () => {
  const parent_id = currentParentNode.value && currentParentNode.value.category_id || 0

  const siblings = categories.value.filter(c => c.parent_id === parent_id || (parent_id === 0 && (c.parent_id === 0 || c.parent_id === null)))
  const sameNameCount = siblings.filter(c => c.category_name.includes('新建文件夹')).length

  let name = categoryForm.category_name.trim()
  if (!name) {
    if (sameNameCount > 0) {
      name = `新建文件夹${sameNameCount + 1}`
    } else {
      name = '新建文件夹'
    }
  } else {
    const existing = siblings.find(c => c.category_name === name)
    if (existing) {
      const count = siblings.filter(c => c.category_name.startsWith(name)).length
      name = `${name}${count + 1}`
    }
  }

  try {
    const result = await createCategory({
      category_name: name,
      parent_id
    })

    ElMessage.success('文件夹创建成功')
    showCategoryDialog.value = false

    const parentId = parent_id || 0
    if (parentId > 0 && !expandedKeys.value.includes(parentId)) {
      expandedKeys.value.push(parentId)
    }

    await loadCategories()
  } catch (error) {
    console.error('创建文件夹失败', error)
  }

  hoveredNode.value = null
}

// 修改分类
const handleEditCategory = () => {
  const category = currentParentNode.value
  if (!category) {
    ElMessage.warning('请选择要修改的文件夹')
    return
  }

  editCategoryForm.category_id = category.category_id
  editCategoryForm.category_name = category.category_name
  showEditCategoryDialog.value = true
  hideContextMenu()
}

const handleUpdateCategory = async () => {
  const name = editCategoryForm.category_name.trim()
  if (!name) {
    ElMessage.warning('文件夹名称不能为空')
    return
  }

  try {
    await updateCategory(editCategoryForm.category_id, {
      category_name: name
    })

    ElMessage.success('文件夹修改成功')
    showEditCategoryDialog.value = false
    loadCategories()
  } catch (error) {
    console.error('修改文件夹失败', error)
  }

  showEditCategoryDialog.value = false
}

// 删除分类
const handleDeleteCategory = async () => {
  hideContextMenu()

  const categoryId = currentParentNode.value && currentParentNode.value.category_id

  if (!categoryId) {
    ElMessage.warning('根目录不能删除')
    return
  }

  const checkCategory = (catId) => {
    let fileCount = 0
    let folderCount = 0
    let categoryName = ''

    const files = drawings.value.filter(d => d.category_id === catId)
    if (files.length > 0) {
      const category = categories.value.find(c => c.category_id === catId)
      categoryName = category && category.category_name || ''
      fileCount += files.length
    }

    const children = categories.value.filter(c => c.parent_id === catId)
    folderCount += children.length
    children.forEach(child => {
      const result = checkCategory(child.category_id)
      if (result.fileCount > 0 && !categoryName) {
        categoryName = result.categoryName
      }
      fileCount += result.fileCount
      folderCount += result.folderCount
    })

    return { fileCount, folderCount, categoryName }
  }

  const checkResult = checkCategory(categoryId)

  let message = ''
  if (checkResult.fileCount > 0) {
    message = `"${checkResult.categoryName}" 目录下存在 ${checkResult.fileCount} 个文件，删除后文件将变为无分类状态。`
    if (checkResult.folderCount > 0) {
      message += `同时将删除 ${checkResult.folderCount} 个子文件夹。`
    }
    message += ' 确定要删除吗？'
  } else {
    if (checkResult.folderCount > 0) {
      message = `此文件夹包含 ${checkResult.folderCount} 个子文件夹（均为空），删除后将同时删除这些子文件夹。确定要删除吗？`
    } else {
      message = '确定要删除此文件夹吗？'
    }
  }

  try {
    await ElMessageBox.confirm(message, '提示', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await deleteCategory(categoryId)
    ElMessage.success('删除成功')
    loadCategories()

    currentCategoryId.value = null
    breadcrumbList.value = [{ name: '目录', categoryId: null }]
    loadDrawings()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文件夹失败', error)
    }
  }

  hoveredNode.value = null
}

// 上传成功
const handleUploadSuccess = () => {
  loadDrawings()
  defaultUploadCategoryId.value = null
}

// 打开上传对话框
const handleUploadFile = () => {
  defaultUploadCategoryId.value = currentCategoryId.value
  showUploadDialog.value = true
}

// 上传到指定目录
const handleUploadToNode = () => {
  if (contextMenuNode.value) {
    defaultUploadCategoryId.value = contextMenuNode.value.category_id
    showUploadDialog.value = true
    hideContextMenu()
  }
}

// 生成唯一 ID
const generateTabId = () => `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

const triggerPreviewFabPulse = () => {
  previewFabPulse.value = false
  setTimeout(() => {
    previewFabPulse.value = true
    setTimeout(() => {
      previewFabPulse.value = false
    }, 1200)
  }, 10)
}

const markPreviewUnread = () => {
  previewUnreadCount.value = Math.min(99, previewUnreadCount.value + 1)
  triggerPreviewFabPulse()
}

const minimizePreviewDialog = () => {
  if (previewTabs.value.length === 0) return
  previewMinimized.value = true
  showPreviewDialog.value = false
}

const restorePreviewDialog = () => {
  if (previewTabs.value.length === 0) return
  previewMinimized.value = false
  previewUnreadCount.value = 0
  previewFabPulse.value = false
  showPreviewDialog.value = true
}

const closeAllPreviewTabs = () => {
  previewTabs.value = []
  activePreviewTabId.value = null
  previewMinimized.value = false
  previewUnreadCount.value = 0
  previewFabPulse.value = false
  previewFullscreen.value = false
  showPreviewDialog.value = false
}

// 预览文件 - 标签页模式
const handlePreview = async (row) => {
  if (!canPreviewFile(row)) {
    try {
      await ElMessageBox.confirm('请先登录后再预览', '提示', {
        confirmButtonText: '去登录',
        cancelButtonText: '取消',
        type: 'warning'
      })
      window.location.href = '/login'
    } catch {
      // 用户取消
    }
    return
  }

  const existingTab = previewTabs.value.find(tab => tab.drawing_id === row.drawing_id)
  if (existingTab) {
    activePreviewTabId.value = existingTab.id
    if (previewMinimized.value || !showPreviewDialog.value) {
      markPreviewUnread()
      return
    }
    restorePreviewDialog()
    return
  }

  if (previewTabs.value.length >= MAX_PREVIEW_TABS) {
    const removedTab = previewTabs.value.shift()
    if (removedTab && removedTab.id === activePreviewTabId.value) {
      activePreviewTabId.value = null
    }
  }

  const newTab = {
    id: generateTabId(),
    drawing_id: row.drawing_id,
    drawing_name: row.drawing_name,
    file_type: row.file_type
  }
  previewTabs.value.push(newTab)
  activePreviewTabId.value = newTab.id
  if (previewMinimized.value) {
    markPreviewUnread()
    return
  }
  restorePreviewDialog()
}

// 获取预览加载提示文字
const getPreviewLoadingText = (drawing) => {
  if (!drawing) return '正在加载...'

  const typeMap = {
    'pdf': '正在加载 PDF...',
    'doc': '正在转换 Word 文档，请稍候...',
    'docx': '正在转换 Word 文档，请稍候...',
    'xlsx': '正在转换 Excel 文档，请稍候...',
    'xls': '正在转换 Excel 文档，请稍候...',
    'ofd': '正在转换 OFD 文档，请稍候...',
    'ceb': '正在转换 CEB 文档，请稍候...'
  }

  return typeMap[drawing.file_type] || '正在加载文档...'
}

// ==================== 标签页管理函数 ====================

// 关闭标签页
const handleCloseTab = (targetId, action) => {
  if (action && action !== 'remove') return
  const index = previewTabs.value.findIndex(tab => tab.id === targetId)
  if (index === -1) return

  // 如果关闭的是当前标签页，切换到相邻标签页
  if (targetId === activePreviewTabId.value) {
    if (previewTabs.value.length === 1) {
      // 最后一个标签页：全部关闭
      closeAllPreviewTabs()
      return
    } else if (index > 0) {
      activePreviewTabId.value = previewTabs.value[index - 1].id
    } else {
      activePreviewTabId.value = previewTabs.value[index + 1].id
    }
  }

  // 移除标签页
  previewTabs.value.splice(index, 1)

  if (previewTabs.value.length === 0) {
    closeAllPreviewTabs()
  }
}

// 切换标签页
const handleTabChange = (tabId) => {
  activePreviewTabId.value = tabId
  // 切换时重置图片位置
  const tab = previewTabs.value.find(t => t.id === tabId)
  if (tab) {
    tab.imagePosition = { x: 0, y: 0 }
    tab.isDragging = false
  }
}

// 下载当前标签页的文件
const handleDownloadCurrent = async () => {
  const tab = currentPreviewTab.value
  if (!tab) return

  const row = drawings.value.find(d => d.drawing_id === tab.drawing_id)
  if (row) {
    handleDownload(row)
  }
}

// 图片缩放（基于当前标签页）
const zoomIn = () => {
  const tab = currentPreviewTab.value
  if (tab && tab.imageScale < 3) {
    tab.imageScale = Math.min(3, tab.imageScale + 0.1)
  }
}

const zoomOut = () => {
  const tab = currentPreviewTab.value
  if (tab && tab.imageScale > 0.25) {
    tab.imageScale = Math.max(0.25, tab.imageScale - 0.1)
  }
}

// 翻页（基于当前标签页）
const goToPrevPage = () => {
  const tab = currentPreviewTab.value
  if (tab && tab.currentPage > 1) {
    tab.currentPage--
  }
}

const goToNextPage = () => {
  const tab = currentPreviewTab.value
  if (tab && tab.currentPage < tab.totalPages) {
    tab.currentPage++
  }
}

// 滚轮事件（基于当前标签页）
const handleWheel = (e) => {
  const tab = currentPreviewTab.value
  if (!tab) return

  if (e.ctrlKey) {
    // Ctrl + 滚轮：缩放
    if (e.deltaY < 0 && tab.imageScale < 3) {
      tab.imageScale = Math.min(3, tab.imageScale + 0.1)
    } else if (e.deltaY > 0 && tab.imageScale > 0.25) {
      tab.imageScale = Math.max(0.25, tab.imageScale - 0.1)
    }
    return
  }

  // 普通滚轮：翻页
  if (e.deltaY > 0 && tab.currentPage < tab.totalPages) {
    tab.currentPage++
  } else if (e.deltaY < 0 && tab.currentPage > 1) {
    tab.currentPage--
  }
}

// 图片拖动（基于当前标签页）
const startDrag = (e) => {
  if (e.button !== 0) return
  const tab = currentPreviewTab.value
  if (!tab) return

  tab.isDragging = true
  tab.dragStart.x = e.clientX - (tab.imagePosition?.x || 0)
  tab.dragStart.y = e.clientY - (tab.imagePosition?.y || 0)
}

const onDrag = (e) => {
  const tab = currentPreviewTab.value
  if (!tab || !tab.isDragging) return

  tab.imagePosition.x = e.clientX - tab.dragStart.x
  tab.imagePosition.y = e.clientY - tab.dragStart.y
}

const stopDrag = () => {
  const tab = currentPreviewTab.value
  if (tab) {
    tab.isDragging = false
  }
}

// 全屏切换
const togglePreviewFullscreen = () => {
  previewFullscreen.value = !previewFullscreen.value
}

// 下载文件
const handleDownload = async (row) => {
  if (!canDownloadFile(row)) {
    try {
      await ElMessageBox.confirm('请先登录后再下载', '提示', {
        confirmButtonText: '去登录',
        cancelButtonText: '取消',
        type: 'warning'
      })
      window.location.href = '/login'
    } catch {
      // 用户取消
    }
    return
  }

  try {
    const token = localStorage.getItem('token')
    const headers = token ? { 'Authorization': token } : {}

    const response = await fetch(`/api/drawings/${row.drawing_id}/download`, {
      headers
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      if (data.need_login) {
        try {
          await ElMessageBox.confirm('请先登录后再下载', '提示', {
            confirmButtonText: '去登录',
            cancelButtonText: '取消',
            type: 'warning'
          })
          window.location.href = '/login'
        } catch {}
        return
      }
      throw new Error(data.error || '下载失败')
    }

    const blob = await response.blob()

    if ('showSaveFilePicker' in window) {
      try {
        const fileHandle = await window.showSaveFilePicker({
          suggestedName: `${row.drawing_name}.${row.file_type}`
        })
        const writable = await fileHandle.createWritable()
        await writable.write(blob)
        await writable.close()
        ElMessage.success('下载成功')
        return
      } catch (err) {
        if (err.name === 'AbortError') {
          return
        }
      }
    }

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${row.drawing_name}.${row.file_type}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('下载失败', error)
    ElMessage.error('下载失败')
  }
}

// 删除文件
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此文件吗？删除后无法恢复！', '提示', {
      type: 'warning'
    })

    await deleteDrawing(row.drawing_id)
    ElMessage.success('删除成功')
    loadDrawings()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文件失败', error)
    }
  }
}

// 刷新
const handleRefresh = () => {
  loadCategories()
  loadDrawings()
}

// 登出
const handleLogout = () => {
  userStore.logout()
  loadDrawings()
}

// 登录
const handleLogin = () => {
  router.push('/login')
}

// 获取分类名称
const getCategoryName = (categoryId) => {
  const findCategory = (list, id) => {
    for (const item of list) {
      if (item.category_id === id) return item
      if (item.children) {
        const found = findCategory(item.children, id)
        if (found) return found
      }
    }
    return null
  }
  const category = findCategory(categories.value, categoryId)
  return category && category.category_name || ''
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

// 获取完整目录路径
const getCategoryPath = (categoryId) => {
  const buildPath = (id) => {
    const path = []
    let current = categories.value.find(c => c.category_id === id)
    while (current) {
      path.unshift(current.category_name)
      current = categories.value.find(c => c.category_id === current.parent_id)
    }
    return path
  }
  return buildPath(categoryId).join('/') || '根目录'
}

// 权限控制
const canModifyFile = (row) => {
  const isAdmin = userStore.user && userStore.user.role === 'admin'
  const isOwner = row.upload_user_id === (userStore.user && userStore.user.user_id)
  if (isAdmin) {
    return row.visibility !== 'private' || isOwner
  }
  return isOwner
}

const canDeleteFile = (row) => {
  const isAdmin = userStore.user && userStore.user.role === 'admin'
  const isOwner = row.upload_user_id === (userStore.user && userStore.user.user_id)
  if (isAdmin) {
    return row.visibility !== 'private' || isOwner
  }
  return isOwner
}

const canPreviewFile = (row) => {
  if (row.visibility === 'public') return true
  return !!userStore.user
}

const canDownloadFile = (row) => {
  if (row.visibility === 'public') return true
  return !!userStore.user
}

// 排序变化处理
const handleSortChange = ({ prop, order }) => {
  sortParams.prop = prop
  sortParams.order = order || 'descending'
  loadDrawings()
}

// 修改文件目录
const handleModifyCategory = (row) => {
  modifyForm.drawing_id = row.drawing_id
  modifyForm.drawing_name = row.drawing_name
  modifyForm.category_id = row.category_id
  const fullPath = categories.value.find(c => c.category_id === row.category_id)
  modifyForm.category_path = fullPath ? [row.category_id] : []
  showModifyDialog.value = true
}

// Cascader 选择变化
const handleModifyCategoryChange = (value) => {
  modifyForm.category_id = value
}

// 保存修改
const handleSaveModify = async () => {
  if (!modifyForm.category_id) {
    ElMessage.warning('请选择目录')
    return
  }

  modifying.value = true
  try {
    await updateDrawing(modifyForm.drawing_id, {
      category_id: modifyForm.category_id
    })
    ElMessage.success('修改成功')
    showModifyDialog.value = false
    loadDrawings()
  } catch (error) {
    console.error('修改失败', error)
    ElMessage.error('修改失败')
  } finally {
    modifying.value = false
  }
}

// 加载文件列表
const loadDrawings = async () => {
  loading.value = true
  try {
    const params = {
      ...filters
    }

    if (filters.file_name && filters.file_name.trim()) {
      console.log('全局搜索文件名:', filters.file_name)
    }
    else if (selectedCategoryIds.value.length > 0) {
      params.category_ids = selectedCategoryIds.value.join(',')
    }

    const data = await getDrawings(params)
    let result = data.drawings || []

    if (sortParams.prop) {
      result.sort((a, b) => {
        let aVal = a[sortParams.prop]
        let bVal = b[sortParams.prop]

        if (sortParams.prop === 'category_path') {
          aVal = getCategoryPath(a.category_id)
          bVal = getCategoryPath(b.category_id)
        }

        if (sortParams.order === 'ascending') {
          return aVal > bVal ? 1 : -1
        } else {
          return aVal < bVal ? 1 : -1
        }
      })
    }

    drawings.value = result
  } catch (error) {
    console.error('加载文件列表失败', error)
  } finally {
    loading.value = false
  }
}

// 过滤节点
const filterNode = (value, data) => {
  if (!value) return true
  return data.category_name.includes(value)
}

// 加载界面设置
const loadInterfaceSettings = () => {
  const saved = localStorage.getItem('interfaceSettings')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      interfaceSettings.appTitle = parsed.appTitle || '文件管理系统'
      interfaceSettings.titleFontSize = parsed.titleFontSize || 24
      interfaceSettings.nodeFontSize = parsed.nodeFontSize || 16
    } catch (e) {
      console.error('加载界面设置失败', e)
    }
  }
  applyInterfaceSettings()
}

// 保存界面设置
const saveInterfaceSettings = () => {
  localStorage.setItem('interfaceSettings', JSON.stringify(interfaceSettings))
  applyInterfaceSettings()
}

// 应用界面设置
const applyInterfaceSettings = () => {
  document.documentElement.style.setProperty('--title-font-size', interfaceSettings.titleFontSize + 'px')
  document.documentElement.style.setProperty('--node-font-size', interfaceSettings.nodeFontSize + 'px')
}

// 重置界面设置
const resetInterfaceSettings = () => {
  interfaceSettings.appTitle = '文件管理系统'
  interfaceSettings.titleFontSize = 24
  interfaceSettings.nodeFontSize = 16
  saveInterfaceSettings()
}

// 监听设置变化
watch(interfaceSettings, () => {
  saveInterfaceSettings()
}, { deep: true })

// 点击外部关闭右键菜单
const handleClickOutside = (event) => {
  const contextMenu = document.querySelector('.context-menu')
  if (contextMenu && !contextMenu.contains(event.target)) {
    hideContextMenu()
  }
}

// ESC 键关闭右键菜单
const handleKeyPress = (event) => {
  if (event.key === 'Escape') {
    hideContextMenu()
  }
}

// 添加全局事件监听
onMounted(() => {
  loadInterfaceSettings()
  loadCategories()
  loadDrawings()

  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeyPress)
})

// 组件卸载时清理
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeyPress)
})
</script>

<style scoped>
/* CSS 变量默认值 */
:root {
  --title-font-size: 24px;
  --node-font-size: 16px;
}

.home-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left h2 {
  margin: 0;
  color: #333;
  font-size: var(--title-font-size);
}

.header-right {
  display: flex;
  align-items: center;
}

.header-right > * {
  margin-right: 10px;
}

.header-right > *:last-child {
  margin-right: 0;
}

.user-dropdown {
  cursor: pointer;
}

.user-avatar-wrapper {
  display: flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-avatar-wrapper > * {
  margin-right: 8px;
}

.user-avatar-wrapper > *:last-child {
  margin-right: 0;
}

.user-avatar-wrapper:hover {
  background-color: #f5f5f5;
}

.username-avatar {
  background-color: #409EFF;
  color: white;
  font-weight: bold;
}

.username-text {
  font-size: 14px;
  color: #333;
}

.main-content {
  flex: 1;
  overflow: hidden;
}

.sidebar {
  background-color: #f5f5f5;
  padding: 20px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.directory-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.directory-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 15px;
}

.tree-container {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.tree-container :deep(.el-tree) {
  min-width: max-content;
  font-size: var(--node-font-size);
}

.tree-container :deep(.el-tree-node__content) {
  font-size: var(--node-font-size);
}

.tree-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.tree-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.tree-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.tree-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.sidebar-buttons {
  display: flex;
  margin-top: 15px;
}

.sidebar-buttons > * {
  margin-right: 10px;
}

.sidebar-buttons > *:last-child {
  margin-right: 0;
}

.sidebar-btn {
  width: 100%;
  justify-content: flex-start;
}

.el-main {
  padding: 20px;
  background-color: #fff;
  overflow-y: auto;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 8px;
  overflow-x: auto;
  overflow-y: hidden;
}

.tree-node-label {
  display: inline-block;
  white-space: nowrap;
  font-size: var(--node-font-size);
}

/* 右键菜单样式 */
.context-menu {
  position: fixed;
  z-index: 9999;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 4px 0;
  min-width: 140px;
  user-select: none;
}

.context-menu-item {
  padding: 8px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #606266;
  transition: all 0.2s;
}

.context-menu-item > * {
  margin-right: 8px;
}

.context-menu-item > *:last-child {
  margin-right: 0;
}

.context-menu-item:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

.context-menu-item.danger:hover {
  background-color: #fef0f0;
  color: #f56c6c;
}

.context-menu-item .el-icon {
  font-size: 16px;
}

.filter-bar {
  background-color: #fff;
  padding: 15px;
  margin-bottom: 15px;
  border: 1px solid #e6e6e6;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.filter-bar > * {
  margin-right: 10px;
}

.filter-bar > *:last-child {
  margin-right: 0;
}

.search-btn {
  margin-left: 0;
}

.filter-bar-actions {
  display: flex;
  margin-left: auto;
}

.filter-bar-actions .el-button {
  margin-right: 10px;
}

.filter-bar-actions .el-button:last-child {
  margin-right: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-dialog :deep(.el-dialog__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 70vh;
}

.preview-dialog-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 70vh;
}

.preview-loading p {
  margin-top: 15px;
  font-size: 14px;
}

.preview-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 70vh;
}

/* 标签页预览对话框样式 */
.preview-tabs-dialog :deep(.el-dialog) {
  display: flex;
  flex-direction: column;
  height: 88vh;
  max-height: 88vh;
  margin: 0 auto;
}

.preview-tabs-dialog :deep(.el-dialog.is-fullscreen) {
  height: 100vh;
  max-height: 100vh;
}

.preview-tabs-dialog :deep(.el-dialog__header) {
  flex-shrink: 0;
  padding: 10px 14px;
  border-bottom: 1px solid #e5e7eb;
}

.preview-tabs-dialog :deep(.el-dialog__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.preview-tabs-dialog :deep(.el-dialog__footer) {
  display: none;
}

.preview-tabs-dialog :deep(.el-tabs) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.preview-tabs-dialog :deep(.el-tabs__header) {
  margin: 0;
  padding: 10px 16px 0;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.preview-tabs-dialog :deep(.el-tabs__item) {
  height: 40px;
  line-height: 40px;
  font-size: 14px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-tabs-dialog :deep(.el-tabs__content) {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  min-height: 0;
  padding: 0;
  overflow: hidden;
}

.preview-tabs-dialog :deep(.el-tab-pane) {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* 仅 Excel：全屏时内容区固定高度 980px */
.preview-tabs-dialog :deep(.el-dialog.is-fullscreen .excel-html-container) {
  flex: 0 0 980px;
  height: 980px;
  max-height: 980px;
  min-height: 980px;
}

.preview-tabs-dialog :deep(.el-dialog.is-fullscreen .excel-preview-iframe) {
  height: 100%;
  max-height: 100%;
  min-height: 980px;
}

/* 预览加载状态 */
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
}

.preview-loading p {
  margin-top: 15px;
  font-size: 14px;
  color: #606266;
}

/* 预览错误状态 */
.preview-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 60vh;
}

/* HTML 预览容器 */
.html-preview-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-iframe {
  flex: 1;
  width: 100%;
  height: 100%;
  border: none;
  background: #fff;
}

/* 图片预览容器 */
.image-preview-container {
  display: flex;
  flex-direction: column;
  height: 65vh;
}

.image-preview-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: #e8e8e8;
  padding: 20px;
  position: relative;
}

.preview-image {
  max-width: 100%;
  height: auto;
  display: block;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.1s ease-out;
  cursor: grab;
  user-select: none;
}

.preview-image:active {
  cursor: grabbing;
}

/* 预览工具栏 */
.preview-toolbar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
  gap: 10px;
}

.preview-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.preview-dialog-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.preview-dialog-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.embedded-preview-container {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 520px;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.embedded-preview-iframe {
  position: static;
  width: 100%;
  height: 100%;
  min-height: 520px;
  border: none;
  display: block;
}

.preview-fab-badge {
  position: fixed;
  left: 24px;
  bottom: 24px;
  z-index: 2200;
}

.preview-fab {
  width: 54px;
  height: 54px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.preview-fab.is-unread {
  box-shadow: 0 10px 24px rgba(245, 108, 108, 0.45);
}

.preview-fab.is-pulse {
  animation: previewFabPulse 1.2s ease-out 1;
}

.preview-fab-badge.is-unread :deep(.el-badge__content) {
  animation: previewBadgeBounce 0.6s ease-out;
}

@keyframes previewFabPulse {
  0% { transform: scale(1); }
  40% { transform: scale(1.12); }
  100% { transform: scale(1); }
}

@keyframes previewBadgeBounce {
  0% { transform: translateY(0) scale(1); }
  40% { transform: translateY(-4px) scale(1.15); }
  100% { transform: translateY(0) scale(1); }
}

/* 旧的预览样式已删除，由新的标签页样式替代 */

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.full-height-dialog :deep(.el-dialog__body) {
  max-height: 80vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.full-height-dialog :deep(.el-table) {
  flex: 1;
}

.full-height-dialog .filter-bar {
  flex-shrink: 0;
}

.full-height-dialog .pagination-wrapper {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: 15px;
}

.cascader-node-label {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

/* 界面调整对话框表单样式 */
.interface-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.interface-form :deep(.el-form-item__label) {
  font-size: 15px;
}

.interface-form :deep(.el-slider) {
  padding: 0 10px;
}

/* 个人中心样式 */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #e6e6e6;
  margin-bottom: 20px;
}

.avatar-section .avatar {
  border: 3px solid #409eff;
}

.user-form {
  max-width: 400px;
  margin: 0 auto;
}

.text-ellipsis {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
</style>
