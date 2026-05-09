# LangChain 安装指南

> 来源：https://docs.langchain.com/oss/python/langchain/install

---

## 安装 LangChain 核心包

```bash
# 使用 pip
pip install -U langchain
# 需要 Python 3.10+

# 使用 uv
uv add langchain
# 需要 Python 3.10+
```

## 安装模型提供商集成包

LangChain 通过独立的提供商包来集成数百个 LLM 和数千种其他服务。

```bash
# pip 方式
pip install -U langchain-openai      # OpenAI 集成
pip install -U langchain-anthropic   # Anthropic 集成

# uv 方式
uv add langchain-openai
uv add langchain-anthropic
```

### 常用集成包一览

| 集成包 | 说明 | 安装命令 |
|--------|------|----------|
| `langchain-openai` | OpenAI / Azure OpenAI | `pip install -U langchain-openai` |
| `langchain-anthropic` | Anthropic (Claude) | `pip install -U langchain-anthropic` |
| `langchain-google-genai` | Google Gemini | `pip install -U "langchain[google-genai]"` |
| `langchain-aws` | AWS Bedrock | `pip install -U "langchain[aws]"` |
| `langchain-huggingface` | HuggingFace | `pip install -U "langchain[huggingface]"` |
| `langchain-openrouter` | OpenRouter | `pip install -U langchain-openrouter` |

> 💡 完整集成列表请参阅 LangChain 官方文档的 Integrations 页面。

## 配置 LangSmith 追踪

安装完成后，建议配置 LangSmith 来调试你的 LangChain 应用：

```shell
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="your-langsmith-api-key"
```

---

## 下一步

安装完成后，请参考 [快速开始指南](./01-quickstart.md) 构建你的第一个 Agent！
