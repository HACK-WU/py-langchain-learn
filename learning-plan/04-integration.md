# 阶段四：综合实战

> 融合文档 00-11 全部知识点
>
> 预计时间：5-7 天

---

## 学习目标

- 将模型、消息、工具、记忆、流式、结构化输出、中间件全部打通
- 构建一个接近生产级的 Agent 应用
- 深入理解 `Runnable` 执行引擎的设计
- 具备独立设计和实现复杂 Agent 系统的能力

---

## 前置回顾

在进入综合实战之前，确保你已经掌握以下能力：

| 能力 | 来源 | 验证方式 |
|------|------|---------|
| 初始化和切换模型 | 阶段一 | 能用 `init_chat_model` + `stream` + `batch` |
| 定义工具并读取上下文 | 阶段二 | 能用 `@tool` + `ToolRuntime` + `Command` |
| 管理对话记忆 | 阶段二 | 能配置 `Checkpointer` + 自定义 `AgentState` |
| 使用流式输出 | 阶段二 | 能用多种 `stream_mode` 组合 |
| 实现结构化输出 | 阶段二 | 能用 `ProviderStrategy` / `ToolStrategy` |
| 组合中间件 | 阶段三 | 能混用内置 + 自定义中间件 |

---

## 实战 Demo：智能研究助手

> **难度**：⭐⭐⭐⭐⭐
>
> 详细实现见 [Demo 4 说明](./demos/demo4-research-assistant.md)

### 功能描述

构建一个能分析文档的智能研究助手，融合全部知识点：

### 架构设计

```
用户输入（文本/URL）
    │
    ▼
┌─────────────────────────────────────┐
│         智能研究助手 Agent           │
│                                     │
│  ┌─────────── 中间件栈 ───────────┐ │
│  │ SummarizationMiddleware        │ │
│  │ ContextEditingMiddleware       │ │
│  │ ModelCallLimitMiddleware       │ │
│  │ ModelRetryMiddleware           │ │
│  │ 自定义 @after_agent (保存摘要) │ │
│  └───────────────────────────────┘ │
│              │                      │
│              ▼                      │
│  ┌─────────── 模型 ──────────────┐ │
│  │ init_chat_model (可配置)      │ │
│  │ ModelFallbackMiddleware       │ │
│  └───────────────────────────────┘ │
│              │                      │
│              ▼                      │
│  ┌─────────── 工具 ──────────────┐ │
│  │ fetch_url       → 抓取网页    │ │
│  │ search_keyword  → 搜索关键词  │ │
│  │ count_lines     → 统计行数    │ │
│  │ summarize_text  → 摘要内容    │ │
│  │ save_note       → 保存笔记    │ │
│  └───────────────────────────────┘ │
│              │                      │
│              ▼                      │
│  ┌─────────── 记忆 ──────────────┐ │
│  │ InMemorySaver  → 短期(对话内) │ │
│  │ InMemoryStore  → 长期(跨对话) │ │
│  └───────────────────────────────┘ │
│              │                      │
│              ▼                      │
│  ┌─────────── 输出 ──────────────┐ │
│  │ stream_mode=["messages",      │ │
│  │              "custom"]         │ │
│  │ response_format=ResearchReport│ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
    │
    ▼
ResearchReport（结构化输出）
├── summary: str           # 研究摘要
├── key_findings: list     # 关键发现
├── references: list       # 引用（行号/段落）
└── notes_saved: bool      # 笔记是否已保存
```

### 知识点映射

| 知识点 | 在 Demo 中的应用 |
|--------|-----------------|
| **模型** | `init_chat_model` 初始化 + `ModelFallbackMiddleware` 容错 |
| **消息** | `content_blocks` 处理多模态输入（文本 + URL） |
| **工具** | 5 个工具覆盖数据获取、分析、存储全流程 |
| **短期记忆** | `InMemorySaver` 维持对话内研究上下文 |
| **长期记忆** | `InMemoryStore` 保存研究笔记，跨对话可查 |
| **结构化输出** | `ToolStrategy(ResearchReport)` 返回结构化研究报告 |
| **流式输出** | `stream_mode=["messages", "custom"]`，工具通过 `stream_writer` 发进度 |
| **中间件** | 5 个中间件组合：摘要 + 上下文编辑 + 调用限制 + 重试 + 自动保存 |
| **系统提示词** | `SystemMessage` + `content_blocks`，含研究方法论指导 |

### 预期产出

```
你: 帮我分析 https://example.com/article.txt 这篇文章中 AI 相关的内容

[进度] 正在获取网页内容...
[进度] 内容获取完成，共 523 行
[进度] 正在搜索关键词 "AI"...
[进度] 找到 47 处匹配
[进度] 正在生成摘要...

📊 研究报告
━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 摘要：该文章探讨了人工智能在...
🔑 关键发现：
  1. AI 在医疗领域的应用增长迅速（第 12、45、89 行）
  2. 伦理挑战仍是主要障碍（第 156 行）
  3. 预计 2026 年市场规模达 $500B（第 201 行）
📎 引用：
  - 第 12 行: "AI-driven diagnostics have shown..."
  - 第 156 行: "Ethical concerns around AI..."
💾 研究笔记已保存

[Token 统计] input=1,245, output=892, total=2,137
```

---

## 深度源码阅读

完成 Demo 4 后，进入最硬核的源码阅读阶段：

### Runnable 执行引擎

`langchain_core/runnables/base.py`（220KB）是整个 LangChain 的执行引擎核心。

**阅读路线**：

```
1. Runnable 基类
   ├── invoke()        → 同步执行入口
   ├── stream()        → 流式执行入口
   ├── batch()         → 批量执行入口
   └── ainvoke()       → 异步版本

2. Runnable 配置
   ├── with_config()   → 配置传递
   ├── with_fallbacks() → 降级链
   └── with_retry()    → 重试链

3. Runnable 组合
   ├── RunnableSequence  → 管道 |
   ├── RunnableParallel  → 并行 {}
   └── RunnableBranch    → 分支

4. 内部机制
   ├── _call_with_config()   → 配置注入
   └── _batch_with_config()   → 批量配置注入
```

**关键问题引导**：

1. `invoke` 内部如何传递 `RunnableConfig`？
2. `stream` 是如何实现逐步 yield 的？
3. `batch` 的并发控制 `max_concurrency` 是如何实现的？
4. `with_fallbacks` 和 `with_retry` 的本质是不是也是 Runnable？
5. 为什么说 LangChain 的核心抽象就是 Runnable？

---

## 进阶方向

完成阶段四后，你可以继续深入以下方向：

| 方向 | 说明 | 相关资源 |
|------|------|---------|
| **LangGraph** | 更灵活的状态图编排，Agent 只是 LangGraph 的一种特例 | `langgraph` 包 |
| **RAG** | 检索增强生成，结合向量数据库实现知识库问答 | `langchain/retrievers/` + `langchain/vectorstores/` |
| **多 Agent 系统** | Supervisor + Worker 模式，子 Agent 协作 | `SubAgentMiddleware` |
| **生产部署** | PostgresSaver/PostgresStore、LangGraph Server | `langgraph-checkpoint-postgres` |
| **评估与测试** | LangSmith 评估、LLMToolEmulator 测试 | `langchain/evaluation/` |
| **Deep Agents** | 内置高级能力的 Agent 框架 | `deepagents` 包 |

---

## 阶段自检

完成阶段四后，你应该能回答以下问题：

1. 如何设计一个工具体系，使工具既能独立工作又能协作？
2. 短期记忆和长期记忆的适用场景和实现方式有什么区别？
3. 多个中间件组合时，执行顺序如何影响最终行为？
4. 结构化输出的错误重试机制在什么情况下可能失效？如何兜底？
5. `stream_mode=["messages", "custom"]` 组合输出时，如何区分不同类型的 chunk？
6. `Runnable` 的 invoke/stream/batch 三种执行方式在内部有什么联系？
7. 如果要给 Demo 4 添加多用户支持，需要修改哪些部分？
8. 从架构角度，Agent 和 LangGraph StateGraph 的关系是什么？
