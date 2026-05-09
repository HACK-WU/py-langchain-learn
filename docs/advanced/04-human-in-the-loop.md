# 人在回路 (Human-in-the-loop)

人在回路（HITL）中间件允许你为智能体工具调用添加人工监督。
当模型提出可能需要审查的操作时（例如写入文件或执行 SQL），中间件可以暂停执行并等待决策。

它通过根据可配置策略检查每个工具调用来实现这一点。如果需要干预，中间件会发出中断信号来停止执行。图状态使用 LangGraph 的持久层保存，因此执行可以安全地暂停并在稍后恢复。

然后，人工决策决定接下来发生什么：操作可以按原样批准（`approve`）、在运行前修改（`edit`）、附带反馈拒绝（`reject`），或直接响应（`respond`）用于"询问用户"类型的工具。

## 中断决策类型

中间件定义了人工响应中断的四种内置方式：

| 决策类型 | 描述 | 示例用例 |
| --- | --- | --- |
| ✅ `approve` | 操作按原样批准并执行，不做更改。 | 完全按照草稿发送邮件 |
| ✏️ `edit` | 工具调用在执行前进行修改。 | 在发送邮件前更改收件人 |
| ❌ `reject` | 工具调用被拒绝，并将解释添加到对话中。 | 拒绝邮件草稿并解释如何重写 |
| 💬 `respond` | 跳过工具执行；人工的消息成为工具结果。 | 用直接回复回答"ask_user"提示 |

每个工具的可用决策类型取决于你在 `interrupt_on` 中配置的策略。
当多个工具调用同时暂停时，每个操作都需要单独的决策。
决策必须按照操作在中断请求中出现的顺序提供。

编辑工具参数时，请保守地进行更改。对原始参数的重大修改可能导致模型重新评估其方法，并可能多次执行工具或采取意外操作。

## 配置中断

要使用 HITL，请在创建智能件时将其添加到智能体的 `middleware` 列表中。

你需要配置一个工具操作到每种操作允许决策类型的映射。当工具调用与映射中的操作匹配时，中间件将中断执行。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware # [!code highlight]
from langgraph.checkpoint.memory import InMemorySaver # [!code highlight]

agent = create_agent(
    model="gpt-5.4",
    tools=[write_file, execute_sql, read_data],
    middleware=[
        HumanInTheLoopMiddleware( # [!code highlight]
            interrupt_on={
                "write_file": True,  # 允许所有决策（approve, edit, reject, respond）
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # 不允许编辑
                "read_data": False, # 安全操作，无需审批
            },
            # 中断消息的前缀 - 与工具名称和参数组合形成完整消息
            # 例如："Tool execution pending approval: execute_sql with query='DELETE FROM...'"
            # 单个工具可以通过在其中断配置中指定 "description" 来覆盖此设置
            description_prefix="Tool execution pending approval",
        ),
    ],
    # 人在回路需要检查点来处理中断。
    # 在生产环境中，使用持久化检查点如 AsyncPostgresSaver。
    checkpointer=InMemorySaver(),  # [!code highlight]
)

```

你必须配置检查点以在中断间持久化图状态。
在生产环境中，使用持久化检查点如 `AsyncPostgresSaver`。对于测试或原型设计，使用 `InMemorySaver`。

调用智能体时，传递包含线程 ID 的 `config` 以将执行与对话线程关联。
有关详细信息，请参阅 LangGraph 中断文档。

## 配置选项

工具名称到审批配置的映射。值可以是 `True`（使用默认配置中断）、`False`（自动批准）或 `InterruptOnConfig` 对象。

操作请求描述的前缀

`InterruptOnConfig` 选项：

允许决策的列表：`'approve'`、`'edit'`、`'reject'` 或 `'respond'`

自定义描述的静态字符串或可调用函数

## 响应中断

当你调用智能体时，它会运行直到完成或引发中断。当工具调用与你在 `interrupt_on` 中配置的策略匹配时，会触发中断。使用 `version="v2"`，结果是带有 `interrupts` 属性的 `GraphOutput`，包含需要审查的操作。然后你可以将这些操作呈现给审查者，并在提供决策后恢复执行。

```python
from langgraph.types import Command

# 人在回路利用 LangGraph 的持久层。
# 你必须提供线程 ID 以将执行与对话线程关联，
# 以便对话可以暂停和恢复（如人工审查所需）。
config = {"configurable": {"thread_id": "some_id"}} # [!code highlight]
# 运行图直到触发中断。
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Delete old records from the database",
            }
        ]
    },
    config=config, # [!code highlight]
    version="v2", # [!code highlight]
)

# result 是带有 .value 和 .interrupts 的 GraphOutput
print(result.interrupts)  # [!code highlight]
# > (
# >    Interrupt(
# >       value={
# >          'action_requests': [
# >             {
# >                'name': 'execute_sql',
# >                'arguments': {'query': 'DELETE FROM records WHERE created_at < NOW() - INTERVAL \'30 days\';'},
# >                'description': 'Tool execution pending approval\n\nTool: execute_sql\nArgs: {...}'
# >             }
# >          ],
# >          'review_configs': [
# >             {
# >                'action_name': 'execute_sql',
# >                'allowed_decisions': ['approve', 'reject']
# >             }
# >          ]
# >       }
# >    ),
# > )

# 使用批准决策恢复
agent.invoke(
    Command( # [!code highlight]
        resume={"decisions": [{"type": "approve"}]}  # 或 "reject" [!code highlight]
    ), # [!code highlight]
    config=config, # 相同的线程 ID 以恢复暂停的对话
    version="v2",
)

```

### 决策类型

## ✅ approve

使用 `approve` 按原样批准工具调用并执行，不做更改。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审查操作一个。
        # 决策的顺序必须与中断请求中操作的顺序一致。
        resume={
            "decisions": [
                {
                    "type": "approve",
                }
            ]
        }
    ),
    config=config,  # 相同的线程 ID 以恢复暂停的对话
    version="v2",
)

```

## ✏️ edit

使用 `edit` 在执行前修改工具调用。
提供带有新工具名称和参数的已编辑操作。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审查操作一个。
        # 决策的顺序必须与中断请求中操作的顺序一致。
        resume={
            "decisions": [
                {
                    "type": "edit",
                    # 带有工具名称和参数的已编辑操作
                    "edited_action": {
                        # 要调用的工具名称。
                        # 通常与原始操作相同。
                        "name": "new_tool_name",
                        # 传递给工具的参数。
                        "args": {"key1": "new_value", "key2": "original_value"},
                    }
                }
            ]
        }
    ),
    config=config,  # 相同的线程 ID 以恢复暂停的对话
    version="v2",
)

```

编辑工具参数时，请保守地进行更改。对原始参数的重大修改可能导致模型重新评估其方法，并可能多次执行工具或采取意外操作。

## ❌ reject

使用 `reject` 拒绝工具调用并提供反馈，而不是执行。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审查操作一个。
        # 决策的顺序必须与中断请求中操作的顺序一致。
        resume={
            "decisions": [
                {
                    "type": "reject",
                    # 关于为什么拒绝操作的解释
                    "message": "No, this is wrong because ..., instead do this ...",
                }
            ]
        }
    ),
    config=config,  # 相同的线程 ID 以恢复暂停的对话
    version="v2",
)

```

`message` 作为反馈添加到对话中，帮助智能体理解为什么操作被拒绝以及它应该做什么。

---

### 多个决策

当多个操作正在审查时，按照它们在中断中出现的顺序为每个操作提供决策：

```python
{
    "decisions": [
        {"type": "approve"},
        {
            "type": "edit",
            "edited_action": {
                "name": "tool_name",
                "args": {"param": "new_value"}
            }
        },
        {
            "type": "reject",
            "message": "This action is not allowed"
        }
    ]
}

```

## 💬 respond

使用 `respond` 处理"询问用户"类型的工具，其中工具的真正实现是人工的回复。`message` 内容直接作为工具结果返回；工具本身不会执行。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审查操作一个。
        # 决策的顺序必须与中断请求中操作的顺序一致。
        resume={
            "decisions": [
                {
                    "type": "respond",
                    # 人工的回复，直接作为工具结果返回
                    "message": "Blue.",
                }
            ]
        }
    ),
    config=config,  # 相同的线程 ID 以恢复暂停的对话
    version="v2",
)

```

`message` 作为成功的 `ToolMessage` 返回给智能体。当工具故意是人工输入的占位符时使用 `respond`——例如，提示澄清的 `ask_user` 工具。

## 使用人在回路进行流式传输

你可以使用 `stream()` 而不是 `invoke()` 来在智能体运行和处理中断时获取实时更新。使用 `stream_mode=['updates', 'messages']` 和 `version="v2"` 以统一 v2 格式流式传输智能体进度和 LLM token。

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

# 流式传输智能体进度和 LLM token 直到中断
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Delete old records from the database"}]},
    config=config,
    stream_mode=["updates", "messages"],  # [!code highlight]
    version="v2",  # [!code highlight]
):
    if chunk["type"] == "messages":  # [!code highlight]
        # LLM token
        token, metadata = chunk["data"]  # [!code highlight]
        if token.content:
            print(token.content, end="", flush=True)
    elif chunk["type"] == "updates":  # [!code highlight]
        # 检查中断
        if "__interrupt__" in chunk["data"]:  # [!code highlight]
            print(f"\n\nInterrupt: {chunk['data']['__interrupt__']}")

# 人工决策后使用流式传输恢复
for chunk in agent.stream(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
    stream_mode=["updates", "messages"],
    version="v2",  # [!code highlight]
):
    if chunk["type"] == "messages":  # [!code highlight]
        token, metadata = chunk["data"]  # [!code highlight]
        if token.content:
            print(token.content, end="", flush=True)

```

有关流式模式的更多详细信息，请参阅流式传输指南。

## 执行生命周期

中间件定义了一个 `after_model` 钩子，在模型生成响应后但在任何工具调用执行前运行：

1. 智能体调用模型生成响应。
2. 中间件检查响应中的工具调用。
3. 如果任何调用需要人工输入，中间件会构建带有 `action_requests` 和 `review_configs` 的 `HITLRequest` 并调用中断。
4. 智能体等待人工决策。
5. 基于 `HITLResponse` 决策，中间件执行批准或编辑的调用，为拒绝的调用合成 ToolMessage，为 `respond` 决策将人工回复直接作为 ToolMessage 返回，并恢复执行。

## 自定义 HITL 逻辑

对于更专业的工作流，你可以直接使用中断原语和中间件抽象构建自定义 HITL 逻辑。

查看上面的执行生命周期以了解如何将中断集成到智能体的操作中。
