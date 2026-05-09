# LangChain 结构化输出（Structured Output）

> 来源：https://docs.langchain.com/oss/python/langchain/structured-output

---

## 概述

结构化输出让 Agent 以特定、可预测的格式返回数据。无需解析自然语言响应，直接获取 JSON 对象、Pydantic 模型或 dataclass。

结构化响应存储在 Agent 状态的 `'structured_response'` 键中。

---

## 响应格式策略

```python
agent = create_agent(
    model="gpt-5.4",
    response_format=...,  # 控制结构化输出
)
```

| 策略 | 说明 |
|------|------|
| `ToolStrategy[T]` | 通过工具调用实现结构化输出，适用于所有支持工具调用的模型 |
| `ProviderStrategy[T]` | 使用提供商原生结构化输出（更可靠） |
| `type[T]` | 直接传入 Schema 类型，自动选择最佳策略 |

> 💡 直接传入 Schema 时，LangChain 自动选择：支持原生结构化输出的模型用 `ProviderStrategy`，否则用 `ToolStrategy`。

---

## ProviderStrategy（提供商策略）

适用于 OpenAI、Anthropic、Gemini、xAI 等支持原生结构化输出的提供商：

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent

class ContactInfo(BaseModel):
    """Contact information for a person."""
    name: str = Field(description="The name of the person")
    email: str = Field(description="The email address of the person")
    phone: str = Field(description="The phone number of the person")

agent = create_agent(
    model="gpt-5.4",
    response_format=ContactInfo,  # 自动选择 ProviderStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

result["structured_response"]
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```

### 支持的 Schema 类型

| Schema 类型 | 返回类型 |
|-------------|----------|
| Pydantic `BaseModel` | 验证后的 Pydantic 实例 |
| Python `dataclass` | `dict` |
| `TypedDict` | `dict` |
| JSON Schema `dict` | `dict` |

### 启用严格模式

```python
from langchain.agents.structured_output import ProviderStrategy

agent = create_agent(
    model="gpt-5.4",
    response_format=ProviderStrategy(ContactInfo, strict=True),  # 严格模式
)
```

---

## ToolStrategy（工具调用策略）

适用于不支持原生结构化输出的模型，通过模拟工具调用实现：

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
    """Analysis of a product review."""
    rating: int | None = Field(description="The rating (1-5)", ge=1, le=5)
    sentiment: Literal["positive", "negative"] = Field(description="The sentiment")
    key_points: list[str] = Field(description="Key points, 1-3 words each")

agent = create_agent(
    model="gpt-5.4",
    tools=tools,
    response_format=ToolStrategy(ProductReview),
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze: 'Great product: 5/5. Fast shipping, but expensive'"}]
})
result["structured_response"]
# ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
```

### 自定义工具消息内容

```python
agent = create_agent(
    model="gpt-5.4",
    tools=[],
    response_format=ToolStrategy(
        schema=MeetingAction,
        tool_message_content="Action item captured and added to meeting notes!"
    ),
)
```

### Union 类型 — 多 Schema 选择

```python
from typing import Union

class ProductReview(BaseModel): ...
class CustomerComplaint(BaseModel): ...

agent = create_agent(
    model="gpt-5.4",
    response_format=ToolStrategy(Union[ProductReview, CustomerComplaint]),
)
```

---

## 错误处理

### 自动重试

当模型生成不合规的结构化输出时，Agent 自动提供错误反馈并提示重试：

**多个结构化输出错误：**

```
AI 调用了 ContactInfo 和 EventDetails（两个！）
→ ToolMessage: "Error: Model incorrectly returned multiple structured responses..."
→ AI 重试，只返回 ContactInfo ✓
```

**Schema 验证错误：**

```
AI 返回 rating=10（超出 1-5 范围）
→ ToolMessage: "Error: Input should be less than or equal to 5..."
→ AI 重试，返回 rating=5 ✓
```

### 自定义错误处理策略

```python
# 1. 自定义错误消息
ToolStrategy(schema=ProductRating, handle_errors="请提供 1-5 之间的有效评分")

# 2. 仅处理特定异常
ToolStrategy(schema=ProductRating, handle_errors=ValueError)

# 3. 处理多种异常
ToolStrategy(schema=ProductRating, handle_errors=(ValueError, TypeError))

# 4. 自定义错误处理函数
from langchain.agents.structured_output import StructuredOutputValidationError, MultipleStructuredOutputsError

def custom_error_handler(error: Exception) -> str:
    if isinstance(error, StructuredOutputValidationError):
        return "格式有问题，请重试。"
    elif isinstance(error, MultipleStructuredOutputsError):
        return "返回了多个结构化输出，请选择最相关的一个。"
    return f"Error: {str(error)}"

ToolStrategy(schema=ProductRating, handle_errors=custom_error_handler)

# 5. 禁用错误处理（所有异常直接抛出）
ToolStrategy(schema=ProductRating, handle_errors=False)
```

---

## 快速参考

```python
# 最简用法 — 直接传 Schema
agent = create_agent(model="gpt-5.4", response_format=ContactInfo)

# 显式指定策略
agent = create_agent(model="gpt-5.4", response_format=ProviderStrategy(ContactInfo))
agent = create_agent(model="gpt-5.4", response_format=ToolStrategy(ContactInfo))

# 带工具
agent = create_agent(model="gpt-5.4", tools=[...], response_format=ContactInfo)

# 访问结果
result = agent.invoke({"messages": [...]})
result["structured_response"]  # 结构化数据
```
