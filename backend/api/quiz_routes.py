from flask import Blueprint, request, jsonify, current_app, session
from api.auth_routes import login_required
from services.database import get_db_connection
import json

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/generate', methods=['POST'])
@login_required
def generate_quiz():
    """生成测评题目"""
    try:
        data = request.json
        document_ids = data.get('document_ids', [])
        quiz_type = data.get('quiz_type', 'mixed')
        num_questions = data.get('num_questions', 10)
        
        if not document_ids:
            return jsonify({'error': '请选择至少一个文档'}), 400
        
        # 验证文档属于当前用户
        db_path = current_app.config['DATABASE_PATH']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(document_ids))
        cursor.execute(f'SELECT id FROM documents WHERE id IN ({placeholders}) AND user_id = ?', 
                     (*document_ids, session['user_id']))
        owned_docs = [row['id'] for row in cursor.fetchall()]
        conn.close()
        
        if len(owned_docs) != len(document_ids):
            return jsonify({'error': '无权访问部分文档'}), 403
        
        # 从ChromaDB检索内容
        if not current_app.chromadb_service:
            return jsonify({'error': '知识库未就绪'}), 503
        
        contents = []
        for doc_id in document_ids:
            chunks = current_app.chromadb_service.get_document_chunks(doc_id)
            contents.extend([c['content'] for c in chunks[:10]])
        
        # 生成题目
        from services.quiz_service import QuizService
        quiz_service = QuizService(current_app)
        questions = quiz_service.generate_questions(contents, quiz_type, num_questions)
        
        return jsonify({'questions': questions, 'quiz_type': quiz_type}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quiz_bp.route('/submit', methods=['POST'])
@login_required
def submit_quiz():
    """提交测评答案"""
    try:
        data = request.json
        document_ids = data.get('document_ids', [])
        quiz_type = data.get('quiz_type', 'mixed')
        answers = data.get('answers', [])
        time_spent = data.get('time_spent', 0)
        
        if not answers:
            return jsonify({'error': '没有答案数据'}), 400
        
        # 评判答案
        from services.quiz_service import QuizService
        quiz_service = QuizService(current_app)
        result = quiz_service.grade_quiz(answers)
        
        # 记录测评结果
        db_path = current_app.config['DATABASE_PATH']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # 可以为多个文档创建记录，这里简化为第一个文档
        doc_id = document_ids[0] if document_ids else None
        
        cursor.execute(
            '''INSERT INTO quiz_records 
               (user_id, document_id, quiz_type, total_questions, correct_count, score, time_spent) 
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], doc_id, quiz_type, len(answers), 
             result['correct_count'], result['score'], time_spent)
        )
        quiz_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'quiz_id': quiz_id, **result}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quiz_bp.route('/history', methods=['GET'])
@login_required
def get_quiz_history():
    """获取测评历史（仅当前用户）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT qr.*, d.filename 
            FROM quiz_records qr
            LEFT JOIN documents d ON qr.document_id = d.id
            WHERE qr.user_id = ?
            ORDER BY qr.created_at DESC 
            LIMIT 50
        ''', (session['user_id'],))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'id': row['id'],
                'document_name': row['filename'],
                'quiz_type': row['quiz_type'],
                'total_questions': row['total_questions'],
                'correct_count': row['correct_count'],
                'score': row['score'],
                'time_spent': row['time_spent'],
                'created_at': row['created_at']
            })
        
        return jsonify({'history': history}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quiz_bp.route('/<int:quiz_id>/review', methods=['GET'])
@login_required
def review_quiz(quiz_id):
    """查看测评详情"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM quiz_records WHERE id = ? AND user_id = ?', 
                      (quiz_id, session['user_id']))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': '测评记录不存在或无权限'}), 404
        
        return jsonify({
            'id': row['id'],
            'document_id': row['document_id'],
            'quiz_type': row['quiz_type'],
            'total_questions': row['total_questions'],
            'correct_count': row['correct_count'],
            'score': row['score'],
            'time_spent': row['time_spent'],
            'created_at': row['created_at']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
