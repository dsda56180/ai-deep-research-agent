# 研究方法论学习记录

## 2026-04-02 首次部署

### 研究流程设计

```
采集 → 筛选 → 深度解读 → 结构化 → 关联 → 入库
```

### 核心原则

1. **质量优先**：每篇论文必须深度分析，不接受浅层摘要
2. **知识关联**：新发现必须与已有知识对比，标注补充/验证/矛盾
3. **持续进化**：每次研究基于前序积累，形成知识脉络
4. **可追溯**：所有结论必须有文献引用

### Oh My OpenCode Agent 分工

| Agent | 角色 | 任务 |
|-------|------|------|
| Sisyphus | 主编排器 | 任务拆分、进度管理 |
| Explore | 信息采集 | 搜索论文、筛选内容 |
| Hephaestus | 内容抓取 | 抓取全文、提取数据 |
| Metis | 深度分析 | 方法分析、创新评估 |
| Librarian | 知识管理 | 知识整理、IMA同步 |

## 2026-04-03 研究方法论更新

### 多 Agent 并行采集策略

```
Explore Agent → 搜索论文/技术博客/社交媒体
Hephaestus Agent → 抓取全文/提取结构化数据
Metis Agent → 深度分析/创新点评估
Librarian Agent → 知识整理/IMA同步
```

### 研究质量控制

1. **来源可信度**：优先 arXiv、顶级会议、官方文档
2. **时效性**：关注 2024-2026 年的最新进展
3. **交叉验证**：多个来源确认同一信息
4. **批判性思维**：记录优缺点，避免盲目接受

### 知识图谱维护

- 每次研究后更新概念和关系
- 标注知识缺口和待验证假设
- 追踪技术趋势和演进方向

---

*持续更新中...*
## 2026-04-09 新增洞察

- [Diagnosing Retrieval vs. Utilization...] 核心方法：We introduce a diagnostic framework that analyzes how performance differences manifest across write strategies, retrieval methods, and memory utilization beh...

## 2026-04-09 新增洞察

- [Diagnosing Retrieval vs. Utilization...] 创新点：We introduce a diagnostic framework that analyzes how performance differences manifest across write strategies, retrieval methods, and memory utilization beh...

## 2026-04-09 新增洞察

- [Diagnosing Retrieval vs. Utilization...] 创新点：Raw chunked storage, which requires zero LLM calls, matches or outperforms expensive lossy alternatives, suggesting that current memory pipelines may discard...

## 2026-04-13 新增洞察

- [Semantic Rate-Distortion for Bounded...] 核心方法：When two agents of different computational capacities interact with the same environment, they need not compress a common semantic alphabet differently; they...

## 2026-04-13 新增洞察

- [Multi-Agent Decision-Focused Learning...] 核心方法：While recent methods optimize messages for intermediate objectives (e.g., reconstruction accuracy or mutual information), rather than decision quality, we in...

## 2026-04-13 新增洞察

- [Multi-Agent Decision-Focused Learning...] 创新点：While recent methods optimize messages for intermediate objectives (e.g., reconstruction accuracy or mutual information), rather than decision quality, we in...

## 2026-04-13 新增洞察

- [Wireless Communication Enhanced Value...] 核心方法：Cooperation in multi-agent reinforcement learning (MARL) benefits from inter-agent communication, yet most approaches assume idealized channels and existing...

## 2026-04-13 新增洞察

- [Wireless Communication Enhanced Value...] 创新点：We propose CLOVER, a cooperative MARL framework whose centralized value mixer is conditioned on the communication graph realized under a realistic wireless c...

## 2026-04-13 新增洞察

- [Wireless Communication Enhanced Value...] 创新点：This graph introduces a relational inductive bias into value decomposition, constraining how individual utilities are mixed based on the realized communicati...

## 2026-04-13 新增洞察

- [Every Response Counts: Quantifying Un...] 核心方法：While Large Language Model-based Multi-Agent Systems (MAS) consistently outperform single-agent systems on complex tasks, their intricate interactions introd...

## 2026-04-13 新增洞察

- [Every Response Counts: Quantifying Un...] 创新点：While Large Language Model-based Multi-Agent Systems (MAS) consistently outperform single-agent systems on complex tasks, their intricate interactions introd...

## 2026-04-13 新增洞察

- [Every Response Counts: Quantifying Un...] 创新点：To bridge this gap, we introduce MATU, a novel framework that quantifies uncertainty through tensor decomposition.

## 2026-04-13 新增洞察

- ["Theater of Mind" for LLMs: A Cogniti...] 核心方法："Theater of Mind" for LLMs: A Cognitive Architecture Based on Global Workspace Theory.

## 2026-04-13 新增洞察

- ["Theater of Mind" for LLMs: A Cogniti...] 创新点：To address this structural limitation, we propose Global Workspace Agents (GWA), a cognitive architecture inspired by Global Workspace Theory.

## 2026-04-13 新增洞察

- ["Theater of Mind" for LLMs: A Cogniti...] 创新点：Furthermore, we introduce an entropy-based intrinsic drive mechanism that mathematically quantifies semantic diversity, dynamically regulating generation tem...

## 2026-04-13 新增洞察

- [DiffuMask: Diffusion Language Model f...] 核心方法：DiffuMask: Diffusion Language Model for Token-level Prompt Pruning.

## 2026-04-13 新增洞察

- [Prompt Compression in the Wild: Measu...] 核心方法：With the wide adoption of language models for IR -- and specifically RAG systems -- the latency of the underlying LLM becomes a crucial bottleneck, since the...

## 2026-04-13 新增洞察

- [Prompt Compression in the Wild: Measu...] 创新点：We present the first systematic, large-scale study of this trade-off, with thousands of runs and 30,000 queries across several open-source LLMs and three GPU...

## 2026-04-13 新增洞察

- [Distributionally Robust Token Optimiz...] 核心方法：Large Language Models (LLMs) tend to respond correctly to prompts that align to the data they were trained and fine-tuned on.

## 2026-04-13 新增洞察

- [Distributionally Robust Token Optimiz...] 创新点：To address this problem, we propose a Distributionally Robust Token Optimization (DRTO) approach, which combines token-level Reinforcement Learning from Huma...

## 2026-04-13 新增洞察

- [Large Language Model as Token Compres...] 核心方法：Large Language Model as Token Compressor and Decompressor.

## 2026-04-13 新增洞察

- [Large Language Model as Token Compres...] 创新点：In this paper, we establish the novel insight that an off-the-shelf LLM can function as an excellent token compressor and decompressor.

## 2026-04-13 新增洞察

- [Towards Real-World Document Parsing v...] 核心方法：Document parsing has recently advanced with multimodal large language models (MLLMs) that directly map document images to structured outputs.

## 2026-04-13 新增洞察

- [Towards Real-World Document Parsing v...] 创新点：To address these challenges, we propose a data-training co-design framework for robust end-to-end document parsing.

## 2026-04-13 新增洞察

- [Towards Real-World Document Parsing v...] 创新点：A Realistic Scene Synthesis strategy constructs large-scale, structurally diverse full-page end-to-end supervision by composing layout templates with rich do...
