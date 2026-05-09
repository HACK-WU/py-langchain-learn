# LangChain 内置中间件

> 来源：https://docs.langchain.com/oss/python/langchain/middleware/built-in

---

## 概述

LangChain 和 Deep Agents 提供了一系列预构建的、生产就绪的中间件。

---

## 提供商无关中间件

| 中间件 | 说明 |
|--------|------|
| **Summarization** | 接近 Token 限制时自动摘要对话历史 |
| **Human-in-the-loop** | 暂停执行等待人工审批工具调用 |
| **Model call limit** | 限制模型调用次数防止过度成本 |
| **Tool call limit** | 控制工具执行次数 |
| **Model fallback** | 主模型失败时自动回退到备选模型 |
| **PII detection** | 检测和处理个人身份信息 |
| **To-do list** | 为 Agent 提供任务规划和跟踪能力 |
| **LLM tool selector** | 使用 LLM 智能选择相关工具 |
| **Tool retry** | 失败工具调用自动重试（指数退避） |
| **Model retry** | 失败模型调用自动重试（指数退避） |
| **LLM tool emulator** | 使用 LLM 模拟工具执行（测试用） |
| **Context editing** | 通过裁剪/清除工具输出来管理上下文 |
| **Shell tool** | 为 Agent 提供持久 Shell 会话 |
| **File search** | 提供文件系统 Glob/Grep 搜索工具 |
| **Filesystem** | 提供文件系统读写工具 |
| **Subagent** | 添加生成子 Agent 的能力 |

---

### Summarization（摘要）

接近 Token 限制时自动摘要对话历史，保留近期消息同时压缩旧上下文：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

# 单条件：Token 数 ≥ 4000 时触发
agent = create_agent(
    model="gpt-5.4",
    tools=[weather_tool, calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",       # 生成摘要的模型
            trigger=("tokens", 4000),    # 触发条件
            keep=("messages", 20),       # 保留最近 20 条消息
        ),
    ],
)

# 多条件：Token ≥ 3000 或 消息 ≥ 6 条时触发（OR 逻辑）
agent2 = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=[("tokens", 3000), ("messages", 6)],
            keep=("messages", 20),
        ),
    ],
)

# 使用比例
agent3 = create_agent(
    model="gpt-5.4",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("fraction", 0.8),   # 达到上下文窗口 80%
            keep=("fraction", 0.3),       # 保留 30%
        ),
    ],
)
```

**触发条件类型：**

| 类型 | 说明 | 示例 |
|------|------|------|
| `fraction` | 模型上下文大小的比例 | `("fraction", 0.8)` |
| `tokens` | 绝对 Token 数 | `("tokens", 4000)` |
| `messages` | 消息条数 | `("messages", 6)` |

---

### Human-in-the-loop（人工干预）

暂停 Agent 执行，等待人工审批/编辑/拒绝工具调用：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.4",
    tools=[read_email, send_email],
    checkpointer=InMemorySaver(),  # 必需
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
                "read_email": False,  # 不中断
            }
        ),
    ],
)
```

---

### Model Call Limit（模型调用限制）

```python
from langchain.agents.middleware import ModelCallLimitMiddleware

agent = create_agent(
    model="gpt-5.4",
    checkpointer=InMemorySaver(),
    tools=[],
    middleware=[
        ModelCallLimitMiddleware(
            thread_limit=10,   # 线程内最大调用数
            run_limit=5,       # 单次调用最大数
            exit_behavior="end",  # "end" 优雅终止 / "error" 抛异常
        ),
    ],
)
```

---

### Tool Call Limit（工具调用限制）

```python
from langchain.agents.middleware import ToolCallLimitMiddleware

# 全局限制
global_limiter = ToolCallLimitMiddleware(thread_limit=20, run_limit=10)

# 特定工具限制
search_limiter = ToolCallLimitMiddleware(tool_name="search", thread_limit=5, run_limit=3)

# 严格限制（超出即报错）
strict_limiter = ToolCallLimitMiddleware(tool_name="scrape_webpage", run_limit=2, exit_behavior="error")

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, database_tool, scraper_tool],
    middleware=[global_limiter, search_limiter, strict_limiter],
)
```

**退出行为：**

| 选项 | 说明 |
|------|------|
| `'continue'`（默认） | 阻止超出的调用，返回错误消息，Agent 继续 |
| `'error'` | 立即抛出异常 |
| `'end'` | 停止执行（仅限单工具场景） |

---

### Model Fallback（模型回退）

```python
from langchain.agents.middleware import ModelFallbackMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        ModelFallbackMiddleware("gpt-5.4-mini", "claude-3-5-sonnet-20241022"),
    ],
)
```

---

### PII Detection（个人身份信息检测）

```python
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
    ],
)
```

**处理策略：**

| 策略 | 说明 | 示例 |
|------|------|------|
| `'block'` | 检测到即抛异常 | — |
| `'redact'` | 替换为 `[REDACTED_{TYPE}]` | `[REDACTED_email]` |
| `'mask'` | 部分遮盖 | `****-****-****-1234` |
| `'hash'` | 替换为确定性哈希 | — |

**自定义 PII 检测器：**

```python
import re

# 方式一：正则字符串
PIIMiddleware("api_key", detector=r"sk-[a-zA-Z0-9]{32}", strategy="block")

# 方式二：编译后的正则
PIIMiddleware("phone", detector=re.compile(r"\+?\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{4}"), strategy="mask")

# 方式三：自定义函数
def detect_ssn(content: str) -> list[dict[str, str | int]]:
    matches = []
    for match in re.finditer(r"\d{3}-\d{2}-\d{4}", content):
        first_three = int(match.group(0)[:3])
        if first_three not in [0, 666] and not (900 <= first_three <= 999):
            matches.append({"text": match.group(0), "start": match.start(), "end": match.end()})
    return matches

PIIMiddleware("ssn", detector=detect_ssn, strategy="hash")
```

---

### To-do List（待办清单）

```python
from langchain.agents.middleware import TodoListMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[read_file, write_file, run_tests],
    middleware=[TodoListMiddleware()],
)
```

自动提供 `write_todos` 工具和指导任务规划的系统提示词。

---

### LLM Tool Selector（LLM 工具选择器）

当 Agent 有 10+ 工具时，用 LLM 预先筛选相关工具：

```python
from langchain.agents.middleware import LLMToolSelectorMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[tool1, tool2, ..., tool15],
    middleware=[
        LLMToolSelectorMiddleware(
            model="gpt-5.4-mini",
            max_tools=3,
            always_include=["search"],
        ),
    ],
)
```

---

### Tool Retry（工具重试）

```python
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, database_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
            max_delay=60.0,
            jitter=True,
            tools=["api_tool"],               # 仅对特定工具重试
            retry_on=(ConnectionError, TimeoutError),  # 仅重试特定异常
            on_failure="continue",            # "return_message" / "raise" / 自定义函数
        ),
    ],
)
```

---

### Model Retry（模型重试）

```python
from langchain.agents.middleware import ModelRetryMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool],
    middleware=[ModelRetryMiddleware(max_retries=3, backoff_factor=2.0)],
)
```

---

### LLM Tool Emulator（LLM 工具模拟器）

测试用——用 LLM 生成模拟的工具响应：

```python
from langchain.agents.middleware import LLMToolEmulator

# 模拟所有工具
agent = create_agent(model="gpt-5.4", tools=[get_weather, send_email], middleware=[LLMToolEmulator()])

# 仅模拟特定工具
agent2 = create_agent(model="gpt-5.4", tools=[get_weather, send_email], middleware=[LLMToolEmulator(tools=["get_weather"])])

# 使用自定义模型模拟
agent3 = create_agent(model="gpt-5.4", tools=[get_weather, send_email], middleware=[LLMToolEmulator(model="claude-sonnet-4-6")])
```

---

### Context Editing（上下文编辑）

当 Token 达到限制时清除旧的工具输出：

```python
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=100000,    # Token 触发阈值
                    keep=3,            # 保留最近 3 个工具结果
                ),
            ],
        ),
    ],
)
```

---

### Shell Tool（Shell 工具）

```python
from langchain.agents.middleware import ShellToolMiddleware, HostExecutionPolicy, DockerExecutionPolicy

# 本地执行
agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool],
    middleware=[ShellToolMiddleware(workspace_root="/workspace", execution_policy=HostExecutionPolicy())],
)

# Docker 隔离
agent_docker = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            startup_commands=["pip install requests"],
            execution_policy=DockerExecutionPolicy(image="python:3.11-slim", command_timeout=60.0),
        ),
    ],
)
```

**执行策略：**

| 策略 | 说明 |
|------|------|
| `HostExecutionPolicy` | 本地执行，完全访问（默认） |
| `DockerExecutionPolicy` | Docker 容器隔离 |
| `CodexSandboxExecutionPolicy` | Codex CLI 沙箱 |

---

### File Search（文件搜索）

```python
from langchain.agents.middleware import FilesystemFileSearchMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[FilesystemFileSearchMiddleware(root_path="/workspace", use_ripgrep=True)],
)
```

自动添加 `glob_search` 和 `grep_search` 两个工具。

---

### Filesystem（文件系统）

Deep Agents 提供 `ls`、`read_file`、`write_file`、`edit_file` 四个工具：

```python
from deepagents.middleware.filesystem import FilesystemMiddleware

agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[FilesystemMiddleware()],
)
```

**跨对话持久化**：配置 `CompositeBackend` 将特定路径路由到持久存储：

```python
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_agent(
    model="claude-sonnet-4-6",
    store=store,
    middleware=[
        FilesystemMiddleware(
            backend=CompositeBackend(
                default=StateBackend(),
                routes={"/memories/": StoreBackend()},  # /memories/ 路径持久化
            ),
        ),
    ],
)
```

---

### Subagent（子 Agent）

将任务委托给子 Agent，隔离上下文：

```python
from deepagents.middleware.subagents import SubAgentMiddleware

agent = create_agent(
    model="claude-sonnet-4-6",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-6",
            subagents=[
                {
                    "name": "weather",
                    "description": "This subagent can get weather in cities.",
                    "system_prompt": "Use the get_weather tool to get the weather.",
                    "tools": [get_weather],
                    "model": "gpt-5.4",
                }
            ],
        )
    ],
)
```

> 💡 主 Agent 始终可访问一个 `general-purpose` 子 Agent，用于上下文隔离。

---

## 提供商特定中间件

| 提供商 | 中间件 |
|--------|--------|
| **Anthropic** | 提示缓存、Bash 工具、文本编辑器、记忆、文件搜索 |
| **AWS** | 提示缓存 |
| **OpenAI** | 内容审核 |
