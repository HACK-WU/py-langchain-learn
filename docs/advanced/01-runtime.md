# Runtime（运行时）

## 概述

LangChain 的 `create_agent` 底层运行在 LangGraph 的运行时之上。

LangGraph 暴露了一个 `Runtime` 对象，包含以下信息：

1. **Context（上下文）**：静态信息，如用户 ID、数据库连接或其他代理调用所需的依赖项
2. **Store（存储）**：用于长期记忆的 BaseStore 实例
3. **Stream writer（流写入器）**：用于通过 `"custom"` 流模式流式传输信息的对象
4. **Execution info（执行信息）**：当前执行的身份和重试信息（线程 ID、运行 ID、尝试次数）
5. **Server info（服务器信息）**：在 LangGraph Server 上运行时的服务器特定元数据（助手 ID、图 ID、已认证用户）

运行时上下文为你的工具和中间件提供依赖注入功能。与其硬编码值或使用全局状态，你可以在调用代理时注入运行时依赖（如数据库连接、用户 ID 或配置）。这使得你的工具更易于测试、复用和灵活。

你可以在工具和中间件中访问运行时信息。

## 访问方式

使用 `create_agent` 创建代理时，你可以指定 `context_schema` 来定义存储在代理 `Runtime` 中的 `context` 结构。

调用代理时，传入包含当前运行相关配置的 `context` 参数：

```python
from dataclasses import dataclass

from langchain.agents import create_agent

@dataclass
class Context:
    user_name: str

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    context_schema=Context  # [!code highlight]
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")  # [!code highlight]
)
```

### 在工具内部

你可以在工具内部访问运行时信息，用于：

- 访问上下文
- 读取或写入长期记忆
- 写入自定义流（例如，工具进度/更新）

使用 `ToolRuntime` 参数在工具内部访问 `Runtime` 对象。

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime  # [!code highlight]

@dataclass
class Context:
    user_id: str

@tool
def fetch_user_email_preferences(runtime: ToolRuntime[Context]) -> str:  # [!code highlight]
    """从存储中获取用户的邮件偏好设置。"""
    user_id = runtime.context.user_id  # [!code highlight]

    preferences: str = "用户希望你撰写简洁礼貌的邮件。"
    if runtime.store:  # [!code highlight]
        if memory := runtime.store.get(("users",), user_id):  # [!code highlight]
            preferences = memory.value["preferences"]

    return preferences
```

### 在工具内部访问执行信息和服务器信息

通过 `runtime.execution_info` 访问执行身份（线程 ID、运行 ID），在 LangGraph Server 上运行时通过 `runtime.server_info` 访问服务器特定元数据（助手 ID、已认证用户）：

```python
from langchain.tools import tool, ToolRuntime

@tool
def context_aware_tool(runtime: ToolRuntime) -> str:
    """使用执行信息和服务器信息的工具。"""
    # 访问线程和运行 ID
    info = runtime.execution_info
    print(f"线程: {info.thread_id}, 运行: {info.run_id}")  # [!code highlight]

    # 访问服务器信息（仅在 LangGraph Server 上运行时可用）
    server = runtime.server_info
    if server is not None:
        print(f"助手: {server.assistant_id}")  # [!code highlight]
        if server.user is not None:
            print(f"用户: {server.user.identity}")  # [!code highlight]

    return "完成"
```

不在 LangGraph Server 上运行时（例如在本地开发期间），`server_info` 为 `None`。

需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）才能使用 `runtime.execution_info` 和 `runtime.server_info`。

### 在中间件内部

你可以在中间件中访问运行时信息，用于创建动态提示词、修改消息或根据用户上下文控制代理行为。

使用 `Runtime` 参数在节点风格的钩子中访问 `Runtime` 对象。对于包装风格的钩子，`Runtime` 对象可在 `ModelRequest` 参数中访问。

```python
from dataclasses import dataclass

from langchain.messages import AnyMessage
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import dynamic_prompt, ModelRequest, before_model, after_model
from langgraph.runtime import Runtime

@dataclass
class Context:
    user_name: str

# 动态提示词
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name  # [!code highlight]
    system_prompt = f"你是一个有帮助的助手。用 {user_name} 来称呼用户。"
    return system_prompt

# 模型前钩子
@before_model
def log_before_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  # [!code highlight]
    print(f"正在处理用户请求: {runtime.context.user_name}")  # [!code highlight]
    return None

# 模型后钩子
@after_model
def log_after_model(state: AgentState, runtime: Runtime[Context]) -> dict | None:  # [!code highlight]
    print(f"已完成用户请求: {runtime.context.user_name}")  # [!code highlight]
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    middleware=[dynamic_system_prompt, log_before_model, log_after_model],  # [!code highlight]
    context_schema=Context
)

agent.invoke(
    {"messages": [{"role": "user", "content": "What's my name?"}]},
    context=Context(user_name="John Smith")
)
```

### 在中间件内部访问执行信息和服务器信息

中间件钩子也可以访问 `runtime.execution_info` 和 `runtime.server_info`：

```python
from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime

@before_model
def auth_gate(state: AgentState, runtime: Runtime) -> dict | None:
    """在 LangGraph Server 上运行时阻止未认证用户。"""
    server = runtime.server_info
    if server is not None and server.user is None:  # [!code highlight]
        raise ValueError("需要认证")
    print(f"线程: {runtime.execution_info.thread_id}")  # [!code highlight]
    return None
```

需要 `deepagents>=0.5.0`（或 `langgraph>=1.1.5`）。
