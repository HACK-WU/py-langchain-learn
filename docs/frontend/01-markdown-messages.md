# Markdown 消息渲染

> 将 LLM 响应渲染为格式丰富的 Markdown 内容，并支持流式传输

大语言模型（LLM）天然会输出 Markdown 格式的文本，包括标题、列表、代码块、表格和内联格式。如果以纯文本方式渲染这些内容，就浪费了模型提供的结构化信息。本文档将向您展示如何在主流前端框架中实时解析和渲染从 Agent 流式传输的 Markdown 内容。

## Markdown 渲染的工作原理

渲染流水线包含三个步骤：

1. **接收**：`useStream` 将流式传输的文本累积到每条 AI 消息的 `msg.text` 中，并在新 token 到达时进行响应式更新。
2. **解析**：Markdown 解析器将原始文本转换为 HTML（或 React 元素树）。此操作在每次更新时运行，但速度足够快，能够处理聊天长度的内容（5 KB 消息耗时 < 5 毫秒）。
3. **渲染**：解析后的输出被渲染到 DOM 中。React 使用虚拟 DOM 算法；Vue 和 Svelte 使用 `v-html` / `{@html}`，并配合经过净化的 HTML。

## 配置 useStream

Markdown 渲染模式使用简单的聊天 Agent，无需特殊配置。使用您的 Agent URL 和 Assistant ID 连接 `useStream`。

定义一个与 Agent 状态结构匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以获得类型安全的状态值访问。在下面的示例中，请将 `typeof myAgent` 替换为您的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

### React

```tsx
import { useStream } from "@langchain/react";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

const AGENT_URL = "http://localhost:2024";

export function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "simple_agent",
  });

  return (
    <div>
      {stream.messages.map((msg) => {
        if (AIMessage.isInstance(msg)) {
          return <Markdown key={msg.id}>{msg.text}</Markdown>;
        }
        if (HumanMessage.isInstance(msg)) {
          return <p key={msg.id}>{msg.text}</p>;
        }
      })}
    </div>
  );
}
```

### Vue

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

const AGENT_URL = "http://localhost:2024";

const stream = useStream<typeof myAgent>({
  apiUrl: AGENT_URL,
  assistantId: "simple_agent",
});
</script>

<template>
  <div>
    <template v-for="msg in stream.messages.value" :key="msg.id">
      <Markdown v-if="AIMessage.isInstance(msg)">{{ msg.text }}</Markdown>
      <p v-else-if="HumanMessage.isInstance(msg)">{{ msg.text }}</p>
    </template>
  </div>
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";
  import { AIMessage, HumanMessage } from "@langchain/core/messages";

  const AGENT_URL = "http://localhost:2024";

  const { messages, submit } = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "simple_agent",
  });
</script>

<div>
  {#each $messages as msg (msg.id)}
    {#if AIMessage.isInstance(msg)}
      <Markdown content={msg.text} />
    {:else if HumanMessage.isInstance(msg)}
      <p>{msg.text}</p>
    {/if}
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
      <app-markdown [content]="msg.text" />
    }
  `,
})
export class ChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: AGENT_URL,
    assistantId: "simple_agent",
  });
}
```

## 选择 Markdown 库

每个框架都有其最合适的 Markdown 渲染库选择：

| 框架 | 库 | 输出 | 原因 |
| --- | --- | --- | --- |
| React | `react-markdown` + `remark-gfm` | React 元素 | 基于组件、虚拟 DOM 差异更新、无需 `dangerouslySetInnerHTML` |
| Vue | `marked` + `dompurify` | 通过 `v-html` 输出净化后的 HTML | 轻量级、快速、内置 GFM 支持 |
| Svelte | `marked` + `dompurify` | 通过 `{@html}` 输出净化后的 HTML | 与 Vue 一致，API 统一 |
| Angular | `marked` + `dompurify` | 通过 `[innerHTML]` 输出净化后的 HTML | 与 Vue/Svelte 一致 |

React 的 `react-markdown` 直接将 Markdown 转换为 React 元素，因此不需要 HTML 净化。这里不涉及 `dangerouslySetInnerHTML`。对于 Vue、Svelte 和 Angular，在渲染前始终使用 `dompurify` 对解析后的 HTML 进行净化。

## 构建 Markdown 组件

### React

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
```

### Vue

```vue
<script setup lang="ts">
import { computed, useSlots } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ gfm: true, breaks: true });

const slots = useSlots();

const html = computed(() => {
  const slot = slots.default?.();
  const text = slot
    ?.map((vnode) =>
      typeof vnode.children === "string" ? vnode.children : ""
    )
    .join("") ?? "";
  if (!text) return "";
  return DOMPurify.sanitize(marked.parse(text) as string);
});
</script>

<template>
  <div class="markdown-content" v-html="html" />
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";

  let { content }: { content: string } = $props();

  marked.setOptions({ gfm: true, breaks: true });

  let html = $derived.by(() => {
    if (!content) return "";
    return DOMPurify.sanitize(marked.parse(content) as string);
  });
</script>

<div class="markdown-content">
  {@html html}
</div>
```

### Angular

```ts
import { Component, Input, computed, signal } from "@angular/core";
import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ gfm: true, breaks: true });

@Component({
  selector: "app-markdown",
  template: `<div class="markdown-content" [innerHTML]="html()"></div>`,
})
export class MarkdownComponent {
  @Input() set content(value: string) {
    this._content.set(value);
  }

  private _content = signal("");

  html = computed(() => {
    const text = this._content();
    if (!text) return "";
    return DOMPurify.sanitize(marked.parse(text) as string);
  });
}
```

## 净化 HTML 输出

当将解析后的 Markdown 作为原始 HTML 渲染时（使用 `v-html`、`{@html}` 或 `[innerHTML]`），必须对输出进行净化以防止跨站脚本（XSS）攻击。LLM 响应可能包含任意文本，包括 Markdown 解析器可能转换为可执行 HTML 的标记。

使用 `dompurify` 剥离危险元素：

```ts
import DOMPurify from "dompurify";

const safeHtml = DOMPurify.sanitize(rawHtml);
```

DOMPurify 会移除 `<script>` 标签、`onclick` 属性、`javascript:` URL 和其他 XSS 攻击向量，同时保留安全的 Markdown 输出，如标题、列表、代码块、表格和链接。

React 的 `react-markdown` 不需要 `dompurify`，因为它直接生成 React 元素，不涉及原始 HTML 注入。

## 流式传输注意事项

`useStream` 在每个 token 到达时响应式地更新 `msg.text`。Markdown 组件在每次更新时重新解析。对于典型的聊天消息，这具有很高的性能：

- `marked` 解析速度约为 ~1 MB/s。5 KB 消息耗时 < 5 毫秒
- `react-markdown` + remark 流水线对于聊天长度内容同样快速
- 浏览器的布局引擎高效地处理 DOM 更新

对于非常长的响应（> 50 KB），请考虑以下优化：

- **节流渲染**：使用 `requestAnimationFrame` 以 60fps 批量更新，而不是在每个 token 上重新渲染
- **增量解析**：仅解析新内容并追加到已渲染的缓冲区（高级用法，聊天 UI 通常不需要）

对于大多数聊天应用，在每个 token 上重新解析完整消息的简单方法已经足够。只有当您在处理非常长的消息时观察到滚动卡顿或丢帧时，才需要进行优化。

## Markdown 内容样式

将样式应用于 `.markdown-content` 类以控制渲染后 Markdown 的外观。以下是基本样式：

```css
.markdown-content p {
  margin: 0.4em 0;
}

.markdown-content ul,
.markdown-content ol {
  margin: 0.4em 0;
  padding-left: 1.4em;
}

.markdown-content pre {
  overflow-x: auto;
  border-radius: 0.375rem;
  background: rgba(0, 0, 0, 0.05);
  padding: 0.5rem;
  font-size: 0.75rem;
}

.markdown-content code {
  border-radius: 0.25rem;
  background: rgba(0, 0, 0, 0.08);
  padding: 0.125rem 0.25rem;
  font-size: 0.75rem;
}

.markdown-content blockquote {
  margin: 0.4em 0;
  padding-left: 0.75em;
  border-left: 3px solid currentColor;
  opacity: 0.8;
}

.markdown-content table {
  border-collapse: collapse;
  margin: 0.4em 0;
}

.markdown-content th,
.markdown-content td {
  border: 1px solid #e5e7eb;
  padding: 0.25em 0.5em;
}
```

为聊天气泡保持 Markdown 样式紧凑。聊天消息比博客文章小，因此与典型的散文样式表相比，使用更紧凑的边距和更小的字体大小。

## 最佳实践

- **始终净化**：当使用 `v-html`、`{@html}` 或 `[innerHTML]` 时，始终通过 `dompurify` 运行解析后的输出。永远不要信任来自 LLM 输出所驱动的 Markdown 解析器的原始 HTML。
- **启用 GFM**：GitHub 风格的 Markdown 增加了表格、删除线、任务列表和自动链接。这些功能是 LLM 常用的。
- **处理空内容**：在解析前检查空字符串，避免渲染空容器。
- **使用 `breaks: true`**：启用换行符转换，使 LLM 输出中的单个换行符渲染为 `<br>` 而不是被忽略。LLM 经常使用单个换行符进行视觉分隔。
- **为聊天场景设置样式**：使用适合聊天气泡的紧凑边距和尺寸，而不是全宽文章布局。
- **使用丰富内容测试**：使用标题、嵌套列表、包含长行的代码块、宽表格和引用来验证渲染，以发现溢出或布局问题。
