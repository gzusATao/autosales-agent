# AutoSales AI Agent

汽车销售顾问 AI Agent 演示项目。项目模拟汽车销售顾问与用户进行购车咨询、车型推荐、配置对比、分期试算、库存查询、试驾预约和销售线索沉淀，并提供 RAG 销售资料库、用户反馈闭环和后台监控页面，方便后续持续优化 Agent 的回答质量。

## 项目亮点

| 模块 | 说明 |
| --- | --- |
| AI 销售对话 | 基于 LangGraph 多节点流程，识别用户意图并完成推荐、对比、金融、库存、试驾等任务 |
| 简单咨询直答 | 普通咨询、闲聊类问题不会强制追问预算/车型，只有识别出购车意图才进入槽位采集 |
| RAG 销售资料库 | 支持粘贴文本和上传 PDF/TXT/DOCX/MD，自动清洗、切片、入库，用于销售资料检索增强 |
| 防幻觉兜底 | 车型、优惠、配置、政策等问题强制基于检索资料回答；RAG 无结果时返回“目前没有xxx相关资料” |
| 工具调用 | 封装车型查询、车型对比、分期试算、库存查询、试驾预约、线索保存、RAG 检索等工具 |
| 客户画像与线索 | 自动沉淀预算、车型、能源、购车周期、意向等级、跟进摘要 |
| 用户反馈闭环 | 每轮 AI 回复后支持“满意/不满意”，不满意时记录原因、问题、回答、意图、工具轨迹和 RAG chunks |
| 后台监控 | 展示成功率、失败率、平均响应时间、满意率、不满意率、RAG 负反馈和工具调用成功率 |
| 前端适配 | 桌面端工作台布局，移动端底部导航和数据卡片适配 |

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | FastAPI、Pydantic、SQLAlchemy |
| Agent 编排 | LangGraph 风格状态图 |
| 大模型 | DeepSeek，兼容 OpenAI API 格式；未配置时可走 Mock |
| RAG | SQLite 存储 + 文本清洗 + chunk 切片 + 关键词/向量化兼容检索封装 |
| 数据库 | SQLite 开发演示，可扩展 PostgreSQL |
| 前端 | 原生 HTML/CSS/JavaScript |
| 部署 | Dockerfile、docker-compose |

## 快速启动

```bash
pip install -r backend/requirements.txt
pip install uvicorn[standard] openai

# 可选：配置 DeepSeek/OpenAI 兼容 API Key
# PowerShell:
# $env:OPENAI_API_KEY="your_api_key"

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

打开浏览器：

- AI 销售对话：http://127.0.0.1:8000/chat.html
- 车型库 / 销售资料库：http://127.0.0.1:8000/cars.html
- 销售线索：http://127.0.0.1:8000/leads.html
- 后台监控：http://127.0.0.1:8000/metrics.html

如果页面没有显示最新导航，优先按 `Ctrl + F5` 强制刷新。项目 HTML 已为 JS 加版本号，正常刷新会加载最新脚本。

## 核心演示流程

可以在 AI 销售对话页依次输入：

```text
1. 我想买20万以内的SUV，省油一点
2. 对比宋PLUS和锋兰达
3. 宋PLUS DM-i首付17w
4. 广州有现车吗？
5. 帮我预约周六下午试驾宋PLUS DM-i
```

系统会展示：

- 当前意图识别
- 购车槽位和客户画像
- 工具调用轨迹
- LangGraph 节点流转
- 每轮回答后的满意/不满意反馈按钮

## RAG 销售资料库

销售资料库位于 `车型库 / 销售资料`。

支持能力：

- 手动粘贴销售资料
- 上传 PDF/TXT/DOCX/MD
- 文本清洗：去空行、去重复段落、过滤过短或无意义片段
- 切片入库：将长文本拆成适合检索的 chunk
- 检索测试：可输入问题查看命中的资料片段和 score

RAG 可靠性策略：

- 用户问题带车型、优惠、配置、政策、竞品等信息时，必须优先查销售资料库。
- 检索到资料时，回答只基于资料片段组织。
- 检索失败或没有结果时，统一兜底：

```text
目前没有“xxx”相关资料。这个问题需要参考车型销售资料来回答，我不能直接编政策、配置或优惠信息；你可以换个问法，或先到销售资料库补充对应车型资料后再问。
```

## 后台监控与反馈闭环

后台监控页面用于展示 Agent 的可维护性指标：

- 成功率
- 失败率
- 平均响应时间
- 满意率
- 不满意率
- RAG 负反馈数量
- 工具调用成功率
- 高频点踩原因
- 最近异常 / 兜底记录

反馈闭环流程：

```text
用户提问 -> Agent 回答 -> 用户点赞/点踩 -> 记录问题、回答、意图、工具轨迹、RAG chunks -> 后台统计 -> 优化 Prompt / 工具描述 / 知识库资料
```

这部分可作为面试亮点说明：项目不仅能完成对话，还能沉淀真实失败样本，为后续维护 RAG 准确率和工具调用稳定性提供依据。

## 可靠性设计

项目内置多层兜底：

| 场景 | 处理方式 |
| --- | --- |
| 节点异常 | Agent 外层捕获异常，返回友好兜底，不让接口崩溃 |
| 工具异常 | 工具 trace 标记 `error=fallback`，回复使用对应业务兜底 |
| RAG 无结果 | 返回“目前没有xxx相关资料”，避免大模型编造 |
| 缺少试驾信息 | 不创建假预约，追问姓名和手机号 |
| 用户短句追问 | 复用会话记忆中的预算、车型、能源等上下文 |
| 统计写入失败 | 不影响正常聊天回复，只记录后端日志 |

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/chat/message` | 发送对话消息 |
| GET | `/api/cars` | 获取车型列表 |
| POST | `/api/cars/compare` | 车型对比 |
| POST | `/api/finance/calculate` | 分期试算 |
| GET | `/api/inventory` | 库存查询 |
| POST | `/api/appointments` | 创建试驾预约 |
| GET | `/api/appointments` | 预约列表 |
| GET | `/api/customers/{id}/profile` | 客户画像 |
| GET | `/api/leads` | 销售线索 |
| GET | `/api/knowledge` | 销售资料列表 |
| POST | `/api/knowledge/search` | RAG 检索 |
| POST | `/api/knowledge/upload` | 手动录入销售资料 |
| POST | `/api/knowledge/upload-file` | 上传销售资料文件 |
| POST | `/api/feedback` | 保存每轮回答反馈 |
| GET | `/api/feedback/stats` | 反馈统计 |
| GET | `/api/metrics/agent` | Agent 后台监控指标 |
| GET | `/api/health` | 健康检查 |

## 项目结构

```text
autosales-agent/
├── backend/
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接与建表
│   ├── llm.py                  # DeepSeek / Mock LLM 封装
│   ├── seed_data.py            # 演示种子数据
│   ├── api/
│   │   ├── chat.py             # 对话 API 与运行指标埋点
│   │   ├── cars.py             # 车型 API
│   │   ├── customers.py        # 客户画像 / 线索 API
│   │   ├── finance.py          # 金融 / 库存 / 预约 API
│   │   ├── knowledge.py        # 销售资料库 API
│   │   ├── feedback.py         # 用户反馈 API
│   │   └── metrics.py          # 后台监控 API
│   ├── agent/
│   │   ├── state.py            # Agent State
│   │   ├── graph.py            # 流程编排
│   │   ├── nodes.py            # 意图、记忆、槽位、路由、工具、回复节点
│   │   └── tools.py            # 业务工具函数
│   ├── rag/
│   │   └── rag.py              # 销售资料检索
│   ├── memory/
│   │   └── memory.py           # 短期/长期记忆
│   ├── models/
│   │   └── models.py           # SQLAlchemy 模型
│   └── schemas/
│       └── schemas.py          # Pydantic Schema
├── frontend/
│   ├── chat.html               # AI 销售对话
│   ├── cars.html               # 车型库 / 销售资料库
│   ├── customers.html          # 客户画像
│   ├── appointments.html       # 试驾预约
│   ├── leads.html              # 销售线索
│   ├── metrics.html            # 后台监控
│   ├── css/style.css
│   └── js/
│       ├── api.js
│       ├── layout.js
│       ├── chat.js
│       ├── cars.js
│       ├── customers.js
│       ├── appointments.js
│       ├── leads.js
│       └── metrics.js
├── test_agent_response.py
├── test_feedback_api.py
├── test_metrics_api.py
├── test_frontend_layout.js
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 测试

```bash
python test_agent_response.py
python test_feedback_api.py
python test_metrics_api.py
python test_knowledge_upload_cleaning.py
python test_backend_routes.py
python -m compileall backend
node test_frontend_layout.js
```

## 面试讲法参考

可以这样介绍项目：

> 我独立做了一个汽车销售顾问 AI Agent。它不是单轮问答，而是一个围绕购车转化的工作流系统：用户输入后，先做意图识别，简单咨询直接回答；如果识别出购车意图，就通过 LangGraph 多节点流程完成槽位采集、工具调用、RAG 检索、回复生成和记忆沉淀。项目里有车型推荐、对比、分期、库存、试驾预约、客户画像和销售线索沉淀。
>
> 可靠性方面，我做了两层兜底：一层是 Agent 外层 try-catch，保证节点异常不会导致接口崩溃；另一层是业务兜底，例如 RAG 检索失败时不会编造优惠政策，而是提示目前没有相关资料，试驾缺联系方式时也不会创建假预约，而是追问必要信息。
>
> 后续维护方面，我加了用户反馈闭环和后台监控。每轮回答后用户可以点赞/点踩，系统会记录问题、回答、意图、工具调用和 RAG chunks。后台可以看到成功率、失败率、平均响应时间、RAG 负反馈和工具调用成功率，用这些数据持续优化 Prompt、工具描述和知识库资料。
