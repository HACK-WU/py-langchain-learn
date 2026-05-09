# 概述

> 将 useStream 连接到任何 React UI 组件库或生成式 UI 框架

`useStream` 是与 UI 无关的。它返回纯反应式状态，包含消息、工具调用、加载标志和线程历史记录，你可以将其连接到你选择的任何视觉层。这些页面展示了不同的库如何与 LangChain 前端集成，每个库都有不同的构建 AI 聊天和生成式 UI 的理念。

## 集成方案

### CopilotKit

完整的 AI 聊天运行时，支持结构化生成式 UI。向你的 LangGraph 部署添加一个自定义 CopilotKit 端点，然后在 React 中渲染动态组件树。

### AI Elements

基于 shadcn/ui 的可组合组件，用于 AI 聊天。直接拖入 `Conversation`、`Message`、`Tool` 和 `Reasoning` 组件，并将它们直接连接到 `stream.messages`。

### assistant-ui

带完整运行时层的 Headless React 框架。通过 `useExternalStoreRuntime` 适配器将 `useStream` 桥接到 `AssistantRuntimeProvider`。

### OpenUI

生成式 UI 库，让智能体能够以声明式组件 DSL 生成完整的、交互式的仪表板。专为数据丰富的报告式 UI 而设计。

## 选择库

每个库适合稍微不同的集成模式。选择取决于你正在构建的 UI 类型：

| | CopilotKit | AI Elements | assistant-ui | OpenUI |
| --- | --- | --- | --- | --- |
| 最适合 | 完整的聊天运行时加上结构化生成式 UI | 带有丰富消息类型的聊天 | 最小设置的全功能聊天 | 生成的仪表板和报告 |
| UI 风格 | CopilotKit 聊天外壳 + 自定义消息渲染器 | 可组合的 shadcn/ui 组件 | Headless 插槽 + 默认主题 | 带声明式 DSL 的预构建组件库 |
| 自定义 | 自定义后端端点、智能体上下文和渲染器 | 直接编辑源文件 | 覆盖组件插槽 | 通过 CSS 自定义属性进行主题设置 |
| 流式 UX | 运行时管理的聊天流，带结构化助手负载 | 组件级渐进渲染 | 内置线程管理 | 提升 — 外壳立即出现，数据逐渐填充 |
| 工具调用 | 通过 CopilotKit 运行时和自定义渲染器 | `Tool` / `ToolHeader` / `ToolOutput` | 通过消息插槽自定义 | 内联在生成的 UI 中 |
| 智能体格式 | 结构化助手响应加上可选的 Markdown | 任何 `stream.messages` | 任何 `stream.messages` | 智能体输出 openui-lang 文本 |

这四个方案都与 LangChain 智能体配合良好，后三个还可以直接连接到 `useStream`。当你需要更丰富的运行时层和一个能与 LangGraph 部署并存的专用端点时，CopilotKit 尤其有用。
