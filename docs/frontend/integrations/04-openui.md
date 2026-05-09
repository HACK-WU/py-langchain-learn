# OpenUI

> 使用 OpenUI 组件库和 openui-lang 生成完整、可交互的仪表板和报告

OpenUI 是一个生成式 UI 库，能够让语言模型以一种名为 openui-lang 的声明性格式生成完整、可交互的 UI。模型不再返回纯文本消息，而是返回一个组件树，其中包含卡片、图表、表格、标签页和表单，然后由 `Renderer` 将其渲染成真实的 React UI。

此集成非常适合数据丰富的输出场景，如报告、仪表板和数据探索器，在这些场景中，模型同时扮演数据分析师和 UI 设计师的角色。

## 工作原理

1. 生成系统提示词：在启动时调用一次 `openuiLibrary.prompt()`；它会生成完整的 openui-lang 参考文档，供模型编写有效的组件树使用
2. 在第一条消息中注入：在新对话开始时，将系统提示词作为第一条系统消息发送
3. 模型编写 openui-lang：模型返回类似 `root = Stack([header, kpis, chart])` 的程序，而不是纯文本
4. 使用 `Renderer` 渲染：将文本传递给 OpenUI 的 `Renderer` 和组件库；它会解析并渲染组件树

```mermaid
%%{
  init: {
    "fontFamily": "monospace",
    "flowchart": {
      "curve": "curve"
    }
  }
}%%
graph LR
  PROMPT["openuiLibrary.prompt()"]
  AGENT["createAgent()"]
  STREAM["useStream()"]
  RENDERER["Renderer"]

  PROMPT --"系统消息"--> AGENT
  AGENT --"openui-lang 文本"--> STREAM
  STREAM --"AI 消息内容"--> RENDERER

```

## 安装

```bash
npm install @langchain/react @openuidev/react-ui @openuidev/react-headless @openuidev/react-lang

```

OpenUI 需要 React 19+ 和 `zustand`。前端代码仅支持 React；LangGraph 代理后端可以使用 TypeScript 或 Python 编写。

## 导入组件样式

在 CSS 入口点或直接在根组件中导入 OpenUI 的打包样式：

```css
@import "@openuidev/react-ui/components.css";
@import "@openuidev/react-ui/styles/index.css";

```

## 生成系统提示词

OpenUI 提供了一个 `openuiLibrary.prompt()` 函数，用于生成完整的 openui-lang 参考文档，包括所有组件签名、语法规则、流式传输技巧和示例。在模块加载时调用一次：

```ts
import { openuiLibrary, openuiPromptOptions } from "@openuidev/react-ui/genui-lib";

// 生成完整的 openui-lang 系统提示词。在启动时调用一次即可，
// 不要在组件内部调用，以避免每次渲染都重新计算。
const SYSTEM_PROMPT = openuiLibrary.prompt({
  ...openuiPromptOptions,
  preamble:
    "你是一个报告生成器。当被要求生成报告时，使用 openui-lang 生成详细的、" +
    "数据丰富的报告：包含执行摘要、KPI 卡片、图表、" +
    "表格和多个章节。你的整个响应必须是原始 openui-lang" +
    "——不要使用代码围栏、markdown 或纯文本。",
});

```

`preamble` 会覆盖默认的角色设定。添加 `additionalRules` 来注入任务特定的约束：

```ts
const SYSTEM_PROMPT = openuiLibrary.prompt({
  ...openuiPromptOptions,
  preamble: "你是一个报告生成器...",
  additionalRules: [
    ...(openuiPromptOptions.additionalRules ?? []),
    "始终使用 " +
    "Button({ type: 'continue_conversation' }, 'secondary') 在 " +
    "Card([CardHeader('深入探索'), Buttons([...])], 'sunk') 内" +
    "在报告末尾添加 3-4 个后续查询按钮。",
  ],
});

```

## 通过 useStream 注入系统提示词

将系统提示词作为每个新线程的第一条消息发送。检查 `stream.messages.length === 0` 以检测新线程并在最前面添加 `system` 消息：

```tsx
import { useCallback } from "react";
import { useStream } from "@langchain/react";

const SYSTEM_PROMPT = openuiLibrary.prompt({ ... });

export function App() {
  const stream = useStream({
    apiUrl: import.meta.env.VITE_LANGGRAPH_API_URL ?? "/api/langgraph",
    assistantId: "my_agent",
    reconnectOnMount: true,
    fetchStateHistory: true,
  });

  const handleSubmit = useCallback(
    (text: string) => {
      // 仅在新线程的第一条消息上注入系统提示词。
      // 后续消息已经在其持久化历史记录中包含它。
      const isNewThread = stream.messages.length === 0;
      stream.submit({
        messages: [
          ...(isNewThread
            ? [{ type: "system", content: SYSTEM_PROMPT }]
            : []),
          { type: "human", content: text },
        ],
      });
    },
    [stream],
  );

  // ...
}

```

## 使用 Renderer 渲染

将 AI 消息的文本内容直接传递给 `Renderer`，同时传入 `openuiLibrary`：

```tsx
import { Renderer } from "@openuidev/react-lang";
import { openuiLibrary } from "@openuidev/react-ui/genui-lib";
import { AIMessage } from "langchain";

function MessageList({ messages, isLoading }) {
  const lastAiIdx = messages.reduce(
    (acc, msg, i) => (AIMessage.isInstance(msg) ? i : acc),
    -1,
  );

  return messages.map((msg, i) => {
    if (AIMessage.isInstance(msg)) {
      const text = typeof msg.content === "string" ? msg.content : "";
      return (
        <Renderer
          key={msg.id ?? i}
          response={text}
          library={openuiLibrary}
          isStreaming={isLoading && i === lastAiIdx}
        />
      );
    }
    // ... 人类消息气泡
  });
}

```

在活动流期间传递 `isStreaming={true}`，以便 Renderer 在处理传入定义时优雅地处理未解析的引用。

## openui-lang 格式

模型编写的是程序而不是 JSON 规范。每条语句都是一个赋值语句；`root` 是入口点。官方提示词会教模型使用这种格式，包括提升（hoisting）——先写 `root`，这样 UI 外壳会立即出现：

```
root = Stack([header, execSummary, kpis, marketSection])

header    = CardHeader("2025 年人工智能现状", "综合分析")
execSummary = MarkDownRenderer("## 执行摘要\n\n人工智能市场达到了...")

kpi1 = Card([CardHeader("$8260亿", "全球市场"), TextContent("同比增长 42%", "small")], "sunk")
kpi2 = Card([CardHeader("78%",   "采用率"),       TextContent("财富 500 强",  "small")], "sunk")
kpis = Stack([kpi1, kpi2], "row", "m", "stretch", "start", true)

col1 = Col("细分市场", "string")
col2 = Col("收入（十亿美元）", "number")
tbl  = Table([col1, col2], [["生成式 AI", 286], ["机器学习基础设施", 198]])
s1   = Series("收入", [286, 198, 147])
ch1  = BarChart(["生成式 AI", "机器学习基础设施", "视觉"], [s1])
marketSection = Card([CardHeader("市场细分"), tbl, ch1])

```

启用提升（推荐）后，`root` 行首先被写入，因此页面结构会立即出现，每个章节在模型定义时逐步填充。

## 渐进式渲染工具

直接将 `useStream` 连接到 `Renderer` 会导致每次流式传输令牌都重新渲染，并产生数百次无操作的重解析。这会在图表组件数据尚未到达时导致崩溃。以下工具解决了这些问题：

| 问题 | 解决方案 |
| --- | --- |
| 不完整的字符串字面量 | `truncateAtOpenString` / `closeOrTruncateOpenString` —— 在解析前删除或关闭不完整的字符串 |
| 令牌中间的抖动 | `useStableText` —— 仅在完整的语句边界（`name = Expr(…)`）上开启 Renderer 更新，而不是每个令牌都更新 |
| 图表空数据崩溃 | `chartDataRefsResolved` —— 在将图表包含在快照中之前，验证图表的 `Series` 和标签数组是否已定义 |
| 没有 `root` 或回退 | `buildProgressiveRoot` —— 当模型尚未编写 `root` 时，从顶级变量合成 `root = Stack([…])` |
| 下划线命名标识符 | `sanitizeIdentifiers` —— 解析器只接受驼峰命名；将模型输出的任何 `snake_case` 名称进行转换 |

将完整代码块复制到您的项目中，并传递 `stable` 给 ``：

```tsx
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  type ActionEvent,
  BuiltinActionType,
  Renderer,
} from "@openuidev/react-lang";
import { openuiLibrary } from "@openuidev/react-ui/genui-lib";

/** 去除模型可能输出的任何 markdown 代码围栏。 */
function stripCodeFence(text: string): string {
  return text
    .replace(/^```[a-z]*\r?\n?/i, "")
    .replace(/\n?```\s*$/i, "")
    .trim();
}

/**
 * openui-lang 解析器只接受驼峰命名标识符。
 * 转换模型输出的任何 snake_case 变量名；字符串内容保持不变。
 */
function sanitizeIdentifiers(text: string): string {
  const toCamel = (s: string) =>
    s.replace(/_([a-zA-Z0-9])/g, (_, c: string) => c.toUpperCase());

  const snakeVars: string[] = [];
  for (const m of text.matchAll(/^([a-zA-Z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)+)\s*=/gm)) {
    if (!snakeVars.includes(m[1])) snakeVars.push(m[1]);
  }
  if (snakeVars.length === 0) return text;

  let result = "";
  let inStr = false;
  let i = 0;
  while (i < text.length) {
    if (text[i] === "\\" && inStr) { result += text[i] + (text[i + 1] ?? ""); i += 2; continue; }
    if (text[i] === '"') { inStr = !inStr; result += text[i++]; continue; }
    if (!inStr) {
      let replaced = false;
      for (const v of snakeVars) {
        if (text.startsWith(v, i) && !/[a-zA-Z0-9_]/.test(text[i + v.length] ?? "")) {
          result += toCamel(v); i += v.length; replaced = true; break;
        }
      }
      if (!replaced) result += text[i++];
    } else {
      result += text[i++];
    }
  }
  return result;
}

/**
 * 遍历文本跟踪未闭合的字符串。如果文本在字符串中间结束，则截断到
 * 最后一个安全的换行符 —— 这可以防止不完整的字符串字面量消耗
 * 我们稍后合成的任何 `root = Stack(…)` 行。
 */
function truncateAtOpenString(text: string): string {
  let inStr = false;
  let lastSafeNewline = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === "\\" && inStr) { i++; continue; }
    if (ch === '"') { inStr = !inStr; continue; }
    if (ch === "\n" && !inStr) lastSafeNewline = i;
  }
  return inStr ? text.slice(0, lastSafeNewline) : text;
}

/**
 * 类似 truncateAtOpenString，但在当前行是 TextContent 语句时
 * 合成一个闭合的 `")`。这让文本在令牌逐个到来时渲染，
 * 而其他所有部分字符串行仍然被截断。
 */
function closeOrTruncateOpenString(text: string): string {
  let inStr = false;
  let lastSafeNewline = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === "\\" && inStr) { i++; continue; }
    if (ch === '"') { inStr = !inStr; continue; }
    if (ch === "\n" && !inStr) lastSafeNewline = i;
  }
  if (!inStr) return text;

  const safeText = lastSafeNewline > 0 ? text.slice(0, lastSafeNewline) : "";
  const partialLine = text.slice(lastSafeNewline > 0 ? lastSafeNewline + 1 : 0);

  if (/^[a-zA-Z][a-zA-Z0-9]*\s*=\s*TextContent\(/.test(partialLine)) {
    return (lastSafeNewline > 0 ? safeText + "\n" : "") + partialLine + '")';
  }
  return safeText;
}

/** 统计形成完整赋值语句的行数，以 `)` 或 `]` 结尾。 */
function countCompleteStatements(text: string): number {
  let count = 0;
  for (const line of text.split("\n")) {
    const t = line.trimEnd();
    if ((t.endsWith(")") || t.endsWith("]")) && /^[a-zA-Z]/.test(t)) count++;
  }
  return count;
}

const CHART_TYPES = new Set([
  "BarChart", "LineChart", "AreaChart", "RadarChart",
  "HorizontalBarChart", "PieChart", "RadialChart",
  "SingleStackedBarChart", "ScatterChart",
]);

const OPENUI_KEYWORDS = new Set([
  "true", "false", "null", "grouped", "stacked", "linear", "natural", "step",
  "pie", "donut", "string", "number", "action", "row", "column", "card", "sunk",
  "clear", "info", "warning", "error", "success", "neutral", "danger", "start",
  "end", "center", "between", "around", "evenly", "stretch", "baseline",
  "small", "default", "large", "none", "xs", "s", "m", "l", "xl",
  "horizontal", "vertical",
]);

/**
 * 当图表的标签或系列属性未解析时，图表组件（recharts）会因 .map() on null 而崩溃。
 * 在提交稳定快照之前，验证文本中的每个图表的所有数据变量是否都已定义。
 */
function chartDataRefsResolved(text: string): boolean {
  const lines = text.split("\n");
  const complete = new Set<string>();
  for (const line of lines) {
    const t = line.trimEnd();
    const m = t.match(/^([a-zA-Z][a-zA-Z0-9]*)\s*=/);
    if (m && (t.endsWith(")") || t.endsWith("]"))) complete.add(m[1]);
  }
  for (const line of lines) {
    const t = line.trimEnd();
    const m = t.match(/^([a-zA-Z][a-zA-Z0-9]*)\s*=\s*([A-Z][a-zA-Z0-9]*)\(/);
    if (!m || !CHART_TYPES.has(m[2]) || !t.endsWith(")")) continue;
    const rhs = t.slice(t.indexOf("=") + 1).replace(/"(?:[^"\\]|\\.)*"/g, '""');
    for (const [, name] of rhs.matchAll(/\b([a-zA-Z][a-zA-Z0-9]*)\b/g)) {
      if (/^[a-z]/.test(name) && !OPENUI_KEYWORDS.has(name) && !complete.has(name))
        return false;
    }
  }
  return true;
}

/**
 * 如果模型尚未编写 `root = Stack(…)`，则从
 * 顶级变量（已定义但未在其他表达式中引用的那些）合成一个。
 * 这使得即使模型最后才写 root，也能实现渐进式渲染。
 */
function buildProgressiveRoot(text: string): string {
  if (!text) return text;
  const safe = truncateAtOpenString(text);
  if (/^root\s*=/m.test(safe)) return safe;

  const defs: string[] = [];
  const seen = new Set<string>();
  for (const m of safe.matchAll(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*=/gm)) {
    if (!seen.has(m[1])) { defs.push(m[1]); seen.add(m[1]); }
  }
  if (defs.length === 0) return safe;

  const referenced = new Set<string>();
  for (const line of safe.split("\n")) {
    const thisVar = line.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*=/)?.[1];
    const stripped = line.replace(/"(?:[^"\\]|\\.)*"/g, '""');
    for (const v of defs) {
      if (v !== thisVar && new RegExp(`\\b${v}\\b`).test(stripped)) referenced.add(v);
    }
  }

  const topLevel = defs.filter((v) => !referenced.has(v));
  const rootVars = topLevel.length > 0 ? topLevel : defs;
  return `${safe.trimEnd()}\nroot = Stack([${rootVars.join(", ")}], "column", "l")`;
}

/**
 * 控制 Renderer 仅在至少有一个新的*完整*语句到达时才更新。
 * 这消除了流式传输过程中数百次无操作的重解析。
 *
 * 特殊情况：TextContent 行通过 closeOrTruncate 逐令牌更新
 * 这样文本可以在不等待整行完成的情况下渐进式渲染。
 */
function useStableText(raw: string, isStreaming: boolean): string {
  const [stable, setStable] = useState<string>("");
  const lastCount = useRef(0);

  useEffect(() => {
    const safe = truncateAtOpenString(raw);         // 严格 —— 仅用于计数
    const enhanced = closeOrTruncateOpenString(raw); // 显示 —— 闭合部分 TextContent

    if (!isStreaming) { setStable(enhanced); return; }

    const count = countCompleteStatements(safe);
    const newComplete = count > lastCount.current && chartDataRefsResolved(safe);
    const partialTextContent = enhanced !== safe;

    if (newComplete || partialTextContent) {
      if (newComplete) lastCount.current = count;
      setStable(enhanced);
    }
  }, [raw, isStreaming]);

  return stable;
}

function AIMessageView({
  raw,
  isStreaming,
  onSubmit,
}: {
  raw: string;
  isStreaming: boolean;
  onSubmit: (text: string) => void;
}) {
  const stable = useStableText(raw, isStreaming);
  const processed = useMemo(() => buildProgressiveRoot(stable), [stable]);

  const handleAction = useCallback(
    (event: ActionEvent) => {
      if (event.type === BuiltinActionType.ContinueConversation) {
        onSubmit(event.humanFriendlyMessage);
      }
    },
    [onSubmit],
  );

  if (!processed) return null;

  return (
    <Renderer
      response={processed}
      library={openuiLibrary}
      isStreaming={isStreaming}
      onAction={handleAction}
    />
  );
}

export function MessageList({ messages, isLoading, onSubmit }) {
  const lastAiIdx = messages.reduce(
    (acc, msg, i) => (msg.getType() === "ai" ? i : acc),
    -1,
  );

  return messages.map((msg, i) => {
    if (msg.getType() === "human") {
      return (
        <div key={msg.id ?? i} className="flex justify-end">
          <div className="user-bubble">
            {typeof msg.content === "string" ? msg.content : ""}
          </div>
        </div>
      );
    }

    if (msg.getType() === "ai") {
      const raw = sanitizeIdentifiers(
        stripCodeFence(typeof msg.content === "string" ? msg.content : ""),
      );
      if (!raw) return null;
      return (
        <div key={msg.id ?? i}>
          <AIMessageView
            raw={raw}
            isStreaming={isLoading && i === lastAiIdx}
            onSubmit={onSubmit}
          />
        </div>
      );
    }

    return null;
  });
}

```

## 后续查询

OpenUI 的 `Button` 组件支持 `continue_conversation` 操作类型。当用户点击后续按钮时，`Renderer` 会触发 `onAction`，上面的 `AIMessageView` 会将按钮的标签作为下一条用户消息提交，代码路径与在输入框中打字完全相同。

通过系统提示词中的 `additionalRules` 为每个报告添加一个"深入探索"部分：

```
followUp1 = Button("2024 年与 2025 年 AI 领导者对比", { type: "continue_conversation" }, "secondary")
followUp2 = Button("全球 AI 投资细分",  { type: "continue_conversation" }, "secondary")
followUpBtns = Buttons([followUp1, followUp2], "row")
followUpCard  = Card([CardHeader("深入探索"), followUpBtns], "sunk")
root = Stack([..., followUpCard])

```

## 最佳实践

- 在模块加载时生成系统提示词：不要在 React 组件内部；提示词有几千字节，应该只计算一次
- 仅在新线程上注入系统提示词：检查 `stream.messages.length === 0`，在后续轮次跳过注入，以避免在线程历史记录中重复提示词
- 使用提升顺序：先写 `root = Stack([...])`；UI 外壳会立即出现，章节会随着模型定义逐步填充
- 在完整语句上开启更新：避免在每个令牌上都重新渲染 Renderer；仅在完整的语句（`name = ComponentCall(...)`）到达时才更新
- 渲染前验证图表数据：图表组件需要其 `Series` 和标签数组在包含在稳定快照中之前就已经定义
- 保持驼峰命名变量名：openui-lang 解析器只接受驼峰命名标识符；在系统提示词的 `additionalRules` 中强化这一点
