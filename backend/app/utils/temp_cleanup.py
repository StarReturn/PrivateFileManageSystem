"""
临时文件清理工具
定期清理超过10分钟的临时文件
"""
import os
import time
import threading
import hashlib
from datetime import datetime, timedelta

# 临时文件前缀
TEMP_PREFIX = 'preview_'
# 清理间隔（秒）
CLEANUP_INTERVAL = 300  # 5分钟
# 文件最大存活时间（秒）
MAX_FILE_AGE = 600  # 10分钟

class TempFileCleaner:
    """临时文件清理器"""

    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        """启动清理线程"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.thread.start()
            print("临时文件清理器已启动")

    def stop(self):
        """停止清理线程"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("临时文件清理器已停止")

    def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                self.cleanup_old_files()
            except Exception as e:
                print(f"清理临时文件时出错: {e}")
            # 等待下一次清理
            time.sleep(CLEANUP_INTERVAL)

    @staticmethod
    def cleanup_old_files():
        """清理过期的临时文件"""
        import tempfile
        temp_dir = tempfile.gettempdir()

        if not os.path.exists(temp_dir):
            return

        now = time.time()
        cleaned_count = 0

        for filename in os.listdir(temp_dir):
            # 只处理以preview_开头的临时文件
            if filename.startswith(TEMP_PREFIX):
                file_path = os.path.join(temp_dir, filename)

                # 检查文件是否过期
                if os.path.isfile(file_path):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > MAX_FILE_AGE:
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                            print(f"已清理过期临时文件: {filename} (存在时间: {file_age:.0f}秒)")
                        except Exception as e:
                            print(f"删除文件失败 {filename}: {e}")

        if cleaned_count > 0:
            print(f"本次清理完成，共删除 {cleaned_count} 个过期临时文件")

    @staticmethod
    def get_temp_pdf_key(drawing_id, file_blob):
        """生成临时PDF文件的唯一标识"""
        # 使用drawing_id和文件内容的hash作为唯一标识
        content_hash = hashlib.md5(file_blob).hexdigest()[:16]
        return f"{TEMP_PREFIX}{drawing_id}_{content_hash}.pdf"

    @staticmethod
    def get_cached_pdf_path(drawing_id, file_blob):
        """获取缓存的PDF文件路径"""
        import tempfile
        temp_dir = tempfile.gettempdir()
        pdf_name = TempFileCleaner.get_temp_pdf_key(drawing_id, file_blob)
        pdf_path = os.path.join(temp_dir, pdf_name)

        # 检查缓存是否存在且未过期
        if os.path.exists(pdf_path):
            file_age = time.time() - os.path.getmtime(pdf_path)
            if file_age <= MAX_FILE_AGE:
                # 重置访问时间，延长存活时间
                os.utime(pdf_path, None)
                print(f"使用缓存的PDF文件: {pdf_name}")
                return pdf_path
            else:
                # 缓存已过期，删除
                try:
                    os.remove(pdf_path)
                    print(f"删除过期的缓存文件: {pdf_name}")
                except:
                    pass

        return None


# 全局清理器实例
cleaner = TempFileCleaner()
