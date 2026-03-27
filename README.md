# 文件管理系统 (Flask + Vue)

基于 Flask 后端 + Vue 前端的文件管理系统，支持多层级分类、文件上传下载、在线预览等功能。

## 文件预览能力（重点）

系统采用“按文件类型分流”的预览链路，目标是稳定、可维护、适配桌面端 CEF 场景。

- PDF：后端按页转图片，前端懒加载分页展示（首屏快、稳定性高）
- Word（doc/docx）：后端转换后走图片分页预览，避免浏览器内核差异导致样式错乱
- Excel（xls/xlsx）：后端转 HTML，前端在预览面板中展示，支持快速模式/完整模式
- OFD/CEB：后端转换为图片序列，前端分页查看

预览交互能力：
- 多标签预览（同一预览弹窗内切换多个文件）
- 缩放、翻页、最小化、全屏、关闭
- Excel 预览区域可按 UI 需求做独立高度控制

核心接口（预览相关）：
- `GET /api/drawings/:id/preview-images`：返回图片分页/懒加载数据（PDF/Word/OFD/CEB 等）
- `GET /api/drawings/:id/preview-html`：返回 HTML 预览（Excel）
- `GET /api/drawings/:id/download`：下载原文件

## 技术栈

### 后端
- Flask 3.0 - Web框架
- SQLAlchemy - ORM
- JWT - 用户认证
- LibreOffice/win32com - Word转PDF

### 前端
- Vue 3 - 前端框架
- Vite - 构建工具
- Element Plus - UI组件库
- Pinia - 状态管理
- Axios - HTTP客户端

## 项目结构

```
fileManage/
├── backend/                    # 后端项目
│   ├── app/
│   │   ├── models/            # 数据模型
│   │   ├── routes/            # API路由
│   │   ├── utils/             # 工具函数
│   │   └── __init__.py        # 应用初始化
│   ├── config/                # 配置文件
│   ├── database/              # 数据库文件
│   ├── requirements.txt       # Python依赖
│   └── run.py                 # 启动入口
├── frontend/                   # 前端项目
│   ├── src/
│   │   ├── api/               # API接口
│   │   ├── components/        # 组件
│   │   ├── views/             # 页面
│   │   ├── stores/            # 状态管理
│   │   ├── router/            # 路由配置
│   │   ├── App.vue            # 根组件
│   │   └── main.js            # 入口文件
│   ├── index.html
│   ├── package.json           # 依赖配置
│   └── vite.config.js         # Vite配置
└── README.md
```

## 功能特性

- ✅ 用户注册/登录（JWT认证）
- ✅ 多层级分类管理
- ✅ 文件上传（支持拖拽，支持常见办公文档）
- ✅ 文件列表（支持筛选搜索）
- ✅ 文件下载
- ✅ 文件在线预览（PDF/Word/Excel/OFD/CEB）
- ✅ 操作日志记录

## 快速开始

### 1. 数据库准备

数据库文件位于 `backend/database/filemanage.db`，默认管理员账户：
- 用户名：`admin`
- 密码：`admin123456`

### 2. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python run.py
```

后端服务运行在 `http://localhost:5000`

### 3. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务运行在 `http://localhost:3000`

### 4. 访问应用

打开浏览器访问 `http://localhost:3000`，使用默认账户登录。

## Word文档预览配置

为了实现Word文档无损预览，需要配置转换工具：

### 方案1：LibreOffice（推荐，跨平台）

1. 下载安装：https://www.libreoffice.org/download/download/
2. 安装后程序会自动检测并使用

### 方案2：pywin32（Windows，需要安装Word）

```bash
pip install pywin32
```

### 方案3：docx2pdf（Windows，需要安装Word）

```bash
pip install docx2pdf
```

### 方案4：unoconv（Linux）

```bash
# Ubuntu/Debian
sudo apt install libreoffice unoconv

# CentOS/RHEL
sudo yum install libreoffice unoconv
```

## API接口文档

### 认证接口

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

### 分类接口

- `GET /api/categories` - 获取分类列表
- `POST /api/categories` - 创建分类
- `DELETE /api/categories/:id` - 删除分类

### 文件接口

- `GET /api/drawings` - 获取文件列表
- `POST /api/drawings` - 上传文件
- `GET /api/drawings/:id` - 获取文件详情
- `GET /api/drawings/:id/download` - 下载文件
- `GET /api/drawings/:id/preview` - 预览文件
- `DELETE /api/drawings/:id` - 删除文件

## 开发说明

### 后端开发

- API路由文件位于 `backend/app/routes/`
- 数据模型位于 `backend/app/models/models.py`
- 工具函数位于 `backend/app/utils/`

### 前端开发

- 页面组件位于 `frontend/src/views/`
- 可复用组件位于 `frontend/src/components/`
- API接口位于 `frontend/src/api/`
- 状态管理位于 `frontend/src/stores/`

## 部署

### 后端部署

使用 Gunicorn + Nginx 部署 Flask 应用：

```bash
pip install gunicorn

# 启动
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

### 前端部署

```bash
# 构建
npm run build

# dist目录部署到Nginx静态目录
```

## 常见问题

1. **CORS错误**：确保后端Flask-CORS配置正确
2. **Word预览失败**：检查是否安装LibreOffice或pywin32
3. **文件上传大小限制**：修改Flask配置中的MAX_CONTENT_LENGTH

## 许可证

MIT License
