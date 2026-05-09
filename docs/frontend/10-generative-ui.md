# 生成式 UI

> 使用 json-render 渲染 AI 生成的用户界面

生成式 UI（Generative UI）让 AI 能够从自然语言提示词生成完整的用户界面。AI 的输出不再是文本形式的聊天气泡，而是真正的 UI：表单、卡片、仪表盘等等。开发者定义可用的组件（"组件目录"），AI 将它们组合成一个有效的 UI 树。

此模式使用 json-render（生成式 UI 框架）来定义组件目录、使用 AI 生成规范，并在 React、Vue、Svelte 和 Angular 中安全地渲染它们。

## 工作原理

1. **定义组件目录**：声明 AI 可以使用的组件及其类型化的 props
2. **向 AI 发送提示词**：用自然语言描述你想要的 UI
3. **AI 生成规范**：一个描述组件树的 JSON 文档
4. **安全渲染**：json-render 的 `Renderer` 使用你的组件渲染规范

组件目录起到护栏作用：AI 只能使用你已定义的组件，并且 props 必须符合你的 schema。输出始终是可预测且安全的。

## 定义组件目录

组件目录描述了 AI 被允许使用的每个组件。每个组件都有一个用于 props 的 Zod schema，以及一个 AI 用来理解何时使用该组件的描述：

```ts
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

const catalog = defineCatalog(schema, {
  components: {
    Card: {
      description: "一个卡片容器，可选标题和内边距",
      props: z.object({
        title: z.string().optional(),
        padding: z.enum(["sm", "md", "lg"]).optional(),
      }),
    },
    TextInput: {
      description: "一个文本输入字段，可选标签和占位符",
      props: z.object({
        label: z.string().optional(),
        placeholder: z.string().optional(),
        type: z.enum(["text", "email", "password", "number", "textarea"]).optional(),
      }),
    },
    Button: {
      description: "一个可点击的按钮，带有标签和样式变体",
      props: z.object({
        label: z.string(),
        variant: z.enum(["primary", "secondary", "ghost", "link"]).optional(),
        fullWidth: z.boolean().optional(),
      }),
    },
  },
  actions: {},
});
```

保持组件目录的专注性。只包含 AI 在该用例中需要的组件。一个更小的组件目录比大而全的方式能产生更好的结果。

## 构建组件注册表

注册表将每个目录组件映射到其实际的渲染实现。使用 `defineRegistry` 来获取目录 props 和组件函数之间的类型安全绑定：

**React:**
```tsx
import { defineRegistry, Renderer, JSONUIProvider } from "@json-render/react";

const { registry } = defineRegistry(catalog, {
  components: {
    Card: ({ props, children }) => (
      <div className="card">
        {props.title && <h2>{props.title}</h2>}
        {children}
      </div>
    ),
    TextInput: ({ props }) => (
      <div>
        {props.label && <label>{props.label}</label>}
        <input type={props.type ?? "text"} placeholder={props.placeholder} />
      </div>
    ),
    Button: ({ props }) => (
      <button className={props.variant ?? "primary"}>
        {props.label}
      </button>
    ),
  },
});
```

**Vue:**
```vue
<script setup lang="ts">
import { h } from "vue";
import { defineRegistry, Renderer, JSONUIProvider } from "@json-render/vue";

const { registry } = defineRegistry(catalog, {
  components: {
    Card: ({ props, children }) =>
      h("div", { class: "card" }, [
        props.title ? h("h2", null, props.title) : null,
        children,
      ]),
    TextInput: ({ props }) =>
      h("div", null, [
        props.label ? h("label", null, props.label) : null,
        h("input", { type: props.type ?? "text", placeholder: props.placeholder }),
      ]),
    Button: ({ props }) =>
      h("button", { class: props.variant ?? "primary" }, props.label),
  },
});
</script>
```

## 连接到 Agent

Agent 使用结构化输出来返回 json-render 规范。使用你的 agent 助手 ID 设置 `useStream`，然后从 AI 消息的 `tool_calls` 中提取规范：

**React:**
```tsx
import { useStream } from "@langchain/react";
import { AIMessage } from "@langchain/core/messages";

function GenerativeUI() {
  const stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "generative_ui",
  });

  const aiMessage = stream.messages.find(AIMessage.isInstance);
  const rawSpec = aiMessage?.tool_calls?.[0]?.args;

  // ... 过滤和渲染（见下方的流式传输部分）
}
```

**Vue:**
```vue
<script setup lang="ts">
import { useStream } from "@langchain/vue";
import { AIMessage } from "@langchain/core/messages";
import { computed } from "vue";

const stream = useStream<typeof myAgent>({
  apiUrl: "http://localhost:2024",
  assistantId: "generative_ui",
});

const aiMessage = computed(() => stream.messages.value.find(AIMessage.isInstance));
const rawSpec = computed(() => aiMessage.value?.tool_calls?.[0]?.args);
</script>
```

**Svelte:**
```svelte
<script lang="ts">
  import { useStream } from "@langchain/svelte";
  import { AIMessage } from "@langchain/core/messages";

  const { messages, isLoading } = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "generative_ui",
  });

  const aiMessage = $derived($messages.find((m) => AIMessage.isInstance(m)));
  const rawSpec = $derived(aiMessage?.tool_calls?.[0]?.args);
</script>
```

**Angular:**
```ts
import { Component } from "@angular/core";
import { useStream } from "@langchain/angular";
import { AIMessage } from "@langchain/core/messages";

@Component({
  selector: "app-generative-ui",
  template: `...`,
})
export class GenerativeUIComponent {
  stream = useStream<typeof myAgent>({
    apiUrl: "http://localhost:2024",
    assistantId: "generative_ui",
  });

  get rawSpec() {
    const ai = this.stream.messages().find(AIMessage.isInstance);
    return ai?.tool_calls?.[0]?.args;
  }
}
```

## 渐进式流式传输和渲染

在流式传输过程中，规范是逐步构建的。元素会逐个到达，最初可能缺少 `type` 或 `props`。过滤出完整的元素并传递 `loading={true}` 给 `Renderer`，这会告诉它静默跳过尚未到达的子元素。UI 逐个组件地构建：

```tsx
/*
 * 过滤流式传输的规范，只包含具有有效 type/props 的元素，
 * 以便在 AI 响应构建过程中实现渐进式渲染。
 * 向 Renderer 传递 loading={true} 告诉它静默跳过缺失的子元素。
 */
const spec = (() => {
  if (!rawSpec?.root || !rawSpec?.elements) return null;
  const rootEl = rawSpec.elements[rawSpec.root];
  if (!rootEl?.type || rootEl?.props == null) return null;

  const safeElements = {};
  for (const [key, el] of Object.entries(rawSpec.elements)) {
    if (el?.type && el?.props != null) {
      safeElements[key] = el;
    }
  }
  return { root: rawSpec.root, elements: safeElements };
})();

return (
  <>
    {spec && (
      <JSONUIProvider registry={registry}>
        <Renderer spec={spec} registry={registry} loading={stream.isLoading} />
      </JSONUIProvider>
    )}
  </>
);
```

`JSONUIProvider` 是必需的，用于设置 json-render 的内部上下文提供者（状态、可见性、验证、操作）。`Renderer` 组件必须在它的内部渲染。

## 规范格式

AI Agent 生成扁平化的 JSON 规范，包含一个指向根元素的 `root` 键和一个包含所有组件的 `elements` 映射：

```json
{
  "root": "login-card",
  "elements": {
    "login-card": {
      "type": "Card",
      "props": { "title": "登录" },
      "children": ["login-stack"]
    },
    "login-stack": {
      "type": "Stack",
      "props": { "direction": "vertical", "gap": "md" },
      "children": ["email-input", "password-input", "submit-btn"]
    },
    "email-input": {
      "type": "TextInput",
      "props": { "label": "邮箱", "placeholder": "请输入邮箱", "type": "email" },
      "children": []
    },
    "password-input": {
      "type": "TextInput",
      "props": { "label": "密码", "placeholder": "请输入密码", "type": "password" },
      "children": []
    },
    "submit-btn": {
      "type": "Button",
      "props": { "label": "登录", "variant": "primary", "fullWidth": true },
      "children": []
    }
  }
}
```

每个元素通过 ID 引用其子元素，而像 `TextInput` 和 `Button` 这样的叶子元素具有空的 `children` 数组。

## 最佳实践

- **使用描述性的组件描述**：AI 使用这些描述来理解何时使用每个组件。清晰的描述能带来更好的 UI 生成效果。
- **渲染前验证**：始终检查元素是否具有有效的 `type` 和非空的 `props`，然后再传递给 Renderer，因为流式传输会传递部分数据。
- **为流式传输设计**：在流式传输期间传递 `loading={true}`，以便 Renderer 优雅地处理尚未到达的子元素。用户会实时看到 UI 逐步构建，而不是等待完整响应。
- **使用设计令牌进行样式设置**：使用 CSS 自定义属性，使渲染的组件自动适应浅色和深色主题。
- **用 JSONUIProvider 包裹**：`Renderer` 必须在 `JSONUIProvider` 内部，才能访问 json-render 用于状态、可见性和操作的内部上下文。

---

*原文链接：https://docs.langchain.com/oss/python/langchain/frontend/generative-ui*
