#!/usr/bin/env python3
"""
精简上下文加载器
基于 Karpathy 的 Prompt 工程原则
- 动态加载，只传当前需要的
- 具体角色 → 具体任务 → 具体格式
- 先给例子再要输出
"""

from pathlib import Path
from typing import Dict, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent

# ============================================
# 角色定义（Role）
# ============================================

ROLE = """你是AI深度研究助手。
专注搜索和分析AI前沿论文，
将研究发现整理为结构化报告。"""

# ============================================
# 任务背景（Background）
# ============================================

BACKGROUND = """研究主题：{topic}
已研究论文：{paper_count}篇
已有概念：{concept_count}个"""

# ============================================
# 任务目标（Objective）
# ============================================

OBJECTIVE = """1. 用 web_search 搜索最新论文（关键词：{keywords}）
2. 用 web_fetch 抓取论文全文
3. 提取：标题、作者、方法、创新点、实验结果、局限性"""

# ============================================
# 输出格式（Format）
# ============================================

OUTPUT_FORMAT = """输出Markdown报告：

## 核心发现
1. [发现1] - 来源URL
2. [发现2] - 来源URL

## 知识图谱更新
- 新增概念：X个
- 新增关系：Y条

## 同步
保存报告到：{report_path}
更新图谱到：{graph_path}
同步到IMA/飞书/Obsidian"""

# ============================================
# 约束条件（Constraints）
# ============================================

CONSTRAINTS = """- 只分析最相关的3-5篇论文
- 每篇论文至少包含：方法、创新、局限
- 报告不超过500字
- 所有发现必须有文献来源"""

# ============================================
# 参考示例（Examples）
# ============================================

EXAMPLES = """示例输出：

## 核心发现
1. MemGPT通过虚拟上下文管理实现长期记忆 - arxiv:2504.xxxxx
2. Zep使用时序知识图谱增强记忆检索 - arxiv:2501.xxxxx

## 知识图谱更新
- 新增概念：MemGPT, Zep, 时序知识图谱
- 新增关系：MemGPT implements 长期记忆"""

# ============================================
# 动态上下文组装
# ============================================

class LeanContext:
    """精简上下文组装器"""
    
    def __init__(self, topic: str):
        self.topic = topic
        self._load_topic_state()
    
    def _load_topic_state(self):
        """加载题材当前状态"""
        import json
        
        topic_id = topic.lower().replace(" ", "-")
        graph_path = SKILL_DIR / "topics" / topic_id / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
        
        self.paper_count = 0
        self.concept_count = 0
        
        if graph_path.exists():
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph = json.load(f)
            self.paper_count = graph.get("metadata", {}).get("paper_count", 0)
            self.concept_count = len(graph.get("concepts", []))
    
    def get_search_prompt(self) -> str:
        """搜索阶段提示词"""
        # 加载关键词
        import yaml
        config_path = SKILL_DIR / "config" / "topics.yaml"
        keywords = [self.topic]
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            for t in config.get("topics", []):
                if self.topic.lower() in t.get("name", "").lower():
                    keywords = t.get("keywords", [self.topic])
                    break
        
        return f"""{ROLE}

{BACKGROUND.format(topic=self.topic, paper_count=self.paper_count, concept_count=self.concept_count)}

{OBJECTIVE.format(topic=self.topic, keywords=', '.join(keywords[:3]))}

{EXAMPLES}

报告保存到：{self._get_report_path()}"""
    
    def get_analysis_prompt(self, papers: list) -> str:
        """分析阶段提示词"""
        return f"""{ROLE}

任务：对以下{papers}篇论文进行深度分析。

{OBJECTIVE.format(topic=self.topic, keywords='')}

{CONSTRAINTS}

{EXAMPLES}

报告保存到：{self._get_report_path()}"""
    
    def _get_report_path(self) -> str:
        topic_id = self.topic.lower().replace(" ", "-")
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
        return str(SKILL_DIR / "topics" / topic_id / "knowledge" / "reports" / f"{topic_id}_{date}.md")
    
    def get_full_prompt(self) -> str:
        """完整提示词（精简版）"""
        return f"""{ROLE}

{BACKGROUND.format(topic=self.topic, paper_count=self.paper_count, concept_count=self.concept_count)}

{OBJECTIVE.format(topic=self.topic, keywords='')}

{OUTPUT_FORMAT.format(
    report_path=self._get_report_path(),
    graph_path=str(SKILL_DIR / "topics" / self.topic.lower().replace(" ", "-") / "knowledge" / "graphs")
)}

{CONSTRAINTS}

{EXAMPLES}"""

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="精简上下文加载器")
    parser.add_argument("--topic", "-t", required=True, help="研究题材")
    parser.add_argument("--phase", choices=["search", "analysis", "full"], default="full")
    
    args = parser.parse_args()
    
    ctx = LeanContext(args.topic)
    
    if args.phase == "search":
        print(ctx.get_search_prompt())
    elif args.phase == "analysis":
        print(ctx.get_analysis_prompt(3))
    else:
        print(ctx.get_full_prompt())