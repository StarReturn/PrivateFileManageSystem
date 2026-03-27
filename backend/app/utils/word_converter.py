"""
Word 转 PDF 工具
使用 Word COM 接口将 Word 文件转换为 PDF
"""
import os
import tempfile
import logging
import time

logger = logging.getLogger(__name__)


def word_to_pdf(word_blob):
    """
    将 Word 文件转换为 PDF

    Args:
        word_blob: Word 文件的二进制数据

    Returns:
        bytes: PDF 文件的二进制数据，如果转换失败返回 None
    """
    temp_dir = None
    temp_doc = None
    temp_pdf = None
    word_app = None
    doc = None

    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        # 确定文件扩展名
        # Word 2007+ 格式通常以 PK 开头（ZIP 格式）
        if word_blob[:2] == b'PK':
            file_ext = '.docx'
        else:
            file_ext = '.doc'

        # 保存 Word 文件
        temp_doc = os.path.join(temp_dir, f'temp{file_ext}')
        with open(temp_doc, 'wb') as f:
            f.write(word_blob)

        # 准备输出 PDF 路径
        temp_pdf = os.path.join(temp_dir, 'temp.pdf')

        # 导入 win32com
        try:
            import win32com.client
        except ImportError:
            logger.error('未安装 pywin32，请运行: pip install pywin32')
            return None

        # 启动 Word 应用程序
        word_app = win32com.client.Dispatch("Word.Application")
        word_app.Visible = False
        word_app.DisplayAlerts = 0
        word_app.AlertBeforeOverwriting = False

        # 打开文档
        try:
            doc = word_app.Documents.Open(temp_doc, ReadOnly=True)
        except Exception as e:
            logger.error(f'无法打开 Word 文件: {str(e)}')
            return None

        # 另存为 PDF (FileFormat=17 表示 wdFormatPDF)
        try:
            doc.SaveAs(temp_pdf, FileFormat=17)
        except Exception as e:
            logger.error(f'Word 导出 PDF 失败: {str(e)}')
            return None

        # 关闭文档
        try:
            doc.Close(SaveChanges=False)
        except:
            pass

        # 退出 Word 应用程序
        try:
            word_app.Quit()
        except:
            pass

        # 等待文件写入完成
        time.sleep(0.5)

        # 读取生成的 PDF 文件
        if not os.path.exists(temp_pdf):
            logger.error('PDF 文件未生成')
            return None

        with open(temp_pdf, 'rb') as f:
            pdf_blob = f.read()

        # 检查 PDF 文件是否有效
        if len(pdf_blob) < 100:
            logger.error('生成的 PDF 文件无效')
            return None

        # 检查 PDF 文件头
        if not pdf_blob.startswith(b'%PDF'):
            logger.error('生成的文件不是有效的 PDF 格式')
            return None

        logger.info(f'Word 转 PDF 成功，PDF 大小: {len(pdf_blob)} 字节')
        return pdf_blob

    except Exception as e:
        logger.error(f'Word 转 PDF 失败: {str(e)}', exc_info=True)
        return None

    finally:
        # 清理 COM 对象
        if doc is not None:
            try:
                doc.Close(SaveChanges=False)
            except:
                pass

        if word_app is not None:
            try:
                word_app.Quit()
            except:
                pass

        # 清理临时文件
        if temp_doc and os.path.exists(temp_doc):
            try:
                os.remove(temp_doc)
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


def check_word_available():
    """
    检查 Word 是否可用

    Returns:
        bool: Word 是否可用
    """
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        version = word.Version
        word.Quit()
        logger.info(f'Word 版本: {version}')
        return True
    except ImportError:
        logger.error('未安装 pywin32')
        return False
    except Exception as e:
        logger.error(f'Word 不可用: {str(e)}')
        return False


# 供外部调用的别名
word_to_pdf_blob = word_to_pdf
