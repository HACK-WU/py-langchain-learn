# LangChain 前端开发概述

构建与 LangChain 智能体实时流式交互的生成式 UI。

---

## 概述

为使用 `create_agent` 创建的代理构建丰富、交互式的前端应用。本文档涵盖了从基础消息渲染到高级工作流（如人工介入审批和时间旅行调试）的所有模式。

---

## 架构

所有模式都遵循相同的架构：`create_agent` 后端通过 `useStream` Hook 将状态流式传输到前端。

```
┌─────────────────┐      stream      ┌─────────────────┐
│   useStream()   │ ◄────────────────│  create_agent() │
│    (前端)        │                  │    (后端)       │
│                 │ ───────────────► │                 │
└─────────────────┘      submit      └─────────────────┘
```

在后端，`create_agent` 会生成一个已编译的 LangGraph 图，该图暴露了一个流式 API。在前端，`useStream` Hook 连接到该 API 并提供响应式状态——包括消息、工具调用、中断、历史记录等——你可以使用任何框架来渲染这些内容。

### 后端示例

```python
from langchain import create_agent
from langgraph.checkpoint.memory import MemorySaver

# 创建智能体
agent = create_agent(
    model="openai:gpt-5.4",
    tools=[get_weather, search_web],
    checkpointer=MemorySaver(),
)
```

### 类型定义

```ts
export interface GraphState {
  messages: BaseMessage[];
}
```

### 前端示例（React）

```tsx
import { useStream } from "@langchain/react";
import type { GraphState } from "./types";

function Chat() {
  const stream = useStream<GraphState>({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
  });

  return (
    <div>
      {stream.messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}
    </div>
  );
}
```

### 多框架支持

`useStream` 支持 React、Vue、Svelte 和 Angular：

```ts
import { useStream } from "@langchain/react";   // React
import { useStream } from "@langchain/vue";      // Vue
import { useStream } from "@langchain/svelte";   // Svelte
import { useStream } from "@langchain/angular";  // Angular
```

---

## 开发模式

### 渲染消息和输出

| 模式 | 描述 | 文档 |
|------|------|------|
| **Markdown 消息** | 解析并渲染流式 Markdown，支持正确的格式和代码高亮 | [markdown-messages.md](./markdown-messages.md) |
| **结构化输出** | 将类型化的智能体响应渲染为自定义 UI 组件，而非纯文本 | [structured-output.md](./structured-output.md) |
| **推理令牌** | 在可折叠块中显示模型思考过程 | [reasoning-tokens.md](./reasoning-tokens.md) |
| **生成式 UI** | 使用 json-render 从自然语言提示生成 AI 用户界面 | [generative-ui.md](./generative-ui.md) |

### 显示智能体操作

| 模式 | 描述 | 文档 |
|------|------|------|
| **工具调用** | 以丰富的类型安全 UI 卡片形式展示工具调用，支持加载和错误状态 | [tool-calling.md](./tool-calling.md) |
| **人工介入** | 暂停智能体以进行人工审核，支持批准、拒绝和编辑工作流 | [human-in-the-loop.md](./human-in-the-loop.md) |

### 管理对话

| 模式 | 描述 | 文档 |
|------|------|------|
| **分支对话** | 编辑消息、重新生成响应，并导航对话分支 | [branching-chat.md](./branching-chat.md) |
| **消息队列** | 在智能体顺序处理时排队多条消息 | [message-queues.md](./message-queues.md) |

### 高级流式处理

| 模式 | 描述 | 文档 |
|------|------|------|
| **加入和重新加入流** | 断开后重新连接到运行中的智能体流，不会丢失进度 | [join-rejoin-streams.md](./join-rejoin-streams.md) |
| **时间旅行** | 检查、导航并从对话历史中的任何检查点恢复 | [time-travel.md](./time-travel.md) |

---

## 集成

`useStream` 与 UI 无关。你可以将其与任何组件库或生成式 UI 框架一起使用。

### AI Elements

可组合的 shadcn/ui 组件，用于 AI 聊天：`Conversation`、`Message`、`Tool`、`Reasoning`。

### assistant-ui

无头 React 框架，内置线程管理、分支和附件支持。

### OpenUI

用于数据丰富报表和仪表板的生成式 UI 库，使用 openui-lang 组件 DSL。

---

## 相关文档

- [Markdown 消息](./markdown-messages.md) - 流式 Markdown 渲染
- [结构化输出](./structured-output.md) - 类型化响应组件
- [推理令牌](./reasoning-tokens.md) - 模型思考过程显示
- [生成式 UI](./generative-ui.md) - AI 生成界面
- [工具调用](./tool-calling.md) - 工具调用卡片
- [人工介入](./human-in-the-loop.md) - 人工审核工作流
- [分支对话](./branching-chat.md) - 对话分支管理
- [消息队列](./message-queues.md) - 消息顺序处理
- [加入/重新加入流](./join-rejoin-streams.md) - 流式连接管理
- [时间旅行](./time-travel.md) - 历史检查点导航

---

*本文档由 LangChain 官方文档翻译整理*
