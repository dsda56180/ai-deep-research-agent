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

import yaml

from knowledge_graph import get_or_create_graph

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent

# ============================================
# 角色定义（Role）
# ============================================

DEFAULT_TEMPLATES = {
    "role": """你是AI深度研究助手。
专注搜索和分析AI前沿论文，
将研究发现整理为结构化报告。""",
    "background": """研究主题：{topic}
已研究论文：{paper_count}篇
已有概念：{concept_count}个""",
    "objective_search": """1. 用 web_search 搜索最新论文（关键词：{keywords}）
2. 用 web_fetch 抓取论文全文
3. 提取：标题、作者、方法、创新点、实验结果、局限性""",
    "objective_analysis": """1. 聚焦最相关论文并完成结构化分析
2. 提取：标题、作者、方法、创新点、实验结果、局限性
3. 对照知识图谱识别新增概念、关系、方法论与知识缺口""",
    "objective_full": """1. 搜索最新论文并做质量过滤
2. 深度分析核心论文并回写知识图谱
3. 输出可同步的结构化研究报告""",
    "output_format": """输出Markdown报告：

## 核心发现
1. [发现1] - 来源URL
2. [发现2] - 来源URL

## 知识图谱更新
- 新增概念：X个
- 新增关系：Y条

## 同步
保存报告到：{report_path}
更新图谱到：{graph_path}
同步到IMA/飞书/Obsidian""",
    "constraints": """- 只分析最相关的3-5篇论文
- 每篇论文至少包含：方法、创新、局限
- 报告不超过500字
- 所有发现必须有文献来源""",
    "examples": """示例输出：

## 核心发现
1. MemGPT通过虚拟上下文管理实现长期记忆 - arxiv:2504.xxxxx
2. Zep使用时序知识图谱增强记忆检索 - arxiv:2501.xxxxx

## 知识图谱更新
- 新增概念：MemGPT, Zep, 时序知识图谱
- 新增关系：MemGPT implements 长期记忆""",
}

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
        self.topic_config = {}
        self.optimized_config = self._load_yaml(SKILL_DIR / "config" / "optimized_config.yaml")
        self.topic_id = self._resolve_topic_id()
        self.graph = None
        self._load_topic_state()
        self.templates = self._load_templates()

    def _load_yaml(self, path: Path) -> Dict:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _load_topics_config(self) -> Dict:
        config = self._load_yaml(SKILL_DIR / "config" / "topics.yaml")
        return config or {"topics": []}

    def _resolve_topic_id(self) -> str:
        config = self._load_topics_config()
        for topic in config.get("topics", []):
            if self.topic.lower() in topic.get("name", "").lower() or self.topic.lower() == topic.get("id", "").lower():
                self.topic = topic.get("name", self.topic)
                self.topic_config = topic
                return topic.get("id", self.topic.lower().replace(" ", "-"))
        return self.topic.lower().replace(" ", "-")
    
    def _load_topic_state(self):
        """加载题材当前状态"""
        graph_dir = SKILL_DIR / "topics" / self.topic_id / "knowledge" / "graphs"
        graph_path = graph_dir / f"{self.topic_id}_knowledge_graph.json"
        self.paper_count = 0
        self.concept_count = 0
        self.graph_path = graph_path
        self.graph = get_or_create_graph(self.topic, base_dir=graph_dir, filename=f"{self.topic_id}_knowledge_graph.json")
        self.paper_count = self.graph.metadata.get("paper_count", 0)
        self.concept_count = len(self.graph.concepts)

    def _load_keywords(self) -> list:
        keywords = [self.topic]
        if self.topic_config:
            keywords = self.topic_config.get("keywords", [self.topic])
        return keywords

    def _load_templates(self) -> Dict:
        templates = dict(DEFAULT_TEMPLATES)
        global_templates = self.optimized_config.get("prompt_templates", {})
        topic_templates = self.topic_config.get("prompt_templates", {})
        templates.update(global_templates)
        templates.update(topic_templates)
        return templates

    def _resolve_budget(self, phase: str, budget: int, query: str = "") -> int:
        graph_complexity = min(self.concept_count * 6, 480)
        paper_complexity = min(self.paper_count * 20, 260)
        query_complexity = min(len((query or self.topic).split()) * 45, 220)
        phase_bias = {"search": 0, "analysis": 180, "full": 260}.get(phase, 120)
        return max(900, min(3200, budget + graph_complexity + paper_complexity + query_complexity + phase_bias))

    def _project_snippets(self, phase: str, query: str = "", budget: int = 1200) -> Dict:
        task_type = {"search": "search", "analysis": "analysis", "full": "report"}.get(phase, "default")
        adaptive_budget = self._resolve_budget(phase, budget, query=query)
        navigation = dict(self.optimized_config.get("projection_navigation", {}))
        navigation.update(self.topic_config.get("projection_navigation", {}))
        mode = navigation.get("mode", "bfs")
        default_depth = {"search": 1, "analysis": 2, "full": 2}.get(phase, 2)
        depth = int(navigation.get("depth", default_depth))
        return self.graph.project_context(
            task_type=task_type,
            query=query or self.topic,
            budget=adaptive_budget,
            mode=mode,
            depth=depth,
        )

    def _render_prompt(self, phase: str, query: str = "", papers: Optional[int] = None, budget: int = 1600) -> str:
        keywords = self._load_keywords()
        projection = self._project_snippets(phase, query=query, budget=budget)
        objective_key = {
            "search": "objective_search",
            "analysis": "objective_analysis",
            "full": "objective_full",
        }.get(phase, "objective_full")
        intro = self.templates["background"].format(
            topic=self.topic,
            paper_count=self.paper_count,
            concept_count=self.concept_count,
        )
        analysis_scope = ""
        if papers is not None:
            analysis_scope = f"\n任务范围：对以下{papers}篇论文进行深度分析。"
        return f"""{self.templates['role']}

{intro}{analysis_scope}

{self.templates[objective_key].format(topic=self.topic, keywords=', '.join(keywords[:4]))}

{self.templates['output_format'].format(
    report_path=self._get_report_path(),
    graph_path=str(SKILL_DIR / 'topics' / self.topic_id / 'knowledge' / 'graphs')
)}

图谱投影上下文：
{projection['prompt'] or '暂无可用图谱上下文'}

{self.templates['constraints']}

{self.templates['examples']}"""
    
    def get_search_prompt(self, query: str = "", budget: int = 1200) -> str:
        return self._render_prompt("search", query=query, budget=budget)
    
    def get_analysis_prompt(self, papers: list, query: str = "", budget: int = 1400) -> str:
        return self._render_prompt("analysis", papers=papers, query=query, budget=budget)
    
    def _get_report_path(self) -> str:
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
        return str(SKILL_DIR / "topics" / self.topic_id / "knowledge" / "reports" / f"{self.topic_id}_{date}.md")
    
    def get_full_prompt(self, query: str = "", budget: int = 1600) -> str:
        return self._render_prompt("full", query=query, budget=budget)

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="精简上下文加载器")
    parser.add_argument("--topic", "-t", required=True, help="研究题材")
    parser.add_argument("--phase", choices=["search", "analysis", "full"], default="full")
    parser.add_argument("--query", default="", help="查询意图")
    parser.add_argument("--budget", type=int, default=1600, help="上下文预算")
    
    args = parser.parse_args()
    
    ctx = LeanContext(args.topic)
    
    if args.phase == "search":
        print(ctx.get_search_prompt(query=args.query, budget=args.budget))
    elif args.phase == "analysis":
        print(ctx.get_analysis_prompt(3, query=args.query, budget=args.budget))
    else:
        print(ctx.get_full_prompt(query=args.query, budget=args.budget))
