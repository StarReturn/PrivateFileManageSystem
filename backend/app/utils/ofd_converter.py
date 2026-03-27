"""
OFD 转 PDF 工具
使用 JAR 包方式（OFDRW 库），通过 Java 调用转换，兼容 Win7

版本说明：
- JAR (OFDRW 2.0.2): 基于 Java 的 OFD 转换方案，兼容性最好
"""
import subprocess
import sys
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# OFD 支持状态缓存
_OFD_AVAILABLE = None
_OFD_UNSUPPORTED_REASON = None


def _get_tools_dir():
    """获取 tools 目录路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return os.path.join(sys._MEIPASS, 'tools')
    else:
        # 开发环境
        return os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools')


def _get_java_executable():
    """获取 Java 可执行文件路径"""
    tools_dir = _get_tools_dir()
    java_path = os.path.join(tools_dir, 'jre1.8.0_151', 'bin', 'java.exe')

    if os.path.exists(java_path):
        return java_path

    # 备用：使用系统 PATH 中的 java
    return 'java'


def _get_jar_path():
    """获取 ofd-converter.jar 路径"""
    tools_dir = _get_tools_dir()
    jar_path = os.path.join(tools_dir, 'ofd-converter.jar')

    if os.path.exists(jar_path):
        return jar_path

    return None


def ofd_to_pdf(ofd_blob):
    """
    将 OFD 文件转换为 PDF

    Args:
        ofd_blob: OFD 文件的二进制数据

    Returns:
        bytes: PDF 文件的二进制数据，如果转换失败返回 None
    """
    # 检查 OFD 转换器是否可用
    available, reason = check_ofd_available_detailed()
    if not available:
        logger.warning(f'OFD 转换器不可用: {reason}')
        return None

    # 获取 Java 和 JAR 路径
    java_exe = _get_java_executable()
    jar_path = _get_jar_path()

    if not jar_path:
        logger.error('ofd-converter.jar 不存在')
        return None

    # 创建临时文件
    with tempfile.TemporaryDirectory() as temp_dir:
        ofd_path = os.path.join(temp_dir, 'input.ofd')
        pdf_path = os.path.join(temp_dir, 'output.pdf')

        try:
            # 写入 OFD 文件
            with open(ofd_path, 'wb') as f:
                f.write(ofd_blob)

            # 调用 JAR 转换
            cmd = [
                java_exe,
                '-jar', jar_path,
                ofd_path,
                pdf_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )

            # 检查结果
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f'OFD 转 PDF 失败: {error_msg}')
                return None

            if 'SUCCESS' not in result.stdout:
                logger.error(f'OFD 转 PDF 失败: 未找到 SUCCESS 标记')
                return None

            # 读取生成的 PDF
            if not os.path.exists(pdf_path):
                logger.error('PDF 文件未生成')
                return None

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            # 验证 PDF
            if len(pdf_bytes) < 100:
                logger.error('生成的 PDF 文件太小')
                return None

            if not pdf_bytes.startswith(b'%PDF'):
                logger.error('生成的文件不是有效的 PDF 格式')
                return None

            logger.info(f'OFD 转 PDF 成功，PDF 大小: {len(pdf_bytes)} 字节')
            return pdf_bytes

        except subprocess.TimeoutExpired:
            logger.error('OFD 转 PDF 超时')
            return None
        except Exception as e:
            logger.error(f'OFD 转 PDF 失败: {str(e)}', exc_info=True)
            return None


def ofd_to_images(ofd_blob, dpi=150):
    """
    将 OFD 文件转换为图片列表
    通过 PDF 中间步骤：OFD → PDF → 图片

    Args:
        ofd_blob: OFD 文件的二进制数据
        dpi: 图片分辨率（默认150）

    Returns:
        list: base64 编码的图片列表
        如果 OFD 转换器不可用，返回 None
        如果转换失败，返回 []
    """
    # 先转为 PDF
    pdf_bytes = ofd_to_pdf(ofd_blob)
    if not pdf_bytes:
        return None

    # 再转为图片
    from app.utils.image_preview import pdf_to_images
    return pdf_to_images(pdf_bytes, dpi=dpi)


def check_ofd_available():
    """
    检查 OFD 转换器是否可用

    Returns:
        bool: OFD 转换器是否可用
    """
    available, _ = check_ofd_available_detailed()
    return available


def check_ofd_available_detailed():
    """
    检查 OFD 转换器是否可用，并返回详细信息

    Returns:
        tuple: (是否可用, 原因描述)
    """
    global _OFD_AVAILABLE, _OFD_UNSUPPORTED_REASON

    # 使用缓存结果
    if _OFD_AVAILABLE is not None:
        return _OFD_AVAILABLE, _OFD_UNSUPPORTED_REASON

    # 检查 JAR 文件
    jar_path = _get_jar_path()
    if not jar_path:
        reason = 'ofd-converter.jar 不存在于 tools 目录，请先编译 Java 项目'
        logger.error(f'{reason}')
        _OFD_AVAILABLE = False
        _OFD_UNSUPPORTED_REASON = reason
        return False, reason

    # 检查 Java 环境
    java_exe = _get_java_executable()

    try:
        # 测试 Java 是否可用
        result = subprocess.run(
            [java_exe, '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            reason = f'Java 不可用: {java_exe}'
            logger.error(f'{reason}')
            _OFD_AVAILABLE = False
            _OFD_UNSUPPORTED_REASON = reason
            return False, reason

        logger.info(f'OFD 转换器可用 (Java: {java_exe}, JAR: {jar_path})')
        _OFD_AVAILABLE = True
        _OFD_UNSUPPORTED_REASON = None
        return True, None

    except FileNotFoundError:
        reason = f'Java 未找到: {java_exe}，请确保 JRE 已安装'
        logger.error(f'{reason}')
        _OFD_AVAILABLE = False
        _OFD_UNSUPPORTED_REASON = reason
        return False, reason
    except subprocess.TimeoutExpired:
        reason = 'Java 命令超时'
        logger.error(f'{reason}')
        _OFD_AVAILABLE = False
        _OFD_UNSUPPORTED_REASON = reason
        return False, reason
    except Exception as e:
        reason = f'OFD 转换器检查失败: {str(e)}'
        logger.error(f'{reason}')
        _OFD_AVAILABLE = False
        _OFD_UNSUPPORTED_REASON = reason
        return False, reason
