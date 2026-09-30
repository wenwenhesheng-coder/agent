# 智慧银行理财顾问智能体

基于大模型技术的智慧银行理财顾问智能体——多智能体协同架构、合规风控硬隔离、Agentic RAG增强检索的银行理财顾问系统。

## 项目定位

**不是替代理财经理，而是智能辅助智能体**——做长尾客户服务、减轻理财经理负担，理财最终决策由用户自行负责，规避越权荐购的监管红线。

## 核心亮点（9大亮点）

| # | 亮点 | 说明 |
|---|------|------|
| 1 | 多智能体协同架构 | 5个专业Agent协同：客户画像/市场分析/产品匹配/合规审查/话术生成 |
| 2 | Agentic RAG增强检索 | 主动检索规划、多源数据融合、来源标注与追溯 |
| 3 | 大小模型协同 | 大模型语义理解 + 量化小模型精准计算（均值-方差、VaR等） |
| 4 | 可解释AI（XAI） | 推理链可视化、推荐理由生成、决策可白盒拆解 |
| 5 | 动态用户记忆与个性化引擎 | 短期对话记忆 + 长期用户档案 + 投资风格画像 |
| 6 | 轻量化部署与成本控制 | 私有化部署、模型压缩、MCP标准化、vLLM加速 |
| 7 | RAG+业务规则双轮驱动 | 知识库事实 + 业务规则双重校验，抑制金融大模型幻觉 |
| 8 | 金融合规硬隔离架构 | 独立规则引擎、全链路审计留痕、强制风险提示 |
| 9 | 用户隐私数据脱敏访问 | 不直接存储敏感数据，仅调取脱敏风险标签 |

## 技术架构（6层）

```
┌─────────────────────────────────────────────┐
│  6. 前端交互层  对话界面 + 理财报告展示        │
├─────────────────────────────────────────────┤
│  5. 对接适配层  FastAPI + MCP标准化            │
├─────────────────────────────────────────────┤
│  4. 合规风控拦截层  规则引擎 + 审计留痕【重中之重】│
├─────────────────────────────────────────────┤
│  3. RAG知识库层  向量化 + Agentic RAG          │
├─────────────────────────────────────────────┤
│  2. Agent智能体核心层  多智能体协同 + 工具调用    │
├─────────────────────────────────────────────┤
│  1. 底层基座层  国产大模型API + 私有化部署       │
└─────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置大模型（可选）

复制 `.env.example` 为 `.env`，填入API Key：

```bash
cp .env.example .env
# 编辑.env填入DASHSCOPE_API_KEY等
```

> 未配置API Key时自动启用Mock演示模式，保证系统可运行。

## 发布到 GitHub 和 Cloudflare Pages

本项目包含 Python/FastAPI 后端和静态前端，建议拆分部署：

1. 将整个项目上传到 GitHub。
2. 在 Cloudflare Pages 中连接 GitHub 仓库，设置根目录为 `frontend`，构建命令留空，输出目录填写 `.`。
3. 将 Python/FastAPI 后端部署到支持 Python 的服务，并获得后端地址，例如 `https://your-api.example.com`。
4. 打开 Pages 网站时，在地址后追加 `?api=https://your-api.example.com/api`，前端会记住该地址并调用远程 API。

如果只完成第 1、2 步，网站页面可以公开访问，但聊天、风险测评等功能仍需要后端服务。

### 3. 启动服务

```bash
# Web服务（推荐）
python run.py
# 访问 http://localhost:8200

# 命令行演示
python run.py --demo
```

### 4. 使用 Docker Compose

```bash
docker compose up --build
```

启动完成后访问：

- Web 界面：http://localhost:8200
- API 文档：http://localhost:8200/docs
- 健康检查：http://localhost:8200/health

默认不需要大模型 API Key，系统会使用 Mock 演示模式。需要连接真实模型时，
可将 `.env.example` 复制为 `.env` 并填写相应 Provider 的 API Key。

默认镜像使用内置轻量词袋向量，适合本地演示和 CPU 环境。如需安装
`sentence-transformers` 与 ChromaDB，可执行：

Linux/macOS：

```bash
INSTALL_ML_DEPS=1 docker compose build
docker compose up
```

Windows PowerShell：

```powershell
$env:INSTALL_ML_DEPS = "1"
docker compose build
docker compose up
Remove-Item Env:INSTALL_ML_DEPS
```

## 多智能体协同流程

```
用户提问
   │
   ▼
协调器（规划拆解）
   │
   ├──▶ 客户画像Agent ──▶ 构建动态用户画像（脱敏数据）
   │
   ├──▶ 市场分析Agent ──▶ 接入行情数据 + RAG研报
   │
   ├──▶ 产品匹配Agent ──▶ 量化小模型计算 + 知识库产品查询
   │                      （大小模型协同）
   │
   ├──▶ 合规审查Agent ──▶ 规则引擎校验 + 拦截违规 + 审计留痕
   │                      （硬隔离，独立一层）
   │
   └──▶ 话术生成Agent ──▶ 个性化回复 + 风险提示
```

## 合规规则引擎

| 规则 | 说明 |
|------|------|
| 禁止承诺保本/保证收益 | 拦截"保本""保证收益""稳赚不赔"等违规话术 |
| 风险等级匹配校验 | 推荐产品风险等级不得超过用户风险等级 |
| 敏感话术拦截 | 拦截"内部消息""内幕""无风险套利"等 |
| 强制风险提示 | 所有输出须附带"理财非存款，产品有风险" |
| 产品来源校验 | 推荐须标注数据来源，防止模型编造（抑制幻觉） |

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 智能理财顾问对话 |
| `/api/risk-assessment` | POST | 提交风险测评 |
| `/api/risk-assessment/questions` | GET | 获取风险测评题库 |
| `/api/tools` | GET | 列出所有工具（MCP标准化） |
| `/api/tools/call` | POST | 调用工具 |
| `/api/yield-calculation` | POST | 收益测算 |
| `/api/user-profile/{user_id}` | GET | 获取用户脱敏画像 |
| `/api/audit/logs` | GET | 查询审计日志 |
| `/api/audit/export` | GET | 导出审计追溯链 |
| `/api/system/status` | GET | 系统状态 |
| `/api/system/architecture` | GET | 系统架构信息 |
| `/docs` | GET | API文档（Swagger） |

## 项目结构

```
├── config/            配置管理（多大模型Provider + 合规参数）
├── core/              核心公共模块（数据模型、异常、系统容器）
├── models/            大小模型协同（LLM客户端 + 量化小模型）
├── tools/             Agent工具集（产品KB、风险测评、计算器等）
├── rag/               Agentic RAG（向量存储 + 文档处理 + 智能检索）
├── compliance/        合规风控硬隔离（规则引擎 + 拦截器 + 审计日志）
├── memory/            动态用户记忆引擎（短期 + 长期 + 画像）
├── agents/            多智能体协同（5个专业Agent + 协调器）
├── data/              数据层（脱敏访问 + 用户数据适配 + 知识库）
├── api/               对接适配层（FastAPI + 路由）
├── frontend/          前端交互层（对话界面 + 推理链展示）
├── run.py             启动入口
└── requirements.txt   依赖清单
```

## 支持的大模型

| Provider | 模型 | 说明 |
|----------|------|------|
| 通义千问 | qwen-plus | DashScope OpenAI兼容接口 |
| 智谱AI | glm-4 | 智谱开放平台 |
| 文心一言 | ernie-bot | 百度智能云 |
| 私有化部署 | Qwen2.5-14B | vLLM加速，适配银行内网 |

## 技术特色

- **抑制幻觉**：RAG优先从知识库拿真实业务数据 + 独立规则引擎双重校验
- **合规硬隔离**：所有输出先过合规校验，不是提示词约束
- **全链路审计**：对话记录、推理链、合规校验结果全留痕，保留≥20年
- **数据脱敏**：智能体不直接接触敏感资产数据，仅调取脱敏风险标签
- **推理可解释**：每条推荐附带理由 + 数据来源 + 推理链可视化

## License

本项目用于中国国际大学生创新创业大赛企业命题赛道参赛。
