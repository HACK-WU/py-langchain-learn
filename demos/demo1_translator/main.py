"""Demo 1: 多模型翻译助手

使用小米（Anthropic 协议）和 DeepSeek（OpenAI 协议）两个模型，
演示 init_chat_model 初始化、流式输出和批量翻译功能。
"""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

# 1. 初始化两个模型
model_xiaomi = init_chat_model(
    "mimo-v2.5",
    model_provider="anthropic",
    anthropic_api_key=os.getenv("XIAOMI_API_KEY"),
    anthropic_api_url=os.getenv("XIAOMI_API_BASE"),
    temperature=0.3,
)

model_deepseek = init_chat_model(
    "deepseek-v4-flash",
    model_provider="deepseek",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    api_base=os.getenv("DEEPSEEK_API_BASE"),
    temperature=0.3,
)

# 2. 系统提示词
system_msg = SystemMessage(
    "你是一个专业的英译中翻译。保持原文语气，翻译自然流畅。只输出翻译结果，不要添加任何解释。"
)


def _extract_text(content) -> str:
    """从消息内容中提取纯文本，兼容字符串和 content blocks 列表"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if block.get("type") == "text"
        )
    return str(content)


# 3. 流式翻译
def stream_translate(model, text: str, label: str):
    """流式输出翻译结果"""
    print(f"\n[{label}] ", end="")
    messages = [system_msg, HumanMessage(text)]
    full_response = None
    for chunk in model.stream(messages):
        full_response = chunk if full_response is None else full_response + chunk
        text_part = _extract_text(chunk.content)
        print(text_part, end="", flush=True)
    print()
    return full_response


# 4. 批量翻译
def batch_translate(model, texts: list[str], label: str):
    """批量翻译并统计 Token"""
    batches = [[system_msg, HumanMessage(text)] for text in texts]
    responses = model.batch(batches)

    total_input = 0
    total_output = 0
    for i, resp in enumerate(responses):
        translation = _extract_text(resp.content)
        print(f"\n[{label}] 文本 {i + 1}: {texts[i][:30]}...")
        print(f"  翻译: {translation}")
        if resp.usage_metadata:
            total_input += resp.usage_metadata.get("input_tokens", 0)
            total_output += resp.usage_metadata.get("output_tokens", 0)

    print(
        f"\n[{label}] Token 统计: input={total_input}, output={total_output}, total={total_input + total_output}"
    )


# 5. 运行
if __name__ == "__main__":
    print("=" * 60)
    print("  多模型翻译助手 - Demo 1")
    print("=" * 60)

    # 流式对比
    text = "The weather today is absolutely beautiful, with clear blue skies and a gentle breeze."
    print("\n--- 流式翻译对比 ---")
    resp_xiaomi = stream_translate(model_xiaomi, text, "小米")
    resp_deepseek = stream_translate(model_deepseek, text, "DeepSeek")

    # 批量对比
    texts = [
        "Machine learning is transforming the way we interact with technology.",
        "Climate change remains one of the most pressing challenges of our time.",
        "The quick brown fox jumps over the lazy dog.",
    ]
    print("\n\n--- 批量翻译对比 ---")
    batch_translate(model_xiaomi, texts, "小米")
    batch_translate(model_deepseek, texts, "DeepSeek")
