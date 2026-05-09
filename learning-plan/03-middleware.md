# 阶段三：高级编排

> 对应文档：09-middleware-overview → 10-middleware-built-in → 11-middleware-custom
>
> 预计时间：3-5 天

---

## 学习目标

- 理解中间件体系在 Agent 执行循环中的位置和作用
- 掌握 6 个钩子类型及其适用场景
- 熟练使用内置中间件（摘要、人工干预、PII 检测、重试、回退等）
- 能够自定义中间件（装饰器方式和类方式）

---

## 知识点清单

### 1. 中间件概述（09-middleware-overview）

- [ ] 理解中间件的四大用途：追踪、转换、重试/回退、护栏
- [ ] 掌握 6 个钩子类型：

**节点式钩子**（按顺序执行）：

| 钩子 | 时机 | 典型用途 |
|------|------|---------|
| `before_agent` | Agent 启动前（每次调用一次） | 初始化、前置检查 |
| `before_model` | 每次模型调用前 | 消息裁剪、上下文注入 |
| `after_model` | 每次模型响应后 | 护栏、内容过滤 |
| `after_agent` | Agent 完成后（每次调用一次） | 日志、清理 |

**包裹式钩子**（嵌套执行，控制 handler 调用）：

| 钩子 | 时机 | 典型用途 |
|------|------|---------|
| `wrap_model_call` | 围绕每次模型调用 | 重试、回退、缓存、动态模型 |
| `wrap_tool_call` | 围绕每次工具调用 | 错误处理、监控、重试 |

**Agent 循环与中间件位置**：

```
开始 → before_agent → before_model → [模型调用]
                                            │
                                      after_model
                                          │
                                   ┌──────┴──────┐
                                   │              │
                              需要工具        无需工具
                                   │              │
                           wrap_tool_call    after_agent → 结束
                                   │
                              [工具执行]
                                   │
                           before_model → [模型调用] → ...
```

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 中间件基类 | `langchain/agents/middleware/` | `AgentMiddleware` 的钩子调度机制 |
| 执行顺序 | `langchain/agents/middleware/` | before 顺序、after 逆序、wrap 嵌套 |

---

### 2. 内置中间件（10-middleware-built-in）

- [ ] **SummarizationMiddleware** — 自动摘要长对话
  - `trigger`：`("tokens", N)` / `("messages", N)` / `("fraction", 0.8)`
  - `keep`：保留最近 N 条消息或比例
- [ ] **HumanInTheLoopMiddleware** — 人工审批工具调用
  - `interrupt_on`：按工具名配置中断
  - `allowed_decisions`：approve / edit / reject
- [ ] **ModelCallLimitMiddleware** — 模型调用次数限制
  - `thread_limit` / `run_limit` / `exit_behavior`
- [ ] **ToolCallLimitMiddleware** — 工具调用次数限制
  - 全局限制 + 特定工具限制
- [ ] **ModelFallbackMiddleware** — 模型回退
- [ ] **PIIMiddleware** — 个人身份信息检测
  - 4 种策略：block / redact / mask / hash
  - 自定义检测器：正则字符串 / 编译正则 / 自定义函数
- [ ] **TodoListMiddleware** — 任务规划和跟踪
- [ ] **LLMToolSelectorMiddleware** — 智能工具选择（10+ 工具时）
- [ ] **ToolRetryMiddleware** — 工具重试（指数退避）
- [ ] **ModelRetryMiddleware** — 模型重试
- [ ] **LLMToolEmulator** — LLM 模拟工具响应（测试用）
- [ ] **ContextEditingMiddleware** — 上下文编辑（清除旧工具输出）
- [ ] **ShellToolMiddleware** — Shell 工具（本地 / Docker）
- [ ] **FilesystemFileSearchMiddleware** — 文件搜索工具
- [ ] **FilesystemMiddleware** — 文件系统读写工具（Deep Agents）
- [ ] **SubAgentMiddleware** — 子 Agent 委托

**内置中间件速查**：

| 场景 | 推荐中间件 |
|------|-----------|
| 对话太长 | SummarizationMiddleware |
| 敏感操作需审批 | HumanInTheLoopMiddleware |
| 防止成本失控 | ModelCallLimitMiddleware + ToolCallLimitMiddleware |
| 模型不稳定 | ModelFallbackMiddleware + ModelRetryMiddleware |
| 隐私保护 | PIIMiddleware |
| 工具太多 | LLMToolSelectorMiddleware |
| 工具 API 不稳定 | ToolRetryMiddleware |

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 摘要中间件 | `langchain/agents/middleware/` | `SummarizationMiddleware` 的触发和摘要逻辑 |
| 人工干预 | `langchain/agents/middleware/` | `HumanInTheLoopMiddleware` 的中断和恢复机制 |
| PII 检测 | `langchain/agents/middleware/` | `PIIMiddleware` 的检测和脱敏流程 |

---

### 3. 自定义中间件（11-middleware-custom）

- [ ] **装饰器方式** — 适用于单钩子、无复杂配置
  - `@before_model(can_jump_to=["end"])`
  - `@after_model`
  - `@wrap_model_call`
  - `@wrap_tool_call`
- [ ] **类方式** — 适用于多钩子、需要配置、需同步/异步
  - 继承 `AgentMiddleware`
  - 实现 `before_model` / `after_model` / `wrap_model_call` 等
  - 异步版本：`abefore_model` / `aafter_model`
- [ ] **状态更新**：
  - 节点式：返回 dict 更新状态
  - 包裹式：返回 `ExtendedModelResponse`（含 `Command`）
- [ ] **自定义状态 Schema**：
  - `AgentMiddleware[CustomState]` + `state_schema = CustomState`
  - `@before_model(state_schema=CustomState)`
- [ ] **执行顺序**：
  - `before_*`：从先到后
  - `after_*`：从后到先（逆序）
  - `wrap_*`：嵌套（第一个中间件包裹所有其他）
- [ ] **跳转控制**：
  - `jump_to`：`"end"` / `"tools"` / `"model"`
  - `can_jump_to` 装饰器参数声明允许的跳转目标
- [ ] **常见模式**：
  - 动态提示词（修改 `system_message`）
  - 动态模型选择（`request.override(model=...)`）
  - 动态工具选择（`request.override(tools=...)`）
  - 工具调用监控
  - Anthropic 提示缓存

**装饰器 vs 类对比**：

| 维度 | 装饰器 | 类 |
|------|--------|-----|
| 复杂度 | 简单 | 较复杂 |
| 钩子数量 | 1 个 | 多个 |
| 配置能力 | 无 | 构造函数参数 |
| 异步支持 | 无 | 有 |
| 状态扩展 | `state_schema` 参数 | `state_schema` 类属性 |
| 适用场景 | 快速原型、单一职责 | 生产级、多钩子协作 |

**源码阅读**：

| 目标 | 路径 | 关注点 |
|------|------|--------|
| 装饰器实现 | `langchain/agents/middleware/` | `@before_model` 等如何将函数转为中间件 |
| 基类 | `langchain/agents/middleware/` | `AgentMiddleware` 的钩子注册和调用链 |
| 执行顺序 | `langchain/agents/middleware/` | 中间件链的编排逻辑 |

---

## 实战 Demo：安全客服 Agent

> **难度**：⭐⭐⭐⭐
>
> 详细实现见 [Demo 3 说明](./demos/demo3-secure-customer-service.md)

### 功能描述

构建一个带安全防护的客服 Agent：

1. **工具**：`query_order`（查订单）、`refund_order`（退款）、`send_coupon`（发优惠券）
2. **PII 防护**：`PIIMiddleware` 脱敏手机号和邮箱
3. **人工审批**：`HumanInTheLoopMiddleware` 对退款操作强制审批
4. **上下文管理**：`SummarizationMiddleware` 自动摘要长对话
5. **动态模型**：自定义 `@wrap_model_call` 根据对话轮数切换模型
6. **输出护栏**：自定义 `@after_model` 检测并替换敏感词
7. **容错**：`ModelFallbackMiddleware` + `ToolRetryMiddleware`

### 预期产出

```
你: 我的手机号 13800138000 想查订单 ORD-2024-001
Agent: [PII] 检测到手机号，已脱敏为 138****8000
Agent: 查询到订单 ORD-2024-001：iPhone 15 Pro，¥8999，已发货

你: 我要退款
Agent: 退款操作需要人工审批...
审批人: 批准 ✓
Agent: 退款已处理，预计 3-5 个工作日到账

你: 给我发个优惠券
Agent: 已发放 50 元优惠券到您的账户

[中间件日志]
- PII: 检测并脱敏手机号 1 次
- 模型切换: 短对话使用 gpt-5.4-mini
- 人工干预: 1 次退款审批（已批准）
- 输出护栏: 0 次拦截
```

---

## 阶段自检

完成阶段三后，你应该能回答以下问题：

1. 节点式钩子和包裹式钩子的核心区别是什么？
2. `before_*` 和 `after_*` 钩子的执行顺序有什么不同？为什么？
3. `wrap_model_call` 中 `handler` 参数的作用是什么？不调用 handler 会怎样？
4. `SummarizationMiddleware` 的三种 `trigger` 类型分别如何工作？
5. `HumanInTheLoopMiddleware` 为什么必须配合 `Checkpointer` 使用？
6. `PIIMiddleware` 的四种处理策略分别适用于什么场景？
7. `jump_to` 的三个可用目标（end / tools / model）分别跳转到哪里？
8. 装饰器方式定义中间件时，`can_jump_to` 参数有什么作用？
9. 多个中间件返回 `ExtendedModelResponse` 时，Commands 如何合并？
10. 自定义中间件中，`request.override()` 的作用是什么？能修改哪些内容？
