# AI PM 学习助手

**本地大模型解决方案学习管理系统**  
Flask + ChromaDB + DeepSeek API

---

## 功能特性

✅ **持续上传文档** - 支持 PDF/MD/PPT/TXT，上传后自动解析建索引  
✅ **RAG 智能问答** - 基于文档内容，带引用来源  
✅ **自动测评** - 基于文档自动出题（选择+判断），自动评判  
✅ **学习进度追踪** - 问答次数、测评记录、知识点掌握度  
✅ **可视化报告** - ECharts 雷达图+环形图  
✅ **暗色主题** - 金色点缀，专业感设计  


## 快速启动

### 1. 配置 DeepSeek API Key

```bash
# 复制配置模板
cp backend/.env.example backend/.env

# 编辑 backend/.env，填入你的 DeepSeek API Key
# DEEPSEEK_API_KEY=your-api-key-here
```

### 2. 安装依赖（首次运行）

```bash
cd learning-assistant/backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 3. 启动服务

```bash
venv\Scripts\python app.py
```

浏览器打开：`http://localhost:5000`


## 使用流程

### Step 1: 上传学习资料
→ 进入「文档管理」页  
→ 拖拽 PDF/MD/PPT 文件到上传区  
→ 等待解析（状态显示：处理中 → 已就绪）

### Step 2: 智能问答
→ 进入「智能问答」页  
→ 选择文档范围（全部文档 或 指定文档）  
→ 输入问题，按 Enter 发送  
→ 查看回答（带原文引用）

### Step 3: 参与测评
→ 进入「测评中心」页  
→ 选择文档 + 题目类型 + 题目数量  
→ 点击「生成测评」  
→ 答题 → 提交 → 查看解析

### Step 4: 查看报告
→ 进入「学习报告」页  
→ 查看统计卡片 + 知识点雷达图 + 测评分布环形图


## 技术架构

```
前端：纯 HTML/CSS/JS SPA
后端：Flask + ChromaDB + SQLite
LLM：DeepSeek API
向量化：ChromaDB 内置 Embedding (ONNX)
```

## 目录结构

```
learning-assistant/
├── backend/
│   ├── app.py              # Flask 主程序
│   ├── api/                # API 路由
│   ├── services/           # 业务逻辑
│   ├── .env                # 配置文件（填入API Key）
│   ├── requirements.txt    # Python 依赖
│   └── venv/              # 虚拟环境
├── frontend/
│   └── index.html         # 前端 SPA
└── data/
    ├── uploads/            # 上传的文件
    ├── db/                 # SQLite 数据库
    └── chromadb/          # ChromaDB 向量数据
```


## 常见问题

**Q: 提示 "请先配置 DEEPSEEK_API_KEY"**  
A: 编辑 `backend/.env` 文件，填入你的 DeepSeek API Key（需在 https://platform.deepseek.com 获取）

**Q: 上传文档后状态一直显示 "解析中"**  
A: 检查 `backend/services/` 目录下是否有错误日志，或查看终端输出

**Q: 问答时提示 "知识库未就绪"**  
A: 等待 ChromaDB 初始化完成（首次启动需要下载 embedding 模型，约 30 秒）

**Q: 测评生成失败**  
A: 检查 DeepSeek API Key 是否有效，以及余额是否充足


## 开发者说明

- DeepSeek API 费用：约 ¥0.001/1K tokens（deepseek-chat 模型）
- ChromaDB 首次启动：自动下载 embedding 模型（约 80MB，需联网）
- 文档解析：纯本地，不上传任何内容到云端（除了 RAG 问答调用 DeepSeek API）


## 未来优化方向

- [ ] 支持更多文档格式（DOCX、XLSX）
- [ ] 知识图谱可视化
- [ ] 多用户管理
- [ ] 导出学习报告 PDF
- [ ] 支持本地 LLM（Ollama）完全离线运行
