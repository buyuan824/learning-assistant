from flask import Blueprint, request, jsonify, current_app, session
import os
import threading
from api.auth_routes import login_required
from services.database import get_db_connection
from services.document_parser import DocumentParser
from services.text_chunker import TextChunker

document_bp = Blueprint('document', __name__)

@document_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """上传文档API - 支持持续上传"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in ['pdf', 'pptx', 'md', 'txt']:
            return jsonify({'error': f'不支持的文件类型: {file_ext}'}), 400
        
        db_path = current_app.config['DATABASE_PATH']
        upload_folder = current_app.config['UPLOAD_FOLDER']
        user_id = session['user_id']
        
        # 写入数据库
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO documents (user_id, filename, file_type, file_size, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, filename, file_ext, 0, 'processing')
        )
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 保存文件到磁盘
        file_path = os.path.join(upload_folder, f"{doc_id}_{filename}")
        file.save(file_path)
        
        # 更新文件大小
        file_size = os.path.getsize(file_path)
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', (file_size, doc_id))
        conn.commit()
        conn.close()
        
        # 保存app引用（后台线程需要）
        app_instance = current_app._get_current_object()
        
        # 异步解析文档
        def process_document():
            with app_instance.app_context():
                try:
                    text = DocumentParser.parse_file(file_path, file_ext)
                    chunks = TextChunker.chunk_by_sentences(text, max_chunk_size=500)
                    
                    # 等待ChromaDB就绪
                    import time
                    retry = 0
                    svc = app_instance.chromadb_service
                    while svc is None and retry < 30:
                        time.sleep(1)
                        svc = app_instance.chromadb_service
                        retry += 1
                    
                    if svc is None:
                        raise Exception("ChromaDB服务未就绪")
                    
                    chunk_count = svc.add_documents(doc_id, chunks)
                    
                    conn = get_db_connection(db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE documents SET status = ?, chunk_count = ? WHERE id = ?',
                        ('ready', chunk_count, doc_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    print(f"[OK] Document {doc_id} processed: {chunk_count} chunks")
                    
                except Exception as e:
                    print(f"[ERROR] Document {doc_id} processing failed: {str(e)}")
                    conn = get_db_connection(db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE documents SET status = ?, error_message = ? WHERE id = ?',
                        ('error', str(e)[:500], doc_id)
                    )
                    conn.commit()
                    conn.close()
        
        thread = threading.Thread(target=process_document)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': '文件上传成功，正在解析中',
            'doc_id': doc_id,
            'filename': filename,
            'status': 'processing'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@document_bp.route('/', methods=['GET'])
@login_required
def list_documents():
    """获取文档列表（仅当前用户）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        user_id = session['user_id']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM documents WHERE user_id = ? ORDER BY upload_time DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            documents.append({
                'id': row['id'],
                'filename': row['filename'],
                'file_type': row['file_type'],
                'file_size': row['file_size'],
                'upload_time': row['upload_time'],
                'status': row['status'],
                'chunk_count': row['chunk_count'],
                'error_message': row['error_message']
            })
        
        return jsonify({'documents': documents}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@document_bp.route('/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_document(doc_id):
    """删除文档（仅本人）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        user_id = session['user_id']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT filename FROM documents WHERE id = ? AND user_id = ?', (doc_id, user_id))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': '文档不存在或无权限'}), 404
        
        filename = row['filename']
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{doc_id}_{filename}")
        
        # 删除文件
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 从ChromaDB删除
        if current_app.chromadb_service:
            current_app.chromadb_service.delete_document(doc_id)
        
        # 从数据库删除
        cursor.execute('DELETE FROM documents WHERE id = ? AND user_id = ?', (doc_id, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'message': '文档删除成功'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@document_bp.route('/<int:doc_id>/status', methods=['GET'])
@login_required
def get_document_status(doc_id):
    """获取单个文档状态（仅本人）"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        user_id = session['user_id']
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, status, chunk_count, error_message FROM documents WHERE id = ? AND user_id = ?', (doc_id, user_id))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': '文档不存在或无权限'}), 404
        
        return jsonify({
            'id': row['id'],
            'status': row['status'],
            'chunk_count': row['chunk_count'],
            'error_message': row['error_message']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
