# 工具调用 (Tool Calling)

> 使用丰富、类型安全的 UI 卡片展示智能体工具调用

智能体可以调用外部工具，如天气 API、计算器、网页搜索、数据库查询等。这些工具返回的结果通常是原始 JSON 格式。本文档将介绍如何为智能体的每一次工具调用渲染结构化的、类型安全的 UI 卡片，包括加载状态和错误处理。

## 工具调用的工作原理

当 LangGraph 智能体决定需要外部数据时，它会作为 AI 消息的一部分发出一个或多个工具调用。每个工具调用包含以下信息：

- **name**：被调用的工具名称（例如 `"get_weather"`、`"calculator"`）
- **args**：传递给工具的结构化参数
- **id**：唯一标识符，用于将调用与其结果关联

智能体运行时执行该工具，结果以 `ToolMessage` 的形式返回。`useStream` 钩子将所有这些信息统一到一个 `toolCalls` 数组中，你可以直接渲染它。

## 设置 useStream

第一步是将 `useStream` 连接到你的智能体后端。该钩子返回响应式状态，包括一个 `toolCalls` 数组，它会随着智能体的流式输出实时更新。

定义一个 TypeScript 接口来匹配你的智能体状态模式，并将其作为类型参数传递给 `useStream`，以获得类型安全的状态值访问。在下面的示例中，将 `typeof myAgent` 替换为你的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

### React

```tsx
import { useStream } from "@langchain/react";

const AGENT_URL = "http://localhost:2024";

export function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "tool_calling",
  });

  return (
    <div>
      {stream.messages.map((msg) => (
        <Message key={msg.id} message={msg} toolCalls={stream.toolCalls} />
      ))}
    </div>
  );
}
```

### Vue

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";

const AGENT_URL = "http://localhost:2024";

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "tool_calling",
});
</script>

<template>
  <div>
    <Message
      v-for="msg in stream.messages.value"
      :key="msg.id"
      :message="msg"
      :tool-calls="stream.toolCalls.value"
    />
  </div>
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";

  const AGENT_URL = "http://localhost:2024";

  const { messages, toolCalls, submit } = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "tool_calling",
  });
</script>

<div>
  {#each $messages as msg (msg.id)}
    <Message message={msg} toolCalls={$toolCalls} />
  {/each}
</div>
```

### Angular

```ts
import { Component } from "@angular/core";
import { useStream } from "@langchain/angular";

const AGENT_URL = "http://localhost:2024";

@Component({
  selector: "app-chat",
  template: `
    @for (msg of stream.messages(); track msg.id) {
      <app-message [message]="msg" [toolCalls]="stream.toolCalls()" />
    }
  `,
})
export class ChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "tool_calling",
  });
}
```

## ToolCallWithResult 类型

`toolCalls` 数组中的每个条目都是一个 `ToolCallWithResult` 对象：

```ts
interface ToolCallWithResult {
  call: {
    id: string;
    name: string;
    args: Record<string, unknown>;
  };
  result: ToolMessage | undefined;
  state: "pending" | "completed" | "error";
}
```

| 属性 | 描述 |
| --- | --- |
| `call.id` | 唯一 ID，与 AI 消息的 `tool_calls` 条目匹配 |
| `call.name` | 工具名称（例如 `"get_weather"`） |
| `call.args` | 智能体传递给工具的结构化参数 |
| `result` | `ToolMessage` 响应，工具执行完成后可用 |
| `state` | 生命周期状态：执行中为 `"pending"`，成功为 `"completed"`，失败为 `"error"` |

## 按消息过滤工具调用

一条 AI 消息可能触发多个工具调用，且你的聊天中可能包含多条 AI 消息。为了在每条消息下方渲染正确的工具卡片，需要通过匹配 `call.id` 与消息的 `tool_calls` 数组来进行过滤：

```tsx
function Message({
  message,
  toolCalls,
}: {
  message: AIMessage;
  toolCalls: ToolCallWithResult[];
}) {
  const messageToolCalls = toolCalls.filter((tc) =>
    message.tool_calls?.find((t) => t.id === tc.call.id)
  );

  return (
    <div>
      <p>{message.content}</p>
      {messageToolCalls.map((tc) => (
        <ToolCard key={tc.call.id} toolCall={tc} />
      ))}
    </div>
  );
}
```

## 构建专用工具卡片

与其直接显示原始 JSON，不如为每个工具构建专用的 UI 组件。使用 `call.name` 来选择正确的卡片：

```tsx
function ToolCard({ toolCall }: { toolCall: ToolCallWithResult }) {
  if (toolCall.state === "pending") {
    return <LoadingCard name={toolCall.call.name} />;
  }

  if (toolCall.state === "error") {
    return <ErrorCard name={toolCall.call.name} error={toolCall.result} />;
  }

  switch (toolCall.call.name) {
    case "get_weather":
      return <WeatherCard args={toolCall.call.args} result={toolCall.result} />;
    case "calculator":
      return (
        <CalculatorCard args={toolCall.call.args} result={toolCall.result} />
      );
    case "web_search":
      return <SearchCard args={toolCall.call.args} result={toolCall.result} />;
    default:
      return <GenericToolCard toolCall={toolCall} />;
  }
}
```

### 天气卡片示例

```tsx
function WeatherCard({
  args,
  result,
}: {
  args: { location: string };
  result: ToolMessage;
}) {
  const data = JSON.parse(result.content as string);

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2">
        <CloudIcon />
        <h3 className="font-semibold">{args.location}</h3>
      </div>
      <div className="mt-2 text-3xl font-bold">{data.temperature}°F</div>
      <p className="text-muted-foreground">{data.condition}</p>
    </div>
  );
}
```

### 加载和错误状态

始终处理 pending 和 error 状态，以给用户提供清晰的反馈：

```tsx
function LoadingCard({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border p-4 animate-pulse">
      <Spinner />
      <span>正在运行 {name}...</span>
    </div>
  );
}

function ErrorCard({ name, error }: { name: string; error?: ToolMessage }) {
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 p-4">
      <h3 className="font-semibold text-red-700">{name} 出错</h3>
      <p className="text-sm text-red-600">
        {error?.content ?? "工具执行失败"}
      </p>
    </div>
  );
}
```

## 类型安全的工具参数

如果你的工具使用结构化模式定义，可以使用 `ToolCallFromTool` 工具类型来获取完全类型化的 `args`：

```ts
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const getWeather = tool(async ({ location }) => { /* ... */ }, {
  name: "get_weather",
  description: "获取指定位置的当前天气",
  schema: z.object({
    location: z.string().describe("城市名称"),
  }),
});

type WeatherToolCall = ToolCallFromTool<typeof getWeather>;
// WeatherToolCall.call.args 现在是 { location: string }
```

使用 `ToolCallFromTool` 可以获得编译时安全性。如果工具模式发生变化，你的 UI 组件将立即标记出类型错误。

## 与流式文本内联渲染工具调用

工具调用通常与流式文本交错到达。`useStream` 钩子使 `toolCalls` 与流保持同步，因此 pending 卡片会在智能体发出调用的瞬间显示，在工具执行完成之前。

这意味着用户会看到：

1. AI 的文本随着流式传输逐步显示
2. 工具调用发出时立即显示加载卡片
3. 工具完成后，卡片更新显示结果

工具调用会就地更新。相同的 `call.id` 从 `"pending"` 过渡到 `"completed"`（或 `"error"`），因此你的 UI 会使用新状态重新渲染相同的组件。

## 处理多个并发工具调用

智能体可以并行调用多个工具。`toolCalls` 数组将同时包含多个 `state: "pending"` 的条目。每个工具独立解析，因此你的 UI 应该优雅地处理部分完成的情况：

```tsx
function ToolCallList({ toolCalls }: { toolCalls: ToolCallWithResult[] }) {
  const pending = toolCalls.filter((tc) => tc.state === "pending");
  const completed = toolCalls.filter((tc) => tc.state === "completed");

  return (
    <div className="space-y-2">
      {completed.map((tc) => (
        <ToolCard key={tc.call.id} toolCall={tc} />
      ))}
      {pending.map((tc) => (
        <LoadingCard key={tc.call.id} name={tc.call.name} />
      ))}
    </div>
  );
}
```

## 最佳实践

构建工具调用 UI 时，请遵循以下准则：

- **始终处理所有三种状态**：`pending`、`completed` 和 `error`。用户不应该看到空白卡片。
- **安全地解析结果**。工具结果以字符串形式到达。将 `JSON.parse()` 包装在 try/catch 中，并在解析失败时显示回退方案。
- **提供通用回退方案**。不是每个工具都需要专门的卡片。对于未知的工具名称，渲染一个可折叠的 JSON 视图。
- **在加载期间显示工具名称和参数**。用户想知道智能体在做什么，即使在结果到达之前。
- **保持卡片紧凑**。工具卡片与聊天消息内联显示。避免用过大的组件淹没对话。
