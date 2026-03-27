"""
文件转换工具 - 将各种格式转换为 PDF
支持：PDF、Word、Excel
"""
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


def convert_to_pdf(file_blob, file_type):
    """
    将各种格式的文件转换为 PDF

    Args:
        file_blob: 文件的二进制数据
        file_type: 文件类型 (pdf, doc, docx, xlsx, xls)

    Returns:
        bytes: PDF 文件的二进制数据，如果转换失败返回 None
    """
    try:
        if file_type == 'pdf':
            # PDF 直接返回
            return file_blob

        elif file_type in ['doc', 'docx']:
            # Word 转 PDF
            from .word_converter import word_to_pdf
            return word_to_pdf(file_blob)

        elif file_type in ['xlsx', 'xls']:
            # Excel 转 PDF
            from .excel_converter import excel_to_pdf
            return excel_to_pdf(file_blob)

        else:
            logger.error(f'不支持的文件类型: {file_type}')
            return None

    except Exception as e:
        logger.error(f'文件转换失败 ({file_type}): {str(e)}')
        return None


def get_converter_status():
    """
    检查各种转换器是否可用

    Returns:
        dict: 各转换器的状态
    """
    status = {
        'pdf': True,  # PDF 无需转换
        'word': check_word_converter(),
        'excel': check_excel_converter()
    }
    return status


def check_word_converter():
    """检查 Word 转换器是否可用"""
    try:
        # 检查是否安装了 Word
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Quit()
        return True
    except:
        return False


def check_excel_converter():
    """检查 Excel 转换器是否可用"""
    try:
        # 检查是否安装了 Excel
        import win32com.client
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Quit()
        return True
    except:
        return False
