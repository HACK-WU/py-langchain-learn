# 多智能体 (Multi-agent)

多智能体系统允许多个智能体协同工作以完成复杂任务。与单个智能体相比，多智能体架构可以将任务分解为更小的子任务，由专门的智能体处理，从而提高整体效率和准确性。

LangChain 提供了构建多智能体系统的灵活工具，支持智能体之间的通信、协调和任务分配。

## 多智能体架构概述

在多智能体系统中，通常有以下几种架构模式：

| 架构模式 | 描述 | 适用场景 |
|---------|------|---------|
| **监督者模式 (Supervisor)** | 一个中心智能体协调多个工作智能体 | 需要集中控制和决策的任务 |
| **网络模式 (Network)** | 智能体之间直接相互通信 | 需要频繁协作和去中心化决策的任务 |
| **层次模式 (Hierarchical)** | 多层智能体结构，上层智能体管理下层 | 复杂的企业级应用 |

## 使用 LangGraph 构建多智能体系统

LangGraph 是构建多智能体工作流的推荐方式。它提供了循环和持久化能力，使多智能体协调更加可靠。

### 基础示例：监督者模式

以下是一个简单的监督者模式多智能体系统示例：

```python
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

# 定义状态
class AgentState(TypedDict):
    """多智能体系统的状态"""
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    next: str  # 下一个要调用的智能体

# 创建工作智能体
def create_worker_agent(name: str, system_prompt: str, tools: list):
    """创建一个工作智能体"""
    return create_react_agent(
        model="gpt-4",
        tools=tools,
        state_modifier=system_prompt,
    )

# 研究员智能体
research_agent = create_worker_agent(
    "researcher",
    "你是一个研究员。使用搜索工具查找信息并返回研究结果。",
    [search_tool],
)

# 写手智能体
writer_agent = create_worker_agent(
    "writer",
    "你是一个写手。根据提供的研究结果撰写文章。",
    [write_tool],
)

# 监督者智能体 - 决定下一步调用哪个智能体
def supervisor_node(state: AgentState):
    """监督者节点：决定哪个智能体应该执行下一步"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个任务协调员。根据当前任务状态，"
                "决定下一步应该调用哪个智能体：researcher 或 writer。"
                "如果任务完成，请返回 FINISH。"
            ),
        }
    ] + state["messages"]

    response = model.invoke(messages)
    next_agent = response.content.strip()

    return {"next": next_agent}

# 构建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", research_agent)
workflow.add_node("writer", writer_agent)

# 添加边
workflow.add_edge("researcher", "supervisor")
workflow.add_edge("writer", "supervisor")

# 条件边：根据监督者的决定路由
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "researcher": "researcher",
        "writer": "writer",
        "FINISH": END,
    },
)

# 设置入口点
workflow.set_entry_point("supervisor")

# 编译图
graph = workflow.compile()

# 运行多智能体系统
result = graph.invoke({
    "messages": [HumanMessage(content="写一篇关于人工智能的文章")]
})
```

### 网络模式：智能体直接通信

在网络模式中，智能体可以直接相互调用：

```python
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import create_react_agent

# 创建可以相互调用的智能体
code_agent = create_react_agent(
    model="gpt-4",
    tools=[execute_code],
    state_modifier="你是一个代码专家。可以调用 review_agent 来审查你的代码。"
)

review_agent = create_react_agent(
    model="gpt-4",
    tools=[],
    state_modifier="你是一个代码审查专家。提供代码改进建议。"
)

# 定义智能体可以相互调用的工具
code_tools = [{
    "name": "ask_reviewer",
    "description": "请审查者审查代码",
    "func": lambda x: review_agent.invoke({"messages": x}),
}]

# 重新创建带有相互调用能力的智能体
code_agent = create_react_agent(
    model="gpt-4",
    tools=code_tools + [execute_code],
    state_modifier="你是一个代码专家。"
)
```

## 智能体间通信

### 消息传递

智能体通过共享状态进行通信：

```python
class MultiAgentState(MessagesState):
    """扩展的状态，包含共享上下文"""
    shared_context: dict  # 智能体间共享的上下文
    agent_outputs: dict   # 每个智能体的输出

def agent_with_context(state: MultiAgentState):
    """可以访问共享上下文的智能体"""
    context = state.get("shared_context", {})

    # 使用上下文进行决策
    messages = state["messages"]

    # 处理并更新共享上下文
    result = model.invoke(messages)

    return {
        "messages": [result],
        "shared_context": {**context, "last_update": result.content},
    }
```

### 工具调用作为通信机制

智能体可以通过工具调用相互触发：

```python
from langchain_core.tools import tool

@tool
def delegate_to_specialist(task: str, specialist_type: str) -> str:
    """将任务委托给专业智能体"""
    specialists = {
        "code": code_agent,
        "research": research_agent,
        "writing": writer_agent,
    }

    specialist = specialists.get(specialist_type)
    if not specialist:
        return f"未知的专家类型: {specialist_type}"

    result = specialist.invoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content

# 主智能体可以使用此工具委托任务
main_agent = create_react_agent(
    model="gpt-4",
    tools=[delegate_to_specialist, search_tool],
    state_modifier="你是一个主协调智能体。可以委托任务给专业智能体。"
)
```

## 持久化和中断

多智能体系统可以利用 LangGraph 的持久化功能：

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# 添加检查点
workflow = StateGraph(AgentState)
# ... 配置节点和边 ...

# 使用内存检查点（生产环境使用 PostgresSaver）
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# 运行并支持中断恢复
config = {"configurable": {"thread_id": "conversation_1"}}

# 运行直到可能的中断
result = graph.invoke(
    {"messages": [HumanMessage(content="复杂任务")]},
    config=config,
)

# 如果中断，可以恢复执行
if result.get("__interrupt__"):
    # 处理中断后恢复
    result = graph.invoke(
        Command(resume={"action": "continue"}),
        config=config,
    )
```

## 流式传输

多智能体系统支持流式输出：

```python
# 流式运行多智能体系统
for chunk in graph.stream(
    {"messages": [HumanMessage(content="任务")]},
    config=config,
    stream_mode=["updates", "messages"],
):
    if chunk["type"] == "messages":
        # 流式 LLM token
        token, metadata = chunk["data"]
        print(token.content, end="", flush=True)
    elif chunk["type"] == "updates":
        # 智能体更新
        print(f"\n[智能体更新]: {chunk['data']}")
```

## 最佳实践

### 1. 明确的职责划分

每个智能体应该有明确的职责范围：

```python
AGENT_DESCRIPTIONS = {
    "researcher": "搜索和收集信息",
    "writer": "撰写和编辑内容",
    "critic": "审查和提供反馈",
    "coder": "编写和执行代码",
}
```

### 2. 错误处理

在多智能体系统中添加错误处理：

```python
from langgraph.graph import END

def error_handler(state: AgentState):
    """处理智能体执行错误"""
    error = state.get("error")
    if error:
        return {
            "messages": [
                {"role": "system", "content": f"错误发生: {error}. 尝试恢复..."}
            ]
        }
    return state

workflow.add_node("error_handler", error_handler)
```

### 3. 超时控制

为智能体执行设置超时：

```python
import asyncio

async def run_with_timeout(agent_func, state, timeout=30):
    """带超时的智能体执行"""
    try:
        return await asyncio.wait_for(
            agent_func(state),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return {"error": "智能体执行超时"}
```

## 完整示例：研究助手

以下是一个完整的多智能体研究助手示例：

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage

# 状态定义
class ResearchState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    topic: str
    research_notes: str
    draft: str
    final_output: str
    next_step: str

# 工具定义
@tool
def search_web(query: str) -> str:
    """搜索网络获取信息"""
    # 实现搜索逻辑
    return f"搜索结果: {query}"

@tool
def save_notes(notes: str) -> str:
    """保存研究笔记"""
    return "笔记已保存"

# 创建智能体
research_agent = create_react_agent(
    model="gpt-4",
    tools=[search_web, save_notes],
    state_modifier="你是研究员。搜索信息并保存研究笔记。"
)

writer_agent = create_react_agent(
    model="gpt-4",
    tools=[],
    state_modifier="你是写手。根据研究笔记撰写文章。"
)

editor_agent = create_react_agent(
    model="gpt-4",
    tools=[],
    state_modifier="你是编辑。审查文章并提供改进建议。"
)

# 节点函数
def research_node(state: ResearchState):
    """研究节点"""
    result = research_agent.invoke(state)
    return {
        "messages": result["messages"],
        "research_notes": result["messages"][-1].content,
        "next_step": "write",
    }

def write_node(state: ResearchState):
    """写作节点"""
    result = writer_agent.invoke(state)
    return {
        "messages": result["messages"],
        "draft": result["messages"][-1].content,
        "next_step": "edit",
    }

def edit_node(state: ResearchState):
    """编辑节点"""
    result = editor_agent.invoke(state)
    content = result["messages"][-1].content

    # 检查是否需要重写
    if "需要重写" in content:
        return {
            "messages": result["messages"],
            "next_step": "write",
        }

    return {
        "messages": result["messages"],
        "final_output": content,
        "next_step": "end",
    }

def route_next(state: ResearchState):
    """路由到下一个节点"""
    return state["next_step"]

# 构建工作流
workflow = StateGraph(ResearchState)

workflow.add_node("research", research_node)
workflow.add_node("write", write_node)
workflow.add_node("edit", edit_node)

workflow.add_conditional_edges(
    "research",
    route_next,
    {"write": "write"},
)

workflow.add_conditional_edges(
    "write",
    route_next,
    {"edit": "edit"},
)

workflow.add_conditional_edges(
    "edit",
    route_next,
    {"write": "write", "end": END},
)

workflow.set_entry_point("research")

# 编译
app = workflow.compile()

# 运行
result = app.invoke({
    "messages": [HumanMessage(content="研究量子计算")],
    "topic": "量子计算",
})

print(result["final_output"])
```

## 相关资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [ReAct 智能体](https://python.langchain.com/docs/how_to/agent/)
- [工具调用](https://python.langchain.com/docs/how_to/tool_calling/)
- [人在回路](04-human-in-the-loop.md)
