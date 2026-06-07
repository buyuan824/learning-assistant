# LLM Solutions Study Notes

## Chapter 1: LLM Basics

### What is LLM
Large Language Model - deep learning model trained on massive text data.

Key features:
- Billions of parameters
- TB-scale training data
- Emergent abilities

### Transformer Architecture
- Self-Attention mechanism
- Multi-Head Attention
- Positional Encoding
- Feed-Forward Network

## Chapter 2: Prompt Engineering

### Design Principles
1. Be Specific
2. Few-Shot examples
3. Chain-of-Thought
4. Role Prompting

### Chain-of-Thought
Show reasoning steps before answers.
Improves accuracy by 80%+ on complex reasoning tasks.

## Chapter 3: RAG Architecture

### What is RAG
Retrieval-Augmented Generation combines search and generation.

### Vector Databases
- ChromaDB (lightweight)
- Milvus (high performance)
- Pinecone (cloud)
- Weaviate (open source)

### Embedding Models
- text-embedding-ada-002 (OpenAI)
- all-MiniLM-L6-v2 (open source)
- bge-large-zh-v1.5 (Chinese)

## Chapter 4: Agent Design

### What is AI Agent
Autonomous intelligent agent that plans, uses tools, and completes tasks.

Core capabilities:
1. Task Planning
2. Tool Use
3. Memory Management
4. Self-Reflection

### ReAct Framework
ReAct = Reasoning + Acting

## Chapter 5: Model Fine-tuning

### When to Fine-tune
- Domain adaptation
- Output format customization
- Style adjustment
- Data privacy requirements

### Fine-tuning Methods
| Method | Parameters | Cost | Effect |
|--------|-----------|------|--------|
| Full | 100% | High | Best |
| LoRA | 1-5% | Medium | Near Full |
| QLoRA | 1-5% | Low | Near LoRA |

## Chapter 6: Deployment Optimization

### Inference Optimization
1. Quantization (INT8/INT4)
2. Pruning
3. Distillation
4. Batching

### Cost Control
- Use smaller models
- Compress prompts
- Cache frequent queries
- Hybrid deployment
