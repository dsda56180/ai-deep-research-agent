# AI Agent 记忆系统 — 每日深度研究 2026-04-23

## 核心发现（5 条）

1. **AgeMem（Agentic Memory）** — 统一长短期记忆管理框架（arXiv:2601.01885），将记忆操作封装为工具（ADD/UPDATE/DELETE/RETRIEVE/SUMMARY/FILTER），通过三阶段渐进式RL+分步GRPO训练Agent自主决策"记什么、何时记"。五大长程基准（ALFWorld, SciWorld, HotpotQA等）全面超越Mem0/LangMem/A-Mem基线，上下文利用率提升5.1%。

2. **TiMem 时序分层记忆树** — 基于认知神经科学CLS理论，构建5层自动归纳时序树（L1原始→L2会话摘要→L3日总结→L4周总结→L5用户画像），复杂度感知召回机制，LoCoMo 75.30%/LongMemEval-S 76.88%，token消耗减少52%。

3. **2026开源记忆框架全景横评** — Mem0（扁平KV，快速原型但无时序）/ Zep（图谱+时间戳，中期时序好）/ LangMem（双层，LangChain生态锁定）/ MemOS（图谱OS，部署复杂）/ TiMem（五层树，长期最优）。核心选型逻辑：对话周期越长→TiMem；场景越简单→Mem0。

4. **MemDLM** — 港中文提出记忆增强扩散语言模型，双层优化框架（内循环快速适应+外循环参数更新），将生成轨迹经验存储于参数空间，比纯词汇表示更稳定。

5. **Agent Memory四型分类法** — Short-Term/Long-Term/External/Vector，对应认知科学的感觉记忆→短期记忆→长期记忆，Agent智能=短期记忆高效利用+长期记忆精准检索。

## 知识图谱变化
- 新概念：3 个（AgeMem, TiMem, MemDLM）
- 新关系：8 条（AgeMem→工具化记忆管理, TiMem→CLS理论, MemDLM→双层优化）
- 已验证方法：2 个（三阶段RL训练, 五层时序归纳树）

## 同步状态
- IMA: ⏳ 待同步
- 飞书: ❌ HTTP 400（已知问题）
- Obsidian: ⏳ 待同步

## 学习记录
- RL训练记忆工具使用比纯SFT更有效：RL后Agent调用ADD/UPDATE频率大幅增加
- 时序归纳是记忆系统的关键差异因素：无时序→Mem0弱，显式时序树→TiMem强
- 统一框架（STM+LTM一体管理）优于分离式管理（启发式规则+外部控制器）

## 参考来源
- AgeMem: https://arxiv.org/abs/2601.01885
- TiMem: https://arxiv.org/abs/2601.02845
- 2026框架横评: https://blog.csdn.net/RMSXY/article/details/159800698
- MemDLM: https://so.html5.qq.com/page/real/search_news?docid=70000021_11969cb9e3f80552
- Agent Memory四型: https://blog.csdn.net/yangzhihua/article/details/160419045
