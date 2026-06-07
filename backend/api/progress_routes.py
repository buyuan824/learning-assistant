from flask import Blueprint, request, jsonify, current_app, session
from api.auth_routes import login_required
from services.database import get_db_connection

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/stats', methods=['GET'])
@login_required
def get_progress_stats():
    """获取学习进度统计（仅当前用户）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        user_id = session['user_id']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # 问答次数
        cursor.execute('SELECT COUNT(*) as count FROM query_logs WHERE user_id = ?', (user_id,))
        query_count = cursor.fetchone()['count']
        
        # 测评次数和平均分
        cursor.execute('''
            SELECT COUNT(*) as count, AVG(score) as avg_score 
            FROM quiz_records 
            WHERE user_id = ?
        ''', (user_id,))
        quiz_row = cursor.fetchone()
        quiz_count = quiz_row['count']
        avg_score = quiz_row['avg_score'] or 0
        
        # 文档数量
        cursor.execute('SELECT COUNT(*) as count FROM documents WHERE user_id = ?', (user_id,))
        doc_count = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'query_count': query_count,
            'quiz_count': quiz_count,
            'avg_score': round(avg_score, 2),
            'doc_count': doc_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/mastery', methods=['GET'])
@login_required
def get_knowledge_mastery():
    """获取知识点掌握度（仅当前用户）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        user_id = session['user_id']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT point_name, mastery_score 
            FROM knowledge_points 
            WHERE user_id = ?
            ORDER BY mastery_score DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        mastery = []
        for row in rows:
            mastery.append({
                'point_name': row['point_name'],
                'mastery_score': row['mastery_score']
            })
        
        return jsonify({'mastery': mastery}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/quiz_trend', methods=['GET'])
@login_required
def get_quiz_trend():
    """获取测评趋势（仅当前用户）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        user_id = session['user_id']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT score, created_at 
            FROM quiz_records 
            WHERE user_id = ?
            ORDER BY created_at ASC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        trend = []
        for row in rows:
            trend.append({
                'score': row['score'],
                'created_at': row['created_at']
            })
        
        return jsonify({'trend': trend}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
