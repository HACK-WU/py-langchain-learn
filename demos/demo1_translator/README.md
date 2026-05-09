# Demo 1: 多模型翻译助手

使用小米（Anthropic 协议）和 DeepSeek（OpenAI 协议）两个模型，
演示 init_chat_model 初始化、流式输出和批量翻译功能。

## 运行方式

```bash
uv run python demos/demo1_translator/main.py
```

## 涉及知识点

- `init_chat_model` 统一初始化不同协议的模型
- 流式输出 `model.stream()`
- 批量调用 `model.batch()`
- Token 用量统计 `usage_metadata`
- Anthropic 协议 content blocks 兼容处理
