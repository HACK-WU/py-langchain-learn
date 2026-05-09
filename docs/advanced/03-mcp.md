# Model Context Protocol (MCP)

Model Context Protocol（MCP，模型上下文协议）是一个开放协议，用于规范应用程序如何向大型语言模型（LLM）提供工具和上下文。LangChain 智能体可以通过 `langchain-mcp-adapters` 库使用在 MCP 服务器上定义的工具。

## 快速开始

安装 `langchain-mcp-adapters` 库：

```bash
pip install langchain-mcp-adapters
```

```bash
uv add langchain-mcp-adapters
```

`langchain-mcp-adapters` 使智能体能够使用定义在一个或多个 MCP 服务器上的工具。

`MultiServerMCPClient` 默认是无状态的。每次工具调用都会创建一个全新的 MCP `ClientSession`，执行工具，然后清理。有关更多详细信息，请参阅[有状态会话](#有状态会话)部分。

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient  # [!code highlight]
from langchain.agents import create_agent

async def main():
    client = MultiServerMCPClient(  # [!code highlight]
        {
            "math": {
                "transport": "stdio",  # 本地子进程通信
                "command": "python",
                # 指向你的 math_server.py 文件的绝对路径
                "args": ["/path/to/math_server.py"],
            },
            "weather": {
                "transport": "http",  # 基于 HTTP 的远程服务器
                # 确保你的天气服务器在 8000 端口上启动
                "url": "http://localhost:8000/mcp",
            }
        }
    )

    tools = await client.get_tools()  # [!code highlight]
    agent = create_agent(
        "claude-sonnet-4-6",
        tools  # [!code highlight]
    )
    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
    )
    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what is the weather in nyc?"}]}
    )
    print(math_response)
    print(weather_response)

if __name__ == "__main__":
    asyncio.run(main())
```

通过 LangSmith 跟踪 MCP 工具调用以及智能体的推理步骤。按照[跟踪快速入门](https://docs.langchain.com/observability/)进行设置。

## 自定义服务器

要创建自定义 MCP 服务器，请使用 FastMCP 库：

```bash
pip install fastmcp
```

```bash
uv add fastmcp
```

使用以下示例来测试你的智能体与 MCP 工具服务器：

```python
from fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """添加两个数字"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """乘以两个数字"""
    return a * b

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

```python
from fastmcp import FastMCP

mcp = FastMCP("Weather")

@mcp.tool()
async def get_weather(location: str) -> str:
    """获取指定位置的天气"""
    return "纽约总是阳光明媚"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

## 传输机制（Transports）

MCP 支持不同的传输机制用于客户端与服务器的通信。

### HTTP

`http` 传输（也称为 `streamable-http`）使用 HTTP 请求进行客户端与服务器的通信。更多详细信息请参阅 [MCP HTTP 传输规范](https://spec.modelcontextprotocol.io/specification/draft/basic/transports/streamable-http/)。

```python
client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
        }
    }
)
```

#### 传递请求头

通过 HTTP 连接到 MCP 服务器时，你可以在连接配置中使用 `headers` 字段包含自定义请求头（例如用于身份验证或跟踪）。此功能支持 `sse`（已被 MCP 规范弃用）和 `streamable_http` 传输。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {  # [!code highlight]
                "Authorization": "Bearer YOUR_TOKEN",  # [!code highlight]
                "X-Custom-Header": "custom-value"  # [!code highlight]
            },  # [!code highlight]
        }
    }
)
tools = await client.get_tools()
agent = create_agent("openai:gpt-5.4", tools)
response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
```

#### 身份验证

`langchain-mcp-adapters` 库在底层使用官方的 MCP SDK，允许你通过实现 `httpx.Auth` 接口来提供自定义身份验证机制。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "auth": auth, # [!code highlight]
        }
    }
)
```

- [自定义身份验证实现示例](https://github.com/langchain-ai/langchain-mcp-adapters?tab=readme-ov-file#custom-http-auth-implementation)
- [内置 OAuth 流程](https://github.com/langchain-ai/langchain-mcp-adapters?tab=readme-ov-file#built-in-oauth-flow)

### stdio

客户端作为子进程启动服务器，并通过标准输入/输出进行通信。最适合本地工具和简单设置。

与 HTTP 传输不同，`stdio` 连接本质上是**有状态**的：子进程在客户端连接的整个生命周期内持续存在。但是，当在没有显式会话管理的情况下使用 `MultiServerMCPClient` 时，每次工具调用仍然会创建一个新会话。有关管理持久连接的信息，请参阅[有状态会话](#有状态会话)部分。

```python
client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["/path/to/math_server.py"],
        }
    }
)
```

## 有状态会话

默认情况下，`MultiServerMCPClient` 是无状态的：每次工具调用都会创建一个新的 MCP 会话，执行工具，然后清理。

如果你需要控制 MCP 会话的生命周期（例如，当使用在工具调用之间维护上下文的有状态服务器时），你可以使用 `client.session()` 创建一个持久的 `ClientSession`。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent

client = MultiServerMCPClient({...})

# 显式创建会话
async with client.session("server_name") as session:  # [!code highlight]
    # 将会话传递给工具、资源或提示加载函数
    tools = await load_mcp_tools(session)  # [!code highlight]
    agent = create_agent(
        "google_genai:gemini-3.1-pro-preview",
        tools
    )
```

## 核心功能

### 工具（Tools）

工具允许 MCP 服务器公开可由 LLM 调用的可执行函数，以执行操作——例如查询数据库、调用 API 或与外部系统交互。LangChain 将 MCP 工具转换为 LangChain 工具，使其可以直接在任何 LangChain 智能体或工作流中使用。

#### 加载工具

使用 `client.get_tools()` 从 MCP 服务器检索工具并将其传递给你的智能体：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({...})
tools = await client.get_tools()  # [!code highlight]
agent = create_agent("claude-sonnet-4-6", tools)
```

#### 结构化内容

MCP 工具可以在人类可读的文本响应旁边返回结构化内容。当工具需要返回机器可解析的数据（如 JSON）以及显示给模型的文本时，这非常有用。

当 MCP 工具返回 `structuredContent` 时，适配器会将其包装在 `MCPToolArtifact` 中，并将其作为工具的 artifact 返回。你可以使用 `ToolMessage` 上的 `artifact` 字段访问它。你也可以使用拦截器来自动处理或转换结构化内容。

从 artifact 提取结构化内容

在调用智能体后，你可以从响应中的工具消息访问结构化内容：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.messages import ToolMessage

client = MultiServerMCPClient({...})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)

result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "从服务器获取数据"}]}
)

# 从工具消息中提取结构化内容
for message in result["messages"]:
    if isinstance(message, ToolMessage) and message.artifact:
        structured_content = message.artifact["structured_content"]
```

通过拦截器附加结构化内容

如果你希望结构化内容在对话历史记录中可见（对模型可见），你可以使用拦截器自动将结构化内容附加到工具结果：

```python
import json

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import TextContent

async def append_structured_content(request: MCPToolCallRequest, handler):
    """将 artifact 中的结构化内容附加到工具消息"""
    result = await handler(request)
    if result.structuredContent:
        result.content += [
            TextContent(type="text", text=json.dumps(result.structuredContent)),
        ]
    return result

client = MultiServerMCPClient({...}, tool_interceptors=[append_structured_content])
```

#### 多模态工具内容

MCP 工具可以在其响应中返回多模态内容（图像、文本等）。当 MCP 服务器返回包含多个部分的内容（例如文本和图像）时，适配器会将它们转换为 LangChain 的标准内容块。你可以通过 `ToolMessage` 上的 `content_blocks` 属性访问标准化表示：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

client = MultiServerMCPClient({...})
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-6", tools)

result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "截取当前页面的屏幕截图"}]}
)

# 从工具消息中访问多模态内容
for message in result["messages"]:
    if message.type == "tool":
        # 原始内容（提供者原生格式）
        print(f"原始内容: {message.content}")

        # 标准化内容块  # [!code highlight]
        for block in message.content_blocks:  # [!code highlight]
            if block["type"] == "text":  # [!code highlight]
                print(f"文本: {block['text']}")  # [!code highlight]
            elif block["type"] == "image":  # [!code highlight]
                print(f"图片 URL: {block.get('url')}")  # [!code highlight]
                print(f"图片 base64: {block.get('base64', '')[:50]}...")  # [!code highlight]
```

这使你可以以与提供者无关的方式处理多模态工具响应，无论底层 MCP 服务器如何格式化其内容。

### 资源（Resources）

资源允许 MCP 服务器公开可由客户端读取的数据——例如文件、数据库记录或 API 响应。LangChain 将 MCP 资源转换为 Blob 对象，为处理文本和二进制内容提供统一接口。

#### 加载资源

使用 `client.get_resources()` 从 MCP 服务器加载资源：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({...})

# 从服务器加载所有资源
blobs = await client.get_resources("server_name")  # [!code highlight]

# 或通过 URI 加载特定资源
blobs = await client.get_resources("server_name", uris=["file:///path/to/file.txt"])  # [!code highlight]

for blob in blobs:
    print(f"URI: {blob.metadata['uri']}, MIME 类型: {blob.mimetype}")
    print(blob.as_string())  # 用于文本内容
```

你也可以直接使用 `load_mcp_resources` 与会话进行更多控制：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.resources import load_mcp_resources

client = MultiServerMCPClient({...})

async with client.session("server_name") as session:
    # 加载所有资源
    blobs = await load_mcp_resources(session)

    # 或通过 URI 加载特定资源
    blobs = await load_mcp_resources(session, uris=["file:///path/to/file.txt"])
```

### 提示（Prompts）

提示允许 MCP 服务器公开可复用的提示模板，可由客户端检索和使用。LangChain 将 MCP 提示转换为消息，使其易于集成到基于聊天的对话工作流中。

#### 加载提示

使用 `client.get_prompt()` 从 MCP 服务器加载提示：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({...})

# 通过名称加载提示
messages = await client.get_prompt("server_name", "summarize")  # [!code highlight]

# 使用参数加载提示
messages = await client.get_prompt(  # [!code highlight]
    "server_name",  # [!code highlight]
    "code_review",  # [!code highlight]
    arguments={"language": "python", "focus": "security"}  # [!code highlight]
)  # [!code highlight]

# 在工作流中使用消息
for message in messages:
    print(f"{message.type}: {message.content}")
```

你也可以直接使用 `load_mcp_prompt` 与会话进行更多控制：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt

client = MultiServerMCPClient({...})

async with client.session("server_name") as session:
    # 通过名称加载提示
    messages = await load_mcp_prompt(session, "summarize")

    # 使用参数加载提示
    messages = await load_mcp_prompt(
        session,
        "code_review",
        arguments={"language": "python", "focus": "security"}
    )
```

## 高级功能

### 工具拦截器

MCP 服务器作为单独的进程运行——它们无法访问 LangGraph 运行时信息，如 store、上下文或智能体状态。拦截器通过在 MCP 工具执行期间让你访问此运行时上下文来弥合这一差距。

拦截器还提供类似中间件的工具调用控制能力：你可以修改请求、实现重试、动态添加请求头，或完全短路执行。

| 章节 | 描述 |
| --- | --- |
| 访问运行时上下文 | 读取用户 ID、API 密钥、存储数据和智能体状态 |
| 状态更新和命令 | 使用 `Command` 更新智能体状态或控制图流程 |
| 编写拦截器 | 修改请求、组合拦截器和错误处理的模式 |

#### 访问运行时上下文

当 MCP 工具在 LangChain 智能体中使用时（通过 `create_agent`），拦截器可以访问 `ToolRuntime` 上下文。这提供了对工具调用 ID、状态、配置和存储的访问——支持访问用户数据、持久化信息和控制智能体行为的强大模式。

## 运行时上下文

访问在调用时传递的用户特定配置，如用户 ID、API 密钥或权限：

```python
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent

@dataclass
class Context:
    user_id: str
    api_key: str

async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """将用户凭据注入 MCP 工具调用"""
    runtime = request.runtime
    user_id = runtime.context.user_id  # [!code highlight]
    api_key = runtime.context.api_key  # [!code highlight]

    # 将用户上下文添加到工具参数
    modified_request = request.override(
        args={**request.args, "user_id": user_id}
    )
    return await handler(modified_request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[inject_user_context],
)
tools = await client.get_tools()
agent = create_agent("gpt-5.4", tools, context_schema=Context)

# 使用用户上下文调用
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "搜索我的订单"}]},
    context={"user_id": "user_123", "api_key": "sk-..."}
)
```

## 存储（Store）

访问长期记忆以检索用户偏好或在对话之间持久化数据：

```python
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

async def personalize_search(
    request: MCPToolCallRequest,
    handler,
):
    """使用存储的偏好个性化 MCP 工具调用"""
    runtime = request.runtime
    user_id = runtime.context.user_id
    store = runtime.store  # [!code highlight]

    # 从存储中读取用户偏好
    prefs = store.get(("preferences",), user_id)  # [!code highlight]

    if prefs and request.name == "search":
        # 应用用户的首选语言和结果限制
        modified_args = {
            **request.args,
            "language": prefs.value.get("language", "en"),
            "limit": prefs.value.get("result_limit", 10),
        }
        request = request.override(args=modified_args)

    return await handler(request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[personalize_search],
)
tools = await client.get_tools()
agent = create_agent(
    "gpt-5.4",
    tools,
    context_schema=Context,
    store=InMemoryStore()
)
```

## 状态（State）

访问对话状态以基于当前会话做出决策：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage

async def require_authentication(
    request: MCPToolCallRequest,
    handler,
):
    """如果用户未通过身份验证，则阻止敏感的 MCP 工具"""
    runtime = request.runtime
    state = runtime.state  # [!code highlight]
    is_authenticated = state.get("authenticated", False)  # [!code highlight]

    sensitive_tools = ["delete_file", "update_settings", "export_data"]

    if request.name in sensitive_tools and not is_authenticated:
        # 返回错误而不是调用工具
        return ToolMessage(
            content="需要身份验证。请先登录。",
            tool_call_id=runtime.tool_call_id,
        )

    return await handler(request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[require_authentication],
)
```

## 工具调用 ID

访问工具调用 ID 以返回正确格式的响应或跟踪工具执行：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage

async def rate_limit_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """对昂贵的 MCP 工具调用进行速率限制"""
    runtime = request.runtime
    tool_call_id = runtime.tool_call_id  # [!code highlight]

    # 检查速率限制（简化示例）
    if is_rate_limited(request.name):
        return ToolMessage(
            content="超出速率限制。请稍后再试。",
            tool_call_id=tool_call_id,  # [!code highlight]
        )

    result = await handler(request)

    # 记录成功的工具调用
    log_tool_execution(tool_call_id, request.name, success=True)

    return result

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[rate_limit_interceptor],
)
```

有关更多上下文工程模式，请参阅[上下文工程](https://langchain-ai.github.io/langgraph/concepts/context/)和[工具](https://python.langchain.com/core_docs/concepts/tools/)。

#### 状态更新和命令

拦截器可以返回 `Command` 对象来更新智能体状态或控制图执行流程。这对于跟踪任务进度、在智能体之间切换或提前结束执行很有用。

```python
from langchain.agents import AgentState, create_agent
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage
from langgraph.types import Command

async def handle_task_completion(
    request: MCPToolCallRequest,
    handler,
):
    """标记任务完成并移交给摘要智能体"""
    result = await handler(request)

    if request.name == "submit_order":
        return Command(
            update={
                "messages": [result] if isinstance(result, ToolMessage) else [],
                "task_status": "completed",  # [!code highlight]
            },
            goto="summary_agent",  # [!code highlight]
        )

    return result
```

使用 `goto="__end__"` 提前结束执行：

```python
async def end_on_success(
    request: MCPToolCallRequest,
    handler,
):
    """当任务被标记为完成时结束智能体运行"""
    result = await handler(request)

    if request.name == "mark_complete":
        return Command(
            update={"messages": [result], "status": "done"},
            goto="__end__",  # [!code highlight]
        )

    return result
```

#### 自定义拦截器

拦截器是包裹工具执行的异步函数，支持请求/响应修改、重试逻辑和其他横切关注点。它们遵循"洋葱"模式，列表中的第一个拦截器是最外层。

基本模式

拦截器是接收请求和处理程序的异步函数。你可以在调用处理程序之前修改请求，之后修改响应，或完全跳过处理程序。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

async def logging_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """在工具调用执行前后记录日志"""
    print(f"调用工具: {request.name}，参数: {request.args}")
    result = await handler(request)
    print(f"工具 {request.name} 返回: {result}")
    return result

client = MultiServerMCPClient(
    {"math": {"transport": "stdio", "command": "python", "args": ["/path/to/server.py"]}},
    tool_interceptors=[logging_interceptor],  # [!code highlight]
)
```

修改请求

使用 `request.override()` 创建修改后的请求。这遵循不可变模式，保持原始请求不变。

```python
async def double_args_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """在执行前将所有数字参数翻倍"""
    modified_args = {k: v * 2 for k, v in request.args.items()}
    modified_request = request.override(args=modified_args)  # [!code highlight]
    return await handler(modified_request)

# 原始调用: add(a=2, b=3) 变为 add(a=4, b=6)
```

在运行时修改请求头

拦截器可以根据请求上下文动态修改 HTTP 请求头：

```python
async def auth_header_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """根据被调用的工具添加身份验证请求头"""
    token = get_token_for_tool(request.name)
    modified_request = request.override(
        headers={"Authorization": f"Bearer {token}"}  # [!code highlight]
    )
    return await handler(modified_request)
```

组合拦截器

多个拦截器按"洋葱"顺序组合——列表中的第一个拦截器是最外层：

```python
async def outer_interceptor(request, handler):
    print("outer: before")
    result = await handler(request)
    print("outer: after")
    return result

async def inner_interceptor(request, handler):
    print("inner: before")
    result = await handler(request)
    print("inner: after")
    return result

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[outer_interceptor, inner_interceptor],  # [!code highlight]
)

# 执行顺序:
# outer: before -> inner: before -> 工具执行 -> inner: after -> outer: after
```

错误处理

使用拦截器捕获工具执行错误并实现重试逻辑：

```python
import asyncio

async def retry_interceptor(
    request: MCPToolCallRequest,
    handler,
    max_retries: int = 3,
    delay: float = 1.0,
):
    """使用指数退避重试失败的工具调用"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await handler(request)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)  # 指数退避
                print(f"工具 {request.name} 失败（第 {attempt + 1} 次尝试），{wait_time}秒后重试...")
                await asyncio.sleep(wait_time)
    raise last_error

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[retry_interceptor],  # [!code highlight]
)
```

你还可以捕获特定错误类型并返回回退值：

```python
async def fallback_interceptor(
    request: MCPToolCallRequest,
    handler,
):
    """如果工具执行失败则返回回退值"""
    try:
        return await handler(request)
    except TimeoutError:
        return f"工具 {request.name} 超时。请稍后再试。"
    except ConnectionError:
        return f"无法连接到 {request.name} 服务。使用缓存数据。"
```

### 进度通知

订阅长时间运行的工具执行的进度更新：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext

async def on_progress(
    progress: float,
    total: float | None,
    message: str | None,
    context: CallbackContext,
):
    """处理来自 MCP 服务器的进度更新"""
    percent = (progress / total * 100) if total else progress
    tool_info = f" ({context.tool_name})" if context.tool_name else ""
    print(f"[{context.server_name}{tool_info}] 进度: {percent:.1f}% - {message}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_progress=on_progress),  # [!code highlight]
)
```

`CallbackContext` 提供：

- `server_name`: MCP 服务器名称
- `tool_name`: 正在执行的工具名称（在工具调用期间可用）

### 日志记录

MCP 协议支持来自服务器的日志通知。使用 `Callbacks` 类订阅这些事件。

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from mcp.types import LoggingMessageNotificationParams

async def on_logging_message(
    params: LoggingMessageNotificationParams,
    context: CallbackContext,
):
    """处理来自 MCP 服务器的日志消息"""
    print(f"[{context.server_name}] {params.level}: {params.data}")

client = MultiServerMCPClient(
    {...},
    callbacks=Callbacks(on_logging_message=on_logging_message),  # [!code highlight]
)
```

### 引导（Elicitation）

引导允许 MCP 服务器在工具执行期间请求用户的额外输入。不需要预先提供所有输入，服务器可以根据需要交互式地请求信息。

#### 服务器设置

定义一个使用 `ctx.elicit()` 通过模式请求用户输入的工具：

```python
from pydantic import BaseModel
from mcp.server.fastmcp import Context, FastMCP

server = FastMCP("Profile")

class UserDetails(BaseModel):
    email: str
    age: int

@server.tool()
async def create_profile(name: str, ctx: Context) -> str:
    """创建用户资料，通过引导请求详细信息"""
    result = await ctx.elicit(  # [!code highlight]
        message=f"请提供 {name} 的资料详细信息：",  # [!code highlight]
        schema=UserDetails,  # [!code highlight]
    )  # [!code highlight]
    if result.action == "accept" and result.data:
        return f"已为 {name} 创建资料: email={result.data.email}, age={result.data.age}"
    if result.action == "decline":
        return f"用户已拒绝。已为 {name} 创建最小化资料。"
    return "资料创建已取消。"

if __name__ == "__main__":
    server.run(transport="http")
```

#### 客户端设置

通过向 `MultiServerMCPClient` 提供回调来处理引导请求：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext
from mcp.shared.context import RequestContext
from mcp.types import ElicitRequestParams, ElicitResult

async def on_elicitation(
    mcp_context: RequestContext,
    params: ElicitRequestParams,
    context: CallbackContext,
) -> ElicitResult:
    """处理来自 MCP 服务器的引导请求"""
    # 在实际应用中，你应该根据 params.message 和 params.requestedSchema
    # 提示用户输入
    return ElicitResult(  # [!code highlight]
        action="accept",  # [!code highlight]
        content={"email": "user@example.com", "age": 25},  # [!code highlight]
    )  # [!code highlight]

client = MultiServerMCPClient(
    {
        "profile": {
            "url": "http://localhost:8000/mcp",
            "transport": "http",
        }
    },
    callbacks=Callbacks(on_elicitation=on_elicitation),  # [!code highlight]
)
```

#### 响应操作

引导回调可以返回三种操作之一：

| 操作 | 描述 |
| --- | --- |
| `accept` | 用户提供了有效的输入。在 `content` 字段中包含数据。 |
| `decline` | 用户选择不提供请求的信息。 |
| `cancel` | 用户完全取消了操作。 |

```python
# 接受并附带数据
ElicitResult(action="accept", content={"email": "user@example.com", "age": 25})

# 拒绝（用户不想提供信息）
ElicitResult(action="decline")

# 取消（中止操作）
ElicitResult(action="cancel")
```

## 额外资源

- [MCP 文档](https://modelcontextprotocol.io/introduction)
- [MCP 传输文档](https://modelcontextprotocol.io/specification/draft/basic/transports/)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
