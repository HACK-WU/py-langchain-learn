# 长期记忆 (Long-term memory)

长期记忆允许 LangChain 代理在多次对话和会话之间存储和回忆数据。与短期记忆（仅存储当前对话的上下文）不同，长期记忆可以持久化存储用户偏好、历史事实和其他重要信息，以便在未来的交互中使用。

## 概述

LangChain 提供了多种方式来实现长期记忆：

1. **向量存储记忆 (Vector Store Memory)** - 使用向量数据库存储和检索相关记忆
2. **实体记忆 (Entity Memory)** - 跟踪对话中的实体及其属性
3. **知识图谱记忆 (Knowledge Graph Memory)** - 使用知识图谱存储实体关系
4. **自定义记忆存储 (Custom Memory Stores)** - 使用外部数据库或存储系统

## 安装依赖

```bash
pip install langchain langchain-community
```

## 向量存储记忆

向量存储记忆使用向量数据库来存储对话历史，并基于语义相似性检索相关记忆。

### 基本用法

```python
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

# 创建向量存储
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(embedding_function=embeddings, persist_directory="./memory_db")

# 创建记忆组件
retriever = vectorstore.as_retriever(search_kwargs=dict(k=5))
memory = VectorStoreRetrieverMemory(retriever=retriever)

# 存储一些记忆
memory.save_context(
    {"input": "我喜欢吃意大利菜"},
    {"output": "太好了！意大利菜非常美味。"}
)
memory.save_context(
    {"input": "我对海鲜过敏"},
    {"output": "收到，我会记住您对海鲜过敏。"}
)

# 在对话链中使用
llm = ChatOpenAI()
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# 测试记忆检索
response = conversation.predict(input="推荐一些适合我的餐厅")
print(response)
```

### 带记忆的对话链

```python
from langchain.memory import VectorStoreRetrieverMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# 定义提示模板
template = """以下是人类与 AI 的对话。AI 健谈，并根据上下文提供具体细节。

相关历史信息：
{history}

人类：{input}
AI："""

prompt = PromptTemplate(
    input_variables=["history", "input"],
    template=template
)

# 创建带记忆的链
conversation = LLMChain(
    llm=llm,
    prompt=prompt,
    memory=memory,
    verbose=True
)

# 运行对话
response = conversation.predict(input="我今天应该吃什么？")
print(response)
```

## 实体记忆

实体记忆跟踪对话中提到的实体（如人、地点、事物）及其属性。

```python
from langchain.memory import EntityMemory
from langchain.llms import OpenAI

# 创建实体记忆
llm = OpenAI(temperature=0)
memory = EntityMemory(llm=llm)

# 保存上下文
memory.save_context(
    {"input": "我叫张三，是一名软件工程师"},
    {"output": "很高兴认识你，张三！软件工程师是个很有前景的职业。"}
)

memory.save_context(
    {"input": "我住在上海"},
    {"output": "上海是个很棒的城市！"}
)

# 查看存储的实体
print(memory.entity_store.store)
# 输出示例：{'张三': '软件工程师，住在上海'}
```

## 知识图谱记忆

知识图谱记忆使用图结构来存储实体之间的关系。

```python
from langchain.memory import ConversationKGMemory
from langchain.llms import OpenAI

# 创建知识图谱记忆
llm = OpenAI(temperature=0)
memory = ConversationKGMemory(llm=llm)

# 保存对话上下文
memory.save_context(
    {"input": "张三和李四是朋友"},
    {"output": "明白了，张三和李四是朋友关系。"}
)

memory.save_context(
    {"input": "李四在北京工作"},
    {"output": "收到，李四的工作地点是北京。"}
)

# 获取知识图谱
print(memory.kg)
```

## 使用外部存储

对于生产环境，建议使用外部数据库来持久化存储记忆。

### Redis 存储

```python
from langchain.memory import RedisChatMessageHistory
from langchain.memory import ConversationBufferMemory

# 使用 Redis 存储对话历史
message_history = RedisChatMessageHistory(
    session_id="user_123",
    url="redis://localhost:6379/0"
)

memory = ConversationBufferMemory(
    chat_memory=message_history,
    return_messages=True
)

# 在对话中使用
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)
```

### PostgreSQL 存储

```python
from langchain.memory import PostgresChatMessageHistory

# 使用 PostgreSQL 存储对话历史
message_history = PostgresChatMessageHistory(
    session_id="user_123",
    connection_string="postgresql://user:password@localhost/dbname"
)

memory = ConversationBufferMemory(
    chat_memory=message_history,
    return_messages=True
)
```

## 自定义记忆类

你可以创建自定义的记忆类来满足特定需求。

```python
from langchain.memory import BaseMemory
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class CustomMemory(BaseMemory, BaseModel):
    """自定义记忆类示例"""

    # 存储记忆的字典
    memories: Dict[str, Any] = {}

    # 记忆键
    memory_key: str = "history"

    @property
    def memory_variables(self) -> List[str]:
        """返回记忆变量列表"""
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载记忆变量"""
        return {self.memory_key: self.memories}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """保存上下文"""
        # 提取输入和输出
        user_input = inputs.get("input", "")
        ai_output = outputs.get("output", "")

        # 自定义存储逻辑
        self.memories[user_input] = ai_output

    def clear(self) -> None:
        """清除记忆"""
        self.memories = {}

# 使用自定义记忆
memory = CustomMemory()
memory.save_context(
    {"input": "你好"},
    {"output": "你好！有什么可以帮助你的？"}
)

print(memory.load_memory_variables({}))
```

## 记忆组合

你可以组合多种记忆类型以获得更好的效果。

```python
from langchain.memory import CombinedMemory

# 创建多种记忆
buffer_memory = ConversationBufferMemory()
entity_memory = EntityMemory(llm=llm)

# 组合记忆
combined_memory = CombinedMemory(
    memories=[buffer_memory, entity_memory]
)

# 在对话链中使用
conversation = ConversationChain(
    llm=llm,
    memory=combined_memory,
    verbose=True
)
```

## 最佳实践

### 1. 选择合适的记忆类型

| 场景 | 推荐记忆类型 |
|------|-------------|
| 简单对话历史 | ConversationBufferMemory |
| 长对话（控制 token 数） | ConversationBufferWindowMemory |
| 基于相似性检索 | VectorStoreRetrieverMemory |
| 实体跟踪 | EntityMemory |
| 复杂关系 | ConversationKGMemory |

### 2. 记忆清理策略

```python
# 设置最大 token 限制
from langchain.memory import ConversationTokenBufferMemory

memory = ConversationTokenBufferMemory(
    llm=llm,
    max_token_limit=1000  # 限制记忆 token 数
)

# 设置窗口大小
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(
    k=5  # 只保留最近 5 轮对话
)
```

### 3. 持久化存储

```python
# 定期保存向量存储
vectorstore.persist()

# 使用持久化存储路径
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory="./memory_db",  # 持久化目录
    collection_name="user_memories"
)
```

## 完整示例

以下是一个完整的长期记忆实现示例：

```python
import os
from langchain.memory import VectorStoreRetrieverMemory, ConversationBufferMemory
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

# 设置 API 密钥
os.environ["OPENAI_API_KEY"] = "your-api-key"

class LongTermMemorySystem:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.embeddings = OpenAIEmbeddings()

        # 创建用户专属的向量存储
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=f"./memory_db/{user_id}",
            collection_name=f"user_{user_id}_memories"
        )

        # 创建长期记忆
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 3}
        )
        self.long_term_memory = VectorStoreRetrieverMemory(
            retriever=retriever,
            memory_key="long_term_history"
        )

        # 创建短期记忆
        self.short_term_memory = ConversationBufferMemory(
            memory_key="short_term_history",
            return_messages=True
        )

        # 创建 LLM
        self.llm = ChatOpenAI(temperature=0.7)

        # 创建提示模板
        template = """你是一个有帮助的 AI 助手。你可以访问以下记忆：

【长期记忆】
{long_term_history}

【近期对话】
{short_term_history}

人类：{input}
AI："""

        self.prompt = PromptTemplate(
            input_variables=["long_term_history", "short_term_history", "input"],
            template=template
        )

        # 创建对话链
        self.conversation = ConversationChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.long_term_memory,  # 主记忆
            verbose=True
        )

    def chat(self, user_input: str) -> str:
        """处理用户输入并返回回复"""
        # 保存到短期记忆
        self.short_term_memory.save_context(
            {"input": user_input},
            {"output": "待生成"}
        )

        # 获取回复
        response = self.conversation.predict(input=user_input)

        # 更新短期记忆中的输出
        messages = self.short_term_memory.load_memory_variables({})

        return response

    def add_long_term_memory(self, fact: str):
        """手动添加长期记忆"""
        self.long_term_memory.save_context(
            {"input": fact},
            {"output": "已记录"}
        )
        self.vectorstore.persist()

# 使用示例
if __name__ == "__main__":
    # 创建记忆系统
    memory_system = LongTermMemorySystem(user_id="user_001")

    # 添加一些长期记忆
    memory_system.add_long_term_memory("用户喜欢科幻电影")
    memory_system.add_long_term_memory("用户是软件工程师")

    # 开始对话
    while True:
        user_input = input("你: ")
        if user_input.lower() in ["exit", "quit", "退出"]:
            break

        response = memory_system.chat(user_input)
        print(f"AI: {response}")
```

## 总结

长期记忆是构建智能对话系统的关键组件。通过合理选择记忆类型和存储策略，你可以创建能够记住用户信息、偏好和历史上下文的智能代理。主要要点：

1. **短期记忆**：用于当前对话上下文，如 `ConversationBufferMemory`
2. **长期记忆**：用于跨会话持久化，如 `VectorStoreRetrieverMemory`
3. **实体记忆**：用于跟踪对话中的实体信息
4. **外部存储**：使用 Redis、PostgreSQL 等实现真正的持久化
5. **组合使用**：可以组合多种记忆类型获得最佳效果
