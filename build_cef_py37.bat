@echo off
REM ========================================
REM 文件管理系统打包脚本 (CEF 版本)
REM Python 3.7 + CEF Python，支持 Windows 7
REM ========================================

echo.
echo ========================================
REM    文件管理系统打包脚本 (CEF 版本)
REM    Python 3.7 + CEF Python
REM    支持 Windows 7
REM ========================================
echo.

REM 检查 Python 版本
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7.9
    pause
    exit /b 1
)

echo [1/5] 检查 Python 版本...
python --version

echo.
echo [2/5] 安装依赖包...
pip install -r requirements-cef.txt
if errorlevel 1 (
    echo [错误] 依赖包安装失败
    pause
    exit /b 1
)

echo.
echo [3/5] 清理旧的打包文件...
if exist "build" rmdir /s /q "build"
if exist "dist\文件管理系统_v3.1.2" rmdir /s /q "dist\文件管理系统_v3.1.2"

echo.
echo [4/5] 开始打包（PyInstaller）...
pyinstaller build_cef.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo [5/5] 打包完成！
echo.
echo ========================================
REM    打包结果位置：
REM    dist\文件管理系统_v3.1.2\
REM ========================================
echo.
echo 注意：此版本支持 Windows 7
echo      使用 CEF Python 浏览器引擎
echo      OFD 预览支持完整功能（JAR 方式）
echo      Excel 预览使用 HTML 方式
echo.

pause
