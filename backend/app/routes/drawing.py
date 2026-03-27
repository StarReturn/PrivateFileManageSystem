"""
图纸管理路由
"""
from flask import Blueprint, request, jsonify, send_file, Response
from app.models.models import db, Drawing, OperationLog
from app.utils.auth import token_required, optional_token
from datetime import datetime
from urllib.parse import quote
from sqlalchemy import or_, and_
import io
import os
import time
import uuid
import base64
import threading
import tempfile

drawing_bp = Blueprint('drawing', __name__)

# kkFileView 临时文件映射（仅用于 CEB 转换后的临时 PDF）
_KK_TEMP_FILES = {}
_KK_TEMP_FILES_LOCK = threading.Lock()
_KK_TEMP_FILE_TTL_SECONDS = 30 * 60


def _extract_request_token():
    """从请求中提取原始 token（去掉 Bearer 前缀）"""
    token = request.headers.get('Authorization') or request.args.get('token')
    if token and token.startswith('Bearer '):
        token = token[7:]
    return token


def _get_current_user():
    """获取当前用户信息（optional_token 可能未设置）"""
    return getattr(request, 'current_user', None)


def _can_preview_drawing(drawing, current_user):
    """预览权限校验，返回 (ok, msg, status_code)"""
    if not current_user and drawing.visibility != 'public':
        return False, '请先登录', 401

    if current_user:
        current_user_id = int(current_user['user_id'])
        if drawing.visibility == 'private' and drawing.upload_user_id != current_user_id:
            return False, '无权限预览此文件', 403

    return True, '', 200


def _cleanup_expired_kk_temp_files():
    """清理过期 kkFileView 临时文件"""
    now = time.time()
    expired_tokens = []
    with _KK_TEMP_FILES_LOCK:
        for token, meta in _KK_TEMP_FILES.items():
            if meta.get('expires_at', 0) <= now:
                expired_tokens.append(token)

        for token in expired_tokens:
            file_path = _KK_TEMP_FILES[token].get('path')
            del _KK_TEMP_FILES[token]
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass


def _register_kk_temp_file(file_path):
    """注册临时文件并返回访问 token"""
    temp_token = uuid.uuid4().hex
    with _KK_TEMP_FILES_LOCK:
        _KK_TEMP_FILES[temp_token] = {
            'path': file_path,
            'expires_at': time.time() + _KK_TEMP_FILE_TTL_SECONDS,
        }
    return temp_token


@drawing_bp.route('/api/drawings', methods=['GET'])
@optional_token
def get_drawings():
    """获取图纸列表（支持未登录访问）"""
    try:
        # 获取筛选参数
        category_id = request.args.get('category_id', type=int)
        category_ids = request.args.get('category_ids', '')  # 支持多个目录 ID，逗号分隔
        file_type = request.args.get('file_type', '')
        file_name = request.args.get('file_name', '')
        user_name = request.args.get('user_name', '')

        # 获取当前用户信息（可能为 None）
        from flask import request as req
        current_user = getattr(req, 'current_user', None)
        is_admin = current_user and current_user.get('role') == 'admin' if current_user else False
        current_user_id = int(current_user['user_id']) if current_user else None  # 确保是整数

        # 调试信息
        print(f"[文件列表] current_user: {current_user}, current_user_id: {current_user_id}, is_admin: {is_admin}")

        # 构建查询
        from app.models.models import User
        query = db.session.query(Drawing)

        # 过滤已删除的文件（不在回收站中）
        query = query.filter(Drawing.is_deleted == False)

        # 根据登录状态和角色过滤可见性
        if not current_user:
            # 未登录：只能看到全站可见
            print(f"[文件列表] 未登录用户，只显示 public 文件")
            query = query.filter(Drawing.visibility == 'public')
        elif is_admin:
            # 管理员：可以看到所有文件（包括自己上传的 private 文件）
            print(f"[文件列表] 管理员用户，显示 public+login+ 自己的 private 文件")
            query = query.filter(
                or_(
                    Drawing.visibility == 'public',
                    Drawing.visibility == 'login',
                    and_(Drawing.visibility == 'private', Drawing.upload_user_id == current_user_id)
                )
            )
        else:
            # 普通用户：可以看到 public + login + 自己的 private
            print(f"[文件列表] 普通用户，显示 public+login+ 自己的 private 文件")
            query = query.filter(
                or_(
                    Drawing.visibility == 'public',
                    Drawing.visibility == 'login',
                    and_(Drawing.visibility == 'private', Drawing.upload_user_id == current_user_id)
                )
            )

        # 支持多个目录 ID 查询（包括当前目录及所有子目录）
        if category_ids:
            id_list = [int(id.strip()) for id in category_ids.split(',') if id.strip().isdigit()]
            if id_list:
                query = query.filter(Drawing.category_id.in_(id_list))
        elif category_id is not None:
            query = query.filter(Drawing.category_id == category_id)

        if file_type:
            query = query.filter(Drawing.file_type == file_type)

        if file_name:
            query = query.filter(Drawing.drawing_name.like(f'%{file_name}%'))

        if user_name:
            query = query.join(User, Drawing.upload_user_id == User.user_id)
            query = query.filter(User.username.like(f'%{user_name}%'))

        drawings = query.order_by(Drawing.upload_time.desc()).all()

        return jsonify({
            'drawings': [d.to_dict() for d in drawings]
        }), 200

    except Exception as e:
        return jsonify({'error': f'获取图纸列表失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings', methods=['POST'])
@token_required
def upload_drawing():
    """上传图纸"""
    try:
        # 获取表单数据
        drawing_code = request.form.get('drawing_code', '').strip()  # 可选字段
        drawing_name = request.form.get('drawing_name', '').strip()
        category_id = request.form.get('category_id', type=int)
        file = request.files.get('file')

        # 获取可见性参数
        visibility = request.form.get('visibility', 'login').strip()
        if visibility not in ['public', 'login', 'private']:
            visibility = 'login'

        if not drawing_name:
            return jsonify({'error': '图纸名称不能为空'}), 400

        if not category_id:
            return jsonify({'error': '请选择分类'}), 400

        if not file:
            return jsonify({'error': '请选择文件'}), 400

        # 检查文件类型
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        if file_ext not in ['pdf', 'doc', 'docx', 'xlsx', 'xls', 'ofd', 'ceb']:
            return jsonify({'error': '仅支持上传 PDF、Word、Excel、OFD、CEB 文件'}), 400

        # 读取文件内容
        file_blob = file.read()
        file_size = len(file_blob)

        # 检查图纸编号是否已存在（如果提供了编号）
        if drawing_code and Drawing.query.filter_by(drawing_code=drawing_code).first():
            return jsonify({'error': '图纸编号已存在'}), 400

        # 如果没有提供图纸编号，自动生成一个
        if not drawing_code:
            import time
            drawing_code = f"AUTO_{int(time.time())}"

        # 创建图纸记录
        from flask import request as req
        user_id = req.current_user['user_id']

        drawing = Drawing(
            drawing_code=drawing_code,
            drawing_name=drawing_name,
            file_type=file_ext,
            file_size=file_size,
            category_id=category_id,
            upload_user_id=user_id,
            file_blob=file_blob,
            visibility=visibility
        )

        db.session.add(drawing)
        db.session.commit()

        # 记录上传操作
        _log_operation(drawing.drawing_id, 'upload')

        return jsonify({
            'message': '上传成功',
            'drawing': drawing.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'上传失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>', methods=['GET'])
@token_required
def get_drawing(drawing_id):
    """获取图纸详情"""
    try:
        drawing = Drawing.query.get(drawing_id)

        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 记录预览操作
        _log_operation(drawing_id, 'preview')

        return jsonify({'drawing': drawing.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': f'获取图纸失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>/download', methods=['GET'])
@optional_token
def download_drawing(drawing_id):
    """下载图纸（支持未登录下载 public 文件）"""
    try:
        drawing = Drawing.query.get(drawing_id)

        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 权限检查
        from flask import request as req
        current_user = getattr(req, 'current_user', None)
        current_user_id = current_user['user_id'] if current_user else None
        is_admin = current_user and current_user.get('role') == 'admin' if current_user else False

        # 未登录只能下载 public 文件
        if not current_user and drawing.visibility != 'public':
            return jsonify({'error': '请先登录', 'need_login': True}), 401

        # 管理员和普通用户都可以下载 public/login 或自己的 private 文件
        if current_user:
            if drawing.visibility == 'private' and drawing.upload_user_id != current_user_id:
                return jsonify({'error': '无权限下载此文件'}), 403

        # 记录下载操作（仅登录用户）
        if current_user:
            _log_operation(drawing_id, 'download')

        # 返回文件
        file_stream = io.BytesIO(drawing.file_blob)

        # 对文件名进行 URL 编码，支持中文
        filename = f'{drawing.drawing_name}.{drawing.file_type}'
        encoded_filename = quote(filename)

        return Response(
            file_stream.read(),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except Exception as e:
        return jsonify({'error': f'下载失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>/kk-source', methods=['GET'])
@optional_token
def get_kk_source_file(drawing_id):
    """给 kkFileView 提供源文件流（支持 token query）"""
    try:
        drawing = Drawing.query.get(drawing_id)
        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        current_user = _get_current_user()
        allowed, msg, code = _can_preview_drawing(drawing, current_user)
        if not allowed:
            return jsonify({'error': msg}), code

        filename = request.args.get('fullfilename') or f"{drawing.drawing_name}.{drawing.file_type}"
        encoded_filename = quote(filename)

        file_stream = io.BytesIO(drawing.file_blob)
        return Response(
            file_stream.read(),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f"inline; filename*=UTF-8''{encoded_filename}",
                'Cache-Control': 'no-store'
            }
        )
    except Exception as e:
        return jsonify({'error': f'获取预览源文件失败：{str(e)}'}), 500


@drawing_bp.route('/api/kk/temp-file/<string:temp_token>', methods=['GET'])
def get_kk_temp_file(temp_token):
    """提供 kkFileView 临时文件访问（用于 CEB 转 PDF）"""
    _cleanup_expired_kk_temp_files()
    with _KK_TEMP_FILES_LOCK:
        file_meta = _KK_TEMP_FILES.get(temp_token)
        if not file_meta:
            return jsonify({'error': '预览链接已失效'}), 404
        file_path = file_meta.get('path')
        # 命中后续期，避免用户打开后立刻过期
        file_meta['expires_at'] = time.time() + _KK_TEMP_FILE_TTL_SECONDS

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': '预览文件不存在'}), 404

    filename = request.args.get('fullfilename', 'preview.pdf')
    encoded_filename = quote(filename)
    return send_file(
        file_path,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=encoded_filename
    )


@drawing_bp.route('/api/drawings/<int:drawing_id>/preview-url', methods=['GET'])
@optional_token
def get_kk_preview_url(drawing_id):
    """生成 kkFileView 预览链接（前端点击预览后打开独立子窗口）"""
    try:
        _cleanup_expired_kk_temp_files()

        drawing = Drawing.query.get(drawing_id)
        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        current_user = _get_current_user()
        allowed, msg, code = _can_preview_drawing(drawing, current_user)
        if not allowed:
            return jsonify({'error': msg}), code

        # 记录预览操作（仅登录用户）
        if current_user:
            _log_operation(drawing_id, 'preview')

        host_base = request.host_url.rstrip('/')
        origin_token = _extract_request_token()

        # 处理 CEB：先转 PDF，再走临时文件链接
        if drawing.file_type == 'ceb':
            from app.utils.ceb_converter import ceb_to_pdf

            pdf_blob = ceb_to_pdf(drawing.file_blob)
            if not pdf_blob:
                return jsonify({'error': 'CEB 转 PDF 失败'}), 500

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='kk_preview_')
            temp_file.write(pdf_blob)
            temp_file.close()

            temp_token = _register_kk_temp_file(temp_file.name)
            source_filename = f"{drawing.drawing_name}.pdf"
            source_url = (
                f"{host_base}/api/kk/temp-file/{temp_token}"
                f"?fullfilename={quote(source_filename, safe='')}"
            )
        else:
            source_filename = f"{drawing.drawing_name}.{drawing.file_type}"
            source_url = (
                f"{host_base}/api/drawings/{drawing_id}/kk-source"
                f"?fullfilename={quote(source_filename, safe='')}"
            )
            if origin_token:
                source_url += f"&token={quote(origin_token, safe='')}"

        encoded_source_url = base64.b64encode(source_url.encode('utf-8')).decode('utf-8')
        kk_preview_url = f"http://127.0.0.1:8012/onlinePreview?url={quote(encoded_source_url, safe='')}"

        return jsonify({
            'success': True,
            'preview_url': kk_preview_url
        }), 200
    except Exception as e:
        return jsonify({'error': f'生成预览链接失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>/preview', methods=['GET'])
@optional_token
def preview_drawing(drawing_id):
    """预览图纸（支持未登录预览 public 文件）"""
    try:
        drawing = Drawing.query.get(drawing_id)

        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 权限检查
        from flask import request as req
        current_user = getattr(req, 'current_user', None)
        current_user_id = int(current_user['user_id']) if current_user else None
        is_admin = current_user and current_user.get('role') == 'admin' if current_user else False

        # 未登录只能预览 public 文件
        if not current_user and drawing.visibility != 'public':
            return jsonify({'error': '请先登录', 'need_login': True}), 401

        # 所有用户（包括管理员）只能预览 public/login 或自己的 private 文件
        if current_user:
            if drawing.visibility == 'private' and drawing.upload_user_id != current_user_id:
                print(f"[预览权限检查] 拒绝访问：private 文件且不是上传者")
                return jsonify({'error': '无权限预览此文件'}), 403

        # 记录预览操作（仅登录用户）
        if current_user:
            _log_operation(drawing_id, 'preview')

        from app.utils.temp_cleanup import TempFileCleaner
        from app.utils.preview import PreviewManager

        # PDF 文件：直接返回
        if drawing.file_type == 'pdf':
            temp_file = PreviewManager.save_temp_file(drawing.file_blob, drawing.file_type)
            if not temp_file:
                return jsonify({'error': '保存临时文件失败'}), 500
            return send_file(temp_file, mimetype='application/pdf')

        # Word 文档：检查缓存或转换
        elif drawing.file_type in ['doc', 'docx']:
            # 检查是否有缓存的 PDF
            cached_pdf = TempFileCleaner.get_cached_pdf_path(drawing_id, drawing.file_blob)
            if cached_pdf:
                print(f"使用缓存的 PDF: {cached_pdf}")
                return send_file(cached_pdf, mimetype='application/pdf')

            # 没有缓存，进行转换
            print(f"开始转换 Word 文档：drawing_id={drawing_id}")

            # 保存 Word 临时文件
            temp_word_file = PreviewManager.save_temp_file(drawing.file_blob, drawing.file_type)
            if not temp_word_file:
                return jsonify({'error': '保存临时文件失败'}), 500

            try:
                # 转换为 PDF
                pdf_file = PreviewManager.convert_word_to_pdf(temp_word_file)

                if pdf_file and os.path.exists(pdf_file):
                    # 将转换后的 PDF 移动到缓存位置
                    temp_dir = tempfile.gettempdir()
                    cached_pdf_name = TempFileCleaner.get_temp_pdf_key(drawing_id, drawing.file_blob)
                    cached_pdf_path = os.path.join(temp_dir, cached_pdf_name)

                    # 重命名为缓存文件名
                    try:
                        if os.path.exists(cached_pdf_path):
                            os.remove(cached_pdf_path)
                        os.rename(pdf_file, cached_pdf_path)
                        print(f"PDF 已缓存：{cached_pdf_name}")
                        return send_file(cached_pdf_path, mimetype='application/pdf')
                    except Exception as e:
                        print(f"缓存 PDF 失败，使用临时文件：{e}")
                        return send_file(pdf_file, mimetype='application/pdf')
                else:
                    print("转换失败")
                    return jsonify({
                        'error': 'Word 转 PDF 失败。请确保已安装 Microsoft Word 并运行：pip install pywin32',
                        'need_convert': True,
                        'suggestions': [
                            '安装 pywin32: pip install pywin32',
                            '确保已安装 Microsoft Word'
                        ]
                    }), 400

            finally:
                # 清理临时 Word 文件
                if temp_word_file and os.path.exists(temp_word_file):
                    try:
                        os.remove(temp_word_file)
                    except:
                        pass

        return jsonify({'error': '不支持的文件类型'}), 400

    except Exception as e:
        import traceback
        print(f"预览异常：{str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'预览失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>', methods=['PUT'])
@token_required
def update_drawing(drawing_id):
    """更新图纸信息（修改目录）"""
    try:
        data = request.get_json()
        new_category_id = data.get('category_id')

        if not new_category_id:
            return jsonify({'error': '目录 ID 不能为空'}), 400

        drawing = Drawing.query.get(drawing_id)
        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 权限检查
        from flask import request as req
        user_id = int(req.current_user['user_id'])  # 确保是整数
        user_role = req.current_user.get('role', 'ordinary')

        # 调试信息
        print("=" * 50)
        print(f"[修改权限检查] 当前用户 ID: {user_id} (类型：{type(user_id).__name__}), 角色：{user_role}")
        print(f"[修改权限检查] 文件可见性：{drawing.visibility}, 上传者 ID: {drawing.upload_user_id} (类型：{type(drawing.upload_user_id).__name__})")
        print(f"[修改权限检查] 是自己的文件：{drawing.upload_user_id == user_id}")
        print("=" * 50)

        # 权限规则：
        # 1. 管理员可以修改 public/login 文件，以及自己的 private 文件
        # 2. 普通用户只能修改自己的文件（任何可见性）
        if user_role == 'admin':
            # 管理员：可以修改 public/login 文件，或自己的 private 文件
            if drawing.visibility == 'private' and drawing.upload_user_id != user_id:
                print(f"[修改权限检查] 拒绝：管理员不能修改其他人的 private 文件")
                return jsonify({'error': '管理员无权限修改此私密文件'}), 403
        else:
            # 普通用户：只能修改自己的文件
            if drawing.upload_user_id != user_id:
                print(f"[修改权限检查] 拒绝：普通用户不能修改他人的文件")
                return jsonify({'error': '无权限修改此文件'}), 403

        # 更新目录
        old_category_id = drawing.category_id
        drawing.category_id = new_category_id

        db.session.commit()

        # 记录操作
        _log_operation(drawing_id, 'modify')

        return jsonify({
            'message': '修改成功',
            'drawing': drawing.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'修改失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>', methods=['DELETE'])
@token_required
def delete_drawing(drawing_id):
    """删除图纸（软删除，移入回收站）"""
    try:
        drawing = Drawing.query.get(drawing_id)

        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 权限检查
        from flask import request as req
        user_id = int(req.current_user['user_id'])  # 确保是整数
        user_role = req.current_user.get('role', 'ordinary')

        # 调试信息
        print("=" * 50)
        print(f"[删除权限检查] 当前用户 ID: {user_id} (类型：{type(user_id).__name__}), 角色：{user_role}")
        print(f"[删除权限检查] 文件可见性：{drawing.visibility}, 上传者 ID: {drawing.upload_user_id} (类型：{type(drawing.upload_user_id).__name__})")
        print(f"[删除权限检查] 是自己的文件：{drawing.upload_user_id == user_id}")
        print("=" * 50)

        # 权限规则：
        # 1. 管理员可以删除 public/login 文件，以及自己的 private 文件
        # 2. 普通用户只能删除自己的文件（任何可见性）
        if user_role == 'admin':
            # 管理员：可以删除 public/login 文件，或自己的 private 文件
            if drawing.visibility == 'private' and drawing.upload_user_id != user_id:
                print(f"[删除权限检查] 拒绝：管理员不能删除其他人的 private 文件")
                return jsonify({'error': '管理员无权限删除此私密文件'}), 403
        else:
            # 普通用户：只能删除自己的文件
            if drawing.upload_user_id != user_id:
                print(f"[删除权限检查] 拒绝：普通用户不能删除他人的文件")
                return jsonify({'error': '无权限删除此文件'}), 403

        # 软删除：移入回收站
        drawing.is_deleted = True
        drawing.deleted_at = datetime.now()
        drawing.original_category_id = drawing.category_id

        db.session.commit()

        # 记录删除操作
        _log_operation(drawing_id, 'delete')

        return jsonify({'message': '文件已移至回收站'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败：{str(e)}'}), 500


def _log_operation(drawing_id, operation_type):
    """记录操作日志"""
    try:
        from flask import request as req
        user_id = req.current_user['user_id']

        log = OperationLog(
            drawing_id=drawing_id,
            user_id=user_id,
            operation_type=operation_type
        )
        db.session.add(log)
        db.session.commit()
    except:
        db.session.rollback()


def _log_user_operation(operation_type):
    """记录用户操作日志（不关联图纸）"""
    try:
        from flask import request as req
        user_id = req.current_user['user_id']

        log = OperationLog(
            drawing_id=None,
            user_id=user_id,
            operation_type=operation_type
        )
        db.session.add(log)
        db.session.commit()
    except:
        db.session.rollback()


@drawing_bp.route('/api/drawings/<int:drawing_id>/preview-images', methods=['GET'])
@optional_token
def get_preview_images(drawing_id):
    """获取图纸的图片预览（将 PDF/Word/Excel/OFD/CEB 转换为图片）"""
    try:
        drawing = Drawing.query.get(drawing_id)

        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 权限检查
        from flask import request as req
        current_user = getattr(req, 'current_user', None)
        current_user_id = int(current_user['user_id']) if current_user else None
        is_admin = current_user and current_user.get('role') == 'admin' if current_user else False

        # 未登录只能预览 public 文件
        if not current_user and drawing.visibility != 'public':
            return jsonify({'error': '请先登录', 'need_login': True}), 401

        # 检查访问权限
        if current_user:
            if drawing.visibility == 'private' and drawing.upload_user_id != current_user_id:
                return jsonify({'error': '无权限预览此文件'}), 403

        # 记录预览操作（仅登录用户）
        if current_user:
            _log_operation(drawing_id, 'preview')

        # 导入图片转换工具和缓存
        from app.utils.image_preview import pdf_to_images, pdf_page_count, pdf_to_image_page
        from app.utils.preview_cache import get_preview_cache
        from app.utils.temp_cleanup import TempFileCleaner

        lazy_mode = request.args.get('lazy', '0') == '1'
        meta_only = request.args.get('meta', '0') == '1'
        page = request.args.get('page', type=int)
        dpi = request.args.get('dpi', default=150, type=int)
        dpi = max(72, min(dpi, 220))

        def _respond_pdf_images(pdf_blob, cache_prefix):
            cache = get_preview_cache()
            meta_key = f"{cache_prefix}_meta_dpi{dpi}"

            if lazy_mode or meta_only or page is not None:
                page_count = cache.get(meta_key)
                if not page_count:
                    page_count = pdf_page_count(pdf_blob)
                    cache.set(meta_key, page_count)

                if page_count <= 0:
                    return jsonify({'error': 'PDF 转图片失败'}), 500

                if meta_only or page is None:
                    return jsonify({
                        'success': True,
                        'lazy': True,
                        'page_count': page_count,
                        'file_name': drawing.drawing_name
                    }), 200

                if page < 1 or page > page_count:
                    return jsonify({'error': '页码超出范围', 'page_count': page_count}), 400

                page_key = f"{cache_prefix}_page_{page}_dpi{dpi}"
                image = cache.get(page_key)
                if not image:
                    image = pdf_to_image_page(pdf_blob, page=page, dpi=dpi, use_webp=True, webp_quality=80)
                    if not image:
                        return jsonify({'error': '页面渲染失败'}), 500
                    cache.set(page_key, image)

                return jsonify({
                    'success': True,
                    'lazy': True,
                    'page': page,
                    'page_count': page_count,
                    'image': image,
                    'images': [image],
                    'file_name': drawing.drawing_name
                }), 200

            # 兼容旧模式：一次返回全部页
            cache_key = f"{cache_prefix}_all_dpi{dpi}"
            cached_images = cache.get(cache_key)
            if cached_images:
                print(f"[图片预览] 使用缓存：drawing_id={drawing_id}")
                return jsonify({
                    'success': True,
                    'images': cached_images,
                    'page_count': len(cached_images),
                    'file_name': drawing.drawing_name
                }), 200

            images = pdf_to_images(pdf_blob, dpi=dpi, use_webp=True, webp_quality=80)
            if not images:
                return jsonify({'error': 'PDF 转图片失败'}), 500
            cache.set(cache_key, images)
            print(f"[图片预览] 已缓存：drawing_id={drawing_id}, 页数={len(images)}")
            return jsonify({
                'success': True,
                'images': images,
                'page_count': len(images),
                'file_name': drawing.drawing_name
            }), 200

        # PDF 文件：使用 PyMuPDF 转换为图片
        if drawing.file_type == 'pdf':
            return _respond_pdf_images(drawing.file_blob, f"preview_images_{drawing_id}_pdf")

        # Word 文档：先转换为 PDF，再转换为图片
        elif drawing.file_type in ['doc', 'docx']:
            # 检查是否有缓存的 PDF
            cached_pdf = TempFileCleaner.get_cached_pdf_path(drawing_id, drawing.file_blob)
            pdf_blob = None

            if cached_pdf and os.path.exists(cached_pdf):
                # 使用缓存的 PDF
                with open(cached_pdf, 'rb') as f:
                    pdf_blob = f.read()
            else:
                # 没有缓存，进行转换
                from app.utils.preview import PreviewManager

                temp_word_file = PreviewManager.save_temp_file(drawing.file_blob, drawing.file_type)
                if not temp_word_file:
                    return jsonify({'error': '保存临时文件失败'}), 500

                pdf_file = PreviewManager.convert_word_to_pdf(temp_word_file)

                if pdf_file and os.path.exists(pdf_file):
                    # 将转换后的 PDF 移动到缓存位置
                    temp_dir = tempfile.gettempdir()
                    cached_pdf_name = TempFileCleaner.get_temp_pdf_key(drawing_id, drawing.file_blob)
                    cached_pdf_path = os.path.join(temp_dir, cached_pdf_name)

                    try:
                        if os.path.exists(cached_pdf_path):
                            os.remove(cached_pdf_path)
                        os.rename(pdf_file, cached_pdf_path)

                        with open(cached_pdf_path, 'rb') as f:
                            pdf_blob = f.read()
                    except:
                        pass

            if pdf_blob:
                return _respond_pdf_images(pdf_blob, f"preview_images_{drawing_id}_doc")

            return jsonify({'error': 'Word 文档转换失败'}), 500

        # Excel 文档：先转换为 PDF，再转换为图片
        elif drawing.file_type in ['xlsx', 'xls']:
            # 检查是否有缓存的 PDF
            cached_pdf = TempFileCleaner.get_cached_pdf_path(drawing_id, drawing.file_blob)
            pdf_blob = None

            if cached_pdf and os.path.exists(cached_pdf):
                # 使用缓存的 PDF
                with open(cached_pdf, 'rb') as f:
                    pdf_blob = f.read()
            else:
                # 没有缓存，进行转换
                from app.utils.excel_converter import excel_to_pdf

                pdf_blob = excel_to_pdf(drawing.file_blob)

                if pdf_blob:
                    # 将转换后的 PDF 保存到缓存
                    temp_dir = tempfile.gettempdir()
                    cached_pdf_name = TempFileCleaner.get_temp_pdf_key(drawing_id, drawing.file_blob)
                    cached_pdf_path = os.path.join(temp_dir, cached_pdf_name)

                    try:
                        with open(cached_pdf_path, 'wb') as f:
                            f.write(pdf_blob)
                    except:
                        pass

            if pdf_blob:
                return _respond_pdf_images(pdf_blob, f"preview_images_{drawing_id}_excel")

            return jsonify({'error': 'Excel 文档转换失败，请确保系统已安装 Microsoft Excel'}), 500

        # OFD 文档：先转换为 PDF，再转换为图片
        elif drawing.file_type == 'ofd':
            # 导入转换工具
            from app.utils.ofd_converter import ofd_to_pdf
            from app.utils.temp_cleanup import TempFileCleaner

            # 检查是否有缓存的 PDF
            cached_pdf = TempFileCleaner.get_cached_pdf_path(drawing_id, drawing.file_blob)
            pdf_blob = None

            if cached_pdf and os.path.exists(cached_pdf):
                # 使用缓存的 PDF
                with open(cached_pdf, 'rb') as f:
                    pdf_blob = f.read()
            else:
                # 没有缓存，进行转换
                pdf_blob = ofd_to_pdf(drawing.file_blob)

                if pdf_blob:
                    # 将转换后的 PDF 保存到缓存
                    temp_dir = tempfile.gettempdir()
                    cached_pdf_name = TempFileCleaner.get_temp_pdf_key(drawing_id, drawing.file_blob)
                    cached_pdf_path = os.path.join(temp_dir, cached_pdf_name)

                    try:
                        with open(cached_pdf_path, 'wb') as f:
                            f.write(pdf_blob)
                    except:
                        pass

            if pdf_blob:
                return _respond_pdf_images(pdf_blob, f"preview_images_{drawing_id}_ofd")

            # OFD 转换失败
            return jsonify({
                'error': 'OFD_CONVERT_FAILED',
                'message': 'OFD 文件转换失败。该文件可能是较新版本的 OFD 格式，请下载后使用专业阅读器查看。',
                'error_type': 'ofd_convert_failed',
                'file_name': drawing.drawing_name,
                'drawing_id': drawing_id
            }), 500

        # CEB 文档：先转换为 PDF，再转换为图片
        elif drawing.file_type == 'ceb':
            # 导入转换工具
            from app.utils.ceb_converter import ceb_to_pdf
            from app.utils.temp_cleanup import TempFileCleaner

            # 检查是否有缓存的 PDF
            cached_pdf = TempFileCleaner.get_cached_pdf_path(drawing_id, drawing.file_blob)
            pdf_blob = None

            if cached_pdf and os.path.exists(cached_pdf):
                # 使用缓存的 PDF
                with open(cached_pdf, 'rb') as f:
                    pdf_blob = f.read()
            else:
                # 没有缓存，进行转换
                pdf_blob = ceb_to_pdf(drawing.file_blob)

                if pdf_blob:
                    # 将转换后的 PDF 保存到缓存
                    temp_dir = tempfile.gettempdir()
                    cached_pdf_name = TempFileCleaner.get_temp_pdf_key(drawing_id, drawing.file_blob)
                    cached_pdf_path = os.path.join(temp_dir, cached_pdf_name)

                    try:
                        with open(cached_pdf_path, 'wb') as f:
                            f.write(pdf_blob)
                    except:
                        pass

            if pdf_blob:
                return _respond_pdf_images(pdf_blob, f"preview_images_{drawing_id}_ceb")

            return jsonify({'error': 'CEB 文档转换失败，请确保 tools/ceb2Pdf.exe 存在'}), 500

        else:
            return jsonify({'error': '不支持的文件类型'}), 400

    except Exception as e:
        print(f"获取预览图片失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'获取预览图片失败：{str(e)}'}), 500


@drawing_bp.route('/api/drawings/<int:drawing_id>/preview-html', methods=['GET'])
@optional_token
def preview_drawing_html(drawing_id):
    """获取 Word/Excel/PDF 文件的 HTML 预览"""
    try:
        drawing = Drawing.query.get(drawing_id)

        if not drawing:
            return jsonify({'error': '图纸不存在'}), 404

        # 支持 Word、Excel 和 PDF 文件
        if drawing.file_type not in ['doc', 'docx', 'xlsx', 'xls', 'pdf']:
            return jsonify({'error': '仅支持 Word/Excel/PDF 文件的 HTML 预览'}), 400

        # 权限检查
        from flask import request as req
        current_user = getattr(req, 'current_user', None)
        current_user_id = int(current_user['user_id']) if current_user else None
        is_admin = current_user and current_user.get('role') == 'admin' if current_user else False

        # 未登录只能预览 public 文件
        if not current_user and drawing.visibility != 'public':
            return jsonify({'error': '请先登录', 'need_login': True}), 401

        # 检查访问权限
        if current_user:
            if drawing.visibility == 'private' and drawing.upload_user_id != current_user_id:
                return jsonify({'error': '无权限预览此文件'}), 403

        # 记录预览操作（仅登录用户）
        if current_user:
            _log_operation(drawing_id, 'preview')

        # 导入转换工具和缓存
        from app.utils.poi_converter import word_to_html, excel_to_html, pdf_to_html, check_poi_converter_available
        from app.utils.preview_cache import get_preview_cache
        from app.utils.excel_to_html import DEFAULT_MAX_ROWS, DEFAULT_MAX_COLS

        def _safe_int(value, default_value, min_value=1, max_value=20000):
            try:
                parsed = int(value)
                return min(max(parsed, min_value), max_value)
            except (TypeError, ValueError):
                return default_value

        requested_full = request.args.get('full', '0') == '1'
        default_rows = 5000 if requested_full else DEFAULT_MAX_ROWS
        default_cols = 300 if requested_full else DEFAULT_MAX_COLS
        excel_max_rows = _safe_int(request.args.get('max_rows'), default_rows)
        excel_max_cols = _safe_int(request.args.get('max_cols'), default_cols)

        # 先确定转换链路，避免缓存命中到错误版本
        use_poi = check_poi_converter_available()

        # 检查缓存
        cache = get_preview_cache()
        if drawing.file_type in ['xlsx', 'xls']:
            excel_render_mode = 'poi' if use_poi else 'openpyxl'
            cache_key = f"preview_html_{drawing_id}_{drawing.file_type}_{excel_render_mode}_{excel_max_rows}_{excel_max_cols}"
        else:
            cache_key = f"preview_html_{drawing_id}_{drawing.file_type}_{'poi' if use_poi else 'native'}"
        cached_html = cache.get(cache_key)
        if cached_html:
            print(f"[HTML 预览] 使用缓存：drawing_id={drawing_id}")
            return Response(
                cached_html,
                mimetype='text/html',
                headers={'Cache-Control': 'max-age=3600'}
            )

        # 未命中缓存，进行转换
        html_content = None

        if drawing.file_type in ['doc', 'docx']:
            # Word 文档
            if use_poi:
                print(f"[HTML 预览] 使用 POI JAR 转换 Word: drawing_id={drawing_id}")
                # 传入原始文件名用于 HTML 标题
                original_filename = drawing.drawing_name
                html_content = word_to_html(drawing.file_blob, original_filename=original_filename)
            else:
                return jsonify({
                    'error': 'Word 文档需要 POI Converter，请配置 poi-converter.jar',
                    'need_install': True
                }), 500

        elif drawing.file_type in ['xlsx', 'xls']:
            # Excel 文档
            if use_poi:
                print(f"[HTML 预览] 使用 POI JAR 转换 Excel: drawing_id={drawing_id}")
                # 传入原始文件名用于 HTML 标题
                original_filename = drawing.drawing_name
                html_content = excel_to_html(drawing.file_blob, original_filename=original_filename)
            else:
                print(f"[HTML 预览] POI 不可用，使用 openpyxl: drawing_id={drawing_id}")
                # 备用方案：使用 openpyxl
                from app.utils.excel_to_html import excel_to_html as excel_to_html_openpyxl
                result = excel_to_html_openpyxl(
                    drawing.file_blob,
                    max_rows=excel_max_rows,
                    max_cols=excel_max_cols
                )
                if result:
                    html_content = result['html']

        elif drawing.file_type == 'pdf':
            # PDF 文档
            if use_poi:
                print(f"[HTML 预览] 使用 POI JAR 转换 PDF: drawing_id={drawing_id}")
                html_content = pdf_to_html(drawing.file_blob)
            else:
                return jsonify({
                    'error': 'PDF 文档需要 POI Converter，请配置 poi-converter.jar',
                    'need_install': True
                }), 500

        if not html_content:
            return jsonify({
                'error': '文档转 HTML 失败',
                'need_install': not use_poi
            }), 500

        # 保存到缓存
        cache.set(cache_key, html_content)
        print(f"[HTML 预览] 已缓存：drawing_id={drawing_id}")

        # 返回 HTML 内容
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Cache-Control': 'max-age=3600',  # 缓存 1 小时
            }
        )

    except Exception as e:
        print(f"获取 HTML 预览失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'获取 HTML 预览失败：{str(e)}'}), 500
