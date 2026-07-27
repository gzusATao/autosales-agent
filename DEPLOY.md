# Zeabur 部署说明

## 1. 导入仓库

在 Zeabur 新建 Project，选择从 GitHub 导入：

```text
gzusATao/autosales-agent
```

项目包含 Dockerfile，建议选择 Dockerfile 部署。

## 2. 环境变量

在 Zeabur 服务的 Variables 中配置：

```text
LLM_PROVIDER=deepseek
OPENAI_API_KEY=你的 DeepSeek Key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
DATABASE_URL=sqlite:///./autosales.db
```

## 3. 启动命令

Dockerfile 已配置启动命令：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Zeabur 会自动注入 `PORT`。

## 4. 访问路径

部署完成后访问：

```text
https://你的-zeabur域名/chat.html
```

根路径 `/` 会自动进入 AI 销售对话页。
