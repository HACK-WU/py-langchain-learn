# Demo 1：多模型翻译助手

> **阶段**：一（基础入门）
> **难度**：⭐⭐
> **涉及文档**：00-install、01-quickstart、03-models、04-messages

---

## 目标

构建一个命令行翻译助手，掌握模型初始化、消息体系、流式输出和批量调用。

---

## 功能需求

1. 使用 `init_chat_model` 初始化 2 个不同提供商的模型
2. 用 `SystemMessage` 设定翻译角色
3. 使用 `model.stream()` 流式输出翻译结果
4. 使用 `model.batch()` 批量翻译多条文本
5. 对比两个模型的翻译结果和 Token 用量

---

## 核心代码框架

```python
import os
from langchain.chat_models import init_chat_model
from langchain.messages import SystemMessage, HumanMessage, AIMessage

# 1. 初始化两个模型
model_openai = init_chat_model("openai:gpt-5.4-mini", temperature=0.3)
model_deepseek = init_chat_model("deepseek:deepseek-chat", temperature=0.3)

# 2. 系统提示词
system_msg = SystemMessage("你是一个专业的英译中翻译。保持原文语气，翻译自然流畅。")

# 3. 流式翻译
def stream_translate(model, text: str, label: str):
    """流式输出翻译结果"""
    print(f"\n[{label}] ", end="")
    messages = [system_msg, HumanMessage(text)]
    full_response = None
    for chunk in model.stream(messages):
        full_response = chunk if full_response is None else full_response + chunk
        print(chunk.text, end="", flush=True)
    print()
    return full_response

# 4. 批量翻译
def batch_translate(model, texts: list[str], label: str):
    """批量翻译并统计 Token"""
    batches = [
        [system_msg, HumanMessage(text)]
        for text in texts
    ]
    responses = model.batch(batches)
    
    total_input = 0
    total_output = 0
    for i, resp in enumerate(responses):
        print(f"\n[{label}] 文本 {i+1}: {texts[i][:30]}...")
        print(f"  翻译: {resp.text}")
        if resp.usage_metadata:
            total_input += resp.usage_metadata.get("input_tokens", 0)
            total_output += resp.usage_metadata.get("output_tokens", 0)
    
    print(f"\n[{label}] Token 统计: input={total_input}, output={total_output}, total={total_input + total_output}")

# 5. 运行
if __name__ == "__main__":
    # 流式对比
    text = "The weather today is absolutely beautiful, with clear blue skies and a gentle breeze."
    
    stream_translate(model_openai, text, "OpenAI")
    stream_translate(model_deepseek, text, "DeepSeek")
    
    # 批量对比
    texts = [
        "Machine learning is transforming the way we interact with technology.",
        "Climate change remains one of the most pressing challenges of our time.",
        "The quick brown fox jumps over the lazy dog.",
    ]
    
    batch_translate(model_openai, texts, "OpenAI")
    batch_translate(model_deepseek, texts, "DeepSeek")
```

---

## 练习任务

### 基础（必做）

1. **跑通代码**：配置 API Key，确保两个模型都能正常调用
2. **切换模型**：尝试使用 `init_chat_model("anthropic:claude-sonnet-4-6")` 添加第三个模型
3. **Token 分析**：比较不同模型的 Token 使用差异，思考原因

### 进阶（选做）

4. **添加对话历史**：使用 `AIMessage` 构建多轮对话，让模型根据前文翻译
5. **可配置模型**：使用 `init_chat_model(configurable_fields=("model",))` 实现运行时切换模型
6. **速率限制**：使用 `InMemoryRateLimiter` 控制请求频率

---

## 源码阅读指引

完成 Demo 后，阅读以下源码：

| 文件 | 关注点 |
|------|--------|
| `langchain_core/language_models/chat_models.py` | `BaseChatModel.invoke` → `BaseChatModel.stream` → `BaseChatModel.batch` 的调用链 |
| `langchain_core/messages/base.py` | `BaseMessage` 的 `content` 和 `content_blocks` 属性 |
| `langchain_openai/chat_models/` | 具体提供商如何实现 `BaseChatModel` 接口 |

**思考题**：`stream` 方法内部是否调用了 `invoke`？`batch` 的并发控制是在哪一层实现的？
