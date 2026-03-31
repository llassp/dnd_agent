# DnD RAG 战役助手

基于 RAG（检索增强生成）技术的生产级 D&D DM 助手平台。

## 功能特性

- 多战役隔离（无交叉污染）
- 可插拔的版本化战役模块
- 基于规则的答案与强制引用
- 跨会话的状态化叙事推进
- 可扩展的 Agent/工具架构
- 支持 OpenAI / Anthropic LLM 提供者

## 技术栈

- **运行时**: Python 3.11
- **Web 框架**: FastAPI
- **数据库**: PostgreSQL 15+ (pgvector 扩展)
- **向量搜索**: pgvector (IVFFlat 索引)
- **LLM**: OpenAI GPT-4 / Anthropic Claude (可切换)
- **任务队列**: Celery + Redis
- **可观测性**: OpenTelemetry + 结构化 JSON 日志

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目后直接启动
docker-compose up

# 可选：配置 LLM API Key
export OPENAI_API_KEY=your_key
docker-compose up
```

### 方式二：本地开发

#### 前置要求

- Python 3.11+
- PostgreSQL 15+ (已安装 pgvector 扩展)
- Redis (可选)

#### 安装

```bash
pip install -e .
```

#### 配置

创建 `.env` 文件：

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

关键配置：
- `DATABASE_URL` - PostgreSQL 连接字符串
- `LLM_PROVIDER` - `openai` / `anthropic` / `stub`
- `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY` - LLM API 密钥

#### 数据库设置

```bash
alembic upgrade head
```

#### 启动服务器

```bash
uvicorn app.main:app --reload
```

## LLM 配置

### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

### Anthropic

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-latest
```

### Stub 模式（无 LLM）

```bash
LLM_PROVIDER=stub
```

Stub 模式返回结构化数据但无自然语言生成，用于测试。

## API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/campaigns` | POST | 创建战役 |
| `/campaigns/{id}` | GET | 获取战役详情 |
| `/campaigns/{id}/enable-module` | POST | 为战役启用模块 |
| `/campaigns/{id}/modules` | GET | 获取战役已启用的模块 |
| `/modules/ingest` | POST | 导入模块包 |
| `/query` | POST | 查询系统（返回带引用的答案） |
| `/sessions/{id}/events` | POST | 记录会话事件 |
| `/sessions/{id}/events` | GET | 获取时间线 |
| `/state/apply` | POST | 应用世界状态补丁 |
| `/state/campaign/{id}` | GET | 获取世界状态 |
| `/health` | GET | 健康检查 |
| `/health/live` | GET | 存活探针 |
| `/health/ready` | GET | 就绪探针 |

## 查询示例

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "uuid",
    "session_id": "uuid",
    "user_input": "What are the rules for opportunity attacks?",
    "mode": "auto"
  }'
```

响应：
```json
{
  "answer": "**Conclusion**: Opportunity attacks occur when a creature moves out of your reach...\n\n**Evidence**:\n1. Core Rules Reference: \"When a creature moves out of your reach...\"\n\n**DM Adjudication Note**: Based on available evidence.",
  "used_agent": "rules",
  "confidence": 0.85,
  "citations": [...],
  "state_updates": [],
  "needs_clarification": false,
  "clarification_question": null
}
```

## 模块格式

参考 `examples/modules/sample_forgotten_forest/` 目录，模块需要包含：

```
module_name/
├── module.yaml          # 模块清单
├── docs/               # 文档 (.md, .txt, .json)
│   ├── adventure.md
│   └── rules.md
└── data/               # 实体数据 (.json)
    ├── npcs.json
    └── monsters.json
```

## 开发

### 运行测试

```bash
pytest
```

### 代码检查

```bash
ruff check .
black --check .
```

### 项目结构

```
app/
├── agents/          # Agent 处理器 (Rules, Narrative, State, Encounter)
├── api/             # FastAPI 路由
├── core/            # 配置、日志、追踪
├── db/              # SQLAlchemy 模型、Alembic 迁移
├── ingestion/       # 模块导入管道
├── llm/             # LLM 提供者抽象
├── rag/             # RAG 检索管道
├── schemas/         # Pydantic 请求/响应模式
└── state/           # 世界状态管理
```

## 健康检查

- `GET /health` - 基本健康状态
- `GET /health/live` - Kubernetes 存活探针
- `GET /health/ready` - Kubernetes 就绪探针（检查数据库连接）

## 下一步

1. 创建战役：`POST /campaigns`
2. 导入模块：`POST /modules/ingest`
3. 启用模块：`POST /campaigns/{id}/enable-module`
4. 开始查询：`POST /query`
