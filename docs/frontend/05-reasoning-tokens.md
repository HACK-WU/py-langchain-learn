# 推理令牌 (Reasoning Tokens)

> 在可折叠块中展示模型的思考和推理过程

推理令牌可以展示 OpenAI 的 o1/o3 和 Anthropic 的 Claude（扩展思考模式）等高级模型的内部思维过程。这些模型会生成结构化的内容块，将推理过程与最终答案分离，让你能够构建展示模型如何得出响应的用户界面。

## 什么是推理令牌？

当具备推理能力的模型处理提示时，它会生成两种不同类型的内容：

1. **推理块**：模型的内部思维链、问题分解和逐步分析
2. **文本块**：呈现给用户的最终、精炼的响应

这些内容以类型化的内容块形式在 `AIMessage` 中传递，可通过 `contentBlocks` 属性访问：

```ts
// 推理块
{ type: "reasoning", reasoning: "让我一步一步地思考这个问题..." }

// 文本块
{ type: "text", text: "答案是 42。" }
```

并非所有模型都会产生推理令牌。这种模式专门适用于支持扩展思考或思维链输出的模型。标准的聊天模型只返回文本块。

## 使用场景

- **透明度**：向用户展示模型的推理过程，建立对其答案的信任
- **调试**：检查模型的思维过程，找出出错的地方
- **教育工具**：通过展示 AI 如何解决问题来教授学生
- **决策支持**：让领域专家验证建议背后的推理
- **质量保证**：在受监管的行业中审计推理链以确保合规

## 提取推理块和文本块

`AIMessage` 上的 `contentBlocks` 数组包含按生成顺序排列的所有块。按 `type` 过滤以分离推理和文本：

```ts
import { AIMessage } from "@langchain/core/messages";

function extractBlocks(msg: AIMessage) {
  const reasoningBlocks = msg.contentBlocks
    .filter((b) => b.type === "reasoning")
    .map((b) => b.reasoning);

  const textBlocks = msg.contentBlocks
    .filter((b) => b.type === "text")
    .map((b) => b.text);

  return {
    reasoning: reasoningBlocks.join(""),
    text: textBlocks.join(""),
  };
}
```

单条消息可能包含多个推理块（例如，如果模型暂停推理，生成部分文本，然后继续推理）。将它们连接起来可以获得完整的思维过程。

## 从 `useStream` 访问消息

定义一个与代理状态模式匹配的 TypeScript 接口，并将其作为类型参数传递给 `useStream`，以类型安全地访问状态值。在下面的示例中，将 `typeof myAgent` 替换为你的接口名称：

```ts
import type { BaseMessage } from "@langchain/core/messages";

interface AgentState {
  messages: BaseMessage[];
}
```

### React 示例

```tsx
import { useStream } from "@langchain/react";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

function Chat() {
  const stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "reasoning",
  });

  return (
    <div className="messages">
      {stream.messages.map((msg, i) => {
        if (HumanMessage.isInstance(msg)) {
          return <HumanBubble key={i} text={msg.content} />;
        }
        if (AIMessage.isInstance(msg)) {
          return (
            <AIResponse
              key={i}
              message={msg}
              isStreaming={stream.isLoading && i === stream.messages.length - 1}
            />
          );
        }
        return null;
      })}
    </div>
  );
}
```

### Vue 示例

```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

const stream = useStream<typeof myAgent>({
  apiUrl: "http://localhost:2024",
  assistantId: "reasoning",
});
</script>

<template>
  <div class="messages">
    <template v-for="(msg, i) in stream.messages" :key="i">
      <HumanBubble v-if="HumanMessage.isInstance(msg)" :text="msg.content" />
      <AIResponse
        v-else-if="AIMessage.isInstance(msg)"
        :message="msg"
        :isStreaming="stream.isLoading && i === stream.messages.length - 1"
      />
    </template>
  </div>
</template>
```

### Svelte 示例

```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";
  import { AIMessage, HumanMessage } from "@langchain/core/messages";

  const { messages, isLoading, submit } = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "reasoning",
  });
</script>

<div class="messages">
  {#each $messages as msg, i}
    {#if HumanMessage.isInstance(msg)}
      <HumanBubble text={msg.content} />
    {:else if AIMessage.isInstance(msg)}
      <AIResponse
        message={msg}
        isStreaming={$isLoading && i === $messages.length - 1}
      />
    {/if}
  {/each}
</div>
```

### Angular 示例

```ts
import { Component } from "@angular/core";
import { useStream } from "@langchain/angular";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

@Component({
  selector: "app-chat",
  template: `
    <div class="messages">
      @for (msg of stream.messages(); track $index) {
        @if (isHuman(msg)) {
          <human-bubble [text]="msg.content" />
        } @else if (isAI(msg)) {
          <ai-response
            [message]="msg"
            [isStreaming]="stream.isLoading() && $index === stream.messages().length - 1"
          />
        }
      }
    </div>
  `,
})
export class ChatComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "reasoning",
  });

  isHuman = HumanMessage.isInstance;
  isAI = AIMessage.isInstance;
}
```

## 构建 ThinkingBubble 组件

`ThinkingBubble` 组件以视觉上独特的可折叠容器展示推理令牌。用户可以展开它以查看完整的思维过程，或折叠它以专注于最终答案。

```tsx
import { useState } from "react";

function ThinkingBubble({
  reasoning,
  isStreaming,
}: {
  reasoning: string;
  isStreaming: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const charCount = reasoning.length;
  const previewLength = 120;
  const preview =
    reasoning.length > previewLength
      ? reasoning.slice(0, previewLength) + "..."
      : reasoning;

  return (
    <div className="thinking-bubble">
      <button
        className="thinking-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="thinking-icon">
          {isStreaming ? (
            <span className="thinking-spinner" />
          ) : (
            "💭"
          )}
        </span>
        <span className="thinking-label">
          {isStreaming ? "思考中..." : `思考过程 (${charCount} 字符)`}
        </span>
        <span className={`chevron ${isExpanded ? "expanded" : ""}`}>▶</span>
      </button>

      {isExpanded && (
        <div className="thinking-content">
          <pre>{reasoning}</pre>
        </div>
      )}

      {!isExpanded && !isStreaming && (
        <div className="thinking-preview">{preview}</div>
      )}
    </div>
  );
}
```

### 为 ThinkingBubble 添加样式

使用独特的视觉处理来区分推理块和普通消息：

```css
.thinking-bubble {
  background-color: #f8f5ff;
  border: 1px solid #e2d9f3;
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0;
  font-size: 0.9em;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  color: #6b21a8;
  font-weight: 500;
}

.thinking-content {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e2d9f3;
  white-space: pre-wrap;
  color: #4a4a4a;
  line-height: 1.5;
}

.thinking-preview {
  margin-top: 4px;
  color: #9ca3af;
  font-style: italic;
  font-size: 0.85em;
}

.chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.chevron.expanded {
  transform: rotate(90deg);
}
```

## 推理的流式指示器

当模型仍在生成推理令牌时，显示动画指示器以传达思考正在进行中：

```css
.thinking-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #e2d9f3;
  border-top-color: #6b21a8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

在流式传输期间，默认保持 ThinkingBubble 折叠状态，仅显示旋转器。在流式传输过程中展开可能会导致布局抖动，因为新令牌不断到达。让用户在推理阶段完成后再展开。

## 渲染完整的 AI 响应

将 `ThinkingBubble` 和标准文本气泡组合成一个 `AIResponse` 组件：

```tsx
function AIResponse({
  message,
  isStreaming,
}: {
  message: AIMessage;
  isStreaming: boolean;
}) {
  const reasoningBlocks = message.contentBlocks
    .filter((b) => b.type === "reasoning")
    .map((b) => b.reasoning)
    .join("");

  const textBlocks = message.contentBlocks
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("");

  const hasReasoning = reasoningBlocks.length > 0;
  const hasText = textBlocks.length > 0;

  const isReasoningPhase = isStreaming && !hasText;
  const isTextPhase = isStreaming && hasText;

  return (
    <div className="ai-response">
      {hasReasoning && (
        <ThinkingBubble
          reasoning={reasoningBlocks}
          isStreaming={isReasoningPhase}
        />
      )}
      {hasText && (
        <div className="ai-text-bubble">
          <p>{textBlocks}</p>
          {isTextPhase && <span className="cursor-blink">▊</span>}
        </div>
      )}
    </div>
  );
}
```

## 处理边界情况

### 没有推理的消息

并非每条 AI 消息都会包含推理块。当 `contentBlocks` 只有文本块时，渲染标准消息气泡而不显示 ThinkingBubble。

### 空的推理块

某些模型会产生空的推理块作为占位符。过滤掉这些空块：

```ts
const meaningfulReasoning = message.contentBlocks
  .filter((b) => b.type === "reasoning" && b.reasoning.trim().length > 0);
```

### 多轮推理-文本循环

单条消息可能在推理块和文本块之间交替。如果你需要保留这种交错顺序，请按顺序遍历 `contentBlocks` 而不是按类型分组：

```ts
message.contentBlocks.forEach((block) => {
  if (block.type === "reasoning") {
    // 渲染 ThinkingBubble
  } else if (block.type === "text") {
    // 渲染文本段落
  }
});
```

## 最佳实践

- **默认折叠**：按需显示推理，而不是默认显示
- **显示字符数**：让用户快速了解响应背后的思考量
- **视觉差异化**：使用不同的颜色、边框或背景，确保推理不会被误认为实际答案
- **动画过渡**：平滑的展开/折叠动画可提升感知质量
- **考虑无障碍性**：在切换按钮上使用适当的 ARIA 属性（`aria-expanded`、`aria-controls`）
- **预览截断**：折叠时显示推理的简短预览，让用户决定是否展开
