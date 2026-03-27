"""
Flask应用初始化
"""
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from config.config import config
import os
import sys
import mimetypes


def get_frontend_dist_path():
    """获取前端打包文件路径（支持开发环境和打包环境）"""
    # 检查是否在打包环境中运行
    if getattr(sys, 'frozen', False):
        # 打包环境：前端文件相对于可执行文件目录
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, 'frontend', 'dist')
    else:
        # 开发环境：前端文件相对于项目根目录
        # backend/app/__init__.py 向上三级到达项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(project_root, 'frontend', 'dist')


def create_app(config_name='default'):
    """创建Flask应用"""
    # 设置静态文件夹和模板文件夹路径（支持开发和打包环境）
    if getattr(sys, 'frozen', False):
        # 打包环境：static 和 templates 在可执行文件目录下
        exe_dir = os.path.dirname(sys.executable)
        static_folder = os.path.join(exe_dir, 'static')
        if not os.path.exists(static_folder):
            # 兜底：部分打包结构会把资源放在 backend/static
            fallback_static = os.path.join(exe_dir, 'backend', 'static')
            if os.path.exists(fallback_static):
                static_folder = fallback_static
        template_folder = os.path.join(exe_dir, 'templates')
    else:
        # 开发环境：static 和 templates 在 backend 目录下
        static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')

    app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)

    # 加载配置
    app.config.from_object(config[config_name])

    # 启用CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # 初始化数据库
    from app.models.models import db
    db.init_app(app)

    # 注册蓝图
    from app.routes.auth import auth_bp
    from app.routes.category import category_bp
    from app.routes.drawing import drawing_bp
    from app.routes.operation_log import operation_log_bp
    from app.routes.recycle_bin import recycle_bin_bp
    from app.routes.user import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(drawing_bp)
    app.register_blueprint(operation_log_bp)
    app.register_blueprint(recycle_bin_bp)
    app.register_blueprint(user_bp)

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '资源不存在'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '服务器内部错误'}), 500

    # 健康检查
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'}), 200

    @app.route('/assets/pdfjs/<path:filename>')
    def pdfjs_assets(filename):
        """独立的 PDF.js 资源路由，避免被 SPA 路由回退干扰"""
        from flask import send_from_directory

        candidates = [
            os.path.join(static_folder, 'pdfjs'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'pdfjs'),
        ]

        for folder in candidates:
            file_path = os.path.join(folder, filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mimetype, _ = mimetypes.guess_type(file_path)
                return send_from_directory(folder, filename, mimetype=mimetype)

        return jsonify({'error': 'PDF.js 资源不存在'}), 404

    # PDF 查看器（用于 PyQt 桌面应用）
    @app.route('/pdf/viewer')
    def pdf_viewer():
        """PDF 查看器页面"""
        pdf_url = request.args.get('url', '')
        return render_template('pdf_viewer.html', pdf_url=pdf_url)

    # 托管前端静态文件（桌面应用模式）
    @app.route('/')
    def index():
        from flask import send_from_directory
        try:
            frontend_dist = get_frontend_dist_path()
            if os.path.exists(frontend_dist):
                return send_from_directory(frontend_dist, 'index.html')
            else:
                # 开发模式，返回提示信息
                return '''
                <html>
                <head><title>文件管理系统</title></head>
                <body>
                    <h1>文件管理系统 - 后端运行中</h1>
                    <p>前端未打包，请先运行 <code>cd frontend && npm run build</code></p>
                    <p>或者直接访问开发服务器：<a href="http://localhost:5173">http://localhost:5173</a></p>
                </body>
                </html>
                '''
        except Exception as e:
            return f'Error: {str(e)}', 500

    @app.route('/<path:path>')
    def serve_static(path):
        from flask import send_from_directory
        frontend_dist = get_frontend_dist_path()
        if os.path.exists(frontend_dist):
            # API 路径不做前端回退，保留后端 404 语义
            if path.startswith('api/') or path.startswith('static/'):
                return jsonify({'error': '资源不存在'}), 404

            target = os.path.join(frontend_dist, path)
            if os.path.exists(target) and os.path.isfile(target):
                return send_from_directory(frontend_dist, path)

            # SPA History 路由回退（如 /preview-window/:id）
            return send_from_directory(frontend_dist, 'index.html')
        return f'File not found: {path}', 404

    # 创建数据库表
    with app.app_context():
        # 确保数据库目录存在
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database')
        os.makedirs(db_path, exist_ok=True)

        db.create_all()

        # 创建默认管理员账号（如果不存在）
        from app.models.models import User
        from app.utils.auth import hash_password

        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                password=hash_password('admin123'),
                phone='13800138000',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print('Default admin account created - Username: admin, Password: admin123, Phone: 13800138000')

    # 启动临时文件清理器
    from app.utils.temp_cleanup import cleaner
    cleaner.start()

    return app
