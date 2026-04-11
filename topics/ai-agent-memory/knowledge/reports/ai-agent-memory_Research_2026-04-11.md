# AI Agent 记忆系统 研究日报

**日期**: 2026-04-11
**更新时间**: 10:04:00

---

## 📊 研究概览

### 搜索关键词
- AI Agent memory system 2025 2026 latest research
- MemoryOS EMNLP 2025 AI agent memory
- Claude Code 7 layers memory dreaming system

---

## 🔬 核心发现

### 1. Claude Code 七层记忆架构（重磅泄露）

Anthropic Claude Code 源码在2026年3月31日意外泄露（约50万行TypeScript代码），暴露了其精心设计的7层记忆架构。该架构从亚毫秒级token剪枝延伸至数小时后台梦境巩固，核心原则：**以极低成本的浅层拦截，规避算力高昂的深层压缩**。

#### 七层架构一览

| 层级 | 名称 | 成本 | 触发时机 |
|------|------|------|----------|
| L1 | 工具结果存储 | $ (磁盘I/O) | 每个工具结果 |
| L2 | 微压缩 | 极低 (~1ms) | 每个轮次 |
| L3 | 会话记忆压缩 | 免费 | 轮次结束 |
| L4 | 全量压缩 | 完整API调用 (~30秒) | 上下文压力 |
| L5 | 自动记忆提取 | $$$ (~6秒) | 上下文压力 |
| L6 | 梦境系统 | 免费后台 | 每24h+会话 |
| L7 | 跨Agent通信 | 变化 | 按需 |

#### 关键技术亮点

**L1 - 工具结果存储**
- 超阈值结果写入磁盘 `tool-results/<uuid>.txt`，上下文仅保留约2KB预览
- `ContentReplacementState` 冻结决策，确保Prompt前缀字节级一致
- 通过 GrowthBook `tengu_satin_quoll` 特性标志远程调优阈值

**L2 - 微压缩（三种机制）**
- **基于时间**：闲置60分钟+自动触发，清理旧工具结果（保留最近5个）
- **缓存编辑API**：使用 `cache_edits` 机制从服务端缓存删除，不使本地提示词缓存失效
- **API级上下文管理**：通过 `context_management` API参数 `clear_tool_uses_20250919` 直接下放给服务端

**L3 - 会话记忆**
- 持续维护结构化markdown模板文件，按9个区块分类记录会话状态
- 触发提取：token增长超阈值 + 工具调用次数达标 或 最近无工具调用
- 压缩时直接复用现成摘要，**省去昂贵的摘要API调用**

**L4 - 全量压缩**
- 调用专用摘要Agent，生成9大区块结构化摘要
- 两阶段输出：`<scratchpad>` 草稿 + `<summary>` 最终摘要（草稿被剥离不进入上下文）
- 熔断保护：连续3次失败则禁用自动压缩（曾有单会话最高3272次失败死循环的教训）

**L6 - 梦境系统（Dreaming）**
- 在系统闲置期间静默回溯对话转录，执行跨会话记忆巩固
- 相当于AI在"睡眠"时整理和强化记忆

**L7 - 跨Agent通信**
- 支持派生子Agent、消息传递、记忆共享和缓存共享

---

### 2. MemoryOS（EMNLP 2025 Oral）

来自BAI-LAB的开源项目，为个性化AI Agent提供记忆操作系统。灵感来自操作系统内存管理，采用**四模块分层存储架构**：

- **Storage（存储）** - 分层存储架构
- **Updating（更新）** - 记忆更新机制
- **Retrieval（检索）** - 快速检索访问
- **Generation（生成）** - 生成式记忆

实验结果显示，在个性化任务中 F1 提升 49.11%，BLEU-1 提升 46.18%。提供 MCP 协议集成和 ChromaDB 后端支持。

---

### 3. 主流框架记忆系统对比

| 框架 | 短期记忆 | 长期记忆 | 上下文策略 |
|------|----------|----------|------------|
| Google ADK | 会话级 | 向量存储 | 缩减/卸载 |
| LangChain | 消息历史 | Memory Buffer | 自动摘要 |
| AgentScope | 双层记忆 | 外部向量库 | 隔离策略 |

---

### 4. 2026年最新进展（综合分析）

- **《Memory in the Age of AI Agents》** - 多所顶尖大学联合综述，提出"形态-功能-动力学"三维框架，分析200+篇论文
- **三大记忆形态**：Token-level / Parametric / Latent
- **七大前沿方向**：生成式记忆、自动管理、跨模态记忆等
- **MemoryOS** - EMNLP 2025 Oral，开源可复现

---

## 📈 技术趋势分析

### 记忆架构设计三大范式

1. **分层成本拦截**：Claude Code的7层设计代表当前最优实践——浅层拦截高频低成本，深层触发低频高成本
2. **生成式记忆**：从被动存储走向主动生成——MemoryOS的Generation模块是标志性方向
3. **梦境巩固**：跨会话、异步的后台记忆整合，模仿人类睡眠期间的记忆巩固机制

### Token优化仍然是核心痛点

- 上下文窗口限制（200K~1M）与无限输入的矛盾持续存在
- 缓存复用（prompt caching）+ 智能压缩是关键解法
- API级上下文管理正从客户端向服务端迁移

---

## 🔗 参考资源

- [Claude Code源码泄露 - CSDN](https://blog.csdn.net/c9Yv2cf9I06K2A9E/article/details/159739018)
- [MemoryOS - GitHub](https://github.com/BAI-LAB/MemoryOS)
- [AI Agent记忆系统全解析 - CSDN](https://blog.csdn.net/CSDN_430422/article/details/156614388)
- [Awesome-Agent-Memory - GitHub](https://github.com/TeleAI-UAGI/awesome-agent-memory)

---

*报告生成时间: 2026-04-11 10:04:00*
