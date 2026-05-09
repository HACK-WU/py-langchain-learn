# Demo 3：安全客服 Agent

> **阶段**：三（高级编排）
> **难度**：⭐⭐⭐⭐
> **涉及文档**：09-middleware-overview、10-middleware-built-in、11-middleware-custom

---

## 目标

构建一个带安全防护的客服 Agent，掌握中间件体系的组合使用和自定义中间件开发。

---

## 功能需求

1. **工具**：`query_order`（查订单）、`refund_order`（退款）、`send_coupon`（发优惠券）
2. **PII 防护**：`PIIMiddleware` 脱敏手机号和邮箱
3. **人工审批**：`HumanInTheLoopMiddleware` 对退款操作强制审批
4. **上下文管理**：`SummarizationMiddleware` 自动摘要长对话
5. **动态模型**：自定义 `@wrap_model_call` 根据对话轮数切换模型
6. **输出护栏**：自定义 `@after_model` 检测并替换敏感词
7. **容错**：`ModelFallbackMiddleware` + `ToolRetryMiddleware`

---

## 核心代码框架

```python
import re
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    ModelFallbackMiddleware,
    ToolRetryMiddleware,
    ModelCallLimitMiddleware,
    PIIMiddleware,
    before_model,
    after_model,
    wrap_model_call,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, RemoveMessage, SystemMessage
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime

# ============================================================
# 1. 模拟数据
# ============================================================

ORDERS = {
    "ORD-001": {"item": "iPhone 15 Pro", "price": 8999, "status": "已发货"},
    "ORD-002": {"item": "MacBook Air", "price": 12999, "status": "待发货"},
    "ORD-003": {"item": "AirPods Pro", "price": 1899, "status": "已签收"},
}

COUPONS = {"5off": 5, "10off": 10, "50off": 50}

# ============================================================
# 2. 工具定义
# ============================================================

@tool
def query_order(order_id: str) -> str:
    """Query order status by order ID.
    
    Args:
        order_id: The order ID, e.g. ORD-001
    """
    order = ORDERS.get(order_id)
    if order:
        return f"订单 {order_id}: {order['item']}，¥{order['price']}，状态: {order['status']}"
    return f"未找到订单 {order_id}，请检查订单号"

@tool
def refund_order(order_id: str, reason: str) -> str:
    """Process a refund for an order.
    
    Args:
        order_id: The order ID to refund.
        reason: The reason for the refund.
    """
    order = ORDERS.get(order_id)
    if not order:
        return f"未找到订单 {order_id}"
    if order["status"] == "已退款":
        return f"订单 {order_id} 已退款，请勿重复操作"
    order["status"] = "已退款"
    return f"订单 {order_id}（{order['item']}，¥{order['price']}）退款已处理，原因: {reason}"

@tool
def send_coupon(coupon_code: str) -> str:
    """Send a discount coupon to the user.
    
    Args:
        coupon_code: The coupon code to send.
    """
    amount = COUPONS.get(coupon_code)
    if amount:
        return f"已发放 {amount} 元优惠券（券码: {coupon_code}）"
    return f"无效券码: {coupon_code}"

# ============================================================
# 3. 自定义中间件
# ============================================================

# 3.1 动态模型切换：短对话用便宜模型，长对话用强模型
basic_model = init_chat_model("openai:gpt-5.4-mini", temperature=0)
advanced_model = init_chat_model("openai:gpt-5.4", temperature=0)

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """根据对话长度选择模型"""
    message_count = len(request.state["messages"])
    
    if message_count > 10:
        print(f"[中间件] 对话 {message_count} 条，切换到高级模型")
        return handler(request.override(model=advanced_model))
    else:
        print(f"[中间件] 对话 {message_count} 条，使用基础模型")
        return handler(request.override(model=basic_model))

# 3.2 输出护栏：检测敏感词
SENSITIVE_WORDS = ["密码", "口令", "card_number"]

@after_model
def output_guardrail(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """检测模型输出中的敏感词"""
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return None
    
    content = last_message.content if isinstance(last_message.content, str) else ""
    found = [word for word in SENSITIVE_WORDS if word in content]
    
    if found:
        print(f"[中间件] 检测到敏感词: {found}，已替换")
        clean_content = content
        for word in found:
            clean_content = clean_content.replace(word, "***")
        return {
            "messages": [
                RemoveMessage(id=last_message.id),
                AIMessage(content=clean_content),
            ]
        }
    return None

# ============================================================
# 4. 创建 Agent
# ============================================================

agent = create_agent(
    model=basic_model,
    tools=[query_order, refund_order, send_coupon],
    checkpointer=InMemorySaver(),
    system_prompt=(
        "你是一个电商客服助手。帮助用户查询订单、处理退款和发放优惠券。\n"
        "退款操作需要用户说明原因。态度友好专业。"
    ),
    middleware=[
        # PII 防护：脱敏手机号和邮箱
        PIIMiddleware("phone", detector=re.compile(r"1[3-9]\d{9}"), strategy="mask"),
        PIIMiddleware("email", detector=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", strategy="redact"),
        
        # 人工审批：退款需要人工确认
        HumanInTheLoopMiddleware(
            interrupt_on={"refund_order": {"allowed_decisions": ["approve", "reject"]}}
        ),
        
        # 长对话摘要
        SummarizationMiddleware(
            model="openai:gpt-5.4-mini",
            trigger=[("tokens", 3000), ("messages", 20)],
            keep=("messages", 10),
        ),
        
        # 模型调用限制
        ModelCallLimitMiddleware(thread_limit=30, run_limit=10, exit_behavior="end"),
        
        # 模型回退
        ModelFallbackMiddleware("openai:gpt-5.4-mini"),
        
        # 工具重试
        ToolRetryMiddleware(
            max_retries=2,
            backoff_factor=1.5,
            retry_on=(ConnectionError, TimeoutError),
        ),
        
        # 自定义中间件
        dynamic_model_selection,
        output_guardrail,
    ],
)

# ============================================================
# 5. 运行
# ============================================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "customer-001"}}
    
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
            for step, data in chunk.items():
                if step == "agent":
                    msg = data["messages"][-1]
                    if hasattr(msg, "text") and msg.text:
                        print(msg.text, flush=True)
                elif step == "tools":
                    msg = data["messages"][-1]
                    if hasattr(msg, "content") and msg.content:
                        print(f"  → {msg.content}", flush=True)
```

---

## 练习任务

### 基础（必做）

1. **跑通代码**：确保查询、退款、优惠券功能正常
2. **PII 测试**：输入包含手机号和邮箱的内容，验证脱敏效果
3. **人工审批**：触发退款操作，验证中断和恢复流程

### 进阶（选做）

4. **自定义 PII**：添加身份证号的检测器（正则或自定义函数）
5. **动态提示词**：实现 `@dynamic_prompt`，根据用户身份（admin/user）显示不同的系统提示词
6. **跳转控制**：在 `output_guardrail` 中添加 `can_jump_to=["end"]`，检测到严重违规时直接终止
7. **工具调用监控**：添加 `@wrap_tool_call` 中间件，记录每次工具调用的时间、参数和耗时
8. **Token 追踪**：使用 `get_usage_metadata_callback` 统计整个对话的 Token 消耗

---

## 源码阅读指引

| 文件 | 关注点 |
|------|--------|
| `langchain/agents/middleware/` | 各内置中间件的实现（SummarizationMiddleware、HumanInTheLoopMiddleware、PIIMiddleware） |
| `langchain/agents/middleware/` | `AgentMiddleware` 基类和装饰器实现 |
| `langchain/agents/` | `create_agent` 如何编排中间件链 |

**思考题**：
1. `before_*` 和 `after_*` 的执行顺序为什么是相反的？和洋葱模型有什么关系？
2. `HumanInTheLoopMiddleware` 的中断和恢复机制是如何实现的？`interrupt_on` 配置是如何影响流程的？
3. `PIIMiddleware` 的 4 种策略（block/redact/mask/hash）在源码中是如何实现的？
