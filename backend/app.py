from flask import Flask, send_from_directory, jsonify, session
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    
    # Session配置
    app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLY_APP_NAME') is not None  # 生产环境用HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    
    # 基于环境变量或默认值计算路径
    # Fly.io 使用 /data 作为持久化卷挂载点
    data_dir = os.getenv('DATA_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'))
    
    # 配置
    app.config['UPLOAD_FOLDER'] = os.path.join(data_dir, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
    app.config['DATABASE_PATH'] = os.path.join(data_dir, 'db', 'learning.db')
    app.config['CHROMADB_PATH'] = os.path.join(data_dir, 'chromadb')
    app.config['DATA_DIR'] = data_dir
    app.config['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY', '')
    
    # 启用CORS - 生产环境应限制来源
    cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS(app, supports_credentials=True, origins=cors_origins)
    
    # 确保目录存在
    for d in [app.config['UPLOAD_FOLDER'], 
              os.path.dirname(app.config['DATABASE_PATH']),
              app.config['CHROMADB_PATH']]:
        os.makedirs(d, exist_ok=True)
    
    # 初始化数据库
    from services.database import init_db, migrate_db
    init_db(app.config['DATABASE_PATH'])
    migrate_db(app.config['DATABASE_PATH'])
    
    # 延迟初始化ChromaDB（避免启动时加载模型太慢）
    app.chromadb_service = None
    
    # 注册蓝图
    from api.auth_routes import bp as auth_bp
    from api.document_routes import document_bp
    from api.query_routes import query_bp
    from api.quiz_routes import quiz_bp
    from api.progress_routes import progress_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(document_bp, url_prefix='/api/documents')
    app.register_blueprint(query_bp, url_prefix='/api/query')
    app.register_blueprint(quiz_bp, url_prefix='/api/quiz')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    
    # 获取ChromaDB服务（懒加载）
    @app.before_request
    def init_chromadb():
        if app.chromadb_service is None:
            from services.chromadb_service import ChromaDBService
            app.chromadb_service = ChromaDBService(app.config['CHROMADB_PATH'])
    
    # 前端路由
    @app.route('/')
def index():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(os.path.join(base_dir, 'frontend'), 'index.html')

@app.route('/<path:path>')
def static_files(path):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(os.path.join(base_dir, 'frontend'), path)

    
    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'ok', 
            'message': 'Learning Assistant API is running',
            'chromadb_ready': app.chromadb_service is not None,
            'api_key_set': bool(app.config['DEEPSEEK_API_KEY'])
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
