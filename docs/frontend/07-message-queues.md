# 消息队列

> 在智能体按顺序处理消息的同时，将多条消息加入队列并进行管理

消息队列功能允许用户在智能体完成当前消息处理之前，快速连续发送多条消息。每条消息都会在服务器端排队，并按顺序依次处理，让您能够完全查看和控制待处理的队列。

此功能需要 LangGraph 智能体服务器。使用 `langgraph dev` 在本地运行您的智能体，或将其部署到 LangSmith 以使用此模式。

## 为什么需要消息队列？

在典型的聊天界面中，用户必须等待智能体完成响应后才能发送下一条消息。这在以下场景中会造成不便：

- **批量提问**：用户希望一次性提出五个相关的问题，而不是等待每个答案
- **连续追问**：在智能体仍在工作时，提交澄清说明或额外上下文
- **自动化测试序列**：以编程方式发送一系列提示词来验证智能体行为
- **数据录入工作流**：一个接一个地输入结构化数据进行处理

消息队列通过立即接受所有提交并按顺序处理来解决这些问题。

## 工作原理

底层实现上，LangGraph 使用 `multitaskStrategy: "enqueue"` 来管理并发提交。当智能体已经在处理消息时提交新消息，新消息会被添加到服务器端队列中。当前运行完成后，下一条队列中的消息会自动被处理。

`useStream` Hook 提供了一个 `queue` 属性，用于实时查看待处理消息：

| 属性 | 类型 | 描述 |
| --- | --- | --- |
| `queue.entries` | `QueueEntry[]` | 所有待处理队列条目的数组 |
| `queue.size` | `number` | 当前队列中的条目数量 |
| `queue.cancel(id)` | `(id: string) => Promise` | 通过 ID 取消特定队列条目 |
| `queue.clear()` | `() => Promise` | 取消所有队列条目 |

每个 `QueueEntry` 对象包含以下字段：

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| `id` | `string` | 队列条目的唯一标识符 |
| `values` | `object` | 提交的输入值（包括消息） |
| `options` | `object` | 提交时传递的任何额外选项 |
| `createdAt` | `string` | 条目创建的 ISO 时间戳 |

## 设置 `useStream`

定义一个 TypeScript 接口以匹配您的智能体状态模式，并将其作为类型参数传递给 `useStream`，以实现对状态值的类型安全访问。在以下示例中，将 `typeof myAgent` 替换为您的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

### React

```tsx
import { useStream } from "@langchain/react";

function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "message_queue",
  });

  const handleSubmit = (text: string) => {
    stream.submit({
      messages: [{ type: "human", content: text }],
    });
  };

  // 访问队列状态
  const pendingCount = stream.queue.size;
  const entries = stream.queue.entries;

  return (
    <div>
      <MessageList messages={stream.messages} />
      {pendingCount > 0 && <QueueList entries={entries} queue={stream.queue} />}
      <ChatInput onSubmit={handleSubmit} />
    </div>
  );
}
```

### Vue

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";

const stream = useStream<typeof myAgent>({
  apiUrl: "http://localhost:2024",
  assistantId: "message_queue",
});

function handleSubmit(text: string) {
  stream.submit({
    messages: [{ type: "human", content: text }],
  });
}

// 在脚本中通过 .value 访问队列状态
const pendingCount = computed(() => stream.queue.value.size);
const entries = computed(() => stream.queue.value.entries);
</script>

<template>
  <div>
    <MessageList :messages="stream.messages" />
    <QueueList v-if="stream.queue.size > 0" :entries="stream.queue.entries" :queue="stream.queue" />
    <ChatInput @submit="handleSubmit" />
  </div>
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";

  const { messages, submit, queue } = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "message_queue",
  });

  function handleSubmit(text: string) {
    submit({
      messages: [{ type: "human", content: text }],
    });
  }
</script>

<div>
  <MessageList messages={$messages} />
  {#if $queue.size > 0}
    <QueueList entries={$queue.entries} queue={$queue} />
  {/if}
  <ChatInput on:submit={(e) => handleSubmit(e.detail)} />
</div>
```

### Angular

```ts
import { Component } from "@angular/core";
import { useStream } from "@langchain/angular";

@Component({
  selector: "app-chat",
  template: `
    <message-list [messages]="stream.messages()" />
    @if (stream.queue().size > 0) {
      <queue-list [entries]="stream.queue().entries" [queue]="stream.queue()" />
    }
    <chat-input (onSubmit)="handleSubmit($event)" />
  `,
})
export class ChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "message_queue",
  });

  handleSubmit(text: string) {
    this.stream.submit({
      messages: [{ type: "human", content: text }],
    });
  }
}
```

## 显示队列

构建一个 `QueueList` 组件来显示每条待处理消息以及取消按钮。这让用户能够看到正在等待的内容，并移除不再需要的条目。

```tsx
function QueueList({ entries, queue }) {
  return (
    <div className="queue-panel">
      <div className="queue-header">
        <span>队列消息 ({entries.length})</span>
        <button onClick={() => queue.clear()}>全部清除</button>
      </div>
      <ul className="queue-entries">
        {entries.map((entry) => {
          const text = entry.values?.messages?.[0]?.content ?? "Unknown";
          return (
            <li key={entry.id} className="queue-entry">
              <span className="queue-text">{text}</span>
              <span className="queue-time">
                {new Date(entry.createdAt).toLocaleTimeString()}
              </span>
              <button
                className="queue-cancel"
                onClick={() => queue.cancel(entry.id)}
              >
                取消
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

显示每条队列消息的前几个字符作为预览，这样用户可以快速识别需要取消的条目，而无需阅读完整的消息内容。

## 取消队列消息

您有两个层级的取消操作：

### 取消单个条目

通过 ID 从队列中移除特定消息。智能体将跳过它并继续处理下一条条目。

```ts
await queue.cancel(entryId);
```

### 清除整个队列

一次性移除所有待处理的消息。当用户改变上下文或想要重新开始时非常有用。

```ts
await queue.clear();
```

取消队列条目只会影响尚未开始处理的消息。如果智能体已经开始处理某条消息，从队列中取消它没有效果。使用 `stream.stop()` 来中断当前运行。

## 使用 `onCreated` 链式提交后续消息

当新运行创建时，`onCreated` 回调会被触发，为您提供了一个以编程方式提交后续消息的钩子。这对于构建多步骤工作流非常有用，其中下一个问题取决于前一个提交被接受。

```ts
stream.submit(
  { messages: [{ type: "human", content: "什么是量子计算？" }] },
  {
    onCreated(run) {
      console.log("运行已创建:", run.run_id);
      // 链式提交后续消息
      stream.submit({
        messages: [{ type: "human", content: "给我一个简单的类比。" }],
      });
    },
  }
);
```

这种模式会自然地填充队列。第一条消息立即开始处理，后续消息排在它后面。

## 开始新会话

当用户想要开始全新的对话时，使用 `switchThread(null)` 创建一个新会话。这会清除当前的消息历史和队列。

### React

```tsx
function NewThreadButton() {
  const stream = useStream<typeof myAgent>({ /* ... */ });

  return (
    <button onClick={() => stream.switchThread(null)}>
      新对话
    </button>
  );
}
```

### Vue

```vue
<script setup lang="ts">
const stream = useStream<typeof myAgent>({ /* ... */ });
</script>

<template>
  <button @click="stream.switchThread(null)">新对话</button>
</template>
```

### Svelte

```svelte
<script lang="ts">
  const { switchThread } = useStream<typeof myAgent>({ /* ... */ });
</script>

<button on:click={() => switchThread(null)}>新对话</button>
```

### Angular

```ts
stream = useStream<typeof myAgent>({ /* ... */ });

// 在模板中：
// <button (click)="stream.switchThread(null)">新对话</button>
```

## 完整示例

将所有内容整合在一起，以下是一个带有队列管理功能的完整聊天组件：

```tsx
function QueueChat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "message_queue",
  });

  const [input, setInput] = useState("");

  const handleSubmit = () => {
    if (!input.trim()) return;
    stream.submit({
      messages: [{ type: "human", content: input.trim() }],
    });
    setInput("");
  };

  return (
    <div className="chat-container">
      <header>
        <h2>队列聊天</h2>
        <button onClick={() => stream.switchThread(null)}>新会话</button>
      </header>

      <div className="messages">
        {stream.messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {stream.isLoading && <TypingIndicator />}
      </div>

      {stream.queue.size > 0 && (
        <div className="queue-panel">
          <strong>队列中 ({stream.queue.size})</strong>
          <button onClick={() => stream.queue.clear()}>全部清除</button>
          {stream.queue.entries.map((entry) => (
            <div key={entry.id} className="queue-item">
              <span>{entry.values?.messages?.[0]?.content}</span>
              <button onClick={() => stream.queue.cancel(entry.id)}>×</button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息（可以发送多条！）"
        />
        <button type="submit">发送</button>
      </form>
    </div>
  );
}
```

## 最佳实践

- **限制队列大小**：虽然客户端对队列大小没有硬性限制，但要注意非常大的队列会降低用户体验。考虑在队列超过合理阈值（例如 10 项）时显示警告。
- **显示队列位置**：为每个队列项编号，让用户知道处理顺序。
- **保持输入框聚焦**：提交后保持输入框聚焦，让用户可以立即输入下一条消息。
- **添加过渡动画**：当队列项开始处理时，平滑地将它们从队列面板移动到消息列表。
- **优雅处理错误**：如果队列消息失败，在不阻塞后续队列条目的前提下显示错误。
- **对快速提交进行防抖**：对于自动或程序化的提交，在消息之间添加小延迟以避免压垮服务器。
