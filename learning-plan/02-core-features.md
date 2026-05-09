# 阶段二：核心能力

> 对应文档：05-tools → 06-short-term-memory → 07-streaming → 08-structured-output
>
> 预计时间：3-5 天

---

## 学习目标

- 掌握工具定义与 `ToolRuntime` 上下文访问
- 理解短期记忆机制和消息管理策略
- 熟练使用流式输出的多种模式
- 掌握结构化输出的两种策略和错误处理

---

## 知识点清单

### 1. Tools 工具（05-tools）

- [ ] 使用 `@tool` 装饰器定义工具（函数签名 + docstring 即 schema）
- [ ] 自定义工具名称和描述
- [ ] 使用 Pydantic `args_schema` 定义复杂输入
- [ ] 通过 `ToolRuntime` 访问运行时上下文：
  - **State** — 短期记忆（`runtime.state["messages"]`）
  - **Context** — 不可变配置（`runtime.context.user_id`）
  - **Store** — 长期记忆（`runtime.store.get()`）
  - **Stream Writer** — 实时进度（`runtime.stream_writer()`）
  - **Execution Info** — 执行标识
- [ ] 使用 `Command` 从工具中更新 Agent 状态
- [ ] 理解 `ToolNode` 在 LangGraph 工作流中的作用
- [ ] 工具返回值类型：字符串 / 对象 / Command
- [ ] 工具错误处理：`handle_tool_errors` 参数
- [ ] 条件路由：`tools_condition`

**工具与运行时上下文关系**：

```
工具调用 → ToolRuntime
              ├── State（短期）   → 对话历史 / 自定义状态
              ├── Context（不可变）→ user_id / 会话信息
              ├── Store（长期）    → 用户偏好 / 知识库
              └── Stream Writer   → 实时进度反馈
```

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 工具抽象 | `langchain_core/tools/base.py` | `BaseTool` 的 invoke 机制、`args_schema` 的解析 |
| 函数转工具 | `langchain_core/tools/convert.py` | `@tool` 装饰器如何将函数转为 `BaseTool` |
| 工具渲染 | `langchain_core/tools/render.py` | 工具描述如何生成给模型的 prompt |

---

### 2. 短期记忆（06-short-term-memory）

- [ ] 理解 `Checkpointer` 的作用（`InMemorySaver` / `PostgresSaver`）
- [ ] 使用 `thread_id` 隔离不同对话
- [ ] 自定义 `AgentState` 添加自定义字段
- [ ] 三种消息管理策略：
  - **裁剪消息** — `@before_model` + `RemoveMessage`
  - **删除消息** — `RemoveMessage(id=...)` / `REMOVE_ALL_MESSAGES`
  - **摘要消息** — `SummarizationMiddleware`
- [ ] 在工具中读写短期记忆（`runtime.state` + `Command`）
- [ ] 在动态提示词中访问记忆（`@dynamic_prompt`）
- [ ] 在 `@before_model` 和 `@after_model` 中访问记忆

**记忆生命周期**：

```
对话开始 → 消息累加 → 接近上下文窗口限制 → 触发管理策略
              │                                    │
              │          ┌─────────────────────────┤
              │          │         │               │
              │       裁剪消息  删除消息        摘要消息
              │       (丢弃旧的) (精确删除)    (压缩保留)
              │          │         │               │
              └──────────┴─────────┴───────────────┘
                                    │
                              继续对话
```

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| Checkpointer | `langgraph/checkpoint/memory.py` | `InMemorySaver` 的存取机制 |
| AgentState | `langchain/agents/` | `AgentState` 的 TypedDict 定义 |

---

### 3. Streaming 流式输出（07-streaming）

- [ ] 理解三种流式模式：
  - `stream_mode="updates"` — Agent 步骤级更新
  - `stream_mode="messages"` — LLM Token 级流式
  - `stream_mode="custom"` — 自定义事件（stream_writer）
- [ ] 多模式组合：`stream_mode=["updates", "custom"]`
- [ ] v2 流式格式：`version="v2"` 统一输出
- [ ] 流式推理/思考 Token（`content_blocks` 中 `type: "reasoning"`）
- [ ] 流式工具调用（部分 JSON + 完成消息）
- [ ] 流式 + 人工干预（`HumanInTheLoopMiddleware`）
- [ ] 流式子 Agent（`subgraphs=True` + `name` 参数）

**流式模式对比**：

| 模式 | 粒度 | 适用场景 |
|------|------|---------|
| `updates` | 步骤级 | 展示 Agent 进度、调试流程 |
| `messages` | Token 级 | 打字机效果、实时显示 |
| `custom` | 自定义 | 长任务进度、中间状态 |

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 回调系统 | `langchain_core/callbacks/manager.py` | 流式 Token 如何通过回调传递 |
| 事件流 | `langchain_core/tracers/event_stream.py` | `astream_events` 的实现 |

---

### 4. 结构化输出（08-structured-output）

- [ ] 理解两种策略：
  - `ProviderStrategy` — 提供商原生结构化输出（更可靠）
  - `ToolStrategy` — 通过工具调用模拟（兼容性更广）
- [ ] 直接传 Schema 类型的简写方式
- [ ] 支持的 Schema 类型：Pydantic `BaseModel`、`dataclass`、`TypedDict`、JSON Schema
- [ ] 严格模式：`ProviderStrategy(Schema, strict=True)`
- [ ] Union 类型：`ToolStrategy(Union[SchemaA, SchemaB])`
- [ ] 错误处理与自动重试：
  - 多个结构化输出错误
  - Schema 验证错误
  - 自定义错误处理策略
- [ ] 访问结果：`result["structured_response"]`

**策略选择决策树**：

```
需要结构化输出
    │
    ├── 提供商支持原生？── 是 → ProviderStrategy（推荐）
    │                      └── 否 → ToolStrategy
    │
    └── 简写：直接传 Schema → LangChain 自动选择
```

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 结构化输出 | `langchain/agents/structured_output/` | 两种策略的实现差异 |
| 模型端 | `langchain_core/language_models/chat_models.py` | `with_structured_output` 的实现 |

---

## 实战 Demo：个人记账 Agent

> **难度**：⭐⭐⭐
>
> 详细实现见 [Demo 2 说明](./demos/demo2-accountant.md)

### 功能描述

构建一个有状态的个人记账助手：

1. 自定义 `AgentState`，包含 `balance: float` 和 `transactions: list`
2. 定义 3 个工具：`add_income`、`add_expense`、`get_summary`
3. 工具通过 `ToolRuntime` 读写 State，使用 `Command` 更新状态
4. 使用 `InMemorySaver` 实现对话记忆
5. 使用结构化输出返回 `TransactionReport`
6. 用 `stream_mode="updates"` 流式输出进度

### 预期产出

```
你: 我今天赚了 5000 块
Agent: 已记录收入 ¥5000.00，当前余额 ¥5000.00

你: 买菜花了 200
Agent: 已记录支出 ¥200.00，当前余额 ¥4800.00

你: 充值话费 50
Agent: 已记录支出 ¥50.00，当前余额 ¥4750.00

你: 查看账单
Agent: 📊 账单汇总
  收入: 1 笔，共 ¥5000.00
  支出: 2 笔，共 ¥250.00
  余额: ¥4750.00
  
  最近交易:
  1. +¥5000.00 (收入)
  2. -¥200.00 (买菜)
  3. -¥50.00 (充值话费)
```

---

## 阶段自检

完成阶段二后，你应该能回答以下问题：

1. `@tool` 装饰器中，函数签名、docstring、类型注解各自的作用是什么？
2. `ToolRuntime` 的 State、Context、Store 三者有什么区别？
3. `Command` 在工具返回值中的作用是什么？和直接返回字符串有什么区别？
4. `InMemorySaver` 和 `InMemoryStore` 分别用于什么场景？
5. `SummarizationMiddleware` 的 `trigger` 和 `keep` 参数分别控制什么？
6. `stream_mode="updates"` 和 `stream_mode="messages"` 的输出粒度有什么区别？
7. `ProviderStrategy` 和 `ToolStrategy` 分别适用于什么场景？
8. 结构化输出的自动重试机制是如何工作的？
