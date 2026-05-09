# 护栏（Guardrails）

> 为你的智能体实现安全检查和内容过滤

护栏通过在智能体执行的关键节点验证和过滤内容，帮助你构建安全、合规的 AI 应用。它们可以检测敏感信息、执行内容策略、验证输出，并在不安全行为造成问题之前阻止它们。

常见用例包括：

- 防止个人身份信息（PII）泄露
- 检测并阻止提示注入攻击
- 阻止不当或有害内容
- 执行业务规则和合规要求
- 验证输出质量和准确性

你可以使用中间件来实现护栏，在战略点拦截执行——在智能体启动前、完成后，或在模型和工具调用前后。

护栏可以通过两种互补的方法实现：

## 确定性护栏

使用基于规则的逻辑，如正则表达式模式、关键词匹配或显式检查。快速、可预测且成本效益高，但可能会遗漏细微的违规行为。

## 基于模型的护栏

使用大语言模型（LLM）或分类器来评估内容的语义理解。能捕捉到规则遗漏的微妙问题，但速度较慢且成本更高。

LangChain 提供内置护栏（如 PII 检测、人机协同）和灵活的中间件系统，用于使用任一方法构建自定义护栏。

## 内置护栏

### PII 检测

LangChain 提供内置中间件，用于检测和处理对话中的个人身份信息（PII）。该中间件可以检测常见的 PII 类型，如电子邮件、信用卡、IP 地址等。

PII 检测中间件适用于以下场景：具有合规要求的医疗保健和金融应用、需要清理日志的客户服务智能体，以及一般处理敏感用户数据的任何应用。

PII 中间件支持多种处理检测到的 PII 的策略：

| 策略 | 描述 | 示例 |
| --- | --- | --- |
| `redact` | 替换为 `[REDACTED_{PII_TYPE}]` | `[REDACTED_EMAIL]` |
| `mask` | 部分模糊（例如，显示后4位） | `****-****-****-1234` |
| `hash` | 替换为确定性哈希值 | `a8f5f167...` |
| `block` | 检测到后抛出异常 | 抛出错误 |

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[customer_service_tool, email_tool],
    middleware=[
        # 在发送到模型前，对用户输入中的电子邮件进行脱敏处理
        PIIMiddleware(
            "email",
            strategy="redact",
            apply_to_input=True,
        ),
        # 对用户输入中的信用卡进行掩码处理
        PIIMiddleware(
            "credit_card",
            strategy="mask",
            apply_to_input=True,
        ),
        # 阻止 API 密钥 - 如果检测到则抛出错误
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
            apply_to_input=True,
        ),
    ],
)

# 当用户提供 PII 时，将根据策略进行处理
result = agent.invoke({
    "messages": [{"role": "user", "content": "我的邮箱是 john.doe@example.com，卡号是 5105-1051-0510-5100"}]
})

```

## 内置 PII 类型和配置

内置 PII 类型：

- `email` - 电子邮件地址
- `credit_card` - 信用卡号（经过 Luhn 验证）
- `ip` - IP 地址
- `mac_address` - MAC 地址
- `url` - URL

配置选项：

| 参数 | 描述 | 默认值 |
| --- | --- | --- |
| `pii_type` | 要检测的 PII 类型（内置或自定义） | 必填 |
| `strategy` | 处理检测到的 PII 的方式（`"block"`、`"redact"`、`"mask"`、`"hash"`） | `"redact"` |
| `detector` | 自定义检测器函数或正则表达式模式 | `None`（使用内置） |
| `apply_to_input` | 在模型调用前检查用户消息 | `True` |
| `apply_to_output` | 在模型调用后检查 AI 消息 | `False` |
| `apply_to_tool_results` | 在执行后检查工具结果消息 | `False` |

有关 PII 检测功能的完整详细信息，请参阅中间件文档。

### 人机协同（Human-in-the-loop）

LangChain 提供内置中间件，用于在执行敏感操作前要求人工批准。这是高风险决策最有效的护栏之一。

人机协同中间件适用于以下场景：金融交易和转账、删除或修改生产数据、向外部方发送通信，以及任何具有重大业务影响的操作。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, send_email_tool, delete_database_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                # 敏感操作需要批准
                "send_email": True,
                "delete_database": True,
                # 安全操作自动批准
                "search": False,
            }
        ),
    ],
    # 在终端间持久化状态
    checkpointer=InMemorySaver(),
)

# 人机协同需要线程 ID 来进行持久化
config = {"configurable": {"thread_id": "some_id"}}

# 智能体将在执行敏感工具前暂停并等待批准
result = agent.invoke(
    {"messages": [{"role": "user", "content": "给团队发送一封邮件"}]},
    config=config
)

result = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config  # 相同的线程 ID 以恢复暂停的对话
)

```

有关实现审批工作流的完整详细信息，请参阅人机协同文档。

## 自定义护栏

对于更复杂的护栏，你可以创建在智能体执行前后运行的自定义中间件。这使你可以完全控制验证逻辑、内容过滤和安全检查。

### 智能体前置护栏

使用"智能体前置"钩子，在每次调用的开始时验证请求。这适用于会话级别的检查，如身份验证、速率限制，或在任何处理开始前阻止不当请求。

```python
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime

class ContentFilterMiddleware(AgentMiddleware):
    """确定性护栏：阻止包含禁用关键词的请求。"""

    def __init__(self, banned_keywords: list[str]):
        super().__init__()
        self.banned_keywords = [kw.lower() for kw in banned_keywords]

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # 获取第一条用户消息
        if not state["messages"]:
            return None

        first_message = state["messages"][0]
        if first_message.type != "human":
            return None

        content = first_message.content.lower()

        # 检查禁用关键词
        for keyword in self.banned_keywords:
            if keyword in content:
                # 在任何处理开始前阻止执行
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "我无法处理包含不当内容的请求。请重新表述您的请求。"
                    }],
                    "jump_to": "end"
                }

        return None

# 使用自定义护栏
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, calculator_tool],
    middleware=[
        ContentFilterMiddleware(
            banned_keywords=["hack", "exploit", "malware"]
        ),
    ],
)

# 此请求将在任何处理前被阻止
result = agent.invoke({
    "messages": [{"role": "user", "content": "如何入侵数据库？"}]
})

```

```python
from typing import Any

from langchain.agents.middleware import before_agent, AgentState, hook_config
from langgraph.runtime import Runtime

banned_keywords = ["hack", "exploit", "malware"]

@before_agent(can_jump_to=["end"])
def content_filter(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """确定性护栏：阻止包含禁用关键词的请求。"""
    # 获取第一条用户消息
    if not state["messages"]:
        return None

    first_message = state["messages"][0]
    if first_message.type != "human":
        return None

    content = first_message.content.lower()

    # 检查禁用关键词
    for keyword in banned_keywords:
        if keyword in content:
            # 在任何处理开始前阻止执行
            return {
                "messages": [{
                    "role": "assistant",
                    "content": "我无法处理包含不当内容的请求。请重新表述您的请求。"
                }],
                "jump_to": "end"
            }

    return None

# 使用自定义护栏
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, calculator_tool],
    middleware=[content_filter],
)

# 此请求将在任何处理前被阻止
result = agent.invoke({
    "messages": [{"role": "user", "content": "如何入侵数据库？"}]
})

```

### 智能体后置护栏

使用"智能体后置"钩子，在返回给用户之前验证最终输出。这适用于基于模型的安全检查、质量验证，或对完整智能体响应进行最终合规扫描。

```python
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from typing import Any

class SafetyGuardrailMiddleware(AgentMiddleware):
    """基于模型的护栏：使用 LLM 评估响应安全性。"""

    def __init__(self):
        super().__init__()
        self.safety_model = init_chat_model("gpt-5.4-mini")

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # 获取最终的 AI 响应
        if not state["messages"]:
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        # 使用模型评估安全性
        safety_prompt = f"""评估此响应是否安全和适当。
        仅回复 'SAFE' 或 'UNSAFE'。

        响应：{last_message.content}"""

        result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])

        if "UNSAFE" in result.content:
            last_message.content = "我无法提供该响应。请重新表述您的请求。"

        return None

# 使用安全护栏
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, calculator_tool],
    middleware=[SafetyGuardrailMiddleware()],
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "如何制作爆炸物？"}]
})

```

```python
from langchain.agents.middleware import after_agent, AgentState, hook_config
from langgraph.runtime import Runtime
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from typing import Any

safety_model = init_chat_model("gpt-5.4-mini")

@after_agent(can_jump_to=["end"])
def safety_guardrail(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """基于模型的护栏：使用 LLM 评估响应安全性。"""
    # 获取最终的 AI 响应
    if not state["messages"]:
        return None

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return None

    # 使用模型评估安全性
    safety_prompt = f"""评估此响应是否安全和适当。
    仅回复 'SAFE' 或 'UNSAFE'。

    响应：{last_message.content}"""

    result = safety_model.invoke([{"role": "user", "content": safety_prompt}])

    if "UNSAFE" in result.content:
        last_message.content = "我无法提供该响应。请重新表述您的请求。"

    return None

# 使用安全护栏
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, calculator_tool],
    middleware=[safety_guardrail],
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "如何制作爆炸物？"}]
})

```

### 组合多个护栏

你可以通过将多个护栏添加到中间件数组中来堆叠它们。它们按顺序执行，允许你构建分层保护：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, send_email_tool],
    middleware=[
        # 第一层：确定性输入过滤器（智能体前置）
        ContentFilterMiddleware(banned_keywords=["hack", "exploit"]),

        # 第二层：PII 保护（模型前后）
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("email", strategy="redact", apply_to_output=True),

        # 第三层：敏感工具的人工批准
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),

        # 第四层：基于模型的安全检查（智能体后置）
        SafetyGuardrailMiddleware(),
    ],
)

```

## 其他资源

- 中间件文档 - 自定义中间件的完整指南
- 中间件 API 参考 - 自定义中间件的完整指南
- 人机协同 - 为敏感操作添加人工审查
- 测试智能体 - 测试安全机制的策略

---

通过 MCP 将这些文档连接到 Claude、VSCode 等，获取实时答案。

在 GitHub 上编辑此页面或提交问题。
