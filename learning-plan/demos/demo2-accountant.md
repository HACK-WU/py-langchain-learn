# Demo 2：个人记账 Agent

> **阶段**：二（核心能力）
> **难度**：⭐⭐⭐
> **涉及文档**：05-tools、06-short-term-memory、07-streaming、08-structured-output

---

## 目标

构建一个有状态的个人记账助手，掌握工具系统、状态管理、记忆、流式输出和结构化输出。

---

## 功能需求

1. 自定义 `AgentState`，包含 `balance: float` 和 `transactions: list`
2. 定义 3 个工具：`add_income`、`add_expense`、`get_summary`
3. 工具通过 `ToolRuntime` 读写 State，使用 `Command` 更新状态
4. 使用 `InMemorySaver` 实现对话记忆
5. 使用结构化输出返回 `TransactionReport`
6. 用 `stream_mode="updates"` 流式输出进度

---

## 核心代码框架

```python
from typing import Annotated
from typing_extensions import NotRequired, TypedDict
from pydantic import BaseModel, Field

from langchain.agents import create_agent, AgentState
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

# ============================================================
# 1. 自定义状态
# ============================================================

class AccountantState(AgentState):
    balance: NotRequired[float]
    transactions: NotRequired[list]

# ============================================================
# 2. 工具定义
# ============================================================

@tool
def add_income(amount: float, description: str, runtime: ToolRuntime[None, AccountantState]) -> Command:
    """Record an income transaction.
    
    Args:
        amount: The income amount in yuan.
        description: A brief description of the income.
    """
    current_balance = runtime.state.get("balance", 0.0)
    transactions = runtime.state.get("transactions", [])
    
    new_transaction = {"type": "income", "amount": amount, "description": description}
    
    return Command(update={
        "balance": current_balance + amount,
        "transactions": transactions + [new_transaction],
        "messages": [
            ToolMessage(
                content=f"已记录收入 ¥{amount:.2f}（{description}），当前余额 ¥{current_balance + amount:.2f}",
                tool_call_id=runtime.tool_call_id,
            )
        ],
    })

@tool
def add_expense(amount: float, description: str, runtime: ToolRuntime[None, AccountantState]) -> Command:
    """Record an expense transaction.
    
    Args:
        amount: The expense amount in yuan.
        description: A brief description of the expense.
    """
    current_balance = runtime.state.get("balance", 0.0)
    transactions = runtime.state.get("transactions", [])
    
    if amount > current_balance:
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"余额不足！当前余额 ¥{current_balance:.2f}，无法支出 ¥{amount:.2f}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        })
    
    new_transaction = {"type": "expense", "amount": amount, "description": description}
    
    return Command(update={
        "balance": current_balance - amount,
        "transactions": transactions + [new_transaction],
        "messages": [
            ToolMessage(
                content=f"已记录支出 ¥{amount:.2f}（{description}），当前余额 ¥{current_balance - amount:.2f}",
                tool_call_id=runtime.tool_call_id,
            )
        ],
    })

@tool
def get_summary(runtime: ToolRuntime[None, AccountantState]) -> str:
    """Get a summary of all transactions and current balance."""
    balance = runtime.state.get("balance", 0.0)
    transactions = runtime.state.get("transactions", [])
    
    income_total = sum(t["amount"] for t in transactions if t["type"] == "income")
    expense_total = sum(t["amount"] for t in transactions if t["type"] == "expense")
    
    summary = f"📊 账单汇总\n"
    summary += f"  收入: {sum(1 for t in transactions if t['type'] == 'income')} 笔，共 ¥{income_total:.2f}\n"
    summary += f"  支出: {sum(1 for t in transactions if t['type'] == 'expense')} 笔，共 ¥{expense_total:.2f}\n"
    summary += f"  余额: ¥{balance:.2f}\n"
    
    if transactions:
        summary += f"\n  最近交易:\n"
        for i, t in enumerate(transactions[-5:], 1):
            sign = "+" if t["type"] == "income" else "-"
            summary += f"  {i}. {sign}¥{t['amount']:.2f} ({t['description']})\n"
    
    return summary

# ============================================================
# 3. 结构化输出 Schema
# ============================================================

class TransactionReport(BaseModel):
    """Structured report of financial transactions."""
    total_income: float = Field(description="Total income amount")
    total_expense: float = Field(description="Total expense amount")
    balance: float = Field(description="Current balance")
    transaction_count: int = Field(description="Total number of transactions")
    summary_text: str = Field(description="A brief natural language summary")

# ============================================================
# 4. 创建 Agent
# ============================================================

model = init_chat_model("openai:gpt-5.4-mini", temperature=0)

agent = create_agent(
    model=model,
    tools=[add_income, add_expense, get_summary],
    state_schema=AccountantState,
    checkpointer=InMemorySaver(),
    system_prompt="你是一个个人记账助手。用户说收入或支出时，使用对应工具记录。查询时使用汇总工具。回复简洁友好。",
)

# ============================================================
# 5. 运行（流式输出）
# ============================================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "user-001"}}
    
    # 对话循环
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            break
        
        print("Agent: ", end="")
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="updates",
        ):
            if "agent" in chunk:
                msg = chunk["agent"]["messages"][-1]
                if hasattr(msg, "text") and msg.text:
                    print(msg.text, flush=True)
                elif hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_names = [tc["name"] for tc in msg.tool_calls]
                    print(f"[调用工具: {', '.join(tool_names)}]", flush=True)
            elif "tools" in chunk:
                msg = chunk["tools"]["messages"][-1]
                if hasattr(msg, "content") and msg.content:
                    print(f"  → {msg.content}", flush=True)
```

---

## 练习任务

### 基础（必做）

1. **跑通代码**：确保 Agent 能正确记录收入和支出
2. **多轮对话**：验证 `InMemorySaver` 的记忆效果，同一 thread_id 下余额是否持续累加
3. **余额不足**：测试支出超过余额时的处理

### 进阶（选做）

4. **添加类别**：给交易添加分类标签（餐饮、交通、工资等），工具参数增加 `category`
5. **结构化输出**：在查询汇总时使用 `response_format=TransactionReport` 返回结构化数据
6. **长期记忆**：使用 `InMemoryStore` + `ToolRuntime.store` 保存用户偏好（如默认货币、预算上限）
7. **流式进度**：在工具中使用 `runtime.stream_writer` 发送处理进度

---

## 源码阅读指引

| 文件 | 关注点 |
|------|--------|
| `langchain_core/tools/base.py` | `BaseTool.invoke` 如何注入 `ToolRuntime` |
| `langchain_core/tools/convert.py` | `@tool` 如何将函数转为 `BaseTool` |
| `langchain/agents/` | `create_agent` 如何组装 State + Checkpointer + Tools |

**思考题**：`Command` 的 `update` 字典和工具直接返回字符串，对 Agent 状态的影响有什么本质区别？为什么更新 `balance` 时需要使用 `Command` 而不是返回值？
