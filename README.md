# AI Deep Research Agent v3.0

<div align="center">

🔬 **自我进化的深度研究系统**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://python.org)
[![Skills](https://img.shields.io/badge/skills-3.0-orange.svg)](https://clawic.com)

基于 OpenCode + Oh My OpenCode 架构，结合 self-improving-agent 的自学习机制

</div>

---

## ✨ 核心特性

### 🔬 深度研究系统
- **论文搜索与抓取** - 自动搜索 arXiv、Google Scholar 等数据源
- **深度分析引擎** - 提取方法、创新、实验、局限四维度分析
- **知识图谱进化** - 自动添加概念、推断关系、检测矛盾

### 🧠 自我进化机制（继承 self-improving-agent）
- **从纠正中学习** - 记录用户纠正和失败模式
- **从成功中学习** - 积累验证有效的研究方法
- **自动晋升机制** - 使用 3 次自动晋升为最佳实践
- **分层记忆存储** - HOT / WARM / COLD 三层存储

### ☁️ IMA 知识库同步
- 研究报告自动固化
- 知识图谱定期同步
- 方法论更新追踪
- 知识缺口动态维护

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/ai-deep-research-agent.git

# 安装依赖
pip install pyyaml requests

# 配置
cp config/topics.yaml.example config/topics.yaml
```

### 使用

```bash
# 执行完整研究流程
python scripts/evolution.py evolve --topic "AI Agent 记忆系统"

# 查看学习方法
python scripts/self_learning.py show --memory

# 查看知识图谱
python scripts/evolution.py graph --topic "AI Agent 记忆系统" --summary

# 同步到 IMA
python scripts/evolution.py sync --topic "AI Agent 记忆系统"
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [SKILL.md](SKILL.md) | Skill 定义与使用指南 |
| [docs/architecture.md](docs/architecture.md) | 系统架构详解 |
| [docs/self-learning.md](docs/self-learning.md) | 自学习机制说明 |
| [docs/api-reference.md](docs/api-reference.md) | API 参考文档 |

---

## 🔄 每日进化流程

```
每天 10:00 自动触发
        ↓
【步骤 1】加载学习方法
        ↓
【步骤 2】搜索论文（应用最佳实践）
        ↓
【步骤 3】深度分析（使用验证框架）
        ↓
【步骤 4】自我反思
        ↓
【步骤 5】记录学习
        ↓
【步骤 6】知识图谱进化
        ↓
【步骤 7】IMA 同步
        ↓
【自动晋升/降级】
```

---

## 📊 当前知识状态

| 指标 | 数值 |
|------|------|
| 概念数 | 28 个 |
| 关系数 | 29 条 |
| 论文数 | 16 篇 |
| 方法论 | 2 个 |
| 学习记录 | 3+ 条 |
| 已验证模式 | 2 个 |

---

## 🧠 自学习机制

### 学习信号

| 信号类型 | 处理方式 |
|----------|----------|
| 用户纠正 | 立即记录到 corrections.md |
| 成功模式 | 记录为候选模式 |
| 失败模式 | 记录为避免模式 |
| 自我发现 | 记录为改进要点 |

### 晋升规则

| 条件 | 动作 |
|------|------|
| 使用 3 次 + 效果好 | 晋升到 HOT memory |
| 30 天未使用 | 降级到 WARM |
| 90 天未使用 | 归档到 COLD |

---

## 📁 目录结构

```
ai-deep-research-agent/
├── SKILL.md                      # Skill 定义
├── README.md                     # 本文件
├── scripts/
│   ├── evolution.py              # 主进化脚本
│   ├── self_learning.py          # 自学习模块
│   ├── knowledge_evolution_v2.py # 知识进化
│   └── ima_knowledge_solidifier.py # IMA 同步
├── .learnings/
│   ├── memory.md                 # HOT: 最佳实践
│   ├── corrections.md            # 纠正记录
│   ├── methods/                  # WARM: 方法库
│   └── usage_stats.json          # 使用统计
├── knowledge/
│   ├── graphs/                   # 知识图谱
│   └── reports/                  # 研究报告
├── config/
│   └── topics.yaml              # 研究主题配置
└── docs/
    ├── architecture.md
    └── self-learning.md
```

---

## 🔧 配置

### topics.yaml

```yaml
topics:
  - name: AI Agent 记忆系统
    keywords:
      - "AI agent memory architecture"
      - "MemGPT Mem0 Zep long-term memory"
    frequency: daily
    priority: high
    enabled: true
    target_knowledge_base: "YOUR_IMA_KB_ID"
```

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [self-improving-agent](https://clawic.com/skills/self-improving) - 自学习机制
- [OpenCode](https://github.com/opencode-ai) - 多智能体架构
- [Oh My OpenCode](https://github.com/oh-my-opencode) - Agent 协作框架

---

<div align="center">

**Made with 🔬 by QClaw**

[官网](https://qclaw.cn) · [文档](https://docs.qclaw.cn) · [社区](https://community.qclaw.cn)

</div>