# 时间旅行（Time Travel）

> 检查、导航并从对话历史中的任意检查点恢复

LangGraph 代理中的每一次状态变更都会创建一个检查点（checkpoint），这是对代理在该时刻状态的完整快照。时间旅行功能允许你检查任意检查点、查看代理当时的精确状态，并从该点恢复执行以探索替代路径。它是调试器、撤销按钮和审计日志的集合体。

此功能需要 LangGraph Agent Server。使用此模式时，请在本地使用 `langgraph dev` 运行你的代理，或将其部署到 LangSmith。

## 检查点的工作原理

LangGraph 在每个节点执行后持久化代理状态。每个持久化的状态都是一个 `ThreadState` 对象，包含以下信息：

- **checkpoint**: 标识此特定快照的元数据（ID、时间戳）
- **values**: 该时刻的完整代理状态（消息、自定义键）
- **tasks**: 计划接下来运行的图节点
- **next**: 执行计划中即将运行的节点名称

这创建了一个线性时间线，记录了代理做出的每一个决策、调用的每一个工具以及产生的每一个响应。你的 UI 可以渲染这个时间线，让用户跳转到任意时间点。

## 设置 useStream

通过向 `useStream` 传递 `fetchStateHistory: true` 来启用检查点历史记录。这会告诉钩子加载当前线程的完整检查点时间线。

定义一个与代理状态模式匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以实现对状态值的类型安全访问。在下面的示例中，将 `typeof myAgent` 替换为你的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

### React 示例

```tsx
import { useStream } from "@langchain/react";

const AGENT_URL = "http://localhost:2024";

export function TimeTravelChat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "time_travel",
    fetchStateHistory: true,
  });

  const history = stream.history ?? [];

  return (
    <div className="flex h-screen">
      <ChatPanel messages={stream.messages} />
      <TimelineSidebar
        history={history}
        onSelect={(cp) => stream.submit(null, { checkpoint: cp.checkpoint })}
      />
    </div>
  );
}
```

### Vue 示例

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";
import { computed } from "vue";

const AGENT_URL = "http://localhost:2024";

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "time_travel",
  fetchStateHistory: true,
});

const history = computed(() => stream.history.value ?? []);

function resumeFrom(cp: ThreadState) {
  stream.submit(null, { checkpoint: cp.checkpoint });
}
</script>

<template>
  <div class="flex h-screen">
    <ChatPanel :messages="stream.messages.value" />
    <TimelineSidebar :history="history" @select="resumeFrom" />
  </div>
</template>
```

### Svelte 示例

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";

  const AGENT_URL = "http://localhost:2024";

  const { messages, history, submit } = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "time_travel",
    fetchStateHistory: true,
  });

  function resumeFrom(cp: ThreadState) {
    submit(null, { checkpoint: cp.checkpoint });
  }
</script>

<div class="flex h-screen">
  <ChatPanel messages={$messages} />
  <TimelineSidebar history={$history ?? []} onSelect={resumeFrom} />
</div>
```

### Angular 示例

```ts
import { Component, computed } from "@angular/core";
import { useStream } from "@langchain/angular";

const AGENT_URL = "http://localhost:2024";

@Component({
  selector: "app-time-travel-chat",
  template: `
    <div class="flex h-screen">
      <app-chat-panel [messages]="stream.messages()" />
      <app-timeline-sidebar
        [history]="history()"
        (select)="resumeFrom($event)"
      />
    </div>
  `,
})
export class TimeTravelChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "time_travel",
    fetchStateHistory: true,
  });

  history = computed(() => this.stream.history() ?? []);

  resumeFrom(cp: ThreadState) {
    this.stream.submit(null, { checkpoint: cp.checkpoint });
  }
}
```

## ThreadState 对象

`history` 数组中的每个条目都是一个 `ThreadState`，代表时间线上的一个检查点：

```ts
interface ThreadState {
  checkpoint: {
    checkpoint_id: string;
    checkpoint_ns: string;
  };
  values: Record<string, unknown>;
  tasks: Array<{
    id: string;
    name: string;
    interrupts?: unknown[];
  }>;
  next: string[];
}
```

| 属性 | 描述 |
| --- | --- |
| `checkpoint` | 标识此快照。将其传递给 `submit` 以从此处恢复 |
| `values` | 该时刻的完整代理状态，包含 `messages` 和任何自定义状态键 |
| `tasks` | 在此检查点运行的图节点，包括它们的名称和任何中断 |
| `next` | 计划在此检查点后执行的节点名称 |

## 构建检查点时间线

时间线侧边栏将每个检查点显示为可点击的条目。每个条目显示运行的节点以及该时刻存在的消息数量：

```tsx
function TimelineSidebar({
  history,
  onSelect,
}: {
  history: ThreadState[];
  onSelect: (cp: ThreadState) => void;
}) {
  return (
    <aside className="w-80 overflow-y-auto border-l bg-gray-50 p-4">
      <h2 className="mb-4 text-sm font-semibold uppercase text-gray-500">
        检查点时间线
      </h2>
      <div className="space-y-2">
        {history.map((cp, i) => {
          const taskName = cp.tasks?.[0]?.name ?? "unknown";
          const msgCount = (cp.values?.messages as unknown[])?.length ?? 0;

          return (
            <button
              key={cp.checkpoint.checkpoint_id}
              onClick={() => onSelect(cp)}
              className="w-full rounded-lg border bg-white p-3 text-left
                         hover:border-blue-400 hover:shadow-sm transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">#{i + 1}</span>
                <NodeBadge name={taskName} />
              </div>
              <p className="mt-1 text-sm font-medium">{taskName}</p>
              <p className="text-xs text-gray-500">
                {msgCount} 条消息
              </p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
```

## 检查检查点状态

点击检查点应该显示该点的完整状态。JSON 查看器为开发者提供了对代理知道什么以及做了什么决策的完整可见性：

```tsx
function CheckpointInspector({ checkpoint }: { checkpoint: ThreadState }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">
          检查点 {checkpoint.checkpoint.checkpoint_id.slice(0, 8)}...
        </h3>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-blue-600 hover:underline"
        >
          {expanded ? "收起" : "展开"}状态
        </button>
      </div>

      <div className="mt-2 space-y-1 text-sm">
        <p>
          <strong>节点：</strong>{" "}
          {checkpoint.tasks?.[0]?.name ?? "—"}
        </p>
        <p>
          <strong>下一个：</strong>{" "}
          {checkpoint.next?.join(", ") || "—"}
        </p>
        <p>
          <strong>消息数：</strong>{" "}
          {(checkpoint.values?.messages as unknown[])?.length ?? 0}
        </p>
      </div>

      {expanded && (
        <div className="mt-3 max-h-96 overflow-auto rounded bg-gray-900 p-3">
          <pre className="text-xs text-gray-200">
            {JSON.stringify(checkpoint.values, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
```

对于生产环境的 UI，考虑使用具有可折叠节点的专业 JSON 查看器组件，而不是原始的 `JSON.stringify`。像 `react-json-view` 或 `react-json-tree` 这样的库能为用户提供更好的探索体验。

## 从检查点恢复

时间旅行的核心是能够从任意之前的检查点恢复执行。当用户选择一个检查点时，使用 `null` 输入调用 `submit` 并传递检查点引用：

```ts
stream.submit(null, { checkpoint: selectedCheckpoint.checkpoint });
```

这会告诉 LangGraph：

1. 回滚到所选检查点的状态
2. 从该点重新执行图
3. 将新结果流式传输到客户端

所选检查点之后的现有消息将被新的执行路径替换。这实际上在时间线上创建了一个分支。

从检查点恢复不会删除原始时间线。之前的检查点仍然保留在历史记录中。这意味着用户始终可以返回并尝试不同的路径，而不会丢失任何之前的工作。

## SplitView 布局

时间旅行最适合使用左右分屏布局，主聊天在左侧，时间线在右侧：

```tsx
function TimeTravelLayout() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "time_travel",
    fetchStateHistory: true,
  });

  const [selectedCheckpoint, setSelectedCheckpoint] =
    useState<ThreadState | null>(null);

  const history = stream.history ?? [];

  return (
    <div className="flex h-screen">
      {/* 主聊天区域 */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-2xl space-y-4">
          {stream.messages.map((msg) => (
            <Message key={msg.id} message={msg} />
          ))}
        </div>
        <ChatInput
          onSubmit={(text) =>
            stream.submit({ messages: [{ type: "human", content: text }] })
          }
          isLoading={stream.isLoading}
        />
      </main>

      {/* 时间线侧边栏 */}
      <aside className="w-96 overflow-y-auto border-l bg-gray-50">
        <TimelineSidebar
          history={history}
          selected={selectedCheckpoint}
          onSelect={setSelectedCheckpoint}
          onResume={(cp) =>
            stream.submit(null, { checkpoint: cp.checkpoint })
          }
        />
        {selectedCheckpoint && (
          <CheckpointInspector checkpoint={selectedCheckpoint} />
        )}
      </aside>
    </div>
  );
}
```

## 提取检查点元数据

将原始检查点数据转换为显示友好的条目，用于你的时间线：

```ts
function formatCheckpoints(history: ThreadState[]) {
  return history.map((cp, index) => ({
    index,
    id: cp.checkpoint?.checkpoint_id,
    taskName: cp.tasks?.[0]?.name ?? "unknown",
    messageCount: (cp.values?.messages as unknown[])?.length ?? 0,
    hasInterrupts: cp.tasks?.some((t) => t.interrupts?.length) ?? false,
    nextNodes: cp.next ?? [],
  }));
}
```

这使得使用时间线条目渲染有意义的标签（而不是原始 ID）变得容易。

## 使用场景

时间旅行在许多场景中都非常有价值：

- **调试代理行为**：逐步分析代理的决策，了解它为什么选择特定路径
- **撤销操作**：如果代理走错了方向，从较早的检查点恢复并重试
- **探索替代方案**：从对话中间的检查点分叉，查看不同输入如何改变结果
- **审计**：审查代理行为的完整历史，用于合规、质量保证或事后分析
- **教学**：逐步演示代理的执行过程，解释多步推理的工作原理

时间旅行与人在回路（human-in-the-loop）模式结合使用时尤其强大。如果人工审核者在某个中断点拒绝了代理的操作，他们可以从执行该操作之前的检查点恢复并提供纠正性输入。

## 在时间线中处理中断

包含中断（人在回路暂停）的检查点值得特殊的视觉处理。它们代表代理停止并等待人工输入的时刻：

```tsx
function TimelineEntry({
  checkpoint,
  index,
}: {
  checkpoint: ThreadState;
  index: number;
}) {
  const hasInterrupt = checkpoint.tasks?.some(
    (t) => t.interrupts && t.interrupts.length > 0
  );

  return (
    <div
      className={`rounded-lg border p-3 ${
        hasInterrupt
          ? "border-amber-300 bg-amber-50"
          : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">#{index + 1}</span>
        {hasInterrupt && (
          <span className="rounded bg-amber-200 px-1.5 py-0.5 text-xs font-medium text-amber-800">
            中断
          </span>
        )}
      </div>
      <p className="mt-1 text-sm font-medium">
        {checkpoint.tasks?.[0]?.name ?? "—"}
      </p>
    </div>
  );
}
```

## 最佳实践

- **懒加载历史记录**：对于具有数百个检查点的线程，请分页或仅加载最近的 N 个条目，以保持 UI 响应迅速。
- **显示有意义的标签**：显示节点名称和消息数，而不是原始检查点 ID。用户需要上下文，而不是 UUID。
- **恢复前确认**：从旧检查点恢复会替换当前的执行路径。显示确认对话框，以免用户意外丢失当前的对话状态。
- **高亮当前检查点**：在视觉上明确哪个检查点对应于对话的当前状态。
- **支持键盘导航**：高级用户希望使用箭头键逐步浏览检查点。为时间线添加键盘处理程序，以获得流畅的调试体验。
- **检查点之间的状态差异**：对于高级用户，显示两个连续检查点之间的变化可以准确揭示代理状态是如何在每一步演变的。
