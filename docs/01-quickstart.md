# LangChain 快速开始

> 来源：https://docs.langchain.com/oss/python/langchain/quickstart
>
> 目标：几分钟内构建你的第一个 AI Agent！

---

## 安装依赖

```bash
# 方式一：使用 uv（推荐）
uv init
uv add langchain deepagents
uv sync

# 方式二：使用 pip
pip install -U langchain deepagents

# 方式三：使用 venv
python3 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -U langchain deepagents
```

## 配置 API Key

根据你选择的模型提供商，设置对应的 API Key：

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# Google Gemini
export GOOGLE_API_KEY="your-api-key"

# Claude (Anthropic)
export ANTHROPIC_API_KEY="your-api-key"

# OpenRouter
export OPENROUTER_API_KEY="your-api-key"

# Ollama（本地）
export OLLAMA_API_KEY="your-api-key"

# Azure OpenAI
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT_NAME="your-deployment"

# AWS Bedrock
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

---

## 构建基础 Agent

创建一个能回答问题并调用工具的简单 Agent：

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="openai:gpt-5.4",          # 模型标识符
    tools=[get_weather],               # 工具列表
    system_prompt="You are a helpful assistant",  # 系统提示词
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)
```

### 🔄 切换不同模型

只需修改 `model` 参数即可切换模型：

```python
# Google Gemini
agent = create_agent(model="google_genai:gemini-2.5-flash-lite", tools=[get_weather], ...)

# Claude
agent = create_agent(model="claude-sonnet-4-6", tools=[get_weather], ...)

# OpenRouter
agent = create_agent(model="openrouter:anthropic/claude-sonnet-4-6", tools=[get_weather], ...)

# Ollama（本地）
agent = create_agent(model="ollama:devstral-2", tools=[get_weather], ...)
```

---

## 构建真实世界的 Agent

下面构建一个能分析文本文档的研究 Agent，涉及以下概念：

1. **详细系统提示词** — 更好的 Agent 行为
2. **工具创建** — 集成外部数据
3. **模型配置** — 一致的响应
4. **对话记忆** — 类聊天的交互
5. **Deep Agent** — 内置高级功能
6. **测试 Agent**

### 步骤一：定义系统提示词

```python
SYSTEM_PROMPT = """You are a literary data assistant.

## Capabilities

- `fetch_text_from_url`: loads document text from a URL into the conversation.
Do not guess line counts or positions—ground them in tool results from the saved file."""
```

### 步骤二：创建工具

```python
import urllib.error
import urllib.request
from langchain.tools import tool

@tool
def fetch_text_from_url(url: str) -> str:
    """Fetch the document from a URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; quickstart-research/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"Fetch failed: {e}"
    text = raw.decode("utf-8", errors="replace")
    return text
```

> 💡 工具需要良好的文档：函数名、描述和参数名会成为模型提示词的一部分。

### 步骤三：配置模型

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "openai:gpt-5.4",
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
)
```

### 步骤四：添加记忆

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

> 🐞 `InMemorySaver` 仅用于开发。生产环境请使用持久化存储（如数据库）。

### 步骤五：创建并运行 Agent

LangChain 提供两种 Agent 框架：

| 类型 | 特点 | 适用场景 |
|------|------|----------|
| **LangChain Agent** | 精细控制，需要手动实现更多功能 | 需要高度定制 |
| **Deep Agent** | 内置规划、文件系统工具、子 Agent 等 | 最大能力、最少配置 |

```python
from langchain.agents import create_agent
from deepagents import create_deep_agent

# LangChain Agent — 精细控制
agent = create_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# Deep Agent — 内置高级功能
deep_agent = create_deep_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# 执行查询
content = """Project Gutenberg hosts a full plain-text copy of F. Scott Fitzgerald's The Great Gatsby.
URL: https://www.gutenberg.org/files/64317/64317-0.txt

Answer as much as you can:
1) How many lines contain the substring `Gatsby`?
2) The 1-based line number of the first line containing `Daisy`.
3) A two-sentence neutral synopsis.
"""

agent_result = agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-lc"}},
)
deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-da"}},
)
```

---

## 两种 Agent 的结果对比

| 对比项 | LangChain Agent | Deep Agent |
|--------|-----------------|------------|
| 精确计数 | ❌ 无法验证，返回 `null` | ✅ 258 行包含 `Gatsby` |
| 精确定位 | ❌ 无法验证，返回 `null` | ✅ 第 181 行首次出现 `Daisy` |
| 内容摘要 | ✅ 可生成 | ✅ 可生成 |
| 原因 | 缺少代码执行和文本处理工具 | 内置 `grep`、`read_file` 等工具 |

Deep Agent 的优势：
1. 使用 `write_todos` 工具规划研究任务
2. 通过 `fetch_text_from_url` 加载文件
3. 使用文件系统工具（`grep`、`read_file`）管理上下文
4. 按需生成子 Agent 处理复杂子任务

---

## 配置 LangSmith 追踪

```shell
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="your-key"
```

设置后，重新运行脚本即可在 LangSmith 上查看 Agent 每一步的执行详情。

---

## 完整示例代码

```python
import urllib.error
import urllib.request

from langchain.agents import create_agent
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

# 1. 系统提示词
SYSTEM_PROMPT = """You are a literary data assistant.

## Capabilities
- `fetch_text_from_url`: loads document text from a URL into the conversation.
Do not guess line counts or positions—ground them in tool results from the saved file."""

# 2. 工具定义
@tool
def fetch_text_from_url(url: str) -> str:
    """Fetch the document from a URL."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; quickstart-research/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"Fetch failed: {e}"
    text = raw.decode("utf-8", errors="replace")
    return text

# 3. 模型配置
model = init_chat_model(
    "openai:gpt-5.4",
    temperature=0.5,
    timeout=300,
    max_tokens=25000,
)

# 4. 记忆
checkpointer = InMemorySaver()

# 5. 创建 Agent
agent = create_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

deep_agent = create_deep_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# 6. 运行
content = """Project Gutenberg hosts a full plain-text copy of The Great Gatsby.
URL: https://www.gutenberg.org/files/64317/64317-0.txt

Answer as much as you can:
1) How many lines contain the substring `Gatsby`?
2) The 1-based line number of the first line containing `Daisy`.
3) A two-sentence neutral synopsis."""

agent_result = agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-lc"}},
)
deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-da"}},
)

print(agent_result["messages"][-1].content_blocks)
print("\n")
print(deep_agent_result["messages"][-1].content_blocks)
```
