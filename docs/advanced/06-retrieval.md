# Retrieval（检索）

检索（Retrieval）是 LangChain 中用于从数据源获取相关文档的核心组件。检索器（Retriever）比向量存储（Vector Store）更通用——它不需要能够存储文档，只需要能够返回（或检索）文档即可。

## 概述

**Retriever** 类接收文本 **query**（查询），返回 `Document` 对象列表。

检索器比向量存储更通用。检索器不需要能够存储文档，只需要能够返回（或检索）文档即可。向量存储可以作为检索器的底层支持，但也有其他类型的检索器。

## BaseRetriever

`BaseRetriever` 是文档检索系统的抽象基类。

检索系统被定义为可以接受字符串查询并从某个源返回最"相关"文档的内容。

### 使用方法

检索器遵循标准的 `Runnable` 接口，应通过 `Runnable` 的标准方法使用：`invoke`、`ainvoke`、`batch`、`abatch`。

### 实现自定义检索器

在实现自定义检索器时，类应实现 `_get_relevant_documents` 方法来定义检索文档的逻辑。

可选地，可以通过重写 `_aget_relevant_documents` 方法提供异步原生实现。

### 示例：返回文档列表中前 k 个文档的简单检索器

```python
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

class SimpleRetriever(BaseRetriever):
    docs: list[Document]
    k: int = 5

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """返回文档列表中的前 k 个文档"""
        return self.docs[:self.k]

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        """（可选）异步原生实现"""
        return self.docs[:self.k]
```

### 示例：基于 scikit-learn 向量化器的简单检索器

```python
from sklearn.metrics.pairwise import cosine_similarity
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import BaseModel

class TFIDFRetriever(BaseRetriever, BaseModel):
    vectorizer: Any
    docs: list[Document]
    tfidf_array: Any
    k: int = 4

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str) -> list[Document]:
        query_vec = self.vectorizer.transform([query])
        results = cosine_similarity(self.tfidf_array, query_vec).reshape((-1,))
        return [self.docs[i] for i in results.argsort()[-self.k :][::-1]]
```

## 核心方法

### invoke

同步调用检索器获取相关文档。

```python
def invoke(
    self,
    input: str,
    config: RunnableConfig | None = None,
    **kwargs: Any
) -> list[Document]
```

**参数：**
- `input`：查询字符串
- `config`：检索器的配置
- `**kwargs`：传递给检索器的附加参数

**返回：**
相关文档列表

**示例：**
```python
retriever.invoke("query")
```

### ainvoke

异步调用检索器获取相关文档。

```python
async def ainvoke(
    self,
    input: str,
    config: RunnableConfig | None = None,
    **kwargs: Any,
) -> list[Document]
```

**参数：**
- `input`：查询字符串
- `config`：检索器的配置
- `**kwargs`：传递给检索器的附加参数

**返回：**
相关文档列表

**示例：**
```python
await retriever.ainvoke("query")
```

### _get_relevant_documents

获取与查询相关的文档（抽象方法，子类必须实现）。

```python
@abstractmethod
def _get_relevant_documents(
    self,
    query: str,
    *,
    run_manager: CallbackManagerForRetrieverRun
) -> list[Document]
```

**参数：**
- `query`：用于查找相关文档的字符串
- `run_manager`：要使用的回调处理器

## 类型定义

### RetrieverInput

```python
RetrieverInput = str
```

检索器的输入类型为字符串。

### RetrieverOutput

```python
RetrieverOutput = list[Document]
```

检索器的输出类型为 Document 对象列表。

### RetrieverLike

```python
RetrieverLike = Runnable[RetrieverInput, RetrieverOutput]
```

类似检索器的类型，接受字符串输入，输出 Document 列表。

### RetrieverOutputLike

```python
RetrieverOutputLike = Runnable[Any, RetrieverOutput]
```

类似检索器输出的类型，接受任意输入，输出 Document 列表。

## 属性

### tags

```python
tags: list[str] | None = None
```

与检索器关联的可选标签列表。

这些标签将与每次调用此检索器相关联，并作为参数传递给 `callbacks` 中定义的处理器。可用于标识检索器的特定实例及其用例。

### metadata

```python
metadata: dict[str, Any] | None = None
```

与检索器关联的可选元数据。

此元数据将与每次调用此检索器相关联，并作为参数传递给 `callbacks` 中定义的处理器。可用于标识检索器的特定实例及其用例。

## LangSmith 追踪参数

### LangSmithRetrieverParams

用于 LangSmith 追踪的标准参数。

| 参数 | 类型 | 描述 |
|------|------|------|
| `ls_retriever_name` | `str` | 检索器名称 |
| `ls_vector_store_provider` | `str \| None` | 向量存储提供程序 |
| `ls_embedding_provider` | `str \| None` | 嵌入提供程序 |
| `ls_embedding_model` | `str \| None` | 嵌入模型 |

## 内置检索器

### MergerRetriever

合并多个检索器结果的检索器。

```python
from langchain_classic.retrievers import MergerRetriever

retriever = MergerRetriever(
    retrievers=[retriever1, retriever2, retriever3]
)
```

**属性：**
- `retrievers`：`list[BaseRetriever]` - 要合并的检索器列表

### TimeWeightedVectorStoreRetriever

时间加权向量存储检索器，结合嵌入相似度和时效性来检索值。

```python
from langchain_classic.retrievers import TimeWeightedVectorStoreRetriever

retriever = TimeWeightedVectorStoreRetriever(
    vectorstore=vectorstore,
    decay_rate=0.01,
    k=4
)
```

**属性：**
- `vectorstore`：`VectorStore` - 用于存储文档和确定显著性的向量存储
- `search_kwargs`：`dict` - 传递给向量存储相似度搜索的关键字参数
- `memory_stream`：`list[Document]` - 要搜索的文档记忆流
- `decay_rate`：`float` - 指数衰减因子，计算公式为 `(1.0-decay_rate)**(hrs_passed)`
- `k`：`int` - 每次调用检索的最大文档数
- `other_score_keys`：`list[str]` - 元数据中要考虑的其他分数键，例如 'importance'
- `default_salience`：`float \| None` - 分配给未从向量存储检索到的记忆的显著性

### create_history_aware_retriever

创建考虑对话历史的检索器链。

```python
from langchain_classic.chains import create_history_aware_retriever
from langchain_openai import ChatOpenAI
from langchain_classic import hub

rephrase_prompt = hub.pull("langchain-ai/chat-langchain-rephrase")
model = ChatOpenAI()
retriever = ...  # 你的检索器

chat_retriever_chain = create_history_aware_retriever(
    model, retriever, rephrase_prompt
)

# 使用
chain.invoke({"input": "...", "chat_history": [...]})
```

**参数：**
- `llm`：用于根据对话历史生成搜索词的语言模型
- `retriever`：接受字符串输入并输出 `Document` 对象列表的 `RetrieverLike` 对象
- `prompt`：用于为检索器生成搜索查询的提示模板

**返回：**
LCEL Runnable。可运行对象的输入必须包含 `input`，如果有对话历史，应以 `chat_history` 形式传入。`Runnable` 输出为 `Document` 对象列表。

**工作原理：**
- 如果没有 `chat_history`，则直接将 `input` 传递给检索器
- 如果有 `chat_history`，则使用提示和 LLM 生成搜索查询，然后将该搜索查询传递给检索器

## 使用示例

### 基本使用

```python
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

# 创建自定义检索器
class MyRetriever(BaseRetriever):
    docs: list[Document]
    k: int = 5

    def _get_relevant_documents(self, query: str) -> list[Document]:
        # 实现检索逻辑
        return self.docs[:self.k]

# 使用检索器
retriever = MyRetriever(docs=[...])
documents = retriever.invoke("查询字符串")
```

### 异步使用

```python
# 异步调用
documents = await retriever.ainvoke("查询字符串")

# 批量处理
documents = await retriever.abatch(["查询1", "查询2", "查询3"])
```

### 与向量存储结合使用

```python
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

# 创建向量存储
embeddings = OpenAIEmbeddings()
vectorstore = InMemoryVectorStore.from_documents(
    documents=docs,
    embedding=embeddings
)

# 获取检索器
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# 使用检索器
results = retriever.invoke("查询")
```

## 最佳实践

1. **选择合适的检索器类型**：根据应用场景选择基础检索器、时间加权检索器或合并检索器
2. **设置合适的 k 值**：根据应用需求调整返回文档数量
3. **使用异步方法**：在高并发场景下使用 `ainvoke` 和 `abatch` 提高性能
4. **添加回调**：利用 `tags` 和 `metadata` 进行追踪和调试
5. **考虑对话历史**：在对话应用中使用 `create_history_aware_retriever` 处理上下文

## 相关链接

- [Vector Stores](../05-vector-stores.md)
- [Document Loaders](../03-document-loaders.md)
- [Text Splitters](../04-text-splitters.md)
- [LangSmith 追踪](https://docs.smith.langchain.com/)
