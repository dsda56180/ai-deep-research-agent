---
name: ai-deep-research-agent
version: 4.0
slug: ai-deep-research-agent
description: |
  深度研究 Agent v4.0 — 多题材自我进化版
  
  核心能力：
  - 多题材独立研究（每个题材独立文件夹）
  - 全局知识图谱（关联所有题材）
  - 飞书/Obsidian/IMA 多渠道同步
  - 继承 self-improving-agent 的自学习机制
  
  触发词：
  - 「深度研究 [题材]」- 创建/研究题材
  - 「研究进度 [题材]」- 查看进度
  - 「知识图谱」- 全局/题材图谱
  - 「题材列表」- 所有题材
  - 「同步到飞书/Obsidian」
metadata:
  openclaw:
    emoji: "🔬"
    requires:
      skills: ["self-improving"]
    configPaths: ["~/.ai-research/"]
    channels:
      - ima
      - feishu
      - obsidian
  security:
    credentials_usage: |
      飞书：使用 feishu-skill 的凭证
      Obsidian：使用本地 vault 路径
      IMA：使用 ima-skill 的凭证
---
# AI Deep Research Agent v4.0 — 多题材自我进化版

## 🆕 v4.0 新特性

### 1. 多题材管理
- 每个研究题材独立文件夹
- 题材间知识隔离，全局知识图谱关联
- 支持创建、切换、合并题材

### 2. 多渠道同步
| 渠道 | 格式 | 说明 |
|------|------|------|
| IMA | Markdown | 微信知识库 |
| 飞书 | Docx | 云文档协作 |
| Obsidian | Markdown | 本地知识库 |

### 3. 全局知识图谱
- 自动提取各题材核心概念
- 发现跨题材关联（如"Agent记忆"与"多智能体协调"）
- 生成跨题材洞察报告

---

## 📁 文件结构

```
ai-deep-research-agent/
├── SKILL.md                           # 本文件
├── config/
│   ├── topics.yaml                    # 题材配置
│   └── channels.yaml                  # 渠道配置
├── scripts/
│   ├── evolution.py                   # 主进化脚本
│   ├── topic_manager.py               # 题材管理器
│   ├── global_graph.py                # 全局知识图谱
│   ├── self_learning.py               # 自学习模块
│   ├── knowledge_evolution_v2.py      # 知识进化
│   ├── ima_sync.py                    # IMA 同步
│   ├── feishu_sync.py                 # 飞书同步
│   └── obsidian_sync.py               # Obsidian 同步
├── topics/                            # 各题材独立文件夹
│   ├── ai-agent-memory/               # 题材：AI Agent 记忆系统
│   │   ├── knowledge/
│   │   │   ├── graphs/               # 题材知识图谱
│   │   │   └── reports/              # 研究报告
│   │   └── .learnings/               # 题材学习方法
│   ├── multi-agent/                   # 题材：多智能体协作
│   └── llm-optimization/              # 题材：LLM 优化
├── global/                            # 全局知识
│   ├── knowledge_graph.json          # 全局知识图谱
│   ├── cross_topic_insights.md      # 跨题材洞察
│   └── concept_index.json            # 概念索引
├── .learnings/                        # 全局学习方法（HOT）
│   ├── memory.md
│   ├── corrections.md
│   └── methods/
└── exports/                           # 导出文件夹
    ├── feishu/
    └── obsidian/
```

---

## 🚀 使用方式

### 创建新题材
```
深度研究 AI Agent 记忆系统
深度研究 多智能体协作系统
```

### 查看题材列表
```
题材列表
```

### 查看题材进度
```
研究进度 AI Agent 记忆系统
```

### 查看知识图谱
```
知识图谱                        # 全局图谱
知识图谱 AI Agent 记忆系统      # 特定题材图谱
```

### 同步到飞书/Obsidian
```
同步到飞书
同步到 Obsidian
同步所有题材到飞书
```

---

## 🔄 每日进化流程

```
每天 10:00 自动执行
        ↓
【步骤 1】遍历所有启用的题材
        ↓
【步骤 2】对每个题材：
   ├─ 加载学习方法
   ├─ 搜索论文
   ├─ 深度分析
   ├─ 更新题材知识图谱
   └─ 记录学习
        ↓
【步骤 3】更新全局知识图谱
   ├─ 提取核心概念
   ├─ 发现跨题材关联
   └─ 生成跨题材洞察
        ↓
【步骤 4】多渠道同步
   ├─ IMA：所有题材报告
   ├─ 飞书：汇总文档
   └─ Obsidian：本地 vault
        ↓
【步骤 5】学习方法晋升/降级
```

---

## 📊 题材配置

### config/topics.yaml

```yaml
topics:
  - id: ai-agent-memory
    name: AI Agent 记忆系统
    keywords:
      - "AI agent memory architecture"
      - "MemGPT Mem0 Zep"
      - "vector memory RAG"
    enabled: true
    frequency: daily
    channels:
      - ima
      - feishu
      - obsidian
    
  - id: multi-agent
    name: 多智能体协作
    keywords:
      - "multi-agent coordination"
      - "agent communication protocol"
    enabled: true
    frequency: weekly
    channels:
      - feishu

channels:
  ima:
    enabled: true
    kb_id: "eImkUmYly1k-NH7Pz8e4syn4zs0UXJZufvCX5CSKvN8="
  
  feishu:
    enabled: true
    app_id: "${FEISHU_APP_ID}"
    app_secret: "${FEISHU_APP_SECRET}"
    folder_token: "fldcnXXXXXXXXXX"
  
  obsidian:
    enabled: true
    vault_path: "D:/Obsidian/MyVault"
    folder: "AI Research"
```

---

## 🧠 全局知识图谱

### 结构

```json
{
  "topics": [
    {
      "id": "ai-agent-memory",
      "name": "AI Agent 记忆系统",
      "concept_count": 28,
      "relation_count": 29,
      "last_updated": "2026-04-07"
    }
  ],
  "global_concepts": [
    {
      "id": "memory-architecture",
      "name": "记忆架构",
      "appears_in": ["ai-agent-memory", "multi-agent"],
      "definitions": {
        "ai-agent-memory": "LLM 的上下文管理机制",
        "multi-agent": "Agent 间状态共享方式"
      }
    }
  ],
  "cross_topic_relations": [
    {
      "from_topic": "ai-agent-memory",
      "from_concept": "MemGPT",
      "to_topic": "multi-agent",
      "to_concept": "agent-state-sharing",
      "relation": "enables",
      "insight": "MemGPT 的记忆管理可用于多 Agent 状态同步"
    }
  ]
}
```

---

## 🔌 渠道同步

### 飞书同步
- 自动创建云文档
- 支持文件夹结构
- 汇总报告自动生成

### Obsidian 同步
- 导出为 Markdown
- 保留双向链接
- 支持 Obsidian Graph View

### IMA 同步
- 研究报告固化
- 知识图谱更新
- 学习方法同步

---

## 📖 命令行接口

```bash
# 题材管理
python topic_manager.py list
python topic_manager.py create "AI Agent 记忆系统"
python topic_manager.py disable "ai-agent-memory"
python topic_manager.py merge "topic1" "topic2" --into "merged-topic"

# 进化执行
python evolution.py evolve --all
python evolution.py evolve --topic "ai-agent-memory"

# 知识图谱
python global_graph.py build
python global_graph.py insights
python global_graph.py export --format markdown

# 渠道同步
python feishu_sync.py sync --topic "ai-agent-memory"
python obsidian_sync.py sync --all
python ima_sync.py sync --topic "ai-agent-memory"
```

---

## 🎯 最佳实践

### 题材命名
- 使用清晰、唯一的名称
- 避免过于宽泛（"AI"、"机器学习"）
- 推荐：具体领域 + 核心问题

### 频率设置
| 题材类型 | 推荐频率 |
|----------|----------|
| 活跃研究 | daily |
| 稳定跟踪 | weekly |
| 兴趣探索 | monthly |

### 渠道选择
| 用途 | 推荐渠道 |
|------|----------|
| 个人知识库 | Obsidian |
| 团队协作 | 飞书 |
| 移动查看 | IMA |

---

## ⚠️ 注意事项

1. 题材隔离：各题材知识图谱独立，避免概念混淆
2. 定期合并：相似题材考虑合并，减少重复
3. 全局视角：定期查看全局图谱，发现跨题材关联
4. 渠道同步：确保各渠道凭证正确配置
5. 学习继承：全局学习方法对所有题材生效