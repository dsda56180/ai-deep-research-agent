---
name: ai-deep-research-agent
version: 3.0
slug: ai-deep-research-agent
description: |
  深度研究 Agent v3.0 — 自我进化版
  
  结合 self-improving-agent 的自学习能力，实现：
  - 论文搜索与抓取
  - 深度分析与报告生成
  - 知识图谱自动进化
  - 研究方法论持续完善
  - 知识缺口动态追踪
  - IMA知识库自动同步
  - 自我反思与持续改进
  
  触发词：「深度研究」「研究进度」「知识图谱」「方法论」「知识缺口」「学习」
metadata:
  openclaw:
    emoji: "🔬"
    requires:
      skills: ["self-improving"]
    configPaths: ["~/.ai-research/"]
  security:
    credentials_usage: |
      使用 ima-skill 的 get-token.ps1 获取 IMA 凭证
---
# AI Deep Research Agent — 自我进化版

## 核心能力

### 研究系统
```
搜索 → 筛选 → 分析 → 进化 → 反思 → 同步
```

### 自进化机制（继承 self-improving-agent）

**学习信号** → 自动记录：
- 用户纠正："这个分析方法不对..."
- 成功模式："这个框架分析效果很好"
- 失败模式："关键词组合没有找到相关论文"
- 自我发现："下次应该先分析方法论再搜索"

**分层存储**：
| 层级 | 位置 | 内容 |
|------|------|------|
| HOT | `.learnings/memory.md` | 当前最佳实践 |
| WARM | `.learnings/methods/` | 研究方法论库 |
| WARM | `.learnings/patterns/` | 成功模式库 |
| COLD | `.learnings/archive/` | 过时方法 |

## 使用方式

### 基础研究
```
深度研究 AI Agent 记忆系统
```

### 查看学习进度
```
研究学习方法
```

### 查看最佳实践
```
研究最佳实践
```

### 重置学习（谨慎）
```
重置研究学习方法
```

## 自进化流程

```
每天 10:00 自动执行
        ↓
搜索论文（使用已学习方法）
        ↓
发现新论文
        ↓
分析论文
        ↓
自我反思：
  - 搜索策略是否有效？
  - 分析框架是否完整？
  - 有没有遗漏的信息？
        ↓
记录学习：
  - 成功：记录为最佳实践
  - 失败：记录为待改进
        ↓
更新知识图谱
        ↓
同步到 IMA
        ↓
晋升/降级学习方法
```

## 学习记录示例

### memory.md（HOT）
```markdown
# 研究最佳实践（自动更新）

## 搜索策略
- 先用广泛关键词搜索，再用精确关键词筛选
- 同时搜索 arXiv 和 Google Scholar
- 检查引用关系找到核心论文

## 分析框架
- 必须包含：方法、创新、实验、局限
- 对比至少 2 个基准方法
- 提取可复现代码片段

## 避免模式（来自失败）
- 不要只看摘要就下结论
- 不要忽略论文的 limitations 章节
```

### corrections.md
```markdown
# 研究纠正记录

## 2026-04-07
CONTEXT: 分析 Zep 论文
REFLECTION: 只看了摘要，没有抓取全文，遗漏了关键实验细节
LESSON: 必须抓取论文全文进行深度分析

## 2026-04-07
CONTEXT: 搜索 "memory agent"
REFLECTION: 关键词太宽泛，找到 1000+ 篇无关论文
LESSON: 使用更精确的组合关键词，如 "agent memory architecture LLM"
```

## 学习晋升规则

| 模式 | 晋升条件 | 存储位置 |
|------|----------|----------|
| 成功的研究方法 | 使用 3 次 + 效果好 | memory.md (HOT) |
| 项目特定方法 | 项目内重复使用 | .learnings/projects/ |
| 过时的方法 | 30 天未使用 | archive/ |

## 常见陷阱

| 陷阱 | 问题 | 正确做法 |
|------|------|----------|
| 学习太快 | 从单次经验过度推广 | 等 3 次验证再确认 |
| 不学失败 | 只记录成功，忽略失败 | 失败是重要学习信号 |
| 不反思 | 完成任务不评估质量 | 每次完成后自评 |
| 存储混乱 | 不分层，全放 HOT | 遵循 HOT/WARM/COLD |

## 与 self-improving-agent 的集成

本 skill 继承 `self-improving` skill 的自学习机制：

1. **共享学习目录**：`~/.self-improving/` 和 `~/.ai-research/`
2. **统一晋升规则**：相同的 3 次验证机制
3. **跨域学习**：研究方法可被 self-improving 的其他 skill 复用
4. **心跳维护**：在 heartbeat 中检查学习方法有效性

## CLI 命令

```bash
# 执行完整进化流程
python evolution.py evolve --topic "AI Agent 记忆系统"

# 查看学习方法
python evolution.py learn --show

# 记录新的学习方法
python evolution.py learn --add "新方法描述"

# 查看纠正记录
python evolution.py corrections

# 查看知识图谱摘要
python evolution.py graph --topic "AI Agent 记忆系统" --summary

# 晋升/降级学习方法
python evolution.py promote --pattern "搜索策略X"
python evolution.py demote --pattern "过时方法Y"
```

## 文件结构

```
ai-deep-research-agent/
├── SKILL.md                           # 本文件
├── scripts/
│   ├── evolution.py                   # 主进化脚本
│   ├── self_learning.py               # 自学习模块
│   ├── knowledge_evolution_v2.py      # 知识进化
│   └── ima_knowledge_solidifier.py    # IMA同步
├── .learnings/
│   ├── memory.md                      # HOT: 最佳实践
│   ├── corrections.md                 # 纠正记录
│   ├── methods/                       # WARM: 研究方法论
│   ├── patterns/                      # WARM: 成功模式
│   └── archive/                       # COLD: 过时方法
├── knowledge/
│   ├── graphs/                        # 知识图谱
│   └── reports/                       # 研究报告
└── config/
    └── topics.yaml                    # 研究主题配置
```