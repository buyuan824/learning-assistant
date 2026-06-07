import json
import re
import os
from openai import OpenAI

class QuizService:
    def __init__(self, app):
        self.chromadb_service = app.chromadb_service
        
        api_key = app.config.get('DEEPSEEK_API_KEY', '') or os.getenv('DEEPSEEK_API_KEY', '')
        if not api_key or api_key == 'your-api-key-here':
            raise Exception("请先配置 DEEPSEEK_API_KEY")
        
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    def generate_quiz(self, document_id, quiz_type='mixed', num_questions=10):
        """生成测评题目"""
        # 从ChromaDB获取文档内容
        search_results = self.chromadb_service.search(
            f"核心概念和关键知识点", 
            [document_id], 
            top_k=15
        )
        
        if not search_results or not search_results.get('documents') or not search_results['documents'][0]:
            raise Exception('无法获取文档内容，请确认文档已解析完成')
        
        context = '\n\n'.join(search_results['documents'][0])
        
        # 根据题目类型调整生成提示
        type_instructions = {
            'mixed': f'生成{num_questions}道题目，其中{int(num_questions*0.6)}道选择题，{num_questions - int(num_questions*0.6)}道判断题',
            'choice': f'生成{num_questions}道选择题',
            'judge': f'生成{num_questions}道判断题'
        }
        
        prompt = f"""基于以下学习资料内容，{type_instructions.get(quiz_type, type_instructions['mixed'])}。

要求：
1. 难度中等偏上，考察理解和应用能力
2. 选择题：题干 + 4个选项(A/B/C/D) + 正确答案 + 解析 + 知识点名称
3. 判断题：题干(陈述句) + 正确答案(true/false) + 解析 + 知识点名称
4. 知识点名称要简洁（2-6个字），便于雷达图展示

严格输出以下JSON格式，不要有其他文字：
```json
{{
  "quiz_type": "{quiz_type}",
  "questions": [
    {{
      "type": "choice",
      "question": "题干内容",
      "options": {{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}},
      "answer": "A",
      "explanation": "解析说明",
      "knowledge_point": "知识点名称"
    }},
    {{
      "type": "judge",
      "question": "判断题题干陈述",
      "answer": true,
      "explanation": "解析说明",
      "knowledge_point": "知识点名称"
    }}
  ]
}}
```

【资料内容】
{context}"""
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            
            # 提取JSON
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            
            quiz_data = json.loads(result_text)
            
            # 验证格式
            if 'questions' not in quiz_data:
                raise Exception('返回格式错误：缺少questions字段')
            
            for q in quiz_data['questions']:
                if 'type' not in q or 'question' not in q or 'answer' not in q:
                    raise Exception('返回格式错误：题目缺少必要字段')
                if not q.get('knowledge_point'):
                    q['knowledge_point'] = '综合知识'
            
            return quiz_data
            
        except json.JSONDecodeError as e:
            raise Exception(f'解析测评JSON失败: {str(e)}')
        except Exception as e:
            if 'API' in str(e) or 'DeepSeek' in str(e):
                raise
            raise Exception(f"生成测评失败: {str(e)}")
