# AI Deep Research Agent 改造清单

## P0 已完成：安全与稳定性

- [x] 外部 URL 抓取增加协议校验，仅允许 `http/https`
- [x] 阻断私网、保留地址、回环地址与元数据服务地址访问
- [x] 限制远程响应体大小，避免异常大内容拉取
- [x] arXiv 抓取复用安全抓取边界
- [x] URL 导入改为统一安全抓取入口

## P1 已完成：图谱查询与导航能力

- [x] 增加统一图谱查询层，支持按语义相关性排序实体
- [x] 增加 BFS/DFS 图谱导航查询
- [x] 增加邻居查询接口
- [x] 增加社区详情查询接口
- [x] 增强最短路径结果，返回路径段关系、状态与置信度
- [x] 增强图谱统计接口，输出实体类型、层级、置信状态与平均加权度
- [x] 增强 query-time 投影，融合种子节点、图遍历与预算裁剪
- [x] Lean Context 接入导航模式与深度配置

## P1 已完成：图谱分析能力

- [x] 社区检测从简单连通分量升级为加权标签传播分区
- [x] 超大社区支持二次拆分，降低单社区失真
- [x] 社区摘要加入凝聚度指标
- [x] 增加 God Nodes 分析，识别桥接性核心节点
- [x] 增加 Surprising Connections 分析，识别跨社区、跨类型、跨层级连接
- [x] 图谱报告接入新的统计、核心节点与意外连接结果
- [x] 社区摘要节点写入凝聚度与覆盖信息

## P2 已完成：导出、评估与可观测性

- [x] 增加 GraphML 导出
- [x] 增加 Markdown Wiki 导出
- [x] 增加图谱上下文压缩 Benchmark
- [x] 增加 watch 轮询监控，支持目录变化后自动增量刷新图谱

## P2 已完成：CLI 可落地入口

- [x] `stats` 输出结构化统计结果
- [x] `neighbors` 查看节点邻居
- [x] `community` 查看社区详情
- [x] `navigate` 执行 BFS/DFS 导航查询
- [x] `god-nodes` 输出核心桥接节点
- [x] `surprising` 输出意外连接
- [x] `benchmark` 评估上下文压缩收益
- [x] `export --format graphml|wiki` 导出图谱
- [x] `watch` 监控目录并自动刷新图谱
- [x] `project` 新增导航模式与深度参数

## P2 已完成：统一入口与跨主题能力

- [x] `research_agent.py` 接入统一 `graph` 入口
- [x] `research_agent.py` 接入统一 `global` 入口
- [x] `deep_research.py` 接入统一 `graph` 入口
- [x] `deep_research.py` 接入统一 `global` 入口
- [x] `global_graph.py` 升级为基于新图谱模型的跨主题统计中心
- [x] `global_graph.py` 增加按主题统计接口
- [x] `global_graph.py` 增加跨主题 benchmark 汇总接口
- [x] 研究进度展示改为复用新的图谱统计结果

## 本轮改造结果

- 本轮已完成所有仓库内可直接落地、无需新增外部基础设施的核心改造项
- 改造覆盖安全边界、图谱查询、图谱分析、导出、评估、监控、上下文投影、统一入口与跨主题汇总
- 已完成编译检查、关键命令回归、完整 evolve 流程验证与跨主题入口验证
