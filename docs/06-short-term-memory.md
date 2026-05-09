# LangChain 短期记忆（Short-term Memory）

> 来源：https://docs.langchain.com/oss/python/langchain/short-term-memory

---

## 概述

记忆系统让 Agent 能记住之前的交互、从反馈中学习、适应用户偏好。随着 Agent 处理越来越复杂的任务，这种能力对效率和用户满意度至关重要。

**短期记忆**让你的应用在**单个线程/对话**中记住之前的交互。

> 💡 需要跨对话记忆？使用 [长期记忆（Long-term Memory）](https://docs.langchain.com/oss/python/langchain/long-term-memory)。

```mermaid
graph LR
    A[对话消息] --> B[短期记忆 State]
    B --> C[Checkpointer 持久化]
    C --> D[数据库 / 内存]

    E[长对话挑战] --> F[上下文窗口溢出]
    E --> G[模型注意力分散]
    E --> H[响应变慢 / 成本增加]

    F --> I[裁剪消息]
    F --> J[删除消息]
    F --> K[摘要消息]
```

---

## 基本用法

通过指定 `checkpointer` 为 Agent 添加短期记忆：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    "gpt-5.4",
    tools=[get_user_info],
    checkpointer=InMemorySaver(),  # 添加短期记忆
)

agent.invoke(
    {"messages": [{"role": "user", "content": "Hi! My name is Bob."}]},
    {"configurable": {"thread_id": "1"}},  # 线程 ID 标识对话
)
```

### 生产环境

使用数据库支持的 checkpointer：

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    agent = create_agent(
        "gpt-5.4",
        tools=[get_user_info],
        checkpointer=checkpointer,
    )
```

---

## 自定义 Agent 记忆

默认使用 `AgentState`，通过 `messages` 键管理对话历史。扩展 `AgentState` 添加自定义字段：

```python
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver

class CustomAgentState(AgentState):
    user_id: str
    preferences: dict

agent = create_agent(
    "gpt-5.4",
    tools=[get_user_info],
    state_schema=CustomAgentState,
    checkpointer=InMemorySaver(),
)

result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Hello"}],
        "user_id": "user_123",
        "preferences": {"theme": "dark"},
    },
    {"configurable": {"thread_id": "1"}},
)
```

---

## 常见模式

长对话可能超出 LLM 上下文窗口，常见解决方案：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **裁剪消息** | 移除最早/最晚的 N 条消息 | 简单截断，对信息丢失不敏感 |
| **删除消息** | 从状态中永久删除消息 | 需要精确控制消息历史 |
| **摘要消息** | 摘要旧消息并替换 | 需要保留关键信息 |

### 裁剪消息

使用 `@before_model` 中间件：

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from typing import Any

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """仅保留最后几条消息以适应上下文窗口"""
    messages = state["messages"]
    if len(messages) <= 3:
        return None

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages,
        ]
    }

agent = create_agent(
    your_model,
    tools=your_tools,
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)
```

### 删除消息

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

# 删除特定消息
def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}

# 删除所有消息
def delete_all_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
```

> 🐞 删除消息时确保结果历史有效——某些提供商要求以 `user` 消息开头，有工具调用的 `assistant` 消息后必须跟对应的 `tool` 结果消息。

### 摘要消息

使用内置 `SummarizationMiddleware`（推荐）：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),     # 触发条件：Token 数 ≥ 4000
            keep=("messages", 20),         # 保留最近 20 条消息
        )
    ],
    checkpointer=InMemorySaver(),
)
```

---

## 访问记忆

### 在工具中读取短期记忆

```python
from langchain.agents import create_agent, AgentState
from langchain.tools import tool, ToolRuntime

class CustomState(AgentState):
    user_id: str

@tool
def get_user_info(runtime: ToolRuntime) -> str:
    """Look up user info."""
    user_id = runtime.state["user_id"]
    return "User is John Smith" if user_id == "user_123" else "Unknown user"
```

### 在工具中写入短期记忆

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langchain.agents import create_agent, AgentState
from langgraph.types import Command

class CustomState(AgentState):
    user_name: str

@tool
def update_user_info(runtime: ToolRuntime[None, CustomState]) -> Command:
    """Look up and update user info."""
    user_id = runtime.context.user_id
    name = "John Smith" if user_id == "user_123" else "Unknown user"
    return Command(update={
        "user_name": name,
        "messages": [ToolMessage("Successfully looked up user information", tool_call_id=runtime.tool_call_id)]
    })
```

### 在动态提示词中访问

```python
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context["user_name"]
    return f"You are a helpful assistant. Address the user as {user_name}."
```

### 在 before_model 中访问

```mermaid
graph TD
    S(["__start__"]) --> PRE[before_model]
    PRE --> MODEL[model]
    MODEL -.-> TOOLS[tools]
    MODEL -.-> END(["__end__"])
    TOOLS --> PRE
```

```python
from langchain.agents.middleware import before_model

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """在模型调用前处理消息"""
    messages = state["messages"]
    if len(messages) <= 3:
        return None
    # ... 裁剪逻辑
```

### 在 after_model 中访问

```mermaid
graph TD
    S(["__start__"]) --> MODEL[model]
    MODEL --> POST[after_model]
    POST -.-> END(["__end__"])
    POST -.-> TOOLS[tools]
    TOOLS --> MODEL
```

```python
from langchain.agents.middleware import after_model

@after_model
def validate_response(state: AgentState, runtime: Runtime) -> dict | None:
    """移除包含敏感词的消息"""
    STOP_WORDS = ["password", "secret"]
    last_message = state["messages"][-1]
    if any(word in last_message.content for word in STOP_WORDS):
        return {"messages": [RemoveMessage(id=last_message.id)]}
    return None
```
