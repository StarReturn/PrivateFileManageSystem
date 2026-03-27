"""
Apache POI 转换器
使用 JAR 调用 Apache POI 进行 Word/Excel 转换
"""
import os
import sys
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)


def _get_tools_dir():
    """获取 tools 目录路径"""
    candidates = []

    if getattr(sys, 'frozen', False):
        # PyInstaller 运行时优先从解包目录与 exe 同级查找
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            candidates.append(os.path.join(meipass, 'tools'))
        candidates.append(os.path.join(os.path.dirname(sys.executable), 'tools'))
    else:
        # 开发环境：优先项目根目录 tools，再兼容 backend/tools
        utils_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(utils_dir))))
        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(utils_dir)))
        candidates.append(os.path.join(project_root, 'tools'))
        candidates.append(os.path.join(backend_root, 'tools'))

    for path in candidates:
        if path and os.path.exists(path):
            return path

    # 最后兜底返回第一个候选，便于日志定位
    return candidates[0] if candidates else os.path.join(os.getcwd(), 'tools')


def _get_java_command():
    """优先使用内置 JRE，其次使用系统 java"""
    tools_dir = _get_tools_dir()
    java_candidates = [
        os.path.join(tools_dir, 'jre1.8.0_151', 'bin', 'java.exe'),
        os.path.join(tools_dir, 'jre', 'bin', 'java.exe'),
        os.path.join(tools_dir, 'java', 'bin', 'java.exe'),
        'java'
    ]

    for cmd in java_candidates:
        if cmd == 'java' or os.path.exists(cmd):
            return cmd

    return 'java'


def _guess_file_ext(blob_data, original_filename, kind):
    """根据原始文件名和文件头判断临时文件后缀"""
    if original_filename and '.' in original_filename:
        ext = os.path.splitext(original_filename)[1].lower()
        if kind == 'word' and ext in ['.doc', '.docx']:
            return ext
        if kind == 'excel' and ext in ['.xls', '.xlsx']:
            return ext

    # OLE2 复合文档（doc/xls 旧格式）文件头：D0 CF 11 E0
    if blob_data[:4] == b'\xD0\xCF\x11\xE0':
        return '.doc' if kind == 'word' else '.xls'

    # ZIP（docx/xlsx）文件头：PK
    if blob_data[:2] == b'PK':
        return '.docx' if kind == 'word' else '.xlsx'

    # 兜底
    return '.docx' if kind == 'word' else '.xlsx'


# POI Converter JAR 路径
POI_CONVERTER_JAR = os.path.join(_get_tools_dir(), 'poi-converter.jar')


def word_to_html(word_blob, original_filename=None):
    """
    使用 Apache POI 将 Word 文档转换为 HTML

    Args:
        word_blob: Word 文件的二进制数据
        original_filename: 原始文件名（用于 HTML 标题显示）

    Returns:
        str: HTML 内容，如果转换失败返回 None
    """
    temp_dir = None
    temp_html = None

    try:
        # 检查 JAR 是否存在
        if not os.path.exists(POI_CONVERTER_JAR):
            logger.warning(f'POI Converter JAR 不存在：{POI_CONVERTER_JAR}')
            return None

        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        word_ext = _guess_file_ext(word_blob, original_filename, 'word')
        temp_word = os.path.join(temp_dir, f'temp{word_ext}')
        temp_html = os.path.join(temp_dir, 'output.html')

        # 保存 Word 文件
        with open(temp_word, 'wb') as f:
            f.write(word_blob)

        # 调用 JAR 转换
        java_cmd = _get_java_command()
        cmd = [java_cmd, '-jar', POI_CONVERTER_JAR, 'word2html', temp_word, temp_html]
        if original_filename:
            cmd.append(original_filename)

        logger.info(f'执行 Word 转 HTML 命令，文件名：{original_filename or "temp.docx"}')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            logger.error(f'POI Word 转 HTML 失败 (返回码：{result.returncode})，stderr: {result.stderr}')
            return None

        # 检查 HTML 是否生成
        if not os.path.exists(temp_html):
            logger.error('HTML 文件未生成')
            return None

        # 读取 HTML 文件
        with open(temp_html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        logger.info(f'Word 转 HTML 成功，HTML 大小：{len(html_content)} 字符')
        return html_content

    except subprocess.TimeoutExpired:
        logger.error('POI Word 转 HTML 超时')
        return None
    except Exception as e:
        logger.error(f'POI Word 转 HTML 失败：{str(e)}', exc_info=True)
        return None
    finally:
        # 清理临时文件
        if temp_html and os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except:
                pass
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass


def excel_to_html(excel_blob, original_filename=None):
    """
    使用 Apache POI 将 Excel 文件转换为 HTML

    Args:
        excel_blob: Excel 文件的二进制数据
        original_filename: 原始文件名（用于 HTML 标题显示）

    Returns:
        str: HTML 内容，如果转换失败返回 None
    """
    temp_dir = None
    temp_html = None

    try:
        # 检查 JAR 是否存在
        if not os.path.exists(POI_CONVERTER_JAR):
            logger.warning(f'POI Converter JAR 不存在：{POI_CONVERTER_JAR}')
            return None

        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        excel_ext = _guess_file_ext(excel_blob, original_filename, 'excel')
        temp_excel = os.path.join(temp_dir, f'temp{excel_ext}')
        temp_html = os.path.join(temp_dir, 'output.html')

        # 保存 Excel 文件
        with open(temp_excel, 'wb') as f:
            f.write(excel_blob)

        # 调用 JAR 转换
        java_cmd = _get_java_command()
        cmd = [java_cmd, '-jar', POI_CONVERTER_JAR, 'excel2html', temp_excel, temp_html]
        if original_filename:
            cmd.append(original_filename)

        logger.info(f'执行 Excel 转 HTML 命令，文件名：{original_filename or "temp.xlsx"}')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            logger.error(f'POI Excel 转 HTML 失败 (返回码：{result.returncode})，stderr: {result.stderr}')
            return None

        # 检查 HTML 是否生成
        if not os.path.exists(temp_html):
            logger.error('HTML 文件未生成')
            return None

        # 读取 HTML 文件
        with open(temp_html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        logger.info(f'Excel 转 HTML 成功，HTML 大小：{len(html_content)} 字符')
        return html_content

    except subprocess.TimeoutExpired:
        logger.error('POI Excel 转 HTML 超时')
        return None
    except Exception as e:
        logger.error(f'POI Excel 转 HTML 失败：{str(e)}', exc_info=True)
        return None
    finally:
        # 清理临时文件
        if temp_html and os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except:
                pass
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass


def pdf_to_html(pdf_blob):
    """
    使用 Apache PDFBox 将 PDF 文档转换为 HTML

    Args:
        pdf_blob: PDF 文件的二进制数据

    Returns:
        str: HTML 内容，如果转换失败返回 None
    """
    temp_dir = None
    temp_html = None

    try:
        # 检查 JAR 是否存在
        if not os.path.exists(POI_CONVERTER_JAR):
            logger.warning(f'POI Converter JAR 不存在：{POI_CONVERTER_JAR}')
            return None

        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        temp_pdf = os.path.join(temp_dir, 'temp.pdf')
        temp_html = os.path.join(temp_dir, 'output.html')

        # 保存 PDF 文件
        with open(temp_pdf, 'wb') as f:
            f.write(pdf_blob)

        # 调用 JAR 转换
        java_cmd = _get_java_command()
        cmd = [java_cmd, '-jar', POI_CONVERTER_JAR, 'pdf2html', temp_pdf, temp_html]

        logger.info(f'执行 PDF 转 HTML 命令')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            logger.error(f'POI PDF 转 HTML 失败 (返回码：{result.returncode})，stderr: {result.stderr}')
            return None

        # 检查 HTML 是否生成
        if not os.path.exists(temp_html):
            logger.error('HTML 文件未生成')
            return None

        # 读取 HTML 文件
        with open(temp_html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        logger.info(f'PDF 转 HTML 成功，HTML 大小：{len(html_content)} 字符')
        return html_content

    except subprocess.TimeoutExpired:
        logger.error('POI PDF 转 HTML 超时')
        return None
    except Exception as e:
        logger.error(f'POI PDF 转 HTML 失败：{str(e)}', exc_info=True)
        return None
    finally:
        # 清理临时文件
        if temp_html and os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except:
                pass
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass


def check_poi_converter_available():
    """
    检查 POI Converter 是否可用

    Returns:
        bool: POI Converter 是否可用
    """
    try:
        if not os.path.exists(POI_CONVERTER_JAR):
            logger.warning(f'POI Converter JAR 不存在：{POI_CONVERTER_JAR}')
            return False

        # 检查 Java 是否可用（优先内置 JRE）
        java_cmd = _get_java_command()
        result = subprocess.run([java_cmd, '-version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            logger.error(f'Java 命令不可用：{java_cmd}')
            return False
        return True
    except Exception as e:
        logger.error(f'POI Converter 不可用：{str(e)}')
        return False
