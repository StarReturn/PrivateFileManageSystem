"""
文件管理系统 - 局域网版本
支持服务器模式和客户端模式
使用方法：
  - 默认模式：本地单机使用
  python app_cef_lan.py                    # 本地模式
  python app_cef_lan.py --server           # 服务器模式（局域网内其他机器可访问）
  python app_cef_lan.py --client 192.168.1.100  # 客户端模式（连接到指定服务器）

或者打包后：
  文件管理系统.exe                         # 本地模式
  文件管理系统.exe --server                # 服务器模式
  文件管理系统.exe --client 192.168.1.100 # 客户端模式
"""
import sys
import os

# ========== 解析命令行参数 ==========
MODE = "local"  # 默认本地模式
SERVER_IP = "127.0.0.1"  # 默认服务器 IP

for i, arg in enumerate(sys.argv[1:]):
    if arg in ['--server', '-s']:
        MODE = "server"
    elif arg in ['--client', '-c']:
        if i + 1 < len(sys.argv[1:]):
            MODE = "client"
            SERVER_IP = sys.argv[i + 2]  # 下一个参数是 IP
        else:
            print("错误：--client 参数需要指定服务器 IP 地址")
            sys.exit(1)

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
import socket

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 固定端口（前端也使用这个端口）
FLASK_PORT = 5000

from cefpython3 import cefpython as cef
import tkinter as tk
from tkinter import messagebox, simpledialog
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
        try:
            console_window = get_console_window()
            if console_window:
                user32.ShowWindow(console_window, SW_HIDE)
        except:
            pass

    def show_console():
        """显示控制台窗口"""
        try:
            console_window = get_console_window()
            if console_window:
                user32.ShowWindow(console_window, SW_SHOW)
        except:
            pass

except ImportError:
    def hide_console():
        pass
    def show_console():
        pass

# 获取本机局域网 IP
def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

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

    def __init__(self):
        self.download_handler = None

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


def create_flask_app():
    """创建Flask应用"""
    from app import create_app
    return create_app()


def run_flask(host='127.0.0.1'):
    """在后台线程运行Flask"""
    app = create_flask_app()
    # 允许外部访问，禁用日志输出
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    print(f"Flask 运行在: http://{host}:{FLASK_PORT}")
    app.run(host=host, port=FLASK_PORT, debug=False, use_reloader=False, threaded=True)


def show_mode_dialog():
    """显示模式选择对话框"""
    root = tk.Tk()
    root.withdraw()
    root.title("选择启动模式")

    # 创建对话框窗口
    dialog = tk.Toplevel(root)
    dialog.title("文件管理系统 - 启动模式")
    dialog.geometry("400x250")
    dialog.resizable(False, False)

    # 居中显示
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f'{width}x{height}+{x}+{y}')

    # 结果存储
    result = {'mode': 'local', 'ip': ''}

    # 标题
    tk.Label(dialog, text="请选择启动模式", font=("微软雅黑", 14, "bold")).pack(pady=15)

    # 本地模式
    def select_local():
        result['mode'] = 'local'
        dialog.destroy()

    tk.Button(dialog, text="📴 本地模式", font=("微软雅黑", 11), width=25,
              command=select_local, bg="#409eff", fg="white").pack(pady=5)
    tk.Label(dialog, text="仅本机使用，数据存储在本地", font=("微软雅黑", 9), fg="#666").pack()

    tk.Frame(dialog, height=15).pack()  # 间隔

    # 服务器模式
    def select_server():
        local_ip = get_local_ip()
        if messagebox.askyesno("服务器模式", f"将以服务器模式启动\n\n局域网IP: {local_ip}\n端口: {FLASK_PORT}\n\n其他机器可以通过此IP访问\n是否继续？"):
            result['mode'] = 'server'
            dialog.destroy()

    tk.Button(dialog, text="🖥️ 服务器模式", font=("微软雅黑", 11), width=25,
              command=select_server, bg="#67c23a", fg="white").pack(pady=5)
    tk.Label(dialog, text="作为服务器，其他机器可连接访问", font=("微软雅黑", 9), fg="#666").pack()

    tk.Frame(dialog, height=15).pack()  # 间隔

    # 客户端模式
    def select_client():
        ip = simpledialog.askstring("客户端模式", "请输入服务器IP地址:\n例如: 192.168.1.100", parent=root)
        if ip:
            # 简单验证 IP 格式
            parts = ip.split('.')
            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                result['mode'] = 'client'
                result['ip'] = ip
                dialog.destroy()
            else:
                messagebox.showerror("错误", "IP 地址格式不正确")

    tk.Button(dialog, text="💻 客户端模式", font=("微软雅黑", 11), width=25,
              command=select_client, bg="#e6a23c", fg="white").pack(pady=5)
    tk.Label(dialog, text="连接到局域网内的服务器", font=("微软雅黑", 9), fg="#666").pack()

    # 等待用户选择
    root.wait_window(dialog)
    root.destroy()

    return result['mode'], result['ip']


def main():
    """启动桌面应用"""
    global MODE, SERVER_IP

    # 如果没有命令行参数，显示选择对话框
    if MODE == "local" and len(sys.argv) <= 1:
        selected_mode, server_ip = show_mode_dialog()
        MODE = selected_mode
        if MODE == "client" and server_ip:
            SERVER_IP = server_ip

    # 根据模式显示不同信息
    if MODE == "local":
        print("========== 文件管理系统 - 本地模式 ==========")
        print("模式：本地单机使用")
        FLASK_HOST = "127.0.0.1"
        BROWSER_URL = f"http://127.0.0.1:{FLASK_PORT}"

    elif MODE == "server":
        local_ip = get_local_ip()
        print("========== 文件管理系统 - 服务器模式 ==========")
        print(f"模式：服务器模式（局域网共享）")
        print(f"本机IP: {local_ip}")
        print(f"访问地址: http://{local_ip}:{FLASK_PORT}")
        print(f"其他机器请使用此IP地址连接")
        FLASK_HOST = "0.0.0.0"  # 监听所有网络接口
        BROWSER_URL = f"http://127.0.0.1:{FLASK_PORT}"

    elif MODE == "client":
        print("========== 文件管理系统 - 客户端模式 ==========")
        print(f"模式：客户端模式")
        print(f"连接服务器: {SERVER_IP}:{FLASK_PORT}")
        FLASK_HOST = "127.0.0.1"  # 客户端不需要启动 Flask
        BROWSER_URL = f"http://{SERVER_IP}:{FLASK_PORT}"

    print("================================================")
    print("正在启动文件管理系统...")

    # 在后台线程启动Flask（仅本地模式和服务器模式）
    if MODE in ["local", "server"]:
        flask_thread = threading.Thread(target=run_flask, args=(FLASK_HOST,), daemon=True)
        flask_thread.start()

        # 优化：更频繁地检查 Flask 状态（减少启动时间）
        print("正在等待后端服务启动...")
        flask_ready = False
        for i in range(40):  # 最多8秒（40次 x 0.2秒）
            time.sleep(0.2)  # 减少等待间隔
            try:
                import requests
                response = requests.get(f'http://{FLASK_HOST}:{FLASK_PORT}/', timeout=0.5)
                print(f"✓ 后端服务已就绪")
                flask_ready = True
                break
            except:
                if i % 5 == 0:  # 每秒输出一次进度
                    print(f"启动中... {i*0.2:.1f}秒")

        if not flask_ready:
            print("⚠ 后端服务启动超时")

    # 检查前端文件
    frontend_path = os.path.join(exe_dir, 'frontend', 'dist', 'index.html')
    print(f"前端文件存在: {os.path.exists(frontend_path)}")

    # 初始化 CEF
    sys.excepthook = cef.ExceptHook
    cef.Initialize(settings)

    # 创建 Tkinter 窗口
    root = tk.Tk()
    root.title(f"文件管理系统 - {MODE.upper()} 模式")
    root.geometry("1400x900")
    root.minsize(1000, 600)

    # 获取窗口句柄
    window_handle = root.winfo_id()

    # 创建 WindowInfo
    window_info = cef.WindowInfo()
    window_info.SetAsChild(window_handle, [0, 0, 1400, 900])

    # 创建浏览器
    browser = cef.CreateBrowserSync(
        window_info=window_info,
        url=BROWSER_URL,
        window_title="FileManagement"
    )

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
                        # 使用简单的延时方式
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
        if hasattr(browser, 'GetMainFrame'):
            try:
                browser_width = event.width
                browser_height = event.height
                # 使用 Windows API 移动和调整浏览器窗口
                user32.SetWindowPos(window_handle, None, 0, 0, browser_width, browser_height, 0x0002)
            except:
                pass

    root.bind('<Configure>', on_window_configure)

    # 主消息循环
    def main_loop():
        """Tkinter 主消息循环"""
        try:
            root.mainloop()
        finally:
            # 清理 CEF
            if browser:
                try:
                    browser.CloseBrowser(True)
                    del browser
                except:
                    pass
            cef.Shutdown()

    # 启动主循环
    main_loop()


if __name__ == '__main__':
    main()
