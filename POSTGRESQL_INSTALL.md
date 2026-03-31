# PostgreSQL + pgvector 安装指南

本项目需要 PostgreSQL 15+ 和 pgvector 扩展以支持完整的向量搜索功能。

## Windows 安装

### 方法一：使用 Docker（推荐）

```powershell
# 安装 Docker Desktop
# https://www.docker.com/products/docker-desktop/

# 运行 PostgreSQL + pgvector
docker run -d \
  --name dnd_rag_pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=dnd_rag \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

### 方法二：直接安装

1. 下载 PostgreSQL 15+：
   https://www.postgresql.org/download/windows/

2. 安装时勾选：
   - pgvector extension
   - Command Line Tools

3. 或者使用 EDB 安装器：
   https://www.enterprisedb.com/downloads/postgresql

### 方法三：使用 winget

```powershell
winget install --id PostgreSQL.PostgreSQL --version 16.3.1
```

## macOS 安装

```bash
# 使用 Homebrew
brew install postgresql@15
brew install pgvector

# 启动服务
brew services start postgresql@15
```

## Linux (Ubuntu/Debian)

```bash
# 添加 PostgreSQL APT 源
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
sudo apt update

# 安装
sudo apt install postgresql-15 postgresql-15-pgvector
```

## 启用 pgvector 扩展

安装完成后，连接到 PostgreSQL：

```bash
psql -U postgres -d dnd_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

或者通过 SQL：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 验证安装

```bash
psql -U postgres -d dnd_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

应该输出：
```
 extname | extversion
---------+-------------
 vector  | 0.5.1
```

## 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`：
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dnd_rag
```

## 初始化数据库

```bash
alembic upgrade head
```

## 常见问题

### Q: pgvector 安装失败
A: 确保 PostgreSQL 版本 >= 15，pgvector 不支持更早版本。

### Q: 端口 5432 被占用
A: 修改 docker-compose.yml 中的端口映射或停止占用端口的服务。

### Q: 连接被拒绝
A: 检查 PostgreSQL 是否允许 localhost 连接，检查 pg_hba.conf。
