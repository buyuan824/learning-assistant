from flask import Blueprint, request, jsonify, current_app, session
from api.auth_routes import login_required
from services.rag_service import RAGService
from services.database import get_db_connection

query_bp = Blueprint('query', __name__)

@query_bp.route('/ask', methods=['POST'])
@login_required
def ask_question():
    """智能问答API"""
    try:
        data = request.json
        question = data.get('question')
        document_ids = data.get('document_ids', [])
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        
        if not current_app.chromadb_service:
            return jsonify({'error': '知识库未就绪，请先上传文档'}), 503
        
        # 如果指定了文档，验证这些文档属于当前用户
        if document_ids:
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
        
        rag_service = RAGService(current_app)
        result = rag_service.query(question, document_ids if document_ids else None)
        
        # 记录查询日志
        db_path = current_app.config['DATABASE_PATH']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO query_logs (user_id, question, answer, document_ids, confidence) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], question, result['answer'], str(document_ids), result.get('confidence', 0))
        )
        conn.commit()
        conn.close()
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@query_bp.route('/history', methods=['GET'])
@login_required
def get_query_history():
    """获取问答历史（仅当前用户）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM query_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', (session['user_id'],))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'id': row['id'],
                'question': row['question'],
                'answer': row['answer'],
                'document_ids': row['document_ids'],
                'confidence': row['confidence'],
                'created_at': row['created_at']
            })
        
        return jsonify({'history': history}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
