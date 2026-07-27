# AutoLead Agent 🚗

**汽车销售线索转化系统 — AI Agent 销售顾问演示版**

面向汽车销售场景的 AI Agent 系统，围绕"需求采集 → 车型推荐 → 配置对比 → 分期试算 → 库存查询 → 试驾预约 → 线索沉淀"构建销售转化闭环。

## 功能特性

| 功能 | 说明 |
|------|------|
| 🤖 **AI 销售对话** | 多轮对话采集客户购车需求，智能推荐车型 |
| 🚗 **车型推荐** | 基于预算、用途、能源偏好精准推荐 |
| ⚖️ **车型对比** | 多维度对比车型配置、价格、空间、油耗 |
| 💰 **分期试算** | 计算首付、月供、总利息 |
| 📦 **库存查询** | 查询门店库存和交车时间 |
| 🏎️ **试驾预约** | 创建试驾预约记录 |
| 📋 **客户画像** | 跨会话保存客户需求记忆 |
| 📊 **销售线索** | 线索等级评定和跟进管理 |
| 📚 **RAG 知识库** | 车型参数、优惠政策、销售话术语义检索 |
| 🔧 **工具调用轨迹** | 展示每一步的工具调用过程和结果 |

## 技术栈

| 层次 | 技术 |
|------|------|
| **后端框架** | FastAPI + Pydantic + SQLAlchemy |
| **Agent 框架** | LangGraph 状态图编排 |
| **大模型** | DeepSeek（兼容 OpenAI API） |
| **RAG 检索** | 关键词+TF-IDF 语义检索（SQLite 兼容） |
| **数据库** | SQLite（开发）/ PostgreSQL（生产） |
| **缓存** | Redis |
| **异步任务** | Celery |
| **前端** | 原生 HTML/CSS/JS |
| **部署** | Docker Compose |

## 快速开始

### 方式一：直接运行（推荐）

```bash
# 1. 安装依赖
pip install -r backend/requirements.txt
pip install uvicorn[standard] openai

# 2. 配置 DeepSeek API Key（在 backend/config.py 中已配置）
# 或设置环境变量：
# $env:OPENAI_API_KEY="your_deepseek_api_key"

# 3. 启动服务器
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 打开浏览器访问
# http://localhost:8000
```

### 方式二：Docker Compose

```bash
# 设置 DeepSeek API Key
export OPENAI_API_KEY="your_deepseek_api_key"

# 一键启动
docker-compose up -d

# 访问
# http://localhost:8000
```

## 演示流程

打开 http://localhost:8000/chat.html ，依次输入以下问题：

```
1. 我想买20万以内家用SUV，省油一点     → 车型推荐
2. 宋PLUS和锋兰达怎么选？              → 配置对比
3. 首付30%贷款3年月供多少？           → 分期试算
4. 广州有现车吗？                      → 库存查询
5. 帮我预约周六下午试驾宋PLUS DM-i    → 试驾预约 + 线索保存
```

每一步都会在页面右侧展示：
- 🎯 当前意图识别结果
- 🔧 工具调用轨迹（输入/输出）
- 📋 客户画像更新

## 项目结构

```
autosales-agent/
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── llm.py               # DeepSeek/Mock LLM 封装
│   ├── seed_data.py         # 种子数据（8款车型+知识库+演示客户）
│   ├── models/
│   │   └── models.py        # SQLAlchemy 数据模型
│   ├── schemas/
│   │   └── schemas.py       # Pydantic 请求/响应模型
│   ├── api/
│   │   ├── chat.py          # 对话 API
│   │   ├── cars.py          # 车型 API
│   │   ├── customers.py     # 客户/线索 API
│   │   ├── finance.py       # 金融/库存/预约 API
│   │   └── knowledge.py     # 知识库 API
│   ├── agent/
│   │   ├── state.py         # LangGraph 状态定义
│   │   ├── graph.py         # 状态图编排
│   │   ├── nodes.py         # 图节点（意图/记忆/路由/工具/回复）
│   │   └── tools.py         # 业务工具函数
│   ├── rag/
│   │   └── rag.py           # RAG 知识库检索
│   ├── memory/
│   │   └── memory.py        # 短期/长期记忆管理
│   └── requirements.txt
├── frontend/
│   ├── index.html           # 首页
│   ├── chat.html            # 销售对话页
│   ├── cars.html            # 车型库页
│   ├── customers.html       # 客户画像页
│   ├── appointments.html    # 试驾预约页
│   ├── leads.html           # 销售线索页
│   ├── css/style.css        # 样式
│   └── js/
│       ├── api.js           # API 客户端
│       ├── chat.js          # 对话控制器
│       ├── cars.js          # 车型控制器
│       ├── customers.js     # 客户控制器
│       ├── appointments.js  # 预约控制器
│       └── leads.js         # 线索控制器
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/message` | 发送对话消息 |
| GET  | `/api/cars` | 获取车型列表 |
| POST | `/api/cars/compare` | 车型对比 |
| POST | `/api/finance/calculate` | 分期试算 |
| GET  | `/api/inventory` | 库存查询 |
| POST | `/api/appointments` | 创建试驾预约 |
| GET  | `/api/appointments` | 预约列表 |
| GET  | `/api/customers/{id}/profile` | 客户画像 |
| GET  | `/api/leads` | 线索列表 |
| POST | `/api/knowledge/search` | 知识库检索 |
| POST | `/api/knowledge/upload` | 上传知识文档 |
| POST | `/api/knowledge/upload-file` | 上传 PDF/TXT/DOCX/MD 知识文件 |

## 内置数据

**车型（8款）**：比亚迪宋PLUS DM-i、秦PLUS DM-i、丰田锋兰达双擎、本田CR-V e:HEV、哈弗枭龙MAX、吉利星越L、特斯拉Model Y、小鹏G6

**知识库（8篇）**：车型配置说明、选购指南、分期常见问题、试驾流程、竞品对比、话术、优惠政策

**演示客户（2个）**：张先生（高意向，预算18-22万混动SUV）、李女士（中意向，预算15万内混动轿车）

## LangGraph 状态图

```
START → IntentNode → MemoryLoadNode → SlotFillNode → RouteNode
                                                          │
                                          ┌───────────────┼────────────────┐
                                          ▼               ▼                ▼
                                    AskQuestion    ToolExecutor     (其他工具节点)
                                          │               │
                                          ▼               ▼
                                     ResponseNode ←──────┘
                                          │
                                          ▼
                                    MemoryWriteNode → END
```
