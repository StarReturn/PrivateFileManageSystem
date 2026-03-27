"""
Excel 转 PDF 工具
使用 Excel COM 接口将 Excel 文件转换为 PDF
"""
import os
import tempfile
import logging
import time

logger = logging.getLogger(__name__)


def excel_to_pdf(excel_blob):
    """
    将 Excel 文件转换为 PDF

    Args:
        excel_blob: Excel 文件的二进制数据

    Returns:
        bytes: PDF 文件的二进制数据，如果转换失败返回 None
    """
    temp_dir = None
    temp_xlsx = None
    temp_pdf = None
    excel_app = None
    workbook = None

    try:
        import pythoncom
        pythoncom.CoInitialize()

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        # 确定文件扩展名
        # 根据文件内容判断是 .xlsx 还是 .xls
        # Excel 2007+ 格式通常以 PK 开头（ZIP 格式）
        if excel_blob[:2] == b'PK':
            file_ext = '.xlsx'
        else:
            file_ext = '.xls'

        # 保存 Excel 文件
        temp_xlsx = os.path.join(temp_dir, f'temp{file_ext}')
        with open(temp_xlsx, 'wb') as f:
            f.write(excel_blob)

        # 准备输出 PDF 路径
        temp_pdf = os.path.join(temp_dir, 'temp.pdf')

        # 导入 win32com
        try:
            import win32com.client
        except ImportError:
            logger.error('未安装 pywin32，请运行: pip install pywin32')
            return None

        # 启动 Excel 应用程序
        excel_app = win32com.client.DispatchEx("Excel.Application")
        excel_app.Visible = False
        excel_app.DisplayAlerts = False
        excel_app.AlertBeforeOverwriting = False

        # 打开工作簿
        try:
            workbook = excel_app.Workbooks.Open(temp_xlsx)
        except Exception as e:
            logger.error(f'无法打开 Excel 文件: {str(e)}')
            # 尝试使用不同的方法
            try:
                workbook = excel_app.Workbooks.Open(
                    temp_xlsx,
                    ReadOnly=True,
                    IgnoreReadOnlyRecommended=True
                )
            except Exception as e2:
                logger.error(f'使用备用方法打开 Excel 文件也失败: {str(e2)}')
                return None

        # 导出为 PDF
        # ExportAsFixedFormat 参数:
        #   Type: 0 = PDF, 1 = XPS
        #   Quality: xlQualityStandard = 0
        try:
            # 优化宽表分页：尽量压缩为一页宽，减少“一个 sheet 被横向切碎”
            try:
                for sheet in workbook.Worksheets:
                    try:
                        setup = sheet.PageSetup
                        setup.Zoom = False
                        setup.FitToPagesWide = 1
                        setup.FitToPagesTall = False
                        setup.Orientation = 2  # xlLandscape
                    except Exception:
                        pass
            except Exception:
                pass

            workbook.ExportAsFixedFormat(0, temp_pdf)
        except Exception as e:
            logger.error(f'Excel 导出 PDF 失败: {str(e)}')
            return None

        # 关闭工作簿
        try:
            workbook.Close(SaveChanges=False)
        except:
            pass

        # 退出 Excel 应用程序
        try:
            excel_app.Quit()
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

        logger.info(f'Excel 转 PDF 成功，PDF 大小: {len(pdf_blob)} 字节')
        return pdf_blob

    except Exception as e:
        logger.error(f'Excel 转 PDF 失败: {str(e)}', exc_info=True)
        return None

    finally:
        # 清理 COM 对象
        if workbook is not None:
            try:
                workbook.Close(SaveChanges=False)
            except:
                pass

        if excel_app is not None:
            try:
                excel_app.Quit()
            except:
                pass

        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except:
            pass

        # 清理临时文件
        if temp_xlsx and os.path.exists(temp_xlsx):
            try:
                os.remove(temp_xlsx)
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


def check_excel_available():
    """
    检查 Excel 是否可用

    Returns:
        bool: Excel 是否可用
    """
    try:
        import win32com.client
        excel = win32com.client.Dispatch("Excel.Application")
        version = excel.Version
        excel.Quit()
        logger.info(f'Excel 版本: {version}')
        return True
    except ImportError:
        logger.error('未安装 pywin32')
        return False
    except Exception as e:
        logger.error(f'Excel 不可用: {str(e)}')
        return False


# 供外部调用的别名
excel_to_pdf_blob = excel_to_pdf
