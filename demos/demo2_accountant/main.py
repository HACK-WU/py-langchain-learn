"""Demo 2: 个人记账 Agent

使用 LangChain create_agent 构建有状态的记账助手，
演示自定义状态、工具系统（ToolRuntime + Command）、
InMemorySaver 对话记忆和流式输出。
"""

import os
import sys
import time

# 修复 Windows 终端 GBK 编码问题
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import NotRequired

from langchain.agents import create_agent, AgentState
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

load_dotenv()

# ============================================================
# 1. 自定义状态
# ============================================================


class AccountantState(AgentState):
    """记账 Agent 的状态，扩展 AgentState 增加 balance 和 transactions。"""

    balance: NotRequired[float]
    transactions: NotRequired[list]


# ============================================================
# 2. 工具定义
# ============================================================


@tool
def add_income(amount: float, description: str, runtime: ToolRuntime) -> Command:
    """记录一笔收入。

    Args:
        amount: 收入金额（元）。
        description: 收入描述，如"工资"、"兼职"等。
    """
    current_balance = runtime.state.get("balance", 0.0)
    transactions = runtime.state.get("transactions", [])

    new_transaction = {
        "type": "income",
        "amount": amount,
        "description": description,
    }
    new_balance = current_balance + amount

    return Command(
        update={
            "balance": new_balance,
            "transactions": transactions + [new_transaction],
            "messages": [
                ToolMessage(
                    content=f"已记录收入 ¥{amount:.2f}（{description}），当前余额 ¥{new_balance:.2f}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


@tool
def add_expense(amount: float, description: str, runtime: ToolRuntime) -> Command:
    """记录一笔支出。

    Args:
        amount: 支出金额（元）。
        description: 支出描述，如"午餐"、"地铁"等。
    """
    current_balance = runtime.state.get("balance", 0.0)
    transactions = runtime.state.get("transactions", [])

    if amount > current_balance:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"余额不足！当前余额 ¥{current_balance:.2f}，无法支出 ¥{amount:.2f}",
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
            }
        )

    new_transaction = {
        "type": "expense",
        "amount": amount,
        "description": description,
    }
    new_balance = current_balance - amount

    return Command(
        update={
            "balance": new_balance,
            "transactions": transactions + [new_transaction],
            "messages": [
                ToolMessage(
                    content=f"已记录支出 ¥{amount:.2f}（{description}），当前余额 ¥{new_balance:.2f}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


@tool
def get_summary(runtime: ToolRuntime) -> str:
    """获取账单汇总，包含总收入、总支出、当前余额和最近交易记录。"""
    balance = runtime.state.get("balance", 0.0)
    transactions = runtime.state.get("transactions", [])

    income_total = sum(t["amount"] for t in transactions if t["type"] == "income")
    expense_total = sum(t["amount"] for t in transactions if t["type"] == "expense")
    income_count = sum(1 for t in transactions if t["type"] == "income")
    expense_count = sum(1 for t in transactions if t["type"] == "expense")

    lines = [
        "账单汇总",
        f"  收入: {income_count} 笔，共 ¥{income_total:.2f}",
        f"  支出: {expense_count} 笔，共 ¥{expense_total:.2f}",
        f"  余额: ¥{balance:.2f}",
    ]

    if transactions:
        lines.append("")
        lines.append("  最近交易:")
        for i, t in enumerate(transactions[-5:], 1):
            sign = "+" if t["type"] == "income" else "-"
            lines.append(f"  {i}. {sign}¥{t['amount']:.2f} ({t['description']})")

    return "\n".join(lines)


# ============================================================
# 3. 结构化输出 Schema（进阶：可用于 response_format）
# ============================================================


class TransactionReport(BaseModel):
    """结构化账单报告。"""

    total_income: float = Field(description="总收入金额")
    total_expense: float = Field(description="总支出金额")
    balance: float = Field(description="当前余额")
    transaction_count: int = Field(description="总交易笔数")
    summary_text: str = Field(description="简短的自然语言摘要")


# ============================================================
# 4. 创建 Agent
# ============================================================

model = init_chat_model(
    "deepseek-chat",
    model_provider="deepseek",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    api_base=os.getenv("DEEPSEEK_API_BASE"),
    temperature=0,
)

agent = create_agent(
    model=model,
    tools=[add_income, add_expense, get_summary],
    state_schema=AccountantState,
    checkpointer=InMemorySaver(),
    system_prompt=(
        "你是一个个人记账助手。用户说收入或支出时，使用对应工具记录。"
        "查询时使用汇总工具。回复简洁友好。"
    ),
)

# ============================================================
# 5. 运行（流式输出）
# ============================================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "user-001"}}

    questions = [
        "我今天工资到账了，8000元",
        "中午吃了一顿饭，花了35元",
        "坐地铁花了6元",
        "帮朋友做兼职赚了500元",
        "汇总一下我的账单",
    ]

    print("=" * 60)
    print("  个人记账 Agent - Demo 2（预定义问题演示）")
    print("=" * 60)

    for question in questions:
        print(f"\n你: {question}")
        print("Agent: ", end="")
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
            stream_mode="updates",
        ):
            if "agent" in chunk:
                msg = chunk["agent"]["messages"][-1]
                if hasattr(msg, "text") and msg.text:
                    print(msg.text, end="", flush=True)
                elif hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_names = [tc["name"] for tc in msg.tool_calls]
                    print(f"[调用工具: {', '.join(tool_names)}]", end="", flush=True)
            elif "tools" in chunk:
                msg = chunk["tools"]["messages"][-1]
                if hasattr(msg, "content") and msg.content:
                    print(f"\n  -> {msg.content}", flush=True)
        print()
        time.sleep(1)  # 避免被限流

    print("\n" + "=" * 60)
    print("  演示结束")
    print("=" * 60)
