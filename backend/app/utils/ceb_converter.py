"""
CEB 转 PDF 工具
使用 ceb2Pdf.exe 将 CEB 文件转换为 PDF
"""
import os
import sys
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)


def _get_tools_dir():
    """获取 tools 目录路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return os.path.join(sys._MEIPASS, 'tools')
    else:
        # 开发环境
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tools')


# ceb2Pdf.exe 路径
CEB2PDF_EXE = os.path.join(_get_tools_dir(), 'ceb2Pdf.exe')


def ceb_to_pdf(ceb_blob):
    """
    使用 ceb2Pdf.exe 将 CEB 文件转换为 PDF

    Args:
        ceb_blob: CEB 文件的二进制数据

    Returns:
        bytes: PDF 文件的二进制数据，如果转换失败返回 None
    """
    temp_dir = None
    temp_ceb = None
    temp_pdf = None

    try:
        # 检查 ceb2Pdf.exe 是否存在
        if not os.path.exists(CEB2PDF_EXE):
            logger.error(f'ceb2Pdf.exe 不存在: {CEB2PDF_EXE}')
            return None

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        # 保存 CEB 文件
        temp_ceb = os.path.join(temp_dir, 'temp.ceb')
        with open(temp_ceb, 'wb') as f:
            f.write(ceb_blob)

        # 准备输出 PDF 路径
        temp_pdf = os.path.join(temp_dir, 'temp.pdf')

        # 调用 ceb2Pdf.exe 转换
        cmd = [CEB2PDF_EXE, temp_ceb, temp_pdf]

        logger.info(f'执行命令: {" ".join(cmd)}')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 60秒超时
            encoding='utf-8',
            errors='ignore'  # 忽略编码错误
        )

        if result.returncode != 0:
            logger.error(f'ceb2Pdf 转换失败 (返回码: {result.returncode})')
            logger.error(f'错误输出: {result.stderr}')
            return None

        # 检查 PDF 是否生成
        if not os.path.exists(temp_pdf):
            logger.error('PDF 文件未生成')
            return None

        # 读取 PDF 文件
        with open(temp_pdf, 'rb') as f:
            pdf_blob = f.read()

        # 验证 PDF
        if len(pdf_blob) < 100:
            logger.error('生成的 PDF 文件太小，可能无效')
            return None

        if not pdf_blob.startswith(b'%PDF'):
            logger.error('生成的文件不是有效的 PDF 格式')
            return None

        logger.info(f'CEB 转 PDF 成功，PDF 大小: {len(pdf_blob)} 字节')
        return pdf_blob

    except subprocess.TimeoutExpired:
        logger.error('ceb2Pdf 转换超时')
        return None
    except FileNotFoundError:
        logger.error(f'未找到 ceb2Pdf.exe: {CEB2PDF_EXE}')
        return None
    except Exception as e:
        logger.error(f'CEB 转 PDF 失败: {str(e)}', exc_info=True)
        return None
    finally:
        # 清理临时文件
        if temp_ceb and os.path.exists(temp_ceb):
            try:
                os.remove(temp_ceb)
            except:
                pass
        if temp_pdf and os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except:
                pass
        if temp_dir and os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass


def check_ceb_converter_available():
    """
    检查 CEB 转换器是否可用

    Returns:
        bool: CEB 转换器是否可用
    """
    try:
        if not os.path.exists(CEB2PDF_EXE):
            logger.warning(f'ceb2Pdf.exe 不存在: {CEB2PDF_EXE}')
            return False

        # 尝试运行 ceb2Pdf.exe
        result = subprocess.run(
            [CEB2PDF_EXE],
            capture_output=True,
            timeout=5
        )

        return True
    except Exception as e:
        logger.error(f'CEB 转换器不可用: {str(e)}')
        return False


def get_ceb2pdf_path():
    """获取 ceb2Pdf.exe 的路径"""
    return CEB2PDF_EXE
