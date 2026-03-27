"""
PDF/Word 转图片预览工具
使用 PyMuPDF 将 PDF 转换为图片，支持 WebP 压缩
"""
import os
import tempfile
import base64
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def _render_pdf_page(pdf_blob, page_num, dpi=150, max_size=(2000, 2000), use_webp=True, webp_quality=80):
    """渲染 PDF 指定页并返回 data url"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("错误: 未安装 PyMuPDF，请运行: pip install PyMuPDF")
        return None

    try:
        doc = fitz.open(stream=pdf_blob, filetype="pdf")
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            return None

        page = doc.load_page(page_num)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        if pix.width > max_size[0] or pix.height > max_size[1]:
            scale_w = max_size[0] / pix.width
            scale_h = max_size[1] / pix.height
            zoom = zoom * min(scale_w, scale_h)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

        png_data = pix.tobytes("png")
        if use_webp:
            webp_data = convert_png_to_webp(png_data, webp_quality)
            if webp_data:
                img_data = webp_data
                img_format = "webp"
            else:
                img_data = png_data
                img_format = "png"
        else:
            img_data = png_data
            img_format = "png"

        doc.close()
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/{img_format};base64,{img_base64}"
    except Exception as e:
        logger.error(f"渲染 PDF 页面失败: {str(e)}")
        return None


def pdf_page_count(pdf_blob):
    """返回 PDF 页数"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("错误: 未安装 PyMuPDF，请运行: pip install PyMuPDF")
        return 0

    try:
        doc = fitz.open(stream=pdf_blob, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"读取 PDF 页数失败: {str(e)}")
        return 0


def pdf_to_image_page(pdf_blob, page, dpi=150, max_size=(2000, 2000), use_webp=True, webp_quality=80):
    """
    将 PDF 指定页转换为图片（page 从 1 开始）
    """
    if page < 1:
        return None
    return _render_pdf_page(
        pdf_blob,
        page_num=page - 1,
        dpi=dpi,
        max_size=max_size,
        use_webp=use_webp,
        webp_quality=webp_quality
    )


def pdf_to_images(pdf_blob, dpi=150, max_size=(2000, 2000), use_webp=True, webp_quality=80):
    """
    将 PDF 转换为图片列表

    Args:
        pdf_blob: PDF 文件的二进制数据
        dpi: 图片分辨率（默认 150）
        max_size: 图片最大尺寸
        use_webp: 是否使用 WebP 格式（默认 True）
        webp_quality: WebP 质量（1-100，默认 80）

    Returns:
        list: base64 编码的图片列表
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("错误: 未安装 PyMuPDF，请运行: pip install PyMuPDF")
        return []

    images = []

    try:
        # 从内存加载 PDF
        doc = fitz.open(stream=pdf_blob, filetype="pdf")
        total = len(doc)
        doc.close()
        for page_num in range(total):
            data_url = _render_pdf_page(
                pdf_blob,
                page_num=page_num,
                dpi=dpi,
                max_size=max_size,
                use_webp=use_webp,
                webp_quality=webp_quality
            )
            if data_url:
                images.append(data_url)

        return images

    except Exception as e:
        logger.error(f"PDF 转图片失败: {str(e)}")
        return []


def save_pdf_to_temp_images(pdf_blob, temp_dir=None, dpi=150):
    """
    将 PDF 转换为图片并保存到临时目录

    Args:
        pdf_blob: PDF 文件的二进制数据
        temp_dir: 临时目录（如果为 None，使用系统临时目录）
        dpi: 图片分辨率

    Returns:
        list: 图片文件路径列表
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("错误: 未安装 PyMuPDF")
        return []

    if temp_dir is None:
        temp_dir = tempfile.gettempdir()

    image_paths = []

    try:
        # 从内存加载 PDF
        doc = fitz.open(stream=pdf_blob, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # 设置缩放因子
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            # 渲染页面
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # 保存为 PNG 文件
            img_path = os.path.join(temp_dir, f"pdf_page_{page_num + 1}.png")
            pix.save(img_path)

            image_paths.append(img_path)

        doc.close()

        return image_paths

    except Exception as e:
        logger.error(f"PDF 转图片失败: {str(e)}")
        # 清理已创建的文件
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
        return []


def convert_png_to_webp(png_data, quality=80):
    """
    将 PNG 数据转换为 WebP 格式

    Args:
        png_data: PNG 图片的二进制数据
        quality: WebP 质量（1-100，默认 80）

    Returns:
        bytes: WebP 图片的二进制数据，如果转换失败返回 None
    """
    try:
        from PIL import Image
        from io import BytesIO

        # 从 PNG 数据创建图片对象
        img = Image.open(BytesIO(png_data))

        # 转换为 RGB 模式（WebP 不支持 RGBA）
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 使用 alpha 通道作为 mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 保存为 WebP 格式
        output = BytesIO()
        img.save(output, format='WebP', quality=quality, method=6)
        webp_data = output.getvalue()

        # 检查压缩效果
        original_size = len(png_data)
        webp_size = len(webp_data)
        compression_ratio = (1 - webp_size / original_size) * 100

        logger.debug(f"PNG → WebP: {original_size} → {webp_size} bytes (压缩 {compression_ratio:.1f}%)")

        return webp_data

    except ImportError:
        logger.warning("未安装 Pillow，无法转换为 WebP 格式")
        return None
    except Exception as e:
        logger.error(f"PNG 转 WebP 失败: {str(e)}")
        return None


def check_webp_available():
    """
    检查 WebP 转换是否可用

    Returns:
        bool: WebP 转换是否可用
    """
    try:
        from PIL import Image
        from io import BytesIO

        # 测试转换
        test_img = Image.new('RGB', (10, 10), color='red')
        output = BytesIO()
        test_img.save(output, format='WebP')
        return True
    except ImportError:
        return False
    except Exception:
        return False
