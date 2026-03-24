"""
预览缓存管理器
使用两级缓存：内存缓存（LRU）+ 磁盘缓存
"""
import os
import hashlib
import pickle
import tempfile
import time
import logging
from functools import lru_cache
from threading import Lock

logger = logging.getLogger(__name__)


class PreviewCache:
    """预览缓存管理器"""

    def __init__(self, max_memory_items=100, max_disk_size_gb=2, cache_days=7):
        """
        初始化缓存

        Args:
            max_memory_items: 内存缓存最大条目数
            max_disk_size_gb: 磁盘缓存最大大小（GB）
            cache_days: 缓存保留天数
        """
        self.max_memory_items = max_memory_items
        self.max_disk_size_bytes = max_disk_size_gb * 1024 * 1024 * 1024
        self.cache_days = cache_days

        # 缓存目录
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'preview_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        # 内存缓存（带锁）
        self._memory_cache = {}
        self._memory_cache_lock = Lock()
        self._memory_cache_times = {}

        # 启动时清理过期缓存
        self._cleanup_expired()

    def get(self, key):
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在返回 None
        """
        # 先查内存缓存
        with self._memory_cache_lock:
            if key in self._memory_cache:
                logger.debug(f"内存缓存命中: {key}")
                return self._memory_cache[key]

        # 再查磁盘缓存
        disk_path = self._get_disk_path(key)
        if os.path.exists(disk_path):
            # 检查是否过期
            if self._is_expired(disk_path):
                logger.debug(f"磁盘缓存已过期: {key}")
                os.remove(disk_path)
                return None

            try:
                with open(disk_path, 'rb') as f:
                    cached_payload = pickle.load(f)

                # 兼容历史缓存格式：
                # 新格式 {'data': value, 'time': ts}
                # 旧格式直接是 value
                if isinstance(cached_payload, dict) and 'data' in cached_payload:
                    data = cached_payload['data']
                else:
                    data = cached_payload

                # 加载到内存缓存
                with self._memory_cache_lock:
                    self._memory_cache[key] = data
                    self._memory_cache_times[key] = time.time()
                    self._evict_if_needed()

                logger.debug(f"磁盘缓存命中: {key}")
                return data
            except Exception as e:
                logger.error(f"读取磁盘缓存失败: {e}")
                return None

        return None

    def set(self, key, value):
        """
        设置缓存

        Args:
            key: 缓存键
            value: 要缓存的数据
        """
        # 保存到内存缓存
        with self._memory_cache_lock:
            self._memory_cache[key] = value
            self._memory_cache_times[key] = time.time()
            self._evict_if_needed()

        # 保存到磁盘缓存
        disk_path = self._get_disk_path(key)
        try:
            # 创建临时文件
            temp_path = disk_path + '.tmp'
            with open(temp_path, 'wb') as f:
                pickle.dump({
                    'data': value,
                    'time': time.time()
                }, f)

            # 重命名（原子操作）
            os.rename(temp_path, disk_path)

            # 检查磁盘缓存大小
            self._cleanup_disk_if_needed()

        except Exception as e:
            logger.error(f"保存磁盘缓存失败: {e}")

    def invalidate(self, key):
        """
        使缓存失效

        Args:
            key: 缓存键
        """
        # 删除内存缓存
        with self._memory_cache_lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
            if key in self._memory_cache_times:
                del self._memory_cache_times[key]

        # 删除磁盘缓存
        disk_path = self._get_disk_path(key)
        if os.path.exists(disk_path):
            try:
                os.remove(disk_path)
            except:
                pass

    def clear_all(self):
        """清空所有缓存"""
        # 清空内存缓存
        with self._memory_cache_lock:
            self._memory_cache.clear()
            self._memory_cache_times.clear()

        # 清空磁盘缓存
        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except:
            pass

    def get_cache_info(self):
        """
        获取缓存信息

        Returns:
            dict: 缓存统计信息
        """
        # 内存缓存大小
        memory_count = len(self._memory_cache)

        # 磁盘缓存大小
        disk_size = 0
        disk_count = 0
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    disk_size += os.path.getsize(file_path)
                    disk_count += 1

        return {
            'memory_count': memory_count,
            'memory_max': self.max_memory_items,
            'disk_count': disk_count,
            'disk_size_mb': round(disk_size / 1024 / 1024, 2),
            'disk_max_mb': round(self.max_disk_size_bytes / 1024 / 1024, 2),
            'cache_days': self.cache_days
        }

    def _get_disk_path(self, key):
        """获取磁盘缓存路径"""
        # 使用 MD5 作为文件名
        key_hash = hashlib.md5(str(key).encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")

    def _is_expired(self, file_path):
        """检查文件是否过期"""
        try:
            mtime = os.path.getmtime(file_path)
            age_seconds = time.time() - mtime
            age_days = age_seconds / 86400
            return age_days > self.cache_days
        except:
            return True

    def _evict_if_needed(self):
        """LRU 淘汰内存缓存"""
        while len(self._memory_cache) > self.max_memory_items:
            # 找到最旧的条目
            oldest_key = min(self._memory_cache_times.items(), key=lambda x: x[1])[0]
            del self._memory_cache[oldest_key]
            del self._memory_cache_times[oldest_key]

    def _cleanup_disk_if_needed(self):
        """清理磁盘缓存（如果超过大小限制）"""
        total_size = 0
        files = []

        # 统计所有缓存文件
        if os.path.exists(self.cache_dir):
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    mtime = os.path.getmtime(file_path)
                    files.append((file_path, size, mtime))
                    total_size += size

        # 如果超过限制，删除最旧的文件
        if total_size > self.max_disk_size_bytes:
            # 按修改时间排序（从旧到新）
            files.sort(key=lambda x: x[2])

            for file_path, size, mtime in files:
                if total_size <= self.max_disk_size_bytes * 0.8:  # 保留到 80%
                    break
                try:
                    os.remove(file_path)
                    total_size -= size
                    logger.debug(f"清理磁盘缓存: {file_path}")
                except:
                    pass

    def _cleanup_expired(self):
        """启动时清理过期缓存"""
        if not os.path.exists(self.cache_dir):
            return

        try:
            now = time.time()
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    if self._is_expired(file_path):
                        try:
                            os.remove(file_path)
                            logger.debug(f"清理过期缓存: {file_path}")
                        except:
                            pass
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")


# 全局缓存实例
_preview_cache = None


def get_preview_cache():
    """获取全局缓存实例"""
    global _preview_cache
    if _preview_cache is None:
        _preview_cache = PreviewCache(
            max_memory_items=100,      # 最多缓存 100 个预览结果
            max_disk_size_gb=2,         # 最多占用 2GB 磁盘空间
            cache_days=7                # 缓存保留 7 天
        )
    return _preview_cache
