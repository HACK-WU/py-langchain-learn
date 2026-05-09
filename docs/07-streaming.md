# LangChain Streaming（流式输出）

> 来源：https://docs.langchain.com/oss/python/langchain/streaming

---

## 概述

流式输出对 LLM 应用至关重要——通过逐步显示输出，即使完整响应尚未就绪，也能显著改善用户体验。

LangChain 流式系统支持：
- **Agent 进度** — 每个 Agent 步骤后获取状态更新
- **LLM Token** — 实时流式输出模型生成的 Token
- **推理/思考 Token** — 展示模型推理过程
- **自定义更新** — 发送用户定义的信号（如 `"已获取 10/100 条记录"`）
- **多模式组合** — 同时使用多种流式模式

---

## 支持的流式模式

| 模式 | 说明 |
|------|------|
| `updates` | 每个 Agent 步骤后流式输出状态更新 |
| `messages` | 从任何调用 LLM 的节点流式输出 `(token, metadata)` 元组 |
| `custom` | 使用 stream writer 从图节点内流式输出自定义数据 |

---

## Agent 进度

`stream_mode="updates"` — 每个 Agent 步骤后发出事件：

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(model="gpt-5-nano", tools=[get_weather])

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="updates",
    version="v2",
):
    if chunk["type"] == "updates":
        for step, data in chunk["data"].items():
            print(f"step: {step}")
            print(f"content: {data['messages'][-1].content_blocks}")
```

输出示例：
```
step: model       → content: [{'type': 'tool_call', 'name': 'get_weather', ...}]
step: tools       → content: [{'type': 'text', 'text': "It's always sunny in SF!"}]
step: model       → content: [{'type': 'text', 'text': "It's always sunny in SF!"}]
```

---

## LLM Token

`stream_mode="messages"` — 逐 Token 流式输出：

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        print(f"node: {metadata['langgraph_node']}")
        print(f"content: {token.content_blocks}")
```

---

## 自定义更新

使用 `get_stream_writer` 从工具内部发送实时进度：

```python
from langgraph.config import get_stream_writer

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    writer = get_stream_writer()
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(model="claude-sonnet-4-6", tools=[get_weather])

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="custom",
    version="v2",
):
    if chunk["type"] == "custom":
        print(chunk["data"])
```

> 🐞 使用 `get_stream_writer` 的工具无法在 LangGraph 执行上下文之外调用。

---

## 多模式组合

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode=["updates", "custom"],  # 传入列表
    version="v2",
):
    print(f"stream_mode: {chunk['type']}")
    print(f"content: {chunk['data']}")
```

---

## 常见模式

### 流式推理/思考 Token

```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model_name="claude-sonnet-4-6",
    thinking={"type": "enabled", "budget_tokens": 5000},
)
agent = create_agent(model=model, tools=[get_weather])

for token, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",
):
    if not isinstance(token, AIMessageChunk):
        continue
    reasoning = [b for b in token.content_blocks if b["type"] == "reasoning"]
    text = [b for b in token.content_blocks if b["type"] == "text"]
    if reasoning:
        print(f"[thinking] {reasoning[0]['reasoning']}", end="")
    if text:
        print(text[0]["text"], end="")
```

### 流式工具调用

同时流式输出部分 JSON（工具调用生成时）和已完成的工具调用：

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in Boston?"}]},
    stream_mode=["messages", "updates"],
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if isinstance(token, AIMessageChunk):
            # 部分 JSON（工具调用片段）
            ...
    elif chunk["type"] == "updates":
        for source, update in chunk["data"].items():
            if source in ("model", "tools"):
                # 已完成的消息
                ...
```

### 流式 + 人工干预

结合 `HumanInTheLoopMiddleware` 和 checkpointer 处理中断：

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, Interrupt

checkpointer = InMemorySaver()
agent = create_agent(
    "openai:gpt-5.4",
    tools=[get_weather],
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"get_weather": True})],
    checkpointer=checkpointer,
)

config = {"configurable": {"thread_id": "some_id"}}
interrupts = []

# 第一步：流式运行，收集中断
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Weather in Boston and SF?"}]},
    config=config,
    stream_mode=["messages", "updates"],
    version="v2",
):
    ...
    if source == "__interrupt__":
        interrupts.extend(update)

# 第二步：处理中断，恢复执行
decisions = {}
for interrupt in interrupts:
    decisions[interrupt.id] = {"decisions": [/* approve/edit/reject */]}

for chunk in agent.stream(
    Command(resume=decisions),
    config=config,
    stream_mode=["messages", "updates"],
    version="v2",
):
    ...
```

### 流式子 Agent

当存在多个 LLM 时，通过 `name` 参数和 `subgraphs=True` 区分来源：

```python
weather_agent = create_agent(model=weather_model, tools=[get_weather], name="weather_agent")

agent = create_agent(model=supervisor_model, tools=[call_weather_agent], name="supervisor")

current_agent = None
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in Boston?"}]},
    stream_mode=["messages", "updates"],
    subgraphs=True,
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]
        if agent_name := metadata.get("lc_agent_name"):
            if agent_name != current_agent:
                print(f"🤖 {agent_name}: ")
                current_agent = agent_name
```

---

## 禁用流式输出

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-5.4", streaming=False)
```

---

## v2 流式格式

需 `langgraph>=1.1`。传入 `version="v2"` 获得统一输出格式：

```python
# v2 格式 — 统一的 StreamPart 字典
for chunk in agent.stream(
    {"messages": [...]},
    stream_mode=["updates", "custom"],
    version="v2",
):
    print(chunk["type"])  # "updates" 或 "custom"
    print(chunk["data"])  # 载荷
```

v2 格式的 `invoke()` 返回 `GraphOutput` 对象：

```python
result = agent.invoke({"messages": [...]}, version="v2")
print(result.value)       # 状态（dict / Pydantic / dataclass）
print(result.interrupts)  # Interrupt 对象元组
```
