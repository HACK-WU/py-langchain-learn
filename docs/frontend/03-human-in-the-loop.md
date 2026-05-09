# 人机协同（Human-in-the-Loop）

> 添加基于中断机制的人工审批工作流

并非所有的智能体操作都应在无人监督的情况下运行。当智能体即将发送邮件、删除记录、执行金融交易或执行任何不可逆操作时，你需要人工先审阅并批准该操作。人机协同（HITL）模式使智能体能够暂停执行，将待处理的操作呈现给用户，并在获得明确批准后恢复执行。

## 中断机制的工作原理

LangGraph 智能体支持中断机制——这是显式的暂停点，智能体在此处将控制权交还给客户端。当智能体遇到中断时：

1. 智能体停止执行并发出中断负载
2. `useStream` 钩子通过 `stream.interrupt` 暴露中断信息
3. 你的 UI 渲染一个带有批准/拒绝/编辑选项的审阅卡片
4. 用户做出决定
5. 你的代码调用 `stream.submit()` 并传入恢复命令
6. 智能体从暂停处继续执行

## 为 HITL 配置 useStream

定义一个与智能体状态模式匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream` 以实现类型安全的状态值访问。在以下示例中，将 `typeof myAgent` 替换为你的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

```tsx
import { useStream } from "@langchain/react";

const AGENT_URL = "http://localhost:2024";

export function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "human_in_the_loop",
  });

  const interrupt = stream.interrupt;

  return (
    <div>
      {stream.messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}
      {interrupt && (
        <ApprovalCard
          interrupt={interrupt}
          onRespond={(response) =>
            stream.submit(null, { command: { resume: response } })
          }
        />
      )}
    </div>
  );
}
```

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";

const AGENT_URL = "http://localhost:2024";

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "human_in_the_loop",
});

function handleRespond(response: HITLResponse) {
  stream.submit(null, { command: { resume: response } });
}
</script>

<template>
  <div>
    <Message
      v-for="msg in stream.messages.value"
      :key="msg.id"
      :message="msg"
    />
    <ApprovalCard
      v-if="stream.interrupt.value"
      :interrupt="stream.interrupt.value"
      @respond="handleRespond"
    />
  </div>
</template>
```

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";

  const AGENT_URL = "http://localhost:2024";

  const { messages, interrupt, submit } = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "human_in_the_loop",
  });

  function handleRespond(response: HITLResponse) {
    submit(null, { command: { resume: response } });
  }
</script>

<div>
  {#each $messages as msg (msg.id)}
    <Message message={msg} />
  {/each}

  {#if $interrupt}
    <ApprovalCard interrupt={$interrupt} onRespond={handleRespond} />
  {/if}
</div>
```

```ts
import { Component } from "@angular/core";
import { useStream } from "@langchain/angular";
import type { HITLResponse } from "langchain";

const AGENT_URL = "http://localhost:2024";

@Component({
  selector: "app-chat",
  template: `
    @for (msg of stream.messages(); track msg.id) {
      <app-message [message]="msg" />
    }
    @if (stream.interrupt()) {
      <app-approval-card
        [interrupt]="stream.interrupt()"
        (respond)="handleRespond($event)"
      />
    }
  `,
})
export class ChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "human_in_the_loop",
  });

  handleRespond(response: HITLResponse) {
    this.stream.submit(null, { command: { resume: response } });
  }
}
```

## 中断负载

当智能体暂停时，`stream.interrupt` 包含一个 `HITLRequest`，其结构如下：

```ts
interface HITLRequest {
  actionRequests: ActionRequest[];
  reviewConfigs: ReviewConfig[];
}

interface ActionRequest {
  action: string;
  args: Record<string, unknown>;
  description?: string;
}

interface ReviewConfig {
  allowedDecisions: ("approve" | "reject" | "edit" | "respond")[];
}
```

| 属性 | 说明 |
| --- | --- |
| `actionRequests` | 智能体想要执行的待处理操作数组 |
| `actionRequests[].action` | 操作名称（例如 `"send_email"`、`"delete_record"`） |
| `actionRequests[].args` | 操作的结构化参数 |
| `actionRequests[].description` | 操作功能的可选人类可读描述 |
| `reviewConfigs` | 控制允许哪些决策的每项操作配置 |
| `reviewConfigs[].allowedDecisions` | 显示哪些按钮：`"approve"`、`"reject"`、`"edit"`、`"respond"` |

## 决策类型

HITL 模式支持四种决策类型：

### 批准（Approve）

用户确认操作应按原样继续执行：

```ts
const response: HITLResponse = {
  decision: "approve",
};

stream.submit(null, { command: { resume: response } });
```

### 拒绝（Reject）

用户拒绝操作并可选择提供原因：

```ts
const response: HITLResponse = {
  decision: "reject",
  reason: "邮件语气过于强硬，请修改。",
};

stream.submit(null, { command: { resume: response } });
```

当操作被拒绝时，智能体会收到拒绝原因并决定如何继续。它可能会重新表述、提出澄清问题或完全放弃该操作。

### 编辑（Edit）

用户在批准前修改操作的参数：

```ts
const response: HITLResponse = {
  decision: "edit",
  args: {
    ...originalArgs,
    subject: "更新后的主题行",
    body: "使用更柔和语言修订后的邮件正文。",
  },
};

stream.submit(null, { command: { resume: response } });
```

### 回复（Respond）

用户为"询问用户"类型的工具提供直接回复。`message` 将成为工具结果，而工具本身不会被执行：

```ts
const response: HITLResponse = {
  decision: "respond",
  message: "蓝色。",
};

stream.submit(null, { command: { resume: response } });
```

当工具有意作为人工输入的占位符时使用 `respond` —— 例如，一个提示智能体从用户处收集信息的 `ask_user` 工具。

## 构建 ApprovalCard 组件

以下是一个处理所有四种决策类型的完整审批卡片组件：

```tsx
function ApprovalCard({
  interrupt,
  onRespond,
}: {
  interrupt: { value: HITLRequest };
  onRespond: (response: HITLResponse) => void;
}) {
  const request = interrupt.value;
  const [editedArgs, setEditedArgs] = useState(
    request.actionRequests[0]?.args ?? {}
  );
  const [rejectReason, setRejectReason] = useState("");
  const [respondMessage, setRespondMessage] = useState("");
  const [mode, setMode] = useState<"review" | "edit" | "reject" | "respond">("review");

  const action = request.actionRequests[0];
  const config = request.reviewConfigs[0];

  if (!action || !config) return null;

  return (
    <div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-4">
      <h3 className="font-semibold text-amber-800">需要操作审阅</h3>
      <p className="mt-1 text-sm text-amber-700">
        {action.description ?? `智能体想要执行: ${action.action}`}
      </p>

      <div className="mt-3 rounded bg-white p-3 font-mono text-sm">
        <pre>{JSON.stringify(action.args, null, 2)}</pre>
      </div>

      {mode === "review" && (
        <div className="mt-4 flex gap-2">
          {config.allowedDecisions.includes("approve") && (
            <button
              className="rounded bg-green-600 px-4 py-2 text-white"
              onClick={() => onRespond({ decision: "approve" })}
            >
              批准
            </button>
          )}
          {config.allowedDecisions.includes("reject") && (
            <button
              className="rounded bg-red-600 px-4 py-2 text-white"
              onClick={() => setMode("reject")}
            >
              拒绝
            </button>
          )}
          {config.allowedDecisions.includes("edit") && (
            <button
              className="rounded bg-blue-600 px-4 py-2 text-white"
              onClick={() => setMode("edit")}
            >
              编辑
            </button>
          )}
          {config.allowedDecisions.includes("respond") && (
            <button
              className="rounded bg-purple-600 px-4 py-2 text-white"
              onClick={() => setMode("respond")}
            >
              回复
            </button>
          )}
        </div>
      )}

      {mode === "reject" && (
        <div className="mt-4 space-y-2">
          <textarea
            className="w-full rounded border p-2"
            placeholder="拒绝原因..."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <button
            className="rounded bg-red-600 px-4 py-2 text-white"
            onClick={() =>
              onRespond({ decision: "reject", reason: rejectReason })
            }
          >
            确认拒绝
          </button>
        </div>
      )}

      {mode === "edit" && (
        <div className="mt-4 space-y-2">
          <textarea
            className="w-full rounded border p-2 font-mono text-sm"
            value={JSON.stringify(editedArgs, null, 2)}
            onChange={(e) => {
              try {
                setEditedArgs(JSON.parse(e.target.value));
              } catch {
                // 编辑期间允许无效的 JSON
              }
            }}
          />
          <button
            className="rounded bg-blue-600 px-4 py-2 text-white"
            onClick={() =>
              onRespond({ decision: "edit", args: editedArgs })
            }
          >
            提交编辑
          </button>
        </div>
      )}

      {mode === "respond" && (
        <div className="mt-4 space-y-2">
          <textarea
            className="w-full rounded border p-2"
            placeholder="你的回复..."
            value={respondMessage}
            onChange={(e) => setRespondMessage(e.target.value)}
          />
          <button
            className="rounded bg-purple-600 px-4 py-2 text-white"
            onClick={() =>
              onRespond({ decision: "respond", message: respondMessage })
            }
          >
            发送回复
          </button>
        </div>
      )}
    </div>
  );
}
```

## 恢复流程

用户做出决定后，完整流程如下：

1. 调用 `stream.submit(null, { command: { resume: hitlResponse } })`
2. `useStream` 钩子将恢复命令发送到 LangGraph 后端
3. 智能体接收 `HITLResponse` 并继续执行。HITL 响应可能是以下之一：

- `"approve"`: 智能体继续执行下一个操作
- `"reject"`: 智能体接收拒绝原因并决定下一步操作
- `"edit"`: 智能体使用编辑后的参数运行工具
- `"respond"`: 人类的消息直接作为工具结果返回，而不执行工具

4. 当智能体恢复流式传输时，`interrupt` 属性重置为 `null`

你可以在单次智能体运行中链接多个 HITL 检查点。例如，智能体可能会请求批准搜索，然后在发送包含结果的邮件之前再次请求批准。每个中断都是独立处理的。

## 常见用例

| 用例 | 操作 | 审阅配置 |
| --- | --- | --- |
| 发送邮件 | `send_email` | `["approve", "reject", "edit"]` |
| 数据库写入 | `update_record` | `["approve", "reject"]` |
| 金融交易 | `transfer_funds` | `["approve", "reject"]` |
| 文件删除 | `delete_files` | `["approve", "reject"]` |
| 调用外部服务 API | `call_api` | `["approve", "reject", "edit"]` |
| 收集用户输入 | `ask_user` | `["respond"]` |

## 处理多个待处理操作

当智能体想要同时执行多个操作时，一个中断可以包含多个 `actionRequests`。为每个操作渲染一个卡片并在恢复前收集所有决策：

```tsx
function MultiActionReview({
  interrupt,
  onRespond,
}: {
  interrupt: { value: HITLRequest };
  onRespond: (responses: HITLResponse[]) => void;
}) {
  const [decisions, setDecisions] = useState<Record<number, HITLResponse>>({});
  const request = interrupt.value;

  const allDecided =
    Object.keys(decisions).length === request.actionRequests.length;

  return (
    <div className="space-y-4">
      {request.actionRequests.map((action, i) => (
        <SingleActionCard
          key={i}
          action={action}
          config={request.reviewConfigs[i]}
          onDecide={(response) =>
            setDecisions((prev) => ({ ...prev, [i]: response }))
          }
        />
      ))}
      {allDecided && (
        <button
          className="rounded bg-green-600 px-4 py-2 text-white"
          onClick={() =>
            onRespond(
              request.actionRequests.map((_, i) => decisions[i])
            )
          }
        >
          提交所有决策
        </button>
      )}
    </div>
  );
}
```

## 最佳实践

实施 HITL 工作流时，请遵循以下准则：

- 展示清晰的上下文。始终显示智能体想要做什么以及为什么。
  包括操作描述和完整参数。
- 让批准成为最简单的路径。如果操作看起来正确，批准应该是一个单击操作。
  将多步骤流程保留给拒绝/编辑。
- 验证编辑的参数。当用户编辑操作参数时，在发送前验证 JSON 结构。
  对格式错误的输入显示内联错误。
- 持久化中断状态。如果用户刷新页面，中断仍应可见。
  `useStream` 通过线程的检查点处理这一点。
- 记录所有决策。为了审计追踪，记录每个批准/拒绝/编辑决策，
  并附上时间戳和做出决策的用户。
- 合理设置超时。长时间运行的智能体不应无限期等待人工审阅。
  考虑显示智能体已等待多长时间。
