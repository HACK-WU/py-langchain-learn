# LangChain 学习计划

> 基于 LangChain 官方文档 00-11 及源码，分 4 个阶段由浅入深，每阶段配备实战 Demo

---

## 整体路线

```
阶段一：基础入门（00-04）──────→ 阶段二：核心能力（05-08）
                                        │
                                        ▼
阶段四：综合实战（跨文档融合）←─── 阶段三：高级编排（09-11）
```

| 阶段 | 对应文档 | 核心主题 | 预计时间 | Demo |
|------|---------|---------|---------|------|
| 一 | 00-04 | 安装、Agent、模型、消息 | 2-3 天 | 多模型翻译助手 |
| 二 | 05-08 | 工具、记忆、流式、结构化输出 | 3-5 天 | 个人记账 Agent |
| 三 | 09-11 | 中间件概述、内置中间件、自定义中间件 | 3-5 天 | 安全客服 Agent |
| 四 | 融合 | 全部知识点综合应用 | 5-7 天 | 智能研究助手 |

---

## 源码阅读路线

```
langchain_core/messages/          ← 消息体系（最基础）
    ↓
langchain_core/language_models/  ← 模型抽象（invoke/stream/batch）
    ↓
langchain_core/tools/            ← 工具抽象（@tool / ToolRuntime）
    ↓
langchain/agents/                 ← Agent 核心（create_agent / ReAct 循环）
    ↓
langchain/agents/middleware/      ← 中间件体系（钩子 / 内置 / 自定义）
    ↓
langchain_core/runnables/base.py  ← 执行引擎（Runnable 底层，最硬核）
```

---

## 详细计划

- [阶段一：基础入门](./01-basics.md)
- [阶段二：核心能力](./02-core-features.md)
- [阶段三：高级编排](./03-middleware.md)
- [阶段四：综合实战](./04-integration.md)

---

## 学习方法建议

1. **先跑通 Demo，再读源码** — 动手感受比纸上谈兵更有效
2. **配置 LangSmith** — 追踪 Agent 每一步执行，可视化理解内部流转
3. **源码对照阅读** — Demo 中用到的 API，去源码中找到对应实现，理解其设计意图
4. **修改源码做实验** — 在理解基础上尝试修改行为，加深印象
5. **每阶段写总结** — 记录关键概念、踩坑点、源码阅读心得
