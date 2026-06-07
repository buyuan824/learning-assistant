import chromadb
from chromadb.config import Settings
from services.embedding import OfflineHashEmbedding

class ChromaDBService:
    def __init__(self, persist_directory):
        self.persist_directory = persist_directory
        
        # 使用离线 embedding 函数（不依赖网络）
        self.embedding_function = OfflineHashEmbedding()
        
        # 创建 ChromaDB 客户端（不依赖网络）
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                allow_reset=False,
                anonymized_telemetry=False  # 禁用遥测（避免网络请求）
            )
        )
        
        self.collection = self.client.get_or_create_collection(
            name="learning_docs",
            metadata={"hnsw:space": "cosine"}
        )
        
        # 不在初始化时测试 embedding，避免网络请求
        print(f"[OK] ChromaDB initialized (offline embedding) at {persist_directory}")
    
    def add_documents(self, doc_id, chunks):
        """添加文档chunk到向量数据库（提供预计算嵌入）"""
        if not chunks:
            return 0
            
        ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": str(doc_id), "chunk_index": i}
            for i in range(len(chunks))
        ]
        
        # 预计算嵌入向量（使用离线函数）
        try:
            embeddings = self.embedding_function(chunks)
        except Exception as e:
            print(f"[ERROR] Embedding computation failed: {e}")
            return 0
        
        # 分批添加（每批最多100条）
        batch_size = 100
        added = 0
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = chunks[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_embs = embeddings[i:i+batch_size]
            
            try:
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas,
                    embeddings=batch_embs
                )
                added += len(batch_ids)
            except Exception as e:
                print(f"[ERROR] Batch add failed: {e}")
                continue
        
        return added
    
    def search(self, query, doc_ids=None, top_k=5):
        """搜索相关文档chunk"""
        where_filter = None
        if doc_ids:
            where_filter = {"doc_id": {"$in": [str(did) for did in doc_ids]}}
        
        try:
            count = self.collection.count()
            if count == 0:
                return None
            
            # 预计算查询向量
            query_embedding = self.embedding_function([query])[0]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count),
                where=where_filter
            )
            return results
        except Exception as e:
            print(f"[WARN] Search error: {e}")
            return None
    
    def delete_document(self, doc_id):
        """删除文档的所有chunk"""
        try:
            self.collection.delete(where={"doc_id": str(doc_id)})
        except Exception as e:
            print(f"[WARN] Delete document error: {e}")
    
    def get_document_count(self):
        """获取文档chunk总数"""
        return self.collection.count()
