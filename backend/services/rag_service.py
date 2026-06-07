import os
from openai import OpenAI

class RAGService:
    def __init__(self, app):
        self.chromadb_service = app.chromadb_service
        
        # 初始化DeepSeek客户端
        api_key = app.config.get('DEEPSEEK_API_KEY', '') or os.getenv('DEEPSEEK_API_KEY', '')
        if not api_key or api_key == 'your-api-key-here':
            raise Exception("请先配置 DEEPSEEK_API_KEY（在 backend/.env 文件中设置）")
        
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        self.system_prompt = """你是一位资深AI项目经理和学习专家，专注于大模型解决方案领域。

回答规范：
1. 结构化输出（使用标题、列表、表格）
2. 有洞察力（不仅解释WHAT，更要说明WHY和HOW）
3. 面向PM视角（关注可行性、成本、风险、ROI）
4. 引用资料原文（当使用检索结果时，用【来源：文档X】标注）
5. 承认不确定性（资料未覆盖时明确说明"根据现有资料无法回答"）

禁止：
- 废话开场白（"这是一个很好的问题..."）
- 过于学术化的表述
- 不基于资料的臆测

回答格式：
## 核心观点
（简明扼要的核心结论）

## 详细分析
（结构化展开，使用列表或表格）

## 实践建议
（面向PM的可执行建议）

## 资料来源
（列出引用的文档和chunk）"""
    
    def query(self, question, document_ids=None):
        """执行RAG查询"""
        # 1. 从ChromaDB检索相关chunk
        search_results = self.chromadb_service.search(question, document_ids, top_k=5)
        
        if not search_results or not search_results.get('documents') or not search_results['documents'][0]:
            return {
                'answer': '没有找到相关文档内容。可能的原因：\n1. 还没有上传学习资料\n2. 选择的文档范围中没有相关内容\n\n请先上传文档或切换文档范围。',
                'sources': [],
                'confidence': 0
            }
        
        # 2. 构建上下文
        contexts = []
        sources = []
        
        docs = search_results['documents'][0]
        metas = search_results['metadatas'][0]
        
        for i, (doc, metadata) in enumerate(zip(docs, metas)):
            contexts.append(f"[文档{metadata['doc_id']}_片段{metadata['chunk_index']}]: {doc}")
            sources.append({
                'doc_id': metadata['doc_id'],
                'chunk_index': metadata['chunk_index'],
                'preview': doc[:100] + '...' if len(doc) > 100 else doc
            })
        
        context_str = '\n\n'.join(contexts)
        
        # 3. 构建提示词
        user_prompt = f"""基于以下参考资料回答问题：

【参考资料】
{context_str}

【问题】
{question}

请基于参考资料回答，如果资料中没有相关信息，请明确说明。"""
        
        # 4. 调用DeepSeek API
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': 0.85
            }
            
        except Exception as e:
            raise Exception(f"DeepSeek API调用失败: {str(e)}")
