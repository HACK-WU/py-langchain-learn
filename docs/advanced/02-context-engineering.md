# 智能体中的上下文工程

## 概述

构建智能体（或任何 LLM 应用程序）的难点在于如何使其足够可靠。虽然原型可能工作正常，但它们经常在真实世界的使用场景中失败。

### 为什么智能体会失败？

当智能体失败时，通常是因为智能体内部的 LLM 调用采取了错误的操作 / 没有按我们的预期执行。LLM 失败的原因有以下两种之一：

1. 底层 LLM 能力不足
2. 没有向 LLM 传递"正确"的上下文

更多情况下——实际上是第二个原因导致智能体不可靠。

上下文工程是以正确的格式提供正确的信息和工具，使 LLM 能够完成任务。这是 AI 工程师的首要工作。缺乏"正确"的上下文是阻碍构建更可靠智能体的头号障碍，而 LangChain 的智能体抽象设计独特，旨在促进上下文工程。

刚接触上下文工程？先从概念性概述开始，了解不同类型的上下文以及何时使用它们。

### 智能体循环

典型的智能体循环包括两个主要步骤：

1. 模型调用 - 使用提示和可用工具调用 LLM，返回响应或执行工具的请求
2. 工具执行 - 执行 LLM 请求的工具，返回工具结果

此循环持续进行，直到 LLM 决定完成。

### 你可以控制什么

为了构建可靠的智能体，你需要控制智能体循环的每一步，以及步骤之间发生的事情。

| 上下文类型 | 你控制的 | 瞬态或持久 |
| --- | --- | --- |
| 模型上下文 | 进入模型调用的内容（指令、消息历史、工具、响应格式） | 瞬态 |
| 工具上下文 | 工具可以访问和产生的内容（对状态、存储、运行时上下文的读取/写入） | 持久 |
| 生命周期上下文 | 模型调用和工具调用之间发生的事情（摘要、护栏、日志等） | 持久 |

## 瞬态上下文

LLM 在单次调用中看到的内容。你可以修改消息、工具或提示，而无需更改状态中保存的内容。

## 持久上下文

跨轮次保存在状态中的内容。生命周期钩子和工具写入会永久修改它。

### 数据源

在整个过程中，你的智能体访问（读取/写入）不同的数据源：

| 数据源 | 也称为 | 范围 | 示例 |
| --- | --- | --- | --- |
| 运行时上下文 | 静态配置 | 对话范围 | 用户 ID、API 密钥、数据库连接、权限、环境设置 |
| 状态 | 短期记忆 | 对话范围 | 当前消息、上传的文件、认证状态、工具结果 |
| 存储 | 长期记忆 | 跨对话 | 用户偏好、提取的洞察、记忆、历史数据 |

### 工作原理

LangChain 中间件是使使用 LangChain 的开发人员能够实际进行上下文工程的核心机制。

中间件允许你 hook 到智能体生命周期的任何步骤：

- 更新上下文
- 跳转到智能体生命周期中的不同步骤

在本指南中，你将频繁看到中间件 API 的使用，作为实现上下文工程目标的手段。

## 模型上下文

控制每次模型调用的内容——指令、可用工具、使用哪个模型、输出格式。这些决策直接影响可靠性和成本。

## 系统提示

开发者向 LLM 提供的基础指令。

## 消息

发送给 LLM 的完整消息列表（对话历史）。

## 工具

智能体可用于执行操作的实用程序。

## 模型

要调用的实际模型（包括配置）。

## 响应格式

模型最终响应的模式规范。

所有这些类型的模型上下文都可以从状态（短期记忆）、存储（长期记忆）或运行时上下文（静态配置）中获取。

### 系统提示

系统提示设置 LLM 的行为和能力。不同的用户、上下文或对话阶段需要不同的指令。成功的智能体利用记忆、偏好和配置为对话的当前状态提供合适的指令。

## 状态

从状态访问消息数量或对话上下文：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dynamic_prompt
def state_aware_prompt(request: ModelRequest) -> str:
    # request.messages 是 request.state["messages"] 的快捷方式
    message_count = len(request.messages)

    base = "You are a helpful assistant."

    if message_count > 10:
        base += "\nThis is a long conversation - be extra concise."

    return base

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[state_aware_prompt]
)

```

## 存储

从长期记忆中访问用户偏好：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@dynamic_prompt
def store_aware_prompt(request: ModelRequest) -> str:
    user_id = request.runtime.context.user_id

    # 从存储中读取：获取用户偏好
    store = request.runtime.store
    user_prefs = store.get(("preferences",), user_id)

    base = "You are a helpful assistant."

    if user_prefs:
        style = user_prefs.value.get("communication_style", "balanced")
        base += f"\nUser prefers {style} responses."

    return base

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[store_aware_prompt],
    context_schema=Context,
    store=InMemoryStore()
)

```

## 运行时上下文

从运行时上下文访问用户 ID 或配置：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dataclass
class Context:
    user_role: str
    deployment_env: str

@dynamic_prompt
def context_aware_prompt(request: ModelRequest) -> str:
    # 从运行时上下文读取：用户角色和环境
    user_role = request.runtime.context.user_role
    env = request.runtime.context.deployment_env

    base = "You are a helpful assistant."

    if user_role == "admin":
        base += "\nYou have admin access. You can perform all operations."
    elif user_role == "viewer":
        base += "\nYou have read-only access. Guide users to read operations only."

    if env == "production":
        base += "\nBe extra careful with any data modifications."

    return base

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[context_aware_prompt],
    context_schema=Context
)

```

### 消息

消息构成发送给 LLM 的提示。管理消息内容至关重要，以确保 LLM 拥有做出良好响应的正确信息。

## 状态

当与当前查询相关时，从状态注入上传的文件上下文：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def inject_file_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """注入关于用户本次会话上传文件的上下文。"""
    # 从状态读取：获取上传文件的元数据
    uploaded_files = request.state.get("uploaded_files", [])

    if uploaded_files:
        # 构建关于可用文件的上下文
        file_descriptions = []
        for file in uploaded_files:
            file_descriptions.append(
                f"- {file['name']} ({file['type']}): {file['summary']}"
            )

        file_context = f"""Files you have access to in this conversation:
{chr(10).join(file_descriptions)}

Reference these files when answering questions."""

        # 在最近消息之前注入文件上下文
        messages = [
            *request.messages,
            {"role": "user", "content": file_context},
        ]
        request = request.override(messages=messages)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[inject_file_context]
)

```

## 存储

从存储注入用户的邮件写作风格以指导起草：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@wrap_model_call
def inject_writing_style(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """从存储中注入用户的邮件写作风格。"""
    user_id = request.runtime.context.user_id

    # 从存储读取：获取用户的写作风格示例
    store = request.runtime.store
    writing_style = store.get(("writing_style",), user_id)

    if writing_style:
        style = writing_style.value
        # 从存储的示例构建风格指南
        style_context = f"""Your writing style:
- Tone: {style.get('tone', 'professional')}
- Typical greeting: "{style.get('greeting', 'Hi')}"
- Typical sign-off: "{style.get('sign_off', 'Best')}"
- Example email you've written:
{style.get('example_email', '')}"""

        # 附加到末尾——模型更关注最后的消息
        messages = [
            *request.messages,
            {"role": "user", "content": style_context}
        ]
        request = request.override(messages=messages)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[inject_writing_style],
    context_schema=Context,
    store=InMemoryStore()
)

```

## 运行时上下文

基于用户管辖区从运行时上下文注入合规规则：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@dataclass
class Context:
    user_jurisdiction: str
    industry: str
    compliance_frameworks: list[str]

@wrap_model_call
def inject_compliance_rules(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """从运行时上下文注入合规约束。"""
    # 从运行时上下文读取：获取合规要求
    jurisdiction = request.runtime.context.user_jurisdiction
    industry = request.runtime.context.industry
    frameworks = request.runtime.context.compliance_frameworks

    # 构建合规约束
    rules = []
    if "GDPR" in frameworks:
        rules.append("- Must obtain explicit consent before processing personal data")
        rules.append("- Users have right to data deletion")
    if "HIPAA" in frameworks:
        rules.append("- Cannot share patient health information without authorization")
        rules.append("- Must use secure, encrypted communication")
    if industry == "finance":
        rules.append("- Cannot provide financial advice without proper disclaimers")

    if rules:
        compliance_context = f"""Compliance requirements for {jurisdiction}:
{chr(10).join(rules)}"""

        # 附加到末尾——模型更关注最后的消息
        messages = [
            *request.messages,
            {"role": "user", "content": compliance_context}
        ]
        request = request.override(messages=messages)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[inject_compliance_rules],
    context_schema=Context
)

```

瞬态与持久消息更新：

上面的示例使用 `wrap_model_call` 进行瞬态更新——修改单次调用发送给模型的消息，而不更改状态中保存的内容。

要进行持久更新（修改状态），你可以：

- 从模型调用层返回带有 `Command` 的 `ExtendedModelResponse` 来注入状态更新。
- 使用生命周期钩子如 `before_model`、`after_model` 或 `wrap_tool_call`（用于工具返回）来更新对话历史。有关更多详细信息，请参阅中间件文档。

有关更多信息，请参阅状态更新。

### 工具

工具让模型与数据库、API 和外部系统交互。如何定义和选择工具直接影响模型能否有效完成任务。

#### 定义工具

每个工具需要清晰的中文名、描述、参数名和参数描述。这些不仅仅是元数据——它们指导模型推理何时以及如何使用工具。

```python
from langchain.tools import tool

@tool(parse_docstring=True)
def search_orders(
    user_id: str,
    status: str,
    limit: int = 10
) -> str:
    """Search for user orders by status.

    Use this when the user asks about order history or wants to check
    order status. Always filter by the provided status.

    Args:
        user_id: Unique identifier for the user
        status: Order status: 'pending', 'shipped', or 'delivered'
        limit: Maximum number of results to return
    """
    # 实现代码
    pass

```

#### 选择工具

不是每个工具都适用于每种情况。工具太多可能使模型不堪重负（上下文过载）并增加错误；工具太少则限制能力。动态工具选择根据认证状态、用户权限、功能标志或对话阶段调整可用的工具集。

## 状态

仅在达到某些对话里程碑后才启用高级工具：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def state_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于对话状态过滤工具。"""
    # 从状态读取：检查用户是否已认证
    state = request.state
    is_authenticated = state.get("authenticated", False)
    message_count = len(state["messages"])

    # 仅在认证后启用敏感工具
    if not is_authenticated:
        tools = [t for t in request.tools if t.name.startswith("public_")]
        request = request.override(tools=tools)
    elif message_count < 5:
        # 对话早期限制工具
        tools = [t for t in request.tools if t.name != "advanced_search"]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[public_search, private_search, advanced_search],
    middleware=[state_based_tools]
)

```

## 存储

基于存储中的用户偏好或功能标志过滤工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@wrap_model_call
def store_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于存储偏好过滤工具。"""
    user_id = request.runtime.context.user_id

    # 从存储读取：获取用户启用的功能
    store = request.runtime.store
    feature_flags = store.get(("features",), user_id)

    if feature_flags:
        enabled_features = feature_flags.value.get("enabled_tools", [])
        # 仅包含为此用户启用的工具
        tools = [t for t in request.tools if t.name in enabled_features]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, analysis_tool, export_tool],
    middleware=[store_based_tools],
    context_schema=Context,
    store=InMemoryStore()
)

```

## 运行时上下文

基于运行时上下文中的用户权限过滤工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@dataclass
class Context:
    user_role: str

@wrap_model_call
def context_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于运行时上下文权限过滤工具。"""
    # 从运行时上下文读取：获取用户角色
    user_role = request.runtime.context.user_role

    if user_role == "admin":
        # 管理员获得所有工具
        pass
    elif user_role == "editor":
        # 编辑者不能删除
        tools = [t for t in request.tools if t.name != "delete_data"]
        request = request.override(tools=tools)
    else:
        # 查看者获得只读工具
        tools = [t for t in request.tools if t.name.startswith("read_")]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[read_data, write_data, delete_data],
    middleware=[context_based_tools],
    context_schema=Context
)

```

请参阅动态工具，了解如何过滤预注册工具以及在运行时注册工具（例如从 MCP 服务器）。

### 模型

不同的模型具有不同的优势、成本和上下文窗口。为手头的任务选择正确的模型，这可能在智能体运行期间发生变化。

## 状态

根据对话长度从状态使用不同模型：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable

# 在中间件外部初始化模型一次
large_model = init_chat_model("claude-sonnet-4-6")
standard_model = init_chat_model("gpt-5.4")
efficient_model = init_chat_model("gpt-5.4-mini")

@wrap_model_call
def state_based_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """根据状态对话长度选择模型。"""
    # request.messages 是 request.state["messages"] 的快捷方式
    message_count = len(request.messages)

    if message_count > 20:
        # 长对话——使用具有更大上下文窗口的模型
        model = large_model
    elif message_count > 10:
        # 中等长度对话
        model = standard_model
    else:
        # 短对话——使用高效的模型
        model = efficient_model

    request = request.override(model=model)

    return handler(request)

agent = create_agent(
    model="gpt-5.4-mini",
    tools=[...],
    middleware=[state_based_model]
)

```

## 存储

使用存储中用户偏好的模型：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

# 初始化可用模型一次
MODEL_MAP = {
    "gpt-5.4": init_chat_model("gpt-5.4"),
    "gpt-5.4-mini": init_chat_model("gpt-5.4-mini"),
    "claude-sonnet": init_chat_model("claude-sonnet-4-6"),
}

@wrap_model_call
def store_based_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于存储偏好选择模型。"""
    user_id = request.runtime.context.user_id

    # 从存储读取：获取用户首选模型
    store = request.runtime.store
    user_prefs = store.get(("preferences",), user_id)

    if user_prefs:
        preferred_model = user_prefs.value.get("preferred_model")
        if preferred_model and preferred_model in MODEL_MAP:
            request = request.override(model=MODEL_MAP[preferred_model])

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[store_based_model],
    context_schema=Context,
    store=InMemoryStore()
)

```

## 运行时上下文

基于成本限制或环境从运行时上下文选择模型：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable

@dataclass
class Context:
    cost_tier: str
    environment: str

# 在中间件外部初始化模型一次
premium_model = init_chat_model("claude-sonnet-4-6")
standard_model = init_chat_model("gpt-5.4")
budget_model = init_chat_model("gpt-5.4-mini")

@wrap_model_call
def context_based_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于运行时上下文选择模型。"""
    # 从运行时上下文读取：成本层和环境
    cost_tier = request.runtime.context.cost_tier
    environment = request.runtime.context.environment

    if environment == "production" and cost_tier == "premium":
        # 生产环境高级用户获得最佳模型
        model = premium_model
    elif cost_tier == "budget":
        # 预算层获得高效模型
        model = budget_model
    else:
        # 标准层
        model = standard_model

    request = request.override(model=model)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[context_based_model],
    context_schema=Context
)

```

有关更多示例，请参阅动态模型。

### 响应格式

结构化输出将非结构化文本转换为经过验证的、结构化的数据。当提取特定字段或将数据返回给下游系统时，自由格式文本是不够的。

工作原理：当你将模式作为响应格式提供时，模型的最终响应保证符合该模式。智能体运行模型/工具调用循环，直到模型完成调用工具，然后将最终响应强制转换为提供的格式。

#### 定义格式

模式定义指导模型。字段名、类型和描述精确指定输出应遵循的格式。

```python
from pydantic import BaseModel, Field

class CustomerSupportTicket(BaseModel):
    """Structured ticket information extracted from customer message."""

    category: str = Field(
        description="Issue category: 'billing', 'technical', 'account', or 'product'"
    )
    priority: str = Field(
        description="Urgency level: 'low', 'medium', 'high', or 'critical'"
    )
    summary: str = Field(
        description="One-sentence summary of the customer's issue"
    )
    customer_sentiment: str = Field(
        description="Customer's emotional tone: 'frustrated', 'neutral', or 'satisfied'"
    )

```

#### 选择格式

动态响应格式选择根据用户偏好、对话阶段或角色调整模式——早期返回简单格式，复杂度增加时返回详细格式。

## 状态

基于对话状态配置结构化输出：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from pydantic import BaseModel, Field
from typing import Callable

class SimpleResponse(BaseModel):
    """简单响应，用于对话早期。"""
    answer: str = Field(description="A brief answer")

class DetailedResponse(BaseModel):
    """详细响应，用于已建立的对话。"""
    answer: str = Field(description="A detailed answer")
    reasoning: str = Field(description="Explanation of reasoning")
    confidence: float = Field(description="Confidence score 0-1")

@wrap_model_call
def state_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """根据状态选择输出格式。"""
    # request.messages 是 request.state["messages"] 的快捷方式
    message_count = len(request.messages)

    if message_count < 3:
        # 对话早期——使用简单格式
        request = request.override(response_format=SimpleResponse)
    else:
        # 已建立的对话——使用详细格式
        request = request.override(response_format=DetailedResponse)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[state_based_output]
)

```

## 存储

基于存储中的用户偏好配置输出格式：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from pydantic import BaseModel, Field
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

class VerboseResponse(BaseModel):
    """带详细信息的详细响应。"""
    answer: str = Field(description="Detailed answer")
    sources: list[str] = Field(description="Sources used")

class ConciseResponse(BaseModel):
    """简洁响应。"""
    answer: str = Field(description="Brief answer")

@wrap_model_call
def store_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于存储偏好选择输出格式。"""
    user_id = request.runtime.context.user_id

    # 从存储读取：获取用户首选响应风格
    store = request.runtime.store
    user_prefs = store.get(("preferences",), user_id)

    if user_prefs:
        style = user_prefs.value.get("response_style", "concise")
        if style == "verbose":
            request = request.override(response_format=VerboseResponse)
        else:
            request = request.override(response_format=ConciseResponse)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[store_based_output],
    context_schema=Context,
    store=InMemoryStore()
)

```

## 运行时上下文

基于运行时上下文（如用户角色或环境）配置输出格式：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from pydantic import BaseModel, Field
from typing import Callable

@dataclass
class Context:
    user_role: str
    environment: str

class AdminResponse(BaseModel):
    """为管理员提供技术详细信息的响应。"""
    answer: str = Field(description="Answer")
    debug_info: dict = Field(description="Debug information")
    system_status: str = Field(description="System status")

class UserResponse(BaseModel):
    """普通用户的简单响应。"""
    answer: str = Field(description="Answer")

@wrap_model_call
def context_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """基于运行时上下文选择输出格式。"""
    # 从运行时上下文读取：用户角色和环境
    user_role = request.runtime.context.user_role
    environment = request.runtime.context.environment

    if user_role == "admin" and environment == "production":
        # 生产环境管理员获得详细输出
        request = request.override(response_format=AdminResponse)
    else:
        # 普通用户获得简单输出
        request = request.override(response_format=UserResponse)

    return handler(request)

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[context_based_output],
    context_schema=Context
)

```

## 工具上下文

工具的特殊之处在于它们同时读取和写入上下文。

在最基本的情况下，当工具执行时，它接收 LLM 的请求参数并返回工具消息。工具完成其工作并产生结果。

工具还可以获取模型所需的重要信息，使其能够执行和完成任务。

### 读取

大多数真实世界的工具需要的不仅仅是 LLM 的参数。它们需要用于数据库查询的用户 ID、外部服务的 API 密钥，或当前会话状态来做出决策。工具从状态、存储和运行时上下文读取以访问这些信息。

## 状态

从状态读取以检查当前会话信息：

```python
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent

@tool
def check_authentication(
    runtime: ToolRuntime
) -> str:
    """检查用户是否已认证。"""
    # 从状态读取：检查当前认证状态
    current_state = runtime.state
    is_authenticated = current_state.get("authenticated", False)

    if is_authenticated:
        return "User is authenticated"
    else:
        return "User is not authenticated"

agent = create_agent(
    model="gpt-5.4",
    tools=[check_authentication]
)

```

## 存储

从存储读取以访问持久化的用户偏好：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@tool
def get_preference(
    preference_key: str,
    runtime: ToolRuntime[Context]
) -> str:
    """从存储获取用户偏好。"""
    user_id = runtime.context.user_id

    # 从存储读取：获取现有偏好
    store = runtime.store
    existing_prefs = store.get(("preferences",), user_id)

    if existing_prefs:
        value = existing_prefs.value.get(preference_key)
        return f"{preference_key}: {value}" if value else f"No preference set for {preference_key}"
    else:
        return "No preferences found"

agent = create_agent(
    model="gpt-5.4",
    tools=[get_preference],
    context_schema=Context,
    store=InMemoryStore()
)

```

## 运行时上下文

从运行时上下文读取配置，如 API 密钥和用户 ID：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent

@dataclass
class Context:
    user_id: str
    api_key: str
    db_connection: str

@tool
def fetch_user_data(
    query: str,
    runtime: ToolRuntime[Context]
) -> str:
    """使用运行时上下文配置获取数据。"""
    # 从运行时上下文读取：获取 API 密钥和数据库连接
    user_id = runtime.context.user_id
    api_key = runtime.context.api_key
    db_connection = runtime.context.db_connection

    # 使用配置获取数据
    results = perform_database_query(db_connection, query, api_key)

    return f"Found {len(results)} results for user {user_id}"

agent = create_agent(
    model="gpt-5.4",
    tools=[fetch_user_data],
    context_schema=Context
)

# 使用运行时上下文调用
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Get my data"}]},
    context=Context(
        user_id="user_123",
        api_key="sk-...",
        db_connection="postgresql://..."
    )
)

```

### 写入

工具结果可以帮助智能体完成给定任务。工具可以直接将结果返回给模型，并更新智能体的记忆，使重要上下文对未来步骤可用。

## 状态

使用 Command 写入状态以跟踪会话特定信息：

```python
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.types import Command

@tool
def authenticate_user(
    password: str,
    runtime: ToolRuntime
) -> Command:
    """认证用户并更新状态。"""
    # 执行认证（简化）
    if password == "correct":
        # 写入状态：使用 Command 标记为已认证
        return Command(
            update={"authenticated": True},
        )
    else:
        return Command(update={"authenticated": False})

agent = create_agent(
    model="gpt-5.4",
    tools=[authenticate_user]
)

```

## 存储

写入存储以跨会话持久化数据：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@tool
def save_preference(
    preference_key: str,
    preference_value: str,
    runtime: ToolRuntime[Context]
) -> str:
    """将用户偏好保存到存储。"""
    user_id = runtime.context.user_id

    # 读取现有偏好
    store = runtime.store
    existing_prefs = store.get(("preferences",), user_id)

    # 合并新偏好
    prefs = existing_prefs.value if existing_prefs else {}
    prefs[preference_key] = preference_value

    # 写入存储：保存更新后的偏好
    store.put(("preferences",), user_id, prefs)

    return f"Saved preference: {preference_key} = {preference_value}"

agent = create_agent(
    model="gpt-5.4",
    tools=[save_preference],
    context_schema=Context,
    store=InMemoryStore()
)

```

有关在工具中访问状态、存储和运行时上下文的综合示例，请参阅工具。

## 生命周期上下文

控制核心智能体步骤之间发生的事情——拦截数据流以实现横切关注点，如摘要、护栏和日志。

如你在模型上下文和工具上下文中所见，中间件是使上下文工程实际可行的机制。中间件允许你 hook 到智能体生命周期的任何步骤，可以：

1. 更新上下文 - 修改状态和存储以持久化更改、更新对话历史或保存洞察
2. 跳转到生命周期中的位置 - 根据上下文移动到智能体周期中的不同步骤（例如，如果满足条件则跳过工具执行，使用修改后的上下文重复模型调用）

### 示例：摘要

最常见的生命周期模式之一是在对话历史过长时自动压缩。与模型上下文中显示的瞬态消息修剪不同，摘要持久更新状态——永久替换旧消息为摘要，并为所有未来轮次保存。

LangChain 为此提供内置中间件：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger={"tokens": 4000},
            keep={"messages": 20},
        ),
    ],
)

```

当对话超过令牌限制时，`SummarizationMiddleware` 自动：

1. 使用单独的 LLM 调用来摘要较早的消息
2. 在状态中将其替换为摘要消息（永久）
3. 保留最近消息的完整性以保持上下文

摘要后的对话历史会永久更新——未来的轮次将看到摘要而不是原始消息。

有关内置中间件的完整列表、可用钩子以及如何创建自定义中间件，请参阅中间件文档。

## 最佳实践

1. 从简单开始——从静态提示和工具开始，仅在需要时添加动态功能
2. 增量测试——一次添加一个上下文工程功能
3. 监控性能——跟踪模型调用、令牌使用情况和延迟
4. 使用内置中间件——利用 `SummarizationMiddleware`、`LLMToolSelectorMiddleware` 等
5. 记录你的上下文策略——明确传递了什么上下文以及原因
6. 理解瞬态与持久：模型上下文更改是瞬态的（单次调用），而生命周期上下文更改会持久化到状态

## 相关资源

- 上下文概念概述 - 了解上下文类型以及何时使用它们
- 中间件 - 完整的中间件指南
- 工具 - 工具创建和上下文访问
- 记忆 - 短期和长期记忆模式
- 智能体 - 核心智能体概念
