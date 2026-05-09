# 分支聊天 (Branching Chat)

> 编辑消息、重新生成回复，并导航对话分支

与 AI 智能体的对话很少是线性的。你可能想要重新表述问题、重新生成不满意的回复，或者探索完全不同的对话路径而不丢失之前的工作。分支聊天为你的聊天界面带来了版本控制的语义。每次编辑都会创建一个新分支，你可以在不同分支之间自由导航。

此功能需要 LangGraph Agent 服务器。使用 `langgraph dev` 在本地运行你的智能体，或将其部署到 LangSmith 以使用此模式。

## 什么是分支聊天？

分支聊天将对话视为树结构而非列表。每条消息都是一个节点，编辑消息或重新生成回复会从该点创建一个分叉。原始路径作为兄弟分支被保留，因此用户可以在不同的对话轨迹之间来回切换。

核心能力：

- **编辑任意用户消息**：重写之前的提示并从该点重新运行智能体
- **重新生成任意 AI 回复**：让智能体为相同的输入生成不同的答案
- **导航分支**：使用每条消息的分支控件在不同版本的对话之间切换

## 设置 useStream 与历史记录

要启用分支功能，请传递 `fetchStateHistory: true`，以便 `useStream` 检索分支操作所需的检查点元数据。

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

const AGENT_URL = "http://localhost:2024";

export function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "branching_chat",
    fetchStateHistory: true,
  });

  return (
    <div>
      {stream.messages.map((msg) => {
        const metadata = stream.getMessagesMetadata(msg);
        return (
          <Message
            key={msg.id}
            message={msg}
            metadata={metadata}
            onEdit={(text) => handleEdit(stream, msg, metadata, text)}
            onRegenerate={() => handleRegenerate(stream, metadata)}
            onBranchSwitch={(id) => stream.setBranch(id)}
          />
        );
      })}
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
  assistantId: "branching_chat",
  fetchStateHistory: true,
});

function handleEdit(msg: any, metadata: any, text: string) {
  const checkpoint = metadata.firstSeenState?.parent_checkpoint;
  if (!checkpoint) return;

  stream.submit(
    { messages: [{ ...msg, content: text }] },
    { checkpoint }
  );
}

function handleRegenerate(metadata: any) {
  const checkpoint = metadata.firstSeenState?.parent_checkpoint;
  if (!checkpoint) return;

  stream.submit(undefined, { checkpoint });
}
</script>

<template>
  <div>
    <Message
      v-for="msg in stream.messages.value"
      :key="msg.id"
      :message="msg"
      :metadata="stream.getMessagesMetadata(msg)"
      @edit="(text) => handleEdit(msg, stream.getMessagesMetadata(msg), text)"
      @regenerate="handleRegenerate(stream.getMessagesMetadata(msg))"
      @branch-switch="(id) => stream.setBranch(id)"
    />
  </div>
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";

  const AGENT_URL = "http://localhost:2024";

  const { messages, getMessagesMetadata, setBranch, submit } = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "branching_chat",
    fetchStateHistory: true,
  });

  function handleEdit(msg: any, metadata: any, text: string) {
    const checkpoint = metadata.firstSeenState?.parent_checkpoint;
    if (!checkpoint) return;

    submit(
      { messages: [{ ...msg, content: text }] },
      { checkpoint }
    );
  }

  function handleRegenerate(metadata: any) {
    const checkpoint = metadata.firstSeenState?.parent_checkpoint;
    if (!checkpoint) return;

    submit(undefined, { checkpoint });
  }
</script>

<div>
  {#each $messages as msg (msg.id)}
    {@const metadata = getMessagesMetadata(msg)}
    <Message
      message={msg}
      {metadata}
      onEdit={(text) => handleEdit(msg, metadata, text)}
      onRegenerate={() => handleRegenerate(metadata)}
      onBranchSwitch={(id) => setBranch(id)}
    />
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
      <app-message
        [message]="msg"
        [metadata]="stream.getMessagesMetadata(msg)"
        (edit)="handleEdit(msg, stream.getMessagesMetadata(msg), $event)"
        (regenerate)="handleRegenerate(stream.getMessagesMetadata(msg))"
        (branchSwitch)="stream.setBranch($event)"
      />
    }
  `,
})
export class ChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "branching_chat",
    fetchStateHistory: true,
  });

  handleEdit(msg: any, metadata: any, text: string) {
    const checkpoint = metadata.firstSeenState?.parent_checkpoint;
    if (!checkpoint) return;

    this.stream.submit(
      { messages: [{ ...msg, content: text }] },
      { checkpoint }
    );
  }

  handleRegenerate(metadata: any) {
    const checkpoint = metadata.firstSeenState?.parent_checkpoint;
    if (!checkpoint) return;

    this.stream.submit(undefined, { checkpoint });
  }
}
```

## 理解消息元数据

`getMessagesMetadata(msg)` 函数返回每条消息的分支信息：

```ts
interface MessageMetadata {
  branch: string;
  branchOptions: string[];
  firstSeenState: {
    parent_checkpoint: Checkpoint | null;
  };
}
```

| 属性 | 描述 |
| --- | --- |
| `branch` | 此特定消息版本的分支 ID |
| `branchOptions` | 此消息位置可用的所有分支 ID 数组 |
| `firstSeenState.parent_checkpoint` | 此消息之前的检查点。用作编辑和重新生成的分叉点 |

当消息只有一个版本时，`branchOptions` 包含单个条目。编辑或重新生成后，新的分支 ID 会被添加到 `branchOptions`，你可以在其中导航。

## 编辑消息

要编辑用户消息并创建新分支：

1. 从消息的元数据中获取 `parent_checkpoint`
2. 使用该检查点提交编辑后的消息
3. 智能体从该点重新运行，创建一个新分支

```ts
function handleEdit(
  stream: ReturnType<typeof useStream>,
  originalMsg: HumanMessage,
  metadata: MessageMetadata,
  newText: string
) {
  const checkpoint = metadata.firstSeenState?.parent_checkpoint;
  if (!checkpoint) return;

  stream.submit(
    {
      messages: [{ ...originalMsg, content: newText }],
    },
    { checkpoint }
  );
}
```

编辑后：

- 消息的 `branchOptions` 会添加一个新条目
- 视图自动切换到新分支
- 智能体从分叉点使用更新后的消息重新运行
- 原始版本被保留，可通过分支切换器访问

## 重新生成回复

要在不改变输入的情况下重新生成 AI 回复：

1. 从 AI 消息的元数据中获取 `parent_checkpoint`
2. 使用 `undefined` 输入和父检查点提交
3. 智能体生成新的回复，创建一个新分支

```ts
function handleRegenerate(
  stream: ReturnType<typeof useStream>,
  metadata: MessageMetadata
) {
  const checkpoint = metadata.firstSeenState?.parent_checkpoint;
  if (!checkpoint) return;

  stream.submit(undefined, { checkpoint });
}
```

每次重新生成都会在该位置为 AI 消息创建一个新分支。然后用户可以使用分支切换器比较不同的回复。

重新生成对于非确定性智能体很有用。由于 LLM 输出随温度变化，重新生成相同的提示通常会产生意义不同的回复。

## 构建立分支切换器

当消息有多个分支时，显示一个紧凑的内联控件，包含当前版本索引和导航箭头：

```tsx
function BranchSwitcher({
  metadata,
  onSwitch,
}: {
  metadata: MessageMetadata;
  onSwitch: (branchId: string) => void;
}) {
  const { branch, branchOptions } = metadata;

  if (branchOptions.length <= 1) return null;

  const currentIndex = branchOptions.indexOf(branch);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < branchOptions.length - 1;

  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
      <button
        disabled={!hasPrev}
        onClick={() => onSwitch(branchOptions[currentIndex - 1])}
        className="hover:text-gray-900 disabled:opacity-30"
        aria-label="Previous version"
      >
        ◀
      </button>
      <span className="min-w-[3ch] text-center">
        {currentIndex + 1}/{branchOptions.length}
      </span>
      <button
        disabled={!hasNext}
        onClick={() => onSwitch(branchOptions[currentIndex + 1])}
        className="hover:text-gray-900 disabled:opacity-30"
        aria-label="Next version"
      >
        ▶
      </button>
    </div>
  );
}
```

当用户点击分支箭头时，调用 `stream.setBranch(branchId)` 将对话视图切换到该分支。这是即时的，因为所有分支数据已经通过 `fetchStateHistory: true` 加载。

切换分支不仅影响目标消息，还影响所有后续消息。如果你切换到消息 3 的不同版本，消息 4、5、6 等也会更新以反映该版本之后的对话。

## 分支的工作原理

LangGraph 将每个状态转换持久化为检查点。当你使用 `checkpoint` 参数提交时，后端从该点分叉，而不是追加到当前对话。结果是一个树形结构：

```
User: "What is React?"
  ├─ AI: "React is a JavaScript library..." (分支 A)
  └─ AI: "React is a UI framework..." (分支 B, 重新生成)

User: "Tell me about hooks" (分支 A)
  └─ AI: "Hooks are functions..."

User: "Tell me about JSX" (从分支 A 编辑)
  └─ AI: "JSX is a syntax extension..."
```

每个分支都是对话树中的一个独立路径。切换分支会更新显示的消息，但不会删除任何数据。所有分支都持久保存在检查点存储中。

## 完整的消息组件

以下是一个完整的组件，结合了消息显示、编辑、重新生成和分支切换功能：

```tsx
function MessageWithBranching({
  message,
  metadata,
  stream,
}: {
  message: BaseMessage;
  metadata: MessageMetadata;
  stream: ReturnType<typeof useStream>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content as string);

  const isHuman = message._getType() === "human";
  const isAI = message._getType() === "ai";
  const hasBranches = metadata.branchOptions.length > 1;

  return (
    <div className="group relative py-2">
      {isEditing ? (
        <EditForm
          text={editText}
          onChange={setEditText}
          onSave={() => {
            handleEdit(stream, message as HumanMessage, metadata, editText);
            setIsEditing(false);
          }}
          onCancel={() => {
            setEditText(message.content as string);
            setIsEditing(false);
          }}
        />
      ) : (
        <>
          <div className={isHuman ? "text-right" : "text-left"}>
            <div
              className={
                isHuman
                  ? "inline-block rounded-lg bg-blue-600 px-4 py-2 text-white"
                  : "inline-block rounded-lg bg-gray-100 px-4 py-2"
              }
            >
              {message.content as string}
            </div>
          </div>

          <div className="mt-1 flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
            {isHuman && (
              <button
                className="text-xs text-gray-400 hover:text-gray-700"
                onClick={() => setIsEditing(true)}
              >
                Edit
              </button>
            )}

            {isAI && (
              <button
                className="text-xs text-gray-400 hover:text-gray-700"
                onClick={() =>
                  handleRegenerate(stream, metadata)
                }
              >
                Regenerate
              </button>
            )}

            {hasBranches && (
              <BranchSwitcher
                metadata={metadata}
                onSwitch={(id) => stream.setBranch(id)}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function EditForm({
  text,
  onChange,
  onSave,
  onCancel,
}: {
  text: string;
  onChange: (text: string) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-2">
      <textarea
        className="w-full rounded-lg border p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={text}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
      />
      <div className="flex gap-2">
        <button
          className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700"
          onClick={onSave}
        >
          Save & Rerun
        </button>
        <button
          className="rounded border px-4 py-1.5 text-sm hover:bg-gray-50"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
```

## 结合乐观更新

将分支与乐观更新结合，实现无缝的编辑体验。当用户保存编辑时，在服务器响应之前乐观地显示更新后的消息：

```ts
function handleEditOptimistic(
  stream: ReturnType<typeof useStream>,
  originalMsg: HumanMessage,
  metadata: MessageMetadata,
  newText: string
) {
  const checkpoint = metadata.firstSeenState?.parent_checkpoint;
  if (!checkpoint) return;

  const updatedMsg = { ...originalMsg, content: newText };

  stream.submit(
    { messages: [updatedMsg] },
    {
      checkpoint,
      optimisticValues: (prev) => {
        if (!prev?.messages) return { messages: [updatedMsg] };

        const idx = prev.messages.findIndex((m) => m.id === originalMsg.id);
        if (idx === -1) return prev;

        return {
          ...prev,
          messages: [...prev.messages.slice(0, idx), updatedMsg],
        };
      },
    }
  );
}
```

## 添加键盘导航

为高级用户添加键盘快捷键来导航分支：

```tsx
useEffect(() => {
  function handleKeyDown(e: KeyboardEvent) {
    if (!focusedMessageMetadata) return;

    const { branch, branchOptions } = focusedMessageMetadata;
    const idx = branchOptions.indexOf(branch);

    if (e.altKey && e.key === "ArrowLeft" && idx > 0) {
      stream.setBranch(branchOptions[idx - 1]);
    }
    if (e.altKey && e.key === "ArrowRight" && idx < branchOptions.length - 1) {
      stream.setBranch(branchOptions[idx + 1]);
    }
  }

  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [focusedMessageMetadata, stream]);
```

`Alt + ←` / `Alt + →` 是分支导航的自然映射，因为它模拟了浏览器的前进/后退导航。

## 最佳实践

- **始终启用 `fetchStateHistory`**：没有它，`getMessagesMetadata` 无法返回分支信息。
- **仅在存在多个分支时显示分支切换器**：`1/1` 指示器只会增加视觉噪音而没有实际价值。
- **悬停时显示分支控件**：分支导航箭头和编辑按钮应在悬停时出现，以保持界面简洁。
- **保持分支切换器紧凑**：它与消息控件内联显示，不应主导界面。
- **保留滚动位置**：切换分支时，尽量将视口锚定到发生变化的消息。
- **指示活动分支**：使用微妙的视觉提示（例如彩色圆点或分支标签），让用户知道他们正在查看哪个分支。
- **流式传输时禁用控件**：智能体正在流式传输回复时，不允许编辑或重新生成。在启用这些操作之前检查 `stream.isLoading`。
- **取消时保留编辑文本**：如果用户开始编辑然后取消，将文本区域重置为原始消息内容。
- **使用深度分支树进行测试**：频繁编辑和重新生成的用户可能会创建许多分支。确保分支切换器和数据处理保持高性能。
