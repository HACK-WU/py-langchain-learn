# Demo 4：智能研究助手

> **阶段**：四（综合实战）
> **难度**：⭐⭐⭐⭐⭐
> **涉及文档**：00-11 全部

---

## 目标

构建一个能分析文档的智能研究助手，融合模型、消息、工具、记忆、流式、结构化输出和中间件全部知识点。

---

## 功能需求

### 模型
- `init_chat_model` 初始化 + `ModelFallbackMiddleware` 容错
- `ModelRetryMiddleware` 自动重试

### 消息
- 使用 `content_blocks` 处理多模态输入（文本 + URL）

### 工具（5+个）
| 工具 | 功能 | 使用 ToolRuntime |
|------|------|-----------------|
| `fetch_url` | 抓取网页内容 | Stream Writer（进度反馈） |
| `search_keyword` | 在文本中搜索关键词 | State（读取已抓取的文本） |
| `count_lines` | 统计文本行数 | State（读取已抓取的文本） |
| `summarize_text` | 摘要指定内容 | State + Context（模型配置） |
| `save_note` | 保存笔记到 Store | Store（长期记忆） |

### 记忆
- `InMemorySaver` 短期记忆（对话内保持已抓取的文本）
- `InMemoryStore` 长期记忆（跨对话，保存研究笔记）

### 结构化输出
- `ToolStrategy(ResearchReport)` 返回结构化研究报告

### 流式输出
- `stream_mode=["messages", "custom"]`
- 工具通过 `stream_writer` 发送进度

### 中间件组合
| 中间件 | 类型 | 作用 |
|--------|------|------|
| `SummarizationMiddleware` | 内置 | 长文档上下文管理 |
| `ContextEditingMiddleware` | 内置 | Token 接近限制时清理旧工具输出 |
| `ModelCallLimitMiddleware` | 内置 | 防止失控循环 |
| `ModelRetryMiddleware` | 内置 | 模型调用重试 |
| 自定义 `@after_agent` | 自定义 | 研究完成后自动保存摘要到 Store |

---

## 核心代码框架

```python
import re
from typing import Any, NotRequired

import urllib.request
import urllib.error

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import (
    SummarizationMiddleware,
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
    ContextEditingMiddleware,
    ClearToolUsesEdit,
    after_agent,
)
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langchain.agents.structured_output import ToolStrategy
from langchain.agents import AgentState as BaseAgentState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from langgraph.runtime import Runtime

# ============================================================
# 1. 自定义状态
# ============================================================

class ResearchState(AgentState):
    """研究助手状态：保存当前研究的文档内容"""
    fetched_text: NotRequired[str]  # 已抓取的文本
    fetched_url: NotRequired[str]   # 来源 URL

# ============================================================
# 2. 工具定义
# ============================================================

@tool
def fetch_url(url: str, runtime: ToolRuntime) -> str:
    """Fetch and store the text content from a URL.
    
    Args:
        url: The URL to fetch content from.
    """
    writer = runtime.stream_writer
    if writer:
        writer(f"正在获取 {url} ...")
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; research-agent/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"获取失败: {e}"
    
    text = raw.decode("utf-8", errors="replace")
    line_count = len(text.splitlines())
    
    if writer:
        writer(f"获取完成，共 {line_count} 行")
    
    # 返回预览，完整文本存入 State
    preview = text[:500] + ("..." if len(text) > 500 else "")
    return (
        f"已获取 {url} 的内容（共 {line_count} 行）。\n"
        f"内容预览:\n{preview}\n\n"
        f"可使用 search_keyword 搜索关键词，count_lines 统计行数。"
    )

@tool
def search_keyword(keyword: str, runtime: ToolRuntime) -> str:
    """Search for a keyword in the fetched text.
    
    Args:
        keyword: The keyword to search for.
    """
    text = runtime.state.get("fetched_text", "")
    if not text:
        return "尚未获取任何文档，请先使用 fetch_url 获取文档"
    
    lines = text.splitlines()
    matches = []
    for i, line in enumerate(lines, 1):
        if keyword.lower() in line.lower():
            matches.append(f"第 {i} 行: {line.strip()[:100]}")
    
    if not matches:
        return f"未找到关键词 '{keyword}'"
    
    result = f"找到 {len(matches)} 处包含 '{keyword}' 的行:\n"
    for m in matches[:20]:  # 最多显示 20 条
        result += f"  {m}\n"
    if len(matches) > 20:
        result += f"  ... 还有 {len(matches) - 20} 条结果"
    
    return result

@tool
def count_lines(runtime: ToolRuntime) -> str:
    """Count the number of lines in the fetched text."""
    text = runtime.state.get("fetched_text", "")
    if not text:
        return "尚未获取任何文档"
    
    lines = text.splitlines()
    chars = len(text)
    
    return f"文档统计: {len(lines)} 行，{chars} 字符"

@tool
def summarize_text(start_line: int = 1, end_line: int | None = None, runtime: ToolRuntime) -> str:
    """Summarize a range of lines from the fetched text.
    
    Args:
        start_line: The starting line number (1-based).
        end_line: The ending line number. If None, summarize to the end.
    """
    text = runtime.state.get("fetched_text", "")
    if not text:
        return "尚未获取任何文档"
    
    lines = text.splitlines()
    start_idx = max(0, start_line - 1)
    end_idx = end_line if end_line else len(lines)
    
    selected = "\n".join(lines[start_idx:end_idx])
    
    # 截断过长文本
    if len(selected) > 3000:
        selected = selected[:3000] + "\n... (截断)"
    
    return f"第 {start_line}-{end_idx} 行内容:\n{selected}"

@tool
def save_note(title: str, content: str, runtime: ToolRuntime) -> str:
    """Save a research note to the store for future reference.
    
    Args:
        title: The note title.
        content: The note content.
    """
    store = runtime.store
    if store is None:
        return "存储服务不可用"
    
    store.put(("research_notes",), title, {"content": content, "url": runtime.state.get("fetched_url", "")})
    return f"研究笔记 '{title}' 已保存"

# ============================================================
# 3. 结构化输出 Schema
# ============================================================

class ResearchReport(BaseModel):
    """Structured research report."""
    summary: str = Field(description="A concise summary of the research findings")
    key_findings: list[str] = Field(description="List of key findings, each with reference to line numbers")
    references: list[str] = Field(description="Referenced lines or sections")
    notes_saved: bool = Field(description="Whether research notes were saved to the store")

# ============================================================
# 4. 自定义中间件
# ============================================================

@after_agent
def auto_save_summary(state: ResearchState, runtime: Runtime) -> dict[str, Any] | None:
    """研究完成后自动保存摘要到 Store"""
    store = runtime.store if runtime else None
    if store is None:
        return None
    
    messages = state.get("messages", [])
    if not messages:
        return None
    
    # 获取最后一条 AI 消息作为摘要
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            fetched_url = state.get("fetched_url", "unknown")
            note_key = f"auto-summary-{fetched_url.replace('/', '_')}"
            store.put(("auto_summaries",), note_key, {
                "summary": msg.content[:500],
                "url": fetched_url,
            })
            return None
    
    return None

# ============================================================
# 5. 创建 Agent
# ============================================================

model = init_chat_model("openai:gpt-5.4", temperature=0.3)
store = InMemoryStore()

agent = create_agent(
    model=model,
    tools=[fetch_url, search_keyword, count_lines, summarize_text, save_note],
    state_schema=ResearchState,
    checkpointer=InMemorySaver(),
    store=store,
    response_format=ToolStrategy(ResearchReport),
    system_prompt=SystemMessage(content=[
        {"type": "text", "text": """你是一个智能研究助手。你可以帮助用户分析文本文档。

## 研究方法论
1. 先使用 fetch_url 获取文档
2. 使用 count_lines 了解文档规模
3. 使用 search_keyword 搜索关键内容
4. 使用 summarize_text 阅读关键段落
5. 使用 save_note 保存重要发现

## 注意事项
- 不要猜测内容，所有结论必须基于工具返回的结果
- 引用具体行号支持你的发现
- 研究完成后主动保存笔记"""},
    ]),
    middleware=[
        # 上下文管理
        SummarizationMiddleware(
            model="openai:gpt-5.4-mini",
            trigger=("tokens", 8000),
            keep=("messages", 20),
        ),
        ContextEditingMiddleware(
            edits=[ClearToolUsesEdit(trigger=100000, keep=3)],
        ),
        
        # 安全限制
        ModelCallLimitMiddleware(thread_limit=30, run_limit=15, exit_behavior="end"),
        ModelRetryMiddleware(max_retries=2, backoff_factor=2.0),
        
        # 自定义
        auto_save_summary,
    ],
)

# ============================================================
# 6. 运行（流式 + 多模式）
# ============================================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "research-001"}}
    
    print("智能研究助手 — 输入 URL 或研究问题，输入 'exit' 退出")
    print("=" * 50)
    
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            break
        
        print()
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode=["messages", "custom"],
            version="v2",
        ):
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]
                if hasattr(token, "text") and token.text:
                    print(token.text, end="", flush=True)
            elif chunk["type"] == "custom":
                print(f"\n[进度] {chunk['data']}", flush=True)
        
        print()
```

---

## 练习任务

### 基础（必做）

1. **跑通代码**：给定一个 URL，完成完整的抓取→搜索→摘要→保存流程
2. **记忆验证**：同一 thread_id 下多轮交互，验证 State 中的 `fetched_text` 是否持续可用
3. **流式体验**：观察 `stream_mode=["messages", "custom"]` 的输出效果
4. **结构化输出**：触发 `ResearchReport` 结构化响应，检查 `result["structured_response"]`

### 进阶（选做）

5. **跨对话记忆**：不同 thread_id 下，验证 `InMemoryStore` 中的研究笔记是否可查
6. **多文档对比**：扩展 `ResearchState` 支持多份文档，添加 `compare_documents` 工具
7. **子 Agent**：使用 `SubAgentMiddleware` 为不同研究任务创建专门子 Agent
8. **动态工具**：实现 `@wrap_model_call` 中间件，根据查询意图选择加载哪些工具
9. **Runnable 深入**：阅读 `langchain_core/runnables/base.py`，理解 Agent 底层如何通过 `Runnable` 实现流式和批量

---

## 源码阅读指引

| 文件 | 关注点 |
|------|--------|
| `langchain/agents/` | `create_agent` 的完整实现，从创建到执行的全链路 |
| `langchain_core/runnables/base.py` | `Runnable` 的 invoke/stream/batch 实现（最硬核） |
| `langchain/agents/middleware/` | 各内置中间件的组合和编排逻辑 |
| `langgraph/checkpoint/memory.py` | `InMemorySaver` 的存取机制 |
| `langgraph/store/memory.py` | `InMemoryStore` 的跨对话存储机制 |

**思考题**：
1. `create_agent` 返回的对象本质上是什么？它和 `Runnable` 的关系是什么？
2. `stream_mode=["messages", "custom"]` 在底层是如何同时输出两种模式的？
3. `ToolStrategy` 的结构化输出在源码中是如何通过工具调用模拟实现的？
4. 如果要支持 100 个并发用户研究不同文档，需要改造哪些部分？
5. 从架构角度看，Agent 和 LangGraph StateGraph 的本质关系是什么？
