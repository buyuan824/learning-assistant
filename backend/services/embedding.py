"""
自定义离线 Embedding 函数
- 优先使用 ChromaDB 默认 ONNX 模型（需联网下载）
- 自动降级到基于哈希的本地 Embedding（完全离线）
"""

import hashlib
import numpy as np
from typing import List

# 尝试导入 chromadb 默认 embedding
_USE_ONNX = False
try:
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    # 测试是否可用（模型已下载）
    _test = DefaultEmbeddingFunction()
    _test(["test"])
    _USE_ONNX = True
    print("[OK] ChromaDB ONNX embedding model available")
except Exception as e:
    print(f"[INFO] ONNX model not available ({e}), using offline hash embedding")
    _USE_ONNX = False


class OfflineHashEmbedding:
    """基于哈希的离线 Embedding 函数
    - 无需联网，无需下载模型
    - 生成 384 维向量（与 all-MiniLM-L6-v2 兼容）
    - 使用 n-gram + 哈希 方式生成向量
    - 适合测试和演示，生产环境建议替换为真正的 Embedding 模型
    """
    
    DIMENSION = 384  # 与 all-MiniLM-L6-v2 相同维度
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]
    
    def _embed(self, text: str) -> List[float]:
        """为单个文本生成 embedding 向量"""
        vec = np.zeros(self.DIMENSION, dtype=np.float32)
        
        # 1. 字符级 n-gram (1,2,3)
        for n in [1, 2, 3]:
            for i in range(len(text) - n + 1):
                ngram = text[i:i+n]
                h = int(hashlib.md5(ngram.encode('utf-8')).hexdigest(), 16)
                idx = h % self.DIMENSION
                vec[idx] += 1.0
        
        # 2. 词级特征
        words = text.lower().split()
        for word in words:
            h = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16)
            idx = h % self.DIMENSION
            vec[idx] += 2.0  # 词级权重更高
        
        # 3. 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return vec.tolist()


def get_embedding_function():
    """获取可用的 embedding 函数"""
    if _USE_ONNX:
        return DefaultEmbeddingFunction()
    else:
        return OfflineHashEmbedding()
