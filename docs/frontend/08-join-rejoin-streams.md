# 加入与重新加入流

> 断开与正在运行的智能体流的连接，并在之后重新连接

加入与重新加入功能允许你从正在运行的智能体流中断开连接而不停止智能体，然后在稍后重新连接。当客户端离开期间，智能体继续在服务器端执行，你可以在断开的位置精确地恢复接收流。

此功能需要 LangGraph 智能体服务器。使用 `langgraph dev` 在本地运行你的智能体，或将其部署到 LangSmith 以使用此模式。

## 为什么需要加入与重新加入？

传统的流式 API 将客户端和服务器紧密耦合：如果客户端断开连接，流就会丢失。加入与重新加入打破了这种耦合，实现了几个重要的模式：

- **网络中断**：移动用户在信号塔或 Wi-Fi 网络之间切换时可以无缝恢复
- **页面导航**：用户离开聊天页面后稍后返回而不会丢失进度
- **移动应用后台运行**：被操作系统挂起的应用在返回前台时可以重新加入流
- **长时间运行的任务**：执行多分钟操作的智能体（研究、代码生成、数据分析），用户无需保持页面打开
- **多设备切换**：在手机上开始对话，在桌面上继续

## 核心概念

加入/重新加入模式涉及三个关键机制：

| 方法 / 选项 | 用途 |
| --- | --- |
| `stream.stop()` | 断开客户端与流的连接而不停止智能体 |
| `stream.joinStream(runId)` | 通过运行 ID 重新连接到现有流 |
| `onDisconnect: "continue"` | 提交选项，告诉服务器在客户端断开后继续运行 |
| `streamResumable: true` | 提交选项，启用流在稍后重新加入 |

`stream.stop()` 与取消运行有本质区别。停止仅断开客户端连接，智能体继续在服务器端处理。要实际取消智能体的执行，你需要使用中断或取消机制。

## 设置 `useStream`

关键的设置步骤是从 `onCreated` 回调中捕获 `run_id`，以便稍后重新加入。

定义一个与你的智能体状态模式匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以实现对状态值的类型安全访问。在以下示例中，将 `typeof myAgent` 替换为你的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

### React

```tsx
import { useStream } from "@langchain/react";
import { useState } from "react";

function Chat() {
  const [savedRunId, setSavedRunId] = useState<string | null>(null);

  const stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "join_rejoin",
    onCreated(run) {
      setSavedRunId(run.run_id);
    },
  });

  const isConnected = stream.isLoading;

  return (
    <div>
      <ConnectionStatus connected={isConnected} />
      <MessageList messages={stream.messages} />
      <ChatControls
        stream={stream}
        savedRunId={savedRunId}
        isConnected={isConnected}
      />
    </div>
  );
}
```

### Vue

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";
import { ref, computed } from "vue";

const savedRunId = ref<string | null>(null);

const stream = useStream<typeof myAgent>({
  apiUrl: "http://localhost:2024",
  assistantId: "join_rejoin",
  onCreated(run) {
    savedRunId.value = run.run_id;
  },
});

const isConnected = computed(() => stream.isLoading.value);
</script>

<template>
  <div>
    <ConnectionStatus :connected="isConnected" />
    <MessageList :messages="stream.messages" />
    <ChatControls
      :stream="stream"
      :savedRunId="savedRunId"
      :isConnected="isConnected"
    />
  </div>
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";

  let savedRunId: string | null = null;

  const { messages, isLoading, submit, stop, joinStream } = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "join_rejoin",
    onCreated(run) {
      savedRunId = run.run_id;
    },
  });
</script>

<div>
  <ConnectionStatus connected={$isLoading} />
  <MessageList messages={$messages} />
  <ChatControls
    {savedRunId}
    isConnected={$isLoading}
    on:disconnect={() => stop()}
    on:rejoin={() => joinStream(savedRunId)}
  />
</div>
```

### Angular

```ts
import { Component, signal } from "@angular/core";
import { useStream } from "@langchain/angular";

@Component({
  selector: "app-chat",
  template: `
    <connection-status [connected]="stream.isLoading()" />
    <message-list [messages]="stream.messages()" />
    <chat-controls
      [stream]="stream"
      [savedRunId]="savedRunId()"
      [isConnected]="stream.isLoading()"
    />
  `,
})
export class ChatComponent {
  savedRunId = signal<string | null>(null);

  stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "join_rejoin",
    onCreated: (run) => {
      this.savedRunId.set(run.run_id);
    },
  });
}
```

## 使用可恢复选项提交

当你提交消息时，传递 `onDisconnect: "continue"` 和 `streamResumable: true` 以启用加入/重新加入流程：

```ts
stream.submit(
  { messages: [{ type: "human", content: text }] },
  {
    onDisconnect: "continue",
    streamResumable: true,
  }
);
```

| 选项 | 默认值 | 描述 |
| --- | --- | --- |
| `onDisconnect` | `"cancel"` | 客户端断开连接时发生的情况。`"continue"` 保持智能体运行；`"cancel"` 停止它。 |
| `streamResumable` | `false` | 当为 `true` 时，服务器保留流状态，以便客户端稍后重新加入。 |

始终同时使用这两个选项。设置 `onDisconnect: "continue"` 而不设置 `streamResumable: true` 意味着智能体会继续运行，但你无法重新加入流来查看其输出。

## 断开与流的连接

调用 `stream.stop()` 断开客户端连接。智能体继续在服务器端处理。

```ts
stream.stop();
```

调用 `stop()` 后：

- `stream.isLoading` 变为 `false`
- 消息列表保留断开连接前接收到的所有消息
- 智能体继续在服务器上运行
- 在重新加入之前不会接收到新消息

## 重新加入流

使用保存的运行 ID 调用 `stream.joinStream(runId)` 以重新连接：

```ts
stream.joinStream(savedRunId);
```

重新加入后：

- `stream.isLoading` 再次变为 `true`
- 断开连接期间生成的任何消息都会被传递
- 新的流式消息实时恢复
- 如果智能体已经完成，你会立即收到最终状态

## 构建连接状态指示器

视觉指示器帮助用户了解他们是否正在主动接收来自智能体的更新。

```tsx
function ConnectionStatus({ connected }: { connected: boolean }) {
  return (
    <div className="connection-status">
      <span
        className={`status-dot ${connected ? "connected" : "disconnected"}`}
      />
      <span className="status-text">
        {connected ? "已连接" : "已断开"}
      </span>
    </div>
  );
}
```

使用绿色/红色圆点样式化指示器：

```css
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.status-dot.connected {
  background-color: #22c55e;
  box-shadow: 0 0 4px #22c55e;
}

.status-dot.disconnected {
  background-color: #ef4444;
  box-shadow: 0 0 4px #ef4444;
}
```

## 断开和重新加入控制

提供明确的断开和重新加入按钮，让用户拥有完全的控制权：

```tsx
function ChatControls({ stream, savedRunId, isConnected }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    stream.submit(
      { messages: [{ type: "human", content: input.trim() }] },
      { onDisconnect: "continue", streamResumable: true }
    );
    setInput("");
  };

  return (
    <div className="controls">
      <div className="input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button onClick={handleSend}>发送</button>
      </div>

      <div className="stream-controls">
        {isConnected ? (
          <button onClick={() => stream.stop()} className="disconnect-btn">
            断开连接
          </button>
        ) : (
          savedRunId && (
            <button
              onClick={() => stream.joinStream(savedRunId)}
              className="rejoin-btn"
            >
              重新加入流
            </button>
          )
        )}
      </div>
    </div>
  );
}
```

## 持久化运行 ID

对于跨会话重新加入（例如用户关闭浏览器后稍后返回），将运行 ID 持久化到存储中：

```ts
const stream = useStream<typeof myAgent>({
  apiUrl: "http://localhost:2024",
  assistantId: "join_rejoin",
  onCreated(run) {
    localStorage.setItem("activeRunId", run.run_id);
  },
});

// 页面加载时，检查是否有活动的运行
const existingRunId = localStorage.getItem("activeRunId");
if (existingRunId) {
  stream.joinStream(existingRunId);
}
```

当运行完成时，应该清理持久化的运行 ID。监听流完成事件并移除存储的 ID，以避免尝试重新加入已完成的运行。

## 错误处理

如果运行已过期、被删除或服务器已重启，重新加入可能会失败。优雅地处理这些情况：

```ts
try {
  stream.joinStream(savedRunId);
} catch (error) {
  console.error("重新加入流失败:", error);
  // 清除过期的运行 ID 并通知用户
  setSavedRunId(null);
  localStorage.removeItem("activeRunId");
}
```

## 完整示例

```tsx
function JoinRejoinChat() {
  const [savedRunId, setSavedRunId] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "join_rejoin",
    onCreated(run) {
      setSavedRunId(run.run_id);
    },
  });

  const isConnected = stream.isLoading;

  const handleSend = () => {
    if (!input.trim()) return;
    stream.submit(
      { messages: [{ type: "human", content: input.trim() }] },
      { onDisconnect: "continue", streamResumable: true }
    );
    setInput("");
  };

  return (
    <div className="chat-container">
      <header>
        <h2>加入与重新加入演示</h2>
        <ConnectionStatus connected={isConnected} />
      </header>

      <div className="messages">
        {stream.messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
      </div>

      <div className="controls">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入消息..."
          />
          <button type="submit">发送</button>
        </form>

        <div className="stream-actions">
          {isConnected ? (
            <button onClick={() => stream.stop()}>
              断开连接
            </button>
          ) : (
            savedRunId && (
              <button onClick={() => stream.joinStream(savedRunId)}>
                重新加入流
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
```

## 最佳实践

- **始终保存运行 ID**：没有它，重新加入是不可能的。为了增强弹性，同时使用组件状态和持久化存储。
- **显示清晰的连接状态**：用户应该始终知道他们是在接收实时更新还是查看快照。
- **可见性变化时自动重新加入**：使用 Page Visibility API 在用户返回标签页时自动重新加入。
- **设置合理的超时**：如果重新加入尝试耗时过长，改为获取线程历史记录。
- **清理已完成的运行**：当智能体完成时移除持久化的运行 ID，以避免过期的重新加入尝试。
