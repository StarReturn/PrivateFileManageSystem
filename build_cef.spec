# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 - CEF Python 桌面应用模式
支持 Win7 兼容
使用方法: pyinstaller build_cef.spec
"""

import sys
import os
import shutil
import subprocess

block_cipher = None

# ========== 打包开关（按当前 kkFileView 预览链路精简） ==========
# 关闭后可显著缩小包体积（不再打包旧的 POI/OFD/JRE1.8 链路）
ENABLE_LEGACY_PREVIEW_TOOLCHAIN = False

# ========== 在打包前自动构建前端 ==========
frontend_dir = os.path.join(os.getcwd(), 'frontend')
dist_dir = os.path.join(frontend_dir, 'dist')

# 检查前端 dist 目录是否存在
if not os.path.exists(dist_dir) or not os.listdir(dist_dir):
    print("前端未打包，开始自动构建...")
    try:
        # 检查 npm 是否可用
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            # 运行 npm run build
            result = subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, shell=True)
            if result.returncode == 0:
                print("✓ 前端构建成功")
            else:
                print("⚠ 前端构建失败，请手动运行: cd frontend && npm run build")
        else:
            print("⚠ 未找到 npm，请手动运行: cd frontend && npm run build")
    except Exception as e:
        print(f"⚠ 自动构建失败: {e}")
else:
    print("✓ 前端已打包")


def add_data_if_exists(data_list, src, dst):
    """存在才加入 datas，避免路径缺失导致打包失败"""
    if os.path.exists(src):
        data_list.append((src, dst))
    else:
        print(f"⚠ 跳过不存在的资源: {src}")


datas = []

# 前端打包后的静态文件
add_data_if_exists(datas, 'frontend/dist', 'frontend/dist')
# Flask 模板和静态文件（保留，避免历史页面路由找不到资源）
add_data_if_exists(datas, 'backend/templates', 'backend/templates')
add_data_if_exists(datas, 'backend/static/pdfjs', 'backend/static/pdfjs')

# CEB 转换工具及依赖 DLL（当前仍在用）
add_data_if_exists(datas, 'tools/ceb2Pdf.exe', 'tools')
add_data_if_exists(datas, 'tools/libeay32.dll', 'tools')
add_data_if_exists(datas, 'tools/msvcr100.dll', 'tools')
add_data_if_exists(datas, 'tools/mfc100.dll', 'tools')

# kkFileView（独立预览服务，当前主链路）
add_data_if_exists(datas, 'tools/kkfileview', 'tools/kkfileview')

# 旧预览链路（POI/OFD/JRE1.8）按开关保留
if ENABLE_LEGACY_PREVIEW_TOOLCHAIN:
    add_data_if_exists(datas, 'tools/poi-converter.jar', 'tools')
    add_data_if_exists(datas, 'tools/ofd-converter.jar', 'tools')
    add_data_if_exists(datas, 'tools/jre1.8.0_151', 'tools/jre1.8.0_151')

a = Analysis(
    ['backend/app_cef.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'cefpython3',
        'cefpython3cef',
        'flask',
        'flask_cors',
        'flask_sqlalchemy',
        'sqlalchemy',
        'werkzeug',
        'werkzeug.serving',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        # JWT 相关
        'jwt',
        'PyJWT',
        # cryptography 相关（Win7 兼容）
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.default_backend',
        # passlib 相关
        'passlib',
        'passlib.context',
        'passlib.hash',
        # 以下旧预览链路依赖按开关控制，默认不打
        # 'fitz',
        # 'PyPDF2',
        # 'docx',
        # 'openpyxl',
        # 'openpyxl.cell',
        # 'openpyxl.styles',
        # 'xlrd',
        # pywin32 相关
        'win32com',
        'win32com.client',
        'pywintypes',
        # PIL/WebP 相关（旧图片预览链路）
        # 'PIL',
        # 'PIL.Image',
        # 'PIL.WebPImage',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI 框架（CEF 需要 tkinter，不能排除）
        # 'tkinter',  # CEF 需要 tkinter 作为窗口容器
        'PyQt5',
        'PyQt6',
        'PyQtWebEngine',
        'PySide2',
        'PySide6',
        'wx',
        # 数据科学（不使用）
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'sklearn',
        # 测试框架（不使用）
        'pytest',
        'unittest',
        'mock',
        # OFD（已改用 JAR）
        'ofdparser',
        'easyofd',
        'fonttools',
        'reportlab',
        'xmltodict',
        'lxml',
        'cv2',  # opencv
        # 其他不需要的
        'IPython',
        'jupyter',
        'notebook',
        'tornado',
        'celery',
        'redis',
        'mongoengine',
        'psycopg2',
        'pymysql',
        'pymongo',
        'Crypto',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FileManagement_v1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 启动时显示控制台，页面加载后自动隐藏
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r"D:\EarnMoney\fileManage\文件管理.ico",
)

# 打包输出目录名（使用变量避免编码问题）
DIST_NAME = '文件管理系统_v2.0'

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=DIST_NAME,
)

# ========== 复制 CEF 资源文件 ==========
def copy_cef_files():
    """复制 CEF 资源文件到打包目录"""
    dist_dir = os.path.join(os.getcwd(), 'dist', DIST_NAME)

    # CEF 模块路径
    try:
        import cefpython3
        cef_dir = os.path.dirname(os.path.abspath(cefpython3.__file__))
    except ImportError:
        # 备用方法 - 遍历常见 site-packages 位置
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'cefpython3'),
            r'C:\Users\Turing\AppData\Roaming\Python\Python36\site-packages\cefpython3',
            r'C:\Users\Turing\AppData\Roaming\Python\Python36\site-packages',
        ]
        cef_dir = None
        for path in possible_paths:
            if os.path.exists(path):
                cef_dir = path
                break
        if not cef_dir:
            print("错误: 无法找到 cefpython3 安装目录")
            return

    print(f"✓ CEF 源路径: {cef_dir}")

    # 明确指定需要复制的目录
    dirs_to_copy = ['locales', 'resources', 'swiftshader']

    # 自动查找所有 .dll, .dat, .pak, .bin 文件
    all_files = os.listdir(cef_dir)
    dll_files = [f for f in all_files if f.endswith('.dll')]
    dat_files = [f for f in all_files if f.endswith('.dat')]
    pak_files = [f for f in all_files if f.endswith('.pak')]
    bin_files = [f for f in all_files if f.endswith('.bin')]

    print(f"✓ 找到 {len(dll_files)} DLL, {len(dat_files)} DAT, {len(pak_files)} PAK, {len(bin_files)} BIN 文件")

    # 先复制目录
    for dir_name in dirs_to_copy:
        src = os.path.join(cef_dir, dir_name)
        dst = os.path.join(dist_dir, dir_name)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # 复制所有文件
    all_file_types = dll_files + dat_files + pak_files + bin_files
    copied_count = 0
    for file_name in all_file_types:
        src = os.path.join(cef_dir, file_name)
        dst = os.path.join(dist_dir, file_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied_count += 1

    print(f"✓ 已复制 {copied_count} 个文件到主目录")

    # 关键修复：将资源文件也复制到 cefpython3 子目录
    cefpython3_subdir = os.path.join(dist_dir, 'cefpython3')
    if os.path.exists(cefpython3_subdir):
        # 只复制资源文件，不复制 DLL（DLL 已由 PyInstaller 处理）
        resource_files = dat_files + pak_files + bin_files

        resource_count = 0
        for file_name in resource_files:
            src = os.path.join(cef_dir, file_name)
            dst = os.path.join(cefpython3_subdir, file_name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                resource_count += 1

        print(f"✓ 已复制 {resource_count} 个资源文件到 cefpython3 子目录")

# ========== 复制 VC++ 运行库 DLL ==========
def copy_vc_runtime_dlls():
    """复制 VC++ 2015-2019 运行库到打包目录，支持 Win7 及以上系统"""
    dist_dir = os.path.join(os.getcwd(), 'dist', DIST_NAME)
    system32 = r'C:\Windows\System32'

    vc_dlls = ['msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']

    copied_count = 0
    for dll_name in vc_dlls:
        src = os.path.join(system32, dll_name)
        dst = os.path.join(dist_dir, dll_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied_count += 1

    if copied_count == len(vc_dlls):
        print(f"✓ 已复制 {copied_count} 个 VC++ 运行库")
    else:
        print(f"⚠ 部分运行库未复制，请安装 VC++ 2015-2019 Redistributable")


# ========== 复制 Flask 模板和静态文件 ==========
def copy_flask_assets():
    """复制 Flask templates 和 static 目录"""
    dist_dir = os.path.join(os.getcwd(), 'dist', DIST_NAME)
    project_root = os.getcwd()

    # 复制 templates 目录
    templates_src = os.path.join(project_root, 'backend', 'templates')
    templates_dst = os.path.join(dist_dir, 'templates')
    if os.path.exists(templates_src):
        if os.path.exists(templates_dst):
            shutil.rmtree(templates_dst)
        shutil.copytree(templates_src, templates_dst)
        print(f"✓ 已复制 templates 目录")

    # 复制 static/pdfjs 目录
    pdfjs_src = os.path.join(project_root, 'backend', 'static', 'pdfjs')
    pdfjs_dst = os.path.join(dist_dir, 'static', 'pdfjs')
    if os.path.exists(pdfjs_src):
        os.makedirs(os.path.dirname(pdfjs_dst), exist_ok=True)
        if os.path.exists(pdfjs_dst):
            shutil.rmtree(pdfjs_dst)
        shutil.copytree(pdfjs_src, pdfjs_dst)
        print(f"✓ 已复制 pdfjs 目录")


# ========== 复制 cryptography DLL 文件 ==========
def copy_cryptography_dlls():
    """复制 cryptography 所需的 OpenSSL DLL 文件到主目录和 cryptography 子目录"""
    dist_dir = os.path.join(os.getcwd(), 'dist', DIST_NAME)

    # OpenSSL DLL 文件列表
    openssl_dlls = [
        'libcrypto-1_1-x64.dll',
        'libssl-1_1-x64.dll',
    ]

    # 查找 OpenSSL DLL 源路径（conda 环境）
    conda_lib_bin = os.path.join(os.path.dirname(sys.executable), 'Library', 'bin')
    if not os.path.exists(conda_lib_bin):
        # 备用路径
        conda_lib_bin = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'Library', 'bin')

    copied_count = 0
    for dll_name in openssl_dlls:
        src = os.path.join(conda_lib_bin, dll_name)

        if os.path.exists(src):
            # 复制到主目录
            dst_main = os.path.join(dist_dir, dll_name)
            shutil.copy2(src, dst_main)
            copied_count += 1
            print(f"✓ 已复制 {dll_name} 到主目录")

            # 同时复制到 cryptography 子目录
            crypto_dst_dir = os.path.join(dist_dir, 'cryptography')
            if os.path.exists(crypto_dst_dir):
                dst = os.path.join(crypto_dst_dir, dll_name)
                shutil.copy2(src, dst)
                print(f"✓ 已复制 {dll_name} 到 cryptography 目录")

    if copied_count > 0:
        print(f"✓ 已复制 {copied_count} 个 OpenSSL DLL 文件")
    else:
        print("⚠ 未找到 OpenSSL DLL 文件，请检查 conda 环境")


# 在 COLLECT 之后执行
copy_cef_files()
copy_vc_runtime_dlls()
copy_flask_assets()
copy_cryptography_dlls()
