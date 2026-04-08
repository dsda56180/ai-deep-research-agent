# AI Deep Research Agent v5.0

<div align="center">

🔬 **自我进化的深度研究系统**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://python.org)
[![Skills](https://img.shields.io/badge/skills-5.0-orange.svg)](https://github.com/dsda56180/ai-deep-research-agent)

基于 Karpathy Prompt 原则优化 | 多题材管理 | 多渠道同步

</div>

---

## ✨ v5.0 新特性

### 🎯 基于 Karpathy 原则优化
- **精简 System Prompt** - 从 ~2000 tokens 压缩到 <500 tokens
- **动态加载** - 按需加载指令，避免预加载冗余
- **Token 监控** - 实时监控消耗，自动告警
- **记忆压缩** - 定期归档旧数据，保持高效

### 📚 多题材管理
- **独立文件夹** - 每个题材独立研究
- **全局知识图谱** - 跨题材概念关联
- **灵活配置** - 支持创建/合并/禁用题材

### 📤 多渠道同步
| 渠道 | 状态 | 说明 |
|------|------|------|
| **IMA** | ✅ | 微信知识库 |
| **Obsidian** | ✅ | 本地 Markdown |
| **飞书** | ✅ | 云文档协作 |
| **GitHub** | ✅ | 版本管理 |

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/dsda56180/ai-deep-research-agent.git

# 安装依赖
pip install pyyaml requests

# 配置 Obsidian（可选）
export OBSIDIAN_VAULT="/path/to/your/vault"
```

### 基础使用

```bash
# 列出所有题材
python scripts/topic_manager.py list

# 执行研究（精简 Prompt）
python scripts/lean_context.py --topic "AI Agent 记忆系统"

# 查看全局图谱
python scripts/global_graph.py summary

# Token 消耗状态
python scripts/token_monitor.py status
```

### 同步到多渠道

```bash
# 导出到 Obsidian
python scripts/obsidian_sync.py export --topic "ai-agent-memory"

# 同步到 IMA
python scripts/ima_knowledge_solidifier.py --report "path/to/report.md"

# 同步到飞书（需配置凭证）
python scripts/feishu_sync.py sync --topic "ai-agent-memory"
```

---

## 📊 当前研究状态

| 指标 | 数值 |
|------|------|
| 研究题材 | 3 个 |
| 概念数 | 28+ 个 |
| 关系数 | 29+ 条 |
| 报告数 | 8+ 份 |
| Token 预算 | 50K/天 |

### 研究题材

| 题材 | 频率 | 渠道 |
|------|------|------|
| AI Agent 记忆系统 | 每日 | IMA/飞书/Obsidian |
| 多智能体协作系统 | 每周 | 飞书/Obsidian |
| Agent Token优化 | 每周 | IMA/飞书/Obsidian |

---

## 🔄 自动化流程

```
每天 10:00 自动触发
        ↓
【1】列出研究题材
        ↓
【2】加载学习方法
        ↓
【3】搜索论文 + 生成新报告 ← 生成今日报告！
        ↓
【4】更新知识图谱
        ↓
【5】GitHub 自动推送
        ↓
【6】IMA 知识库同步
        ↓
【7】Obsidian 增量导出 ← 只同步最新报告！
        ↓
【8】Token 消耗监控
```

---

## 📁 目录结构

```
ai-deep-research-agent/
├── SKILL.md                      # Skill 定义 v5.0
├── README.md                     # 本文件
├── scripts/
│   ├── lean_context.py           # 精简上下文加载
│   ├── token_monitor.py          # Token 消耗监控
│   ├── memory_compressor.py      # 记忆压缩
│   ├── topic_manager.py          # 题材管理
│   ├── global_graph.py           # 全局知识图谱
│   ├── obsidian_sync.py          # Obsidian 同步
│   ├── feishu_sync.py            # 飞书同步
│   ├── ima_knowledge_solidifier.py # IMA 同步
│   ├── evolution.py              # 主进化脚本
│   └── daily_report_generator.py # 每日报告生成器 ← 新增！
├── topics/                       # 多题材独立管理
│   ├── ai-agent-memory/
│   │   └── knowledge/
│   │       ├── reports/         # 研究报告（按日期）
│   │       └── graphs/          # 知识图谱
├── global/                       # 全局知识
│   ├── knowledge_graph.json
│   └── cross_topic_graph.json
├── exports/                      # 导出目录
│   ├── obsidian/
│   └── feishu/
├── config/
│   └── topics.yaml               # 题材配置
└── .learnings/                   # 自学习记忆
    ├── memory.md
    ├── corrections.md
    └── methods/
```

---

## 🔧 报告管理

### 最新报告命名

```
AI_Agent_Memory_Research_YYYY-MM-DD.md
```

### 报告更新策略

| 场景 | 策略 |
|------|------|
| 每日首次运行 | 生成新报告（追加到历史） |
| 同一天多次运行 | 增量更新现有报告 |
| 旧报告归档 | 30天后自动压缩 |

---

## 🔬 核心发现（2026-04-07）

### AI Agent 记忆系统

> 主流大模型是"健忘"的，70%-90%推理token被反复重传历史信息。

**解决方案对比**：

| 方案 | 核心机制 | GitHub |
|------|----------|--------|
| MemGPT | 层级存储+缺页中断 | 9.4k ⭐ |
| Mem0 | 自我改进记忆层 | 万星 |
| Zep | 时序知识图谱 | 企业级 |

### Token 优化

> Context Engineering > Prompt Engineering
> 核心从"怎么问"转向"给什么"和"如何管理信息"

### 多智能体协作

> MCP协议成为OpenAI主推的生态枢纽
> AutoGen/Swarms/ChatDev 形成三足鼎立

---

## 🧠 自学习机制

### 学习信号

| 信号类型 | 处理方式 |
|----------|----------|
| 用户纠正 | 立即记录到 corrections.md |
| 成功模式 | 记录为候选模式 |
| 失败模式 | 记录为避免模式 |
| Token 超限 | 自动压缩 + 告警 |

### 记忆分层

```
HOT (热数据)  ← 最近对话，Token消耗高
    ↓
WARM (温数据) ← 近期重要，定期压缩
    ↓
COLD (冷数据) ← 历史记忆，按需召回
```

---

## 🔧 配置

### topics.yaml

```yaml
topics:
  - id: ai-agent-memory
    name: AI Agent 记忆系统
    keywords:
      - "AI agent memory architecture"
      - "MemGPT Mem0 Zep"
    enabled: true
    frequency: daily
    channels:
      - ima
      - feishu
      - obsidian

channels:
  ima:
    enabled: true
    kb_id: "YOUR_KB_ID"
  
  obsidian:
    enabled: true
    vault_path: "${OBSIDIAN_VAULT}"
    folder: "AI Research"
  
  feishu:
    enabled: true
    app_id: "${FEISHU_APP_ID}"
```

### 环境变量

```bash
# Obsidian
export OBSIDIAN_VAULT="/path/to/vault"

# 飞书（可选）
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_secret"
export FEISHU_FOLDER_TOKEN="folder_token"
```

---

## 📈 优化效果

| 指标 | v4.0 | v5.0 | 提升 |
|------|------|------|------|
| System Prompt | ~2000 tokens | ~400 tokens | **80%↓** |
| 报告长度 | ~2000 字 | ~500 字 | **75%↓** |
| Token 消耗/周 | ~50000 | ~15000 | **70%↓** |

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [Karpathy](https://karpathy.ai/) - Prompt 工程原则
- [self-improving-agent](https://clawic.com/skills/self-improving) - 自学习机制
- [MemGPT](https://github.com/cpacker/MemGPT) - 记忆架构参考
- [Mem0](https://mem0.ai/) - 记忆层设计

---

<div align="center">

**Made with 🔬 by QClaw**

[GitHub](https://github.com/dsda56180/ai-deep-research-agent) · [QClaw](https://qclaw.cn)

</div>