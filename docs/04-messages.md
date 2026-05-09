# LangChain Messages（消息）

> 来源：https://docs.langchain.com/oss/python/langchain/messages

---

## 概述

消息是 LangChain 中模型的**基本上下文单元**，代表模型的输入和输出，承载对话状态所需的内容和元数据。

每条消息包含：
- **Role（角色）** — 标识消息类型（如 `system`、`user`）
- **Content（内容）** — 实际内容（文本、图像、音频、文档等）
- **Metadata（元数据）** — 可选字段（响应信息、消息 ID、Token 使用量等）

LangChain 提供跨所有模型提供商的标准消息类型，确保行为一致。

---

## 基本用法

```python
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage

model = init_chat_model("gpt-5-nano")

system_msg = SystemMessage("You are a helpful assistant.")
human_msg = HumanMessage("Hello, how are you?")

messages = [system_msg, human_msg]
response = model.invoke(messages)  # 返回 AIMessage
```

### 三种传参方式

#### 1. 文本提示词（字符串）

```python
response = model.invoke("Write a haiku about spring")
```

适用：单次独立请求、无需对话历史。

#### 2. 消息对象列表

```python
from langchain.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage("You are a poetry expert"),
    HumanMessage("Write a haiku about spring"),
    AIMessage("Cherry blossoms bloom..."),
]
response = model.invoke(messages)
```

适用：多轮对话、多模态内容、包含系统指令。

#### 3. 字典格式（OpenAI 兼容）

```python
messages = [
    {"role": "system", "content": "You are a poetry expert"},
    {"role": "user", "content": "Write a haiku about spring"},
    {"role": "assistant", "content": "Cherry blossoms bloom..."},
]
response = model.invoke(messages)
```

---

## 消息类型

### SystemMessage（系统消息）

设定模型的行为和上下文：

```python
system_msg = SystemMessage("""
You are a senior Python developer with expertise in web frameworks.
Always provide code examples and explain your reasoning.
Be concise but thorough in your explanations.
""")

messages = [system_msg, HumanMessage("How do I create a REST API?")]
response = model.invoke(messages)
```

### HumanMessage（用户消息）

代表用户输入，可包含文本、图像、音频、文件等：

```python
# 纯文本
response = model.invoke(HumanMessage("What is machine learning?"))

# 简写：字符串 = 单条 HumanMessage
response = model.invoke("What is machine learning?")

# 带元数据
human_msg = HumanMessage(
    content="Hello!",
    name="alice",       # 可选：标识不同用户
    id="msg_123",       # 可选：追踪用的唯一标识符
)
```

### AIMessage（AI 消息）

代表模型输出，包含多模态数据、工具调用和元数据：

```python
response = model.invoke("Explain AI")
print(type(response))  # <class 'langchain.messages.AIMessage'>
```

可手动创建 AIMessage 插入对话历史：

```python
ai_msg = AIMessage("I'd be happy to help you with that question!")

messages = [
    SystemMessage("You are a helpful assistant"),
    HumanMessage("Can you help me?"),
    ai_msg,  # 插入模拟的模型回复
    HumanMessage("Great! What's 2+2?")
]
response = model.invoke(messages)
```

#### AIMessage 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 文本内容 |
| `content` | `str \| list` | 原始内容 |
| `content_blocks` | `list` | 标准化内容块 |
| `tool_calls` | `list` | 工具调用列表（无调用时为空） |
| `id` | `str` | 唯一标识符 |
| `usage_metadata` | `dict` | Token 使用量 |
| `response_metadata` | `dict` | 响应元数据 |

#### 工具调用

```python
model_with_tools = model.bind_tools([get_weather])
response = model_with_tools.invoke("What's the weather in Paris?")

for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}")    # 工具名
    print(f"Args: {tool_call['args']}")    # 参数
    print(f"ID: {tool_call['id']}")        # 调用 ID
```

#### Token 使用量

```python
response = model.invoke("Hello!")
response.usage_metadata
# {
#   'input_tokens': 8,
#   'output_tokens': 304,
#   'total_tokens': 312,
#   'input_token_details': {'audio': 0, 'cache_read': 0},
#   'output_token_details': {'audio': 0, 'reasoning': 256},
# }
```

#### 流式输出中的消息块

```python
chunks = []
full_message = None
for chunk in model.stream("Hi"):
    chunks.append(chunk)
    print(chunk.text)
    full_message = chunk if full_message is None else full_message + chunk
```

### ToolMessage（工具消息）

传递单个工具执行结果回模型：

```python
from langchain.messages import AIMessage, ToolMessage

# 模型发出工具调用
ai_message = AIMessage(
    content=[],
    tool_calls=[{
        "name": "get_weather",
        "args": {"location": "San Francisco"},
        "id": "call_123",
    }]
)

# 执行工具并创建结果消息
tool_message = ToolMessage(
    content="Sunny, 72°F",
    tool_call_id="call_123",  # 必须匹配工具调用 ID
)

# 继续对话
messages = [
    HumanMessage("What's the weather in San Francisco?"),
    ai_message,
    tool_message,
]
response = model.invoke(messages)
```

#### ToolMessage 属性

| 属性 | 说明 |
|------|------|
| `content` | 工具调用的字符串化输出 |
| `tool_call_id` | 对应的工具调用 ID |
| `name` | 被调用的工具名 |
| `artifact` | 不发送给模型但可编程访问的附加数据 |

#### artifact 示例

```python
tool_message = ToolMessage(
    content="It was the best of times, it was the worst of times.",  # 发送给模型
    tool_call_id="call_123",
    name="search_books",
    artifact={"document_id": "doc_123", "page": 0},  # 下游可用，但不进入模型上下文
)
```

---

## 消息内容

消息的 `content` 属性支持三种格式：

```python
# 1. 字符串
human_message = HumanMessage("Hello, how are you?")

# 2. 提供商原生格式（如 OpenAI）
human_message = HumanMessage(content=[
    {"type": "text", "text": "Hello, how are you?"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
])

# 3. LangChain 标准内容块
human_message = HumanMessage(content_blocks=[
    {"type": "text", "text": "Hello, how are you?"},
    {"type": "image", "url": "https://example.com/image.jpg"},
])
```

### 标准内容块

`content_blocks` 属性将 `content` 惰性解析为标准化表示：

```python
# Anthropic 的 thinking 块 → 统一为 reasoning 块
message = AIMessage(
    content=[
        {"type": "thinking", "thinking": "...", "signature": "WaUjzkyp..."},
        {"type": "text", "text": "..."},
    ],
    response_metadata={"model_provider": "anthropic"},
)
message.content_blocks
# [{'type': 'reasoning', 'reasoning': '...', 'extras': {'signature': '...'}},
#  {'type': 'text', 'text': '...'}]
```

启用标准内容块序列化（设置 `LC_OUTPUT_VERSION=v1` 或 `output_version="v1"`）：

```python
model = init_chat_model("gpt-5-nano", output_version="v1")
```

---

## 多模态内容

### 图像

```python
# 从 URL
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这张图片的内容。"},
        {"type": "image", "url": "https://example.com/path/to/image.jpg"},
    ]
}

# 从 base64
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这张图片的内容。"},
        {"type": "image", "base64": "...", "mime_type": "image/jpeg"},
    ]
}

# 从 File ID
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这张图片的内容。"},
        {"type": "image", "file_id": "file-abc123"},
    ]
}
```

### 文件（PDF 等）

```python
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这个文档的内容。"},
        {"type": "file", "url": "https://example.com/path/to/document.pdf"},
    ]
}
```

### 音频

```python
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这段音频的内容。"},
        {"type": "audio", "base64": "...", "mime_type": "audio/wav"},
    ]
}
```

### 视频

```python
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这段视频的内容。"},
        {"type": "video", "base64": "...", "mime_type": "video/mp4"},
    ]
}
```

> 🐞 并非所有模型都支持所有文件类型，请查看提供商文档了解支持的格式和大小限制。

---

## 内容块参考

### 核心块

| 块类型 | type 值 | 用途 | 关键字段 |
|--------|---------|------|----------|
| `TextContentBlock` | `"text"` | 标准文本输出 | `text`, `annotations` |
| `ReasoningContentBlock` | `"reasoning"` | 模型推理步骤 | `reasoning`, `extras` |

### 多模态块

| 块类型 | type 值 | 关键字段 |
|--------|---------|----------|
| `ImageContentBlock` | `"image"` | `url`, `base64`, `file_id`, `mime_type` |
| `AudioContentBlock` | `"audio"` | `url`, `base64`, `file_id`, `mime_type` |
| `VideoContentBlock` | `"video"` | `url`, `base64`, `file_id`, `mime_type` |
| `FileContentBlock` | `"file"` | `url`, `base64`, `file_id`, `mime_type` |
| `PlainTextContentBlock` | `"text-plain"` | `text`, `mime_type` |

### 工具调用块

| 块类型 | type 值 | 用途 | 关键字段 |
|--------|---------|------|----------|
| `ToolCall` | `"tool_call"` | 函数调用 | `name`, `args`, `id` |
| `ToolCallChunk` | `"tool_call_chunk"` | 流式工具调用片段 | `name`, `args`, `id`, `index` |
| `InvalidToolCall` | `"invalid_tool_call"` | 格式错误的调用 | `name`, `args`, `error` |

### 服务端工具块

| 块类型 | type 值 | 用途 |
|--------|---------|------|
| `ServerToolCall` | `"server_tool_call"` | 服务端执行的工具调用 |
| `ServerToolCallChunk` | `"server_tool_call_chunk"` | 流式服务端工具调用片段 |
| `ServerToolResult` | `"server_tool_result"` | 服务端工具执行结果 |

### 提供商特定块

| 块类型 | type 值 | 用途 |
|--------|---------|------|
| `NonStandardContentBlock` | `"non_standard"` | 提供商特定的逃生舱 |
