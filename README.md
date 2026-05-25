# 主数据AI助手 — 数智管家 (Demo)

基于 [PRD V2.0](./docs/PRD-v2.md) 构建的**主数据AI助手演示原型**，展示「意图识别路由 → 知识库/MDM数据库联动 → 结构化回答」的完整 AI Agent 管线。

> **"数智管家"** 是荣耀内部的主数据领域 AI 专家顾问，帮助业务人员用自然语言解决主数据规则咨询、实体状态查询、规则与数据联动解释三类核心问题。

## 功能演示

| 场景 | 示例问题 | 意图 |
|---|---|---|
| 规则咨询 | "物料申请里「来源类型」字段有哪些枚举值？" | Intent A |
| 规则咨询 | "申请被退回，原因是命名规范不符，我应该怎么改？" | Intent A |
| 数据查询 | "物料编码 PART-2024-001 现在的状态是什么？" | Intent B |
| 数据查询 | "供应商 SUP-2023-456 是哪家公司？" | Intent B |
| 双库联动 | "物料 PART-2024-003 是冻结状态，还能发起采购申请吗？" | Intent C |
| 双库联动 | "SKU-XX-2024-Pro 能上架电商平台吗？" | Intent C |
| 澄清反问 | "物料状态怎么查？" | Intent D |
| 边界测试 | "物料编码 FAKE-9999-XX 现在什么状态？" → 实体不存在提示 | — |
| 边界测试 | "ERP 凭证规则怎么设置？" → 超出范围提示 | — |

## 架构概览

```
用户输入 → POST /api/chat
  ↓
意图识别路由器（正则 + 关键词 + LLM few-shot）
  ↓
┌─ Intent_Rule ────→ knowledge_tool ────→ RAG 检索 → 格式化
├─ Intent_Data ────→ entity_verify → mdm_query → 格式化
├─ Intent_Dual ────→ entity_verify → 并行(KB + MDM) → 融合推理
└─ Intent_Clarify ─→ 生成反问 / 功能导航
  ↓
ChatResponse { message, intent, sources[], is_bad_case }
  ↓
前端渲染：消息气泡 + 来源标注（【知识库】/【MDM】）+ 意图标签
```

### 核心组件

| 组件 | 职责 | 技术 |
|---|---|---|
| **意图路由器** | 三级策略：正则提取实体编码 → 关键词规则 → LLM降级 | 规则引擎 + LLM |
| **知识库检索** | 对 6 篇主数据规则文档进行语义搜索 | TF-IDF + 字符n-gram + 关键词加权 |
| **MDM 查询** | 模拟主数据管理系统，查询物料/供应商/SKU 状态 | JSON 数据 + 权限过滤 |
| **实体核查** | 查询前验证实体是否存在，防止幻觉 | MDM 轻量查询 |
| **双库融合** | 并行查询知识库+MDM，融合规则与数据 | 异步并行 + COT 推理 |
| **Bad Case** | 无法解答的问题静默写入反馈队列 | JSON 日志 |

## 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装运行

```bash
# 1. 克隆仓库
git clone https://github.com/M3RCUR2Y/mdm-ai-assistant-demo.git
cd mdm-ai-assistant-demo

# 2. 安装依赖
pip install -r requirements.txt

# 3. （可选）配置环境变量
cp .env.example .env

# 4. 启动服务
python backend/main.py
```

浏览器打开 `http://localhost:8000` 即可使用。

### LLM 模式切换

默认使用**模拟模式**（MockLLM），基于模板生成回答，无需 API Key。

如需接入真实 LLM，编辑 `.env`：

```bash
LLM_MODE=deepseek
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## 目录结构

```
mdm-ai-assistant-demo/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── intent_router.py        # 意图识别路由器
│   ├── workflows/              # 四类工作流
│   │   ├── rule_query.py       #   A：规则咨询
│   │   ├── data_query.py       #   B：数据查询
│   │   ├── dual_query.py       #   C：双库联动
│   │   └── clarification.py    #   D：澄清反问
│   ├── tools/                  # 工具层
│   │   ├── knowledge_tool.py   #   知识库检索（TF-IDF）
│   │   ├── entity_verify_tool.py # 实体核查
│   │   ├── mdm_query_tool.py   #   MDM 查询（模拟）
│   │   └── bad_case_tool.py    #   Bad Case 日志
│   ├── llm/                    # LLM 抽象层
│   │   ├── base.py             #   接口定义
│   │   ├── mock_llm.py         #   模拟实现
│   │   └── deepseek_llm.py     #   DeepSeek API
│   ├── data/
│   │   ├── knowledge_base/     #   6篇模拟规则文档
│   │   ├── mdm_data.json       #   15条模拟实体数据
│   │   └── golden_tests.json   #   黄金测试集
│   └── prompts/                #   LLM Prompt 模板
├── frontend/
│   ├── index.html              # 聊天界面
│   ├── css/style.css           # 样式
│   └── js/app.js               # 交互逻辑
├── requirements.txt
└── .env.example
```

## API 文档

### POST /api/chat

**请求：**
```json
{
  "message": "物料编码 PART-2024-001 现在的状态是什么？",
  "session_id": ""
}
```

**响应：**
```json
{
  "message": "PART PART-2024-001（USB-C连接器-100W）当前状态为【量产】。\n- 负责工程师：张三\n...\n【MDM】查询时间：2026-05-26 14:30，编码：PART-2024-001",
  "intent": "Intent_Data",
  "sources": [
    {
      "type": "mdm",
      "entity_id": "PART-2024-001",
      "query_time": "2026-05-26 14:30"
    }
  ],
  "is_bad_case": false,
  "session_id": "a1b2c3d4"
}
```

### GET /api/health

```json
{ "status": "ok", "llm_mode": "mock" }
```

### GET /api/examples

返回前端侧边栏的示例问题列表。

## 模拟数据

### 知识库文档（6篇）

| 文档 | 覆盖场景 |
|---|---|
| 01_物料主数据申请操作手册 | 申请流程、必填字段、来源类型枚举、退回原因 |
| 02_物料编码命名规范 | PART码规则、三段式命名、缩写禁令 |
| 03_退回原因与修改指引 | TOP6退回原因 + QA对 + 修改步骤 |
| 04_物料状态定义与流转规则 | 开发中/量产/冻结/报废 定义、采购规则 |
| 05_主数据概念词典 | Offering/SPU/SKU/PART/BOM/MDM/PDM |
| 06_供应商主数据管理规范 | 准入流程、编码规则、状态管理 |

### MDM 实体数据（15条）

覆盖物料（PART × 10，状态分布：量产/开发中/冻结/报废）、供应商（SUPPLIER × 3）、SKU（× 2）。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 前端 | 原生 HTML/CSS/JS（零构建工具） |
| 知识检索 | scikit-learn TF-IDF + 字符 n-gram |
| LLM | 策略模式：MockLLM / DeepSeekLLM |
| 数据 | JSON + Markdown（零外部依赖） |

## 设计原则

1. **来源可溯**：所有回答必须标注【知识库】或【MDM】来源
2. **诚实优先**：知识库无结果时直说不知道，不编造推断
3. **实体核查**：查询前先验证实体是否存在，防止幻觉
4. **边界严守**：超出主数据范围的问题明确拒绝，引导正确渠道
5. **降级不崩溃**：工具失败时尽可能提供已有结果，标注不可用部分

## License

MIT
