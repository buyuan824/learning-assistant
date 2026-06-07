import hashlib
from flask import Blueprint, request, jsonify, session, current_app
from functools import wraps
from services.database import get_db_connection, init_db

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def hash_password(password):
    """简单密码哈希（生产环境应使用bcrypt）"""
    return hashlib.sha256(password.encode()).hexdigest()

@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        if len(password) < 6:
            return jsonify({'error': '密码长度至少6位'}), 400
        
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': '用户名已存在'}), 400
        
        # 创建用户
        password_hash = hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 自动登录
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            'message': '注册成功',
            'user': {'id': user_id, 'username': username}
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            'SELECT id, username FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 设置session
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        return jsonify({
            'message': '登录成功',
            'user': {'id': user['id'], 'username': user['username']}
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'message': '已登出'}), 200

@bp.route('/me', methods=['GET'])
def get_current_user():
    """获取当前登录用户"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 200
    
    return jsonify({
        'authenticated': True,
        'user': {
            'id': session['user_id'],
            'username': session['username']
        }
    }), 200

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录', 'code': 'UNAUTHENTICATED'}), 401
        return f(*args, **kwargs)
    return decorated_function
