# 阶段一：基础入门

> 对应文档：00-install → 01-quickstart → 02-agents → 03-models → 04-messages
>
> 预计时间：2-3 天

---

## 学习目标

- 完成 LangChain 开发环境搭建
- 理解 Agent 的核心概念和执行循环（ReAct）
- 掌握模型初始化和三种调用方式（invoke / stream / batch）
- 理解消息体系和多模态内容

---

## 知识点清单

### 1. 安装与配置（00-install）

- [ ] 安装 `langchain` 核心包
- [ ] 安装至少一个模型提供商集成包（如 `langchain-openai`、`langchain-deepseek`）
- [ ] 配置 API Key 环境变量
- [ ] 配置 LangSmith 追踪（`LANGSMITH_TRACING` + `LANGSMITH_API_KEY`）

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 包入口 | `langchain/__init__.py` | 看顶层导出了哪些核心 API |

---

### 2. 快速开始（01-quickstart）

- [ ] 使用 `create_agent` 创建第一个 Agent
- [ ] 定义 `@tool` 并传给 Agent
- [ ] 使用 `agent.invoke()` 执行查询
- [ ] 理解 `model` 参数的字符串标识符格式（如 `"openai:gpt-5.4"`）
- [ ] 配置 `system_prompt`
- [ ] 理解 `InMemorySaver` 的作用和 `thread_id` 的意义

**核心概念**：

```
Agent = Model + Tools + System Prompt + Checkpointer
```

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| Agent 创建 | `langchain/agents/` | `create_agent` 如何组装各组件 |

---

### 3. Agents 智能代理（02-agents）

- [ ] 理解 ReAct 循环：推理 → 行动 → 观察 → 循环/结束
- [ ] 掌握静态模型 vs 动态模型选择
- [ ] 理解静态工具 vs 动态工具（过滤/运行时注册）
- [ ] 掌握 `SystemMessage` 与动态提示词 `@dynamic_prompt`
- [ ] 了解结构化输出的两种策略（ToolStrategy / ProviderStrategy）
- [ ] 了解 Agent 的 `name` 参数在多 Agent 系统中的作用

**ReAct 循环**：

```
用户输入 → 模型推理 → 需要工具？→ 是 → 调用工具 → 获取结果 → 模型推理 → ...
                                    → 否 → 返回最终答案
```

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| Agent 循环 | `langchain/agents/` | ReAct 循环的实现机制 |
| 动态模型 | `langchain/agents/middleware/` | `wrap_model_call` 如何拦截模型调用 |

---

### 4. Models 模型（03-models）

- [ ] 使用 `init_chat_model` 初始化不同提供商的模型
- [ ] 掌握模型参数：`temperature`、`max_tokens`、`timeout`、`max_retries`
- [ ] 三种调用方式：`invoke`（完整响应）、`stream`（流式 Token）、`batch`（批量并行）
- [ ] 工具绑定：`model.bind_tools([tool])` + `tool_calls` 解析
- [ ] 工具执行循环：模型生成调用 → 执行工具 → 结果回传模型
- [ ] 结构化输出：`model.with_structured_output(Schema)`
- [ ] 可配置模型：运行时切换模型

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 模型抽象 | `langchain_core/language_models/chat_models.py` | `BaseChatModel` 的 invoke/stream/batch 实现 |
| 工具绑定 | `langchain_core/language_models/chat_models.py` | `bind_tools` 如何将工具 schema 注入模型 |

---

### 5. Messages 消息（04-messages）

- [ ] 掌握 4 种消息类型：`SystemMessage`、`HumanMessage`、`AIMessage`、`ToolMessage`
- [ ] 理解 3 种传参方式：字符串、消息对象列表、字典格式
- [ ] 掌握 `AIMessage` 属性：`text`、`content_blocks`、`tool_calls`、`usage_metadata`
- [ ] 理解 `content_blocks` 标准化内容块（text / reasoning / image / tool_call 等）
- [ ] 了解多模态内容：图像、文件、音频、视频

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 消息基类 | `langchain_core/messages/base.py` | 消息的统一抽象 |
| AI 消息 | `langchain_core/messages/ai.py` | `tool_calls`、`usage_metadata` 的实现 |
| 工具消息 | `langchain_core/messages/tool.py` | `tool_call_id`、`artifact` 的设计 |
| 内容解析 | `langchain_core/messages/content.py` | `content_blocks` 的惰性解析机制 |

---

## 实战 Demo：多模型翻译助手

> **难度**：⭐⭐
>
> 详细实现见 [Demo 1 说明](./demos/demo1-translator.md)

### 功能描述

构建一个命令行翻译助手，对比不同模型提供商的翻译能力：

1. 使用 `init_chat_model` 初始化 2 个不同提供商的模型
2. 用 `SystemMessage` 设定翻译角色
3. 使用 `model.stream()` 流式输出翻译结果
4. 使用 `model.batch()` 批量翻译多条文本
5. 对比两个模型的翻译结果和 Token 用量

### 预期产出

```
=== 英译中翻译对比 ===

[OpenAI] 流式输出:
今天的天气非常美好，阳光明媚...

[DeepSeek] 流式输出:
今天的天气非常美丽，阳光灿烂...

=== 批量翻译 ===
输入: 3 条文本

[OpenAI] Token 用量: input=45, output=120, total=165
[DeepSeek] Token 用量: input=42, output=108, total=150
```

---

## 阶段自检

完成阶段一后，你应该能回答以下问题：

1. `create_agent` 的最小参数组合是什么？
2. `invoke` 和 `stream` 的返回类型分别是什么？
3. `tool_calls` 在 `AIMessage` 中的结构是什么？
4. `InMemorySaver` 的 `thread_id` 有什么作用？
5. `init_chat_model("gpt-5.4")` 和 `init_chat_model("openai:gpt-5.4")` 的区别是什么？
