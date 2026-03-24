"""
文件管理系统 - CEF Python 桌面应用
基于 Chromium 内核，支持 Win7 兼容
"""
import sys
import os

# ========== 最早设置工作目录和路径（必须在导入 cefpython 之前）==========
# 获取可执行文件所在目录
if getattr(sys, 'frozen', False):
    # 打包后的环境
    exe_dir = os.path.dirname(sys.executable)
else:
    # 开发环境
    exe_dir = os.path.dirname(os.path.abspath(__file__))

# 设置工作目录（CEF 需要在当前目录查找资源文件）
os.chdir(exe_dir)

# 将可执行文件目录添加到 sys.path（确保能找到 cefpython3 模块）
if exe_dir not in sys.path:
    sys.path.insert(0, exe_dir)

# 设置环境变量（CEF 可能通过环境变量查找资源）
os.environ['CEF_RESOURCES_DIR_PATH'] = exe_dir
os.environ['CEF_LOCALES_DIR_PATH'] = os.path.join(exe_dir, 'locales')

# ========== 命令行参数（必须在导入 cefpython 之前设置）==========
# GPU 禁用参数（解决 SharedMemory read failed 错误）
gpu_args = [
    "--disable-gpu",
    "--disable-gpu-compositing",
    "--disable-gpu-sandbox",
    "--disable-software-rasterizer",
    "--disable-d3d11",
    "--disable-direct3d11",
    "--disable-direct3d9",
    "--disable-webgl",
    "--disable-webgl-image-chromium",
    "--disable-webgl2",
]

# 资源路径参数
resource_args = [
    f"--resources-dir-path={exe_dir}",
    f"--locales-dir-path={os.path.join(exe_dir, 'locales')}",
    "--single-process",  # 回到单进程模式，确保稳定性
]

# 添加所有参数
for arg in gpu_args + resource_args:
    sys.argv.append(arg)

# ========== 导入其他模块 ==========
import threading
import time
import subprocess
import glob

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 固定端口（前端也使用这个端口）
FLASK_PORT = 5000

from cefpython3 import cefpython as cef
import tkinter as tk
from tkinter import messagebox
from ctypes import windll

# Windows API 用于隐藏控制台
try:
    from ctypes import wintypes
    kernel32 = windll.kernel32
    user32 = windll.user32

    # 获取控制台窗口句柄
    def get_console_window():
        return kernel32.GetConsoleWindow()

    # 显示/隐藏窗口
    SW_HIDE = 0
    SW_SHOW = 5

    def hide_console():
        """隐藏控制台窗口"""
        hwnd = get_console_window()
        if hwnd:
            user32.ShowWindow(hwnd, SW_HIDE)

    def show_console():
        """显示控制台窗口"""
        hwnd = get_console_window()
        if hwnd:
            user32.ShowWindow(hwnd, SW_SHOW)
except:
    # 非 Windows 平台或导入失败
    def hide_console():
        pass
    def show_console():
        pass

# CEF 全局设置
settings = {
    "debug": False,  # 关闭调试模式
    "log_severity": cef.LOGSEVERITY_ERROR,  # 只显示错误级别日志（屏蔽 SharedMemory 警告）
    "log_file": "",  # 禁用日志文件
    "multi_threaded_message_loop": False,  # 使用外部消息循环
    "locale": "zh-CN",
    "resources_dir_path": exe_dir,  # 指定 CEF 资源文件目录
    "locales_dir_path": os.path.join(exe_dir, "locales"),  # 指定 locales 目录
    "single_process": True,  # 使用单进程模式
}

# 预览与 kkFileView 配置
KK_PORT = 8012
KK_HEALTH_URL = f"http://127.0.0.1:{KK_PORT}"
WINDOWS_CREATE_NO_WINDOW = 0x08000000
WINDOWS_STARTF_USESHOWWINDOW = 0x00000001


class KkFileViewManager:
    """kkFileView 进程管理（静默启动/停止）"""

    def __init__(self):
        self.process = None
        self.kk_root = os.path.join(exe_dir, 'tools', 'kkfileview')

    def _is_ready(self):
        try:
            import requests
            resp = requests.get(KK_HEALTH_URL, timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def _run_hidden(self, command, cwd=None):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= WINDOWS_STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        return subprocess.Popen(
            command,
            cwd=cwd,
            creationflags=WINDOWS_CREATE_NO_WINDOW,
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def _get_kk_java_command(self):
        """优先使用 kkFileView 自带 JRE，其次使用系统 java"""
        java_candidates = [
            os.path.join(self.kk_root, 'jre', 'bin', 'java.exe'),
            os.path.join(self.kk_root, 'runtime', 'bin', 'java.exe'),
            'java'
        ]
        for cmd in java_candidates:
            if cmd == 'java' or os.path.exists(cmd):
                return cmd
        return 'java'

    def start(self):
        if self._is_ready():
            print("✓ kkFileView 已在运行")
            return True

        if not os.path.exists(self.kk_root):
            print(f"⚠ 未找到 kkFileView 目录: {self.kk_root}")
            return False

        started = False
        startup_bat = os.path.join(self.kk_root, 'bin', 'startup.bat')
        if os.path.exists(startup_bat):
            try:
                self.process = self._run_hidden(['cmd', '/c', startup_bat], cwd=os.path.dirname(startup_bat))
                started = True
            except Exception as e:
                print(f"⚠ 启动 kkFileView startup.bat 失败: {e}")

        if not started:
            jar_candidates = glob.glob(os.path.join(self.kk_root, '*.jar'))
            if jar_candidates:
                try:
                    java_cmd = self._get_kk_java_command()
                    self.process = self._run_hidden([java_cmd, '-jar', jar_candidates[0]], cwd=self.kk_root)
                    started = True
                except Exception as e:
                    print(f"⚠ 启动 kkFileView jar 失败: {e}")

        if not started:
            print("⚠ 未找到可启动的 kkFileView 脚本或 jar")
            return False

        for _ in range(60):
            time.sleep(0.5)
            if self._is_ready():
                print("✓ kkFileView 已就绪")
                return True

        print("⚠ kkFileView 启动超时")
        return False

    def stop(self):
        shutdown_bat = os.path.join(self.kk_root, 'bin', 'shutdown.bat')
        if os.path.exists(shutdown_bat):
            try:
                self._run_hidden(['cmd', '/c', shutdown_bat], cwd=os.path.dirname(shutdown_bat))
                return
            except Exception:
                pass

        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass


class PreviewWindowManager:
    """独立 CEF 预览子窗口管理器"""

    def __init__(self, root):
        self.root = root
        self.windows = {}

    def open_window(self, url, title='文件预览'):
        preview_window = tk.Toplevel(self.root)
        preview_window.title(title)
        preview_window.geometry("1280x860")
        preview_window.minsize(900, 600)
        preview_window.update_idletasks()

        width = preview_window.winfo_width()
        height = preview_window.winfo_height()
        window_handle = preview_window.winfo_id()

        window_info = cef.WindowInfo()
        window_info.SetAsChild(window_handle, [0, 0, width, height])
        browser = cef.CreateBrowserSync(
            window_info=window_info,
            url=url,
            window_title=title
        )

        browser_id = browser.GetIdentifier()
        self.windows[browser_id] = {
            'window': preview_window,
            'browser': browser
        }

        def on_window_configure(_event):
            try:
                item = self.windows.get(browser_id)
                if not item:
                    return
                b = item['browser']
                cef_window = b.GetWindowHandle()
                if cef_window:
                    win_w = preview_window.winfo_width()
                    win_h = preview_window.winfo_height()
                    windll.user32.SetWindowPos(
                        cef_window,
                        0,
                        0, 0,
                        win_w, win_h,
                        0x0002
                    )
            except Exception:
                pass

        def on_close():
            try:
                item = self.windows.pop(browser_id, None)
                if item:
                    item['browser'].CloseBrowser(True)
            except Exception:
                pass
            finally:
                try:
                    preview_window.destroy()
                except Exception:
                    pass

        preview_window.bind('<Configure>', on_window_configure)
        preview_window.protocol("WM_DELETE_WINDOW", on_close)


class PopupHandler:
    """拦截 window.open 并改为独立 CEF 子窗口"""

    def __init__(self, preview_manager):
        self.preview_manager = preview_manager

    def OnBeforePopup(self, browser, frame, target_url, target_frame_name,
                      target_disposition, user_gesture, popup_features,
                      window_info, client, browser_settings, no_javascript_access):
        if target_url:
            self.preview_manager.open_window(target_url, title='文件预览')
            return True
        return False


class DownloadHandler:
    """下载处理器"""

    def __init__(self, client):
        self.client = client

    def OnBeforeDownload(self, browser, download_item, suggested_name, callback):
        # 获取默认下载路径
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        # 获取用户选择的保存路径
        file_path = filedialog.asksaveasfilename(
            title="保存文件",
            initialfile=suggested_name,
            defaultextension=os.path.splitext(suggested_name)[1] or ".*",
            filetypes=[("所有文件", "*.*")]
        )

        root.destroy()

        if file_path:
            # 继续下载
            callback.Continue(file_path, True)
            print(f"下载文件到: {file_path}")
        else:
            # 取消下载
            callback.Cancel()


class ClientHandler:
    """CEF 客户端处理器"""

    def __init__(self, preview_manager):
        self.download_handler = None
        self.popup_handler = PopupHandler(preview_manager)

    def OnBeforeClose(self, browser):
        """浏览器关闭时"""
        pass

    def OnBeforeDownload(self, browser, download_item, suggested_name, callback):
        """下载前回调"""
        if not self.download_handler:
            self.download_handler = DownloadHandler(browser)
        self.download_handler.OnBeforeDownload(browser, download_item, suggested_name, callback)

    def OnDownloadUpdated(self, browser, download_item, callback):
        """下载更新回调"""
        pass

    def OnBeforePopup(self, browser, frame, target_url, target_frame_name,
                      target_disposition, user_gesture, popup_features,
                      window_info, client, browser_settings, no_javascript_access):
        return self.popup_handler.OnBeforePopup(
            browser, frame, target_url, target_frame_name, target_disposition,
            user_gesture, popup_features, window_info, client, browser_settings, no_javascript_access
        )


def create_flask_app():
    """创建Flask应用"""
    from app import create_app
    return create_app()


def run_flask():
    """在后台线程运行Flask"""
    app = create_flask_app()
    # 允许外部访问（前端需要），禁用日志输出
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='127.0.0.1', port=FLASK_PORT, debug=False, use_reloader=False, threaded=True)


def main():
    """启动桌面应用"""
    print("正在启动文件管理系统...")
    kk_manager = KkFileViewManager()

    # 在后台线程启动Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 优化：更频繁地检查 Flask 状态（减少启动时间）
    print("正在等待后端服务启动...")
    flask_ready = False
    for i in range(40):  # 最多8秒（40次 x 0.2秒）
        time.sleep(0.2)  # 减少等待间隔
        try:
            import requests
            response = requests.get(f'http://127.0.0.1:{FLASK_PORT}/', timeout=0.5)
            print(f"✓ 后端服务已就绪")
            flask_ready = True
            break
        except:
            if i % 5 == 0:  # 每秒输出一次进度
                print(f"启动中... {i*0.2:.1f}秒")

    if not flask_ready:
        print("⚠ 后端服务启动超时")

    # 启动 kkFileView（静默）
    kk_manager.start()

    # 检查前端文件
    frontend_path = os.path.join(exe_dir, 'frontend', 'dist', 'index.html')
    print(f"前端文件存在: {os.path.exists(frontend_path)}")

    # 初始化 CEF
    sys.excepthook = cef.ExceptHook
    cef.Initialize(settings)

    # 创建 Tkinter 窗口
    root = tk.Tk()
    root.title("文件管理系统")
    root.geometry("1400x900")
    root.minsize(1000, 600)
    preview_manager = PreviewWindowManager(root)

    # 获取窗口句柄
    window_handle = root.winfo_id()

    # URL
    url = f'http://127.0.0.1:{FLASK_PORT}'

    # 创建 WindowInfo
    window_info = cef.WindowInfo()
    window_info.SetAsChild(window_handle, [0, 0, 1400, 900])

    # 创建浏览器
    browser = cef.CreateBrowserSync(
        window_info=window_info,
        url=url,
        window_title="FileManagement"
    )
    browser.SetClientHandler(ClientHandler(preview_manager))

    # 页面加载完成后隐藏控制台的标志
    console_hidden = [False]  # 使用列表以便在闭包中修改

    def check_page_loaded():
        """检查页面是否加载完成，完成后隐藏控制台"""
        if not console_hidden[0]:
            try:
                # 检查浏览器是否还在运行
                if browser and hasattr(browser, 'HasDevTools') and browser.GetIdentifier():
                    # 尝试获取主框架
                    frame = browser.GetMainFrame()
                    if frame:
                        # 检查是否已加载完成（isLoading 为 False）
                        # 使用简单的延时方式，因为 CEF Python 66 API 有限
                        def delayed_hide():
                            import time
                            time.sleep(2)  # 等待 2 秒确保页面完全加载
                            if not console_hidden[0]:
                                hide_console()
                                console_hidden[0] = True
                                print("控制台已隐藏")

                        import threading
                        threading.Thread(target=delayed_hide, daemon=True).start()
            except:
                pass

    # 启动页面加载检查
    root.after(100, check_page_loaded)

    # 窗口大小变化处理 - 使用 Windows API
    def on_window_configure(event):
        """窗口大小改变时调整浏览器尺寸"""
        # 防抖：避免频繁调用
        if hasattr(on_window_configure, '_last_time'):
            if time.time() - on_window_configure._last_time < 0.1:
                return
        on_window_configure._last_time = time.time()

        # 获取窗口实际大小
        width = root.winfo_width()
        height = root.winfo_height()

        try:
            # 获取 CEF 浏览器窗口句柄
            cef_window = browser.GetWindowHandle()
            if cef_window:
                # 使用 Windows API 移动和调整窗口大小
                windll.user32.SetWindowPos(
                    cef_window,  # 窗口句柄
                    0,  # hWndInsertAfter (0 = 忽略)
                    0, 0,  # X, Y 位置
                    width, height,  # 宽度, 高度
                    0x0002  # SWP_NOMOVE (忽略位置参数，只调整大小)
                )
        except Exception as e:
            pass  # 静默处理错误

    # 绑定窗口大小变化事件
    root.bind('<Configure>', on_window_configure)

    # 集成 CEF 消息循环到 Tkinter
    def cef_message_loop():
        """CEF 消息循环定时器"""
        cef.MessageLoopWork()
        # 每 10ms 执行一次 CEF 消息处理
        root.after(10, cef_message_loop)

    # 启动集成消息循环
    root.after(10, cef_message_loop)

    # Tkinter 主循环
    try:
        root.mainloop()
    finally:
        # 清理 CEF
        print("正在关闭...")
        cef.Shutdown()
        kk_manager.stop()
        print("CEF 已关闭，程序退出中...")

        # 可选：延迟 2 秒关闭（方便查看日志）
        # import time
        # time.sleep(2)


if __name__ == '__main__':
    main()
