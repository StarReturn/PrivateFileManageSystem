"""
文件预览工具
"""
import io
import os
import tempfile
import time
import uuid


class PreviewManager:
    """文件预览管理器"""

    @staticmethod
    def save_temp_file(blob_data, file_type):
        """将BLOB数据保存为临时文件"""
        try:
            temp_dir = tempfile.gettempdir()
            ext = f'.{file_type.lower()}'
            temp_path = os.path.join(temp_dir, f'preview_{uuid.uuid4().hex}{ext}')

            with open(temp_path, 'wb') as f:
                f.write(blob_data)

            return temp_path
        except Exception as e:
            print(f"保存临时文件失败: {e}")
            return None

    @staticmethod
    def convert_word_to_pdf(word_path, retries=2, retry_delay=0.6):
        """将 Word 文档转换为 PDF（Win7/pywin32 稳定模式）"""
        base, _ = os.path.splitext(word_path)
        pdf_path = base + '.pdf'

        print(f"开始转换Word文档: {word_path} -> {pdf_path}")

        try:
            import pythoncom
            import win32com.client
            from pywintypes import com_error
        except ImportError:
            print("pywin32未安装，请运行: pip install pywin32")
            return None

        for attempt in range(1, retries + 1):
            word = None
            doc = None
            try:
                pythoncom.CoInitialize()

                # 使用 DispatchEx 创建独立实例，避免与现有 WINWORD 进程互相干扰
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = 0
                word.Options.WarnBeforeSavingPrintingSendingMarkup = False

                abs_word_path = os.path.abspath(word_path)
                abs_pdf_path = os.path.abspath(pdf_path)

                # OpenAndRepair 可降低损坏/兼容文档导致的失败概率
                doc = word.Documents.Open(
                    abs_word_path,
                    ConfirmConversions=False,
                    ReadOnly=True,
                    AddToRecentFiles=False,
                    Revert=False,
                    OpenAndRepair=True
                )

                # 优先 SaveAs(FileFormat=17)，失败时回退 ExportAsFixedFormat
                try:
                    doc.SaveAs(abs_pdf_path, FileFormat=17)
                except Exception:
                    doc.ExportAsFixedFormat(abs_pdf_path, 17)

                # 强制落盘
                time.sleep(0.25)

                if os.path.exists(abs_pdf_path) and os.path.getsize(abs_pdf_path) > 0:
                    print(f"Word转PDF成功: {abs_pdf_path}")
                    return abs_pdf_path
                print(f"Word转PDF失败: PDF文件未生成或为空（尝试 {attempt}/{retries}）")

            except com_error as e:
                print(f"Word转PDF COM异常（尝试 {attempt}/{retries}）: {e}")
            except Exception as e:
                print(f"Word转PDF失败（尝试 {attempt}/{retries}）: {e}")
            finally:
                try:
                    if doc is not None:
                        doc.Close(SaveChanges=False)
                except Exception:
                    pass
                try:
                    if word is not None:
                        word.Quit()
                except Exception:
                    pass
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

            if attempt < retries:
                time.sleep(retry_delay)

        return None

    @staticmethod
    def cleanup_temp_file(file_path):
        """清理临时文件"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
