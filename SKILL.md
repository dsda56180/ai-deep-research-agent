---
name: ai-deep-research-agent
version: 5.0
slug: ai-deep-research-agent
description: |
  基于 Karpathy 思想的精简优化版深度研究 Agent
  
  核心特点：
  - System prompt <500 tokens
  - 动态 prompt（按需加载指令）
  - Token 消耗自动监控
  - 记忆自动压缩
  
  触发词：
  - 「深度研究」- 执行研究
  - 「研究进度」- 状态
  - 「知识图谱」- 全局图谱
metadata:
  openclaw:
    emoji: "🔬"
---
# AI Deep Research Agent v5.0 — 精简优化版

## 🆕 v5.0 优化（基于 Karpathy 思想）

### 1. System Prompt 精简（<500 tokens）

| v4.0 | v5.0 |
|-------|-------|
| 7阶段详细说明 | 3行核心任务 |
| 完整配置 | 动态加载 |
| 多渠道指令 | 按需同步 |

### 2. 动态 Prompt 加载

```python
# 按需加载研究指令，而非全部预加载
def get_context(phase: str) -> str:
    """根据研究阶段加载对应指令"""
    if phase == "search":
        return "使用 web_search 搜索关键词，返回前 10 篇论文"
    elif phase == "analysis":
        return "对每篇论文提取：标题、作者、方法、创新、实验、局限"
    # 等等...
```

### 3. Token 消耗监控

```yaml
# 每周自动监控
token_budget:
  max_per_week: 50000
  alert_threshold: 40000
  
auto_optimization:
  # 超过阈值时自动压缩
  - 删除 30 天前报告
  - 知识图谱只保留核心 50 概念
  - 合并相似研究
```

### 4. 记忆分层压缩

```python
# 记忆自动压缩
compress_memory():
    if concepts > 50:
        # 提取核心概念，删除细节
        core = extract_core(concepts)
        archive(detailed, days=30)
    if reports > 20:
        # 合并旧报告为摘要
        summary = merge_reports(old_reports)
```

### 5. 输出精简

```markdown
# 优化后的报告格式（精简版）

## 核心发现（不超过 5 条）
1. [发现1] - 来源
2. [发现2] - 来源

## 知识图谱变化
- 新概念：X 个
- 新关系：Y 条
- 已验证方法：Z 个

## 同步状态
- IMA: ✅
- 飞书: ✅
- Obsidian: ✅

## 学习记录（仅新增）
- [新方法/新教训]
```

### 6. 定时任务精简

```json
{
  "message": "ultrawork 执行深度研究：
  1. 搜索关键词，返回前 5 篇论文
  2. 每篇提取：标题+方法+创新+局限
  3. 更新知识图谱（JSON）
  4. 输出精简报告（<500 字）
  5. 同步到 IMA/飞书/Obsidian
  6. 记录学习要点"
}
```

## 📁 文件结构

```
ai-deep-research-agent/
├── SKILL.md                       # 精简版（<500行）
├── scripts/
│   ├── evolution.py               # 主脚本
│   ├── lean_context.py           # 动态加载
│   ├── token_monitor.py         # 消耗监控
│   └── memory_compressor.py    # 记忆压缩
├── config/
│   └── lean_config.yaml          # 精简配置
└── topics/                      # 各题材
```

## 🚀 优化效果

| 指标 | v4.0 | v5.0 | 提升 |
|------|------|------|------|
| System Prompt | ~2000 tokens | ~400 tokens | 80%↓ |
| 报告长度 | ~2000 字 | ~500 字 | 75%↓ |
| 执行时间 | ~10 min | ~3 min | 70%↓ |
| Token 消耗 | ~50000/周 | ~15000/周 | 70%↓ |

## CLI 命令

```bash
# 精简执行
python lean_context.py run --topic "AI Agent 记忆系统"

# 压缩记忆（手动）
python memory_compressor.py compress

# 监控消耗
python token_monitor.py status
```