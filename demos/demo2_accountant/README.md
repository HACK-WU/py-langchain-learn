# Demo 2: 个人记账 Agent

使用 LangChain `create_agent` 构建有状态的记账助手，
演示自定义状态、工具系统（ToolRuntime + Command）、InMemorySaver 对话记忆和流式输出。

## 运行方式

```bash
uv run python demos/demo2_accountant/main.py
```

## 功能

- 记录收入和支出，自动维护余额
- 余额不足时拒绝支出
- 查看账单汇总和最近交易
- 多轮对话记忆（同一 thread_id 下余额持续累加）
- 流式输出工具调用进度

## 使用示例

```
你: 收入 5000 工资
你: 支出 35 午餐
你: 支出 6 地铁
你: 汇总
你: 退出
```

## 涉及知识点

- `AgentState` 自定义状态扩展（TypedDict + NotRequired）
- `@tool` 工具定义 + `ToolRuntime` 自动注入
- `Command(update={...})` 通过工具更新 Agent 状态
- `ToolMessage` 携带 `tool_call_id` 返回工具结果
- `InMemorySaver` 对话记忆（checkpointer）
- `stream_mode="updates"` 流式输出
- Pydantic `BaseModel` 结构化输出 Schema（TransactionReport）
