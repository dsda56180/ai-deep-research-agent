#!/usr/bin/env python3
"""
直接研究执行器
绕过 OpenCode TUI，直接使用主模型能力执行深度研究
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ============================================
# 配置
# ============================================

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"
DATA_DIR = SKILL_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

# 研究缓存
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH_CACHE_FILE = CACHE_DIR / "research_cache.json"

# ============================================
# 工具函数
# ============================================

def now(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.now().strftime(fmt)

def today():
    return datetime.now().strftime("%Y-%m-%d")

def load_cache() -> Dict:
    """加载研究缓存"""
    if RESEARCH_CACHE_FILE.exists():
        with open(RESEARCH_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"papers": {}, "last_update": {}}

def save_cache(cache: Dict):
    """保存研究缓存"""
    with open(RESEARCH_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def is_paper_cached(paper_id: str, cache: Dict) -> bool:
    """检查论文是否已缓存"""
    return paper_id in cache.get("papers", {})

def extract_arxiv_id(url: str) -> Optional[str]:
    """从 URL 提取 arXiv ID"""
    match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', url)
    if match:
        return f"arxiv:{match.group(1)}"
    return None

# ============================================
# 论文质量评估 (P2)
# ============================================

def evaluate_paper_quality(paper: Dict) -> float:
    """
    评估论文质量分数 (0-5)
    
    评分维度：
    - 发表场所
    - 引用速度
    - 作者影响力
    - 相关性
    """
    score = 0.0
    
    # 1. 发表场所评分
    venue = paper.get("venue", "")
    if venue in ["NeurIPS", "ICML", "ICLR", "ACL", "EMNLP", "CVPR"]:
        score += 2.0
    elif venue in ["AAAI", "IJCAI", "AISTATS"]:
        score += 1.5
    elif "arxiv" in paper.get("url", "").lower():
        score += 1.0
    
    # 2. 引用数评分
    citations = paper.get("citations", 0)
    if citations > 100:
        score += 1.5
    elif citations > 50:
        score += 1.0
    elif citations > 10:
        score += 0.5
    
    # 3. 时效性评分（越新越重要）
    pub_date = paper.get("pub_date", "")
    if pub_date:
        try:
            pub_dt = datetime.strptime(pub_date[:10], "%Y-%m-%d")
            days_old = (datetime.now() - pub_dt).days
            if days_old < 90:  # 3个月内
                score += 1.0
            elif days_old < 180:  # 6个月内
                score += 0.5
        except:
            pass
    
    # 4. 相关性评分（基于关键词匹配）
    relevance = paper.get("relevance_score", 0)
    score += relevance * 0.5
    
    return min(score, 5.0)  # 最高5分

def filter_high_quality_papers(papers: List[Dict], min_score: float = 3.0) -> List[Dict]:
    """筛选高质量论文"""
    for paper in papers:
        paper["quality_score"] = evaluate_paper_quality(paper)
    
    filtered = [p for p in papers if p["quality_score"] >= min_score]
    return sorted(filtered, key=lambda x: x["quality_score"], reverse=True)

# ============================================
# 知识进化机制 (P1)
# ============================================

def analyze_relation_to_concept(paper: Dict, concept: Dict) -> Tuple[str, str]:
    """
    分析论文与概念的关系
    
    Returns:
        (relation_type, evidence)
        relation_type: "补充" | "验证" | "矛盾" | "扩展" | "无关"
    """
    paper_methods = set(paper.get("methods", []))
    paper_findings = set(paper.get("findings", []))
    
    concept_name = concept.get("name", "").lower()
    concept_desc = concept.get("description", "").lower()
    
    # 检查是否直接相关
    is_related = False
    for method in paper_methods:
        if method.lower() in concept_name or method.lower() in concept_desc:
            is_related = True
            break
    
    if not is_related:
        return "无关", ""
    
    # 分析关系类型
    # 这里简化处理，实际应该用模型分析
    paper_contrib = paper.get("contribution", "").lower()
    
    if "improve" in paper_contrib or "enhance" in paper_contrib:
        return "扩展", f"论文改进了 {concept_name}"
    elif "validate" in paper_contrib or "confirm" in paper_contrib:
        return "验证", f"论文验证了 {concept_name} 的有效性"
    elif "contradict" in paper_contrib or "challenge" in paper_contrib:
        return "矛盾", f"论文对 {concept_name} 提出质疑"
    else:
        return "补充", f"论文补充了 {concept_name} 的新视角"

def evolve_knowledge_graph(paper: Dict, graph: Dict) -> Dict:
    """
    知识图谱进化
    
    Args:
        paper: 新分析的论文
        graph: 现有知识图谱
    
    Returns:
        更新后的知识图谱
    """
    new_relations = []
    
    # 与每个现有概念对比
    for concept in graph.get("concepts", []):
        relation_type, evidence = analyze_relation_to_concept(paper, concept)
        
        if relation_type != "无关":
            new_relations.append({
                "from": paper.get("id", ""),
                "to": concept["id"],
                "type": relation_type,
                "evidence": evidence,
                "date": today()
            })
            
            # 如果是矛盾关系，记录到洞察
            if relation_type == "矛盾":
                if "contradictions" not in graph["insights"]:
                    graph["insights"]["contradictions"] = []
                graph["insights"]["contradictions"].append({
                    "paper": paper.get("title"),
                    "concept": concept["name"],
                    "evidence": evidence
                })
    
    # 添加新关系
    graph["relations"].extend(new_relations)
    
    # 更新元数据
    graph["metadata"]["updated"] = now()
    graph["metadata"]["paper_count"] = graph["metadata"].get("paper_count", 0) + 1
    
    return graph

# ============================================
# 自动知识图谱更新 (P1)
# ============================================

def extract_concepts_from_paper(paper: Dict) -> List[Dict]:
    """从论文提取概念"""
    concepts = []
    
    # 提取方法作为概念
    for method in paper.get("methods", []):
        concepts.append({
            "id": method.lower().replace(" ", "-"),
            "name": method,
            "type": "method",
            "description": f"来自论文 {paper.get('title', '')}",
            "papers": [paper.get("id", "")],
            "parent": None,
            "children": [],
            "attributes": {}
        })
    
    # 提取系统/框架名称
    for system in paper.get("systems", []):
        concepts.append({
            "id": system.lower().replace(" ", "-"),
            "name": system,
            "type": "system",
            "description": paper.get("title", ""),
            "papers": [paper.get("id", "")],
            "parent": None,
            "children": [],
            "attributes": {
                "source": paper.get("url", "")
            }
        })
    
    return concepts

def update_knowledge_graph_with_paper(paper: Dict, graph: Dict) -> Dict:
    """
    用新论文更新知识图谱
    """
    # 1. 提取新概念
    new_concepts = extract_concepts_from_paper(paper)
    
    # 2. 匹配或创建概念
    existing_ids = {c["id"] for c in graph.get("concepts", [])}
    
    for new_concept in new_concepts:
        if new_concept["id"] in existing_ids:
            # 更新现有概念（添加论文引用）
            for concept in graph["concepts"]:
                if concept["id"] == new_concept["id"]:
                    if paper.get("id") not in concept.get("papers", []):
                        concept["papers"].append(paper.get("id"))
        else:
            # 创建新概念
            graph["concepts"].append(new_concept)
            existing_ids.add(new_concept["id"])
    
    # 3. 知识进化
    graph = evolve_knowledge_graph(paper, graph)
    
    # 4. 更新统计
    graph["metadata"]["concept_count"] = len(graph["concepts"])
    
    return graph

# ============================================
# 跨主题关联发现 (P3)
# ============================================

def find_cross_topic_insights(graphs: Dict[str, Dict]) -> List[Dict]:
    """
    发现跨主题洞察
    
    Args:
        graphs: {topic_name: graph_data}
    
    Returns:
        跨主题洞察列表
    """
    insights = []
    
    # 收集所有概念
    all_concepts = {}
    for topic, graph in graphs.items():
        for concept in graph.get("concepts", []):
            name = concept["name"].lower()
            if name not in all_concepts:
                all_concepts[name] = []
            all_concepts[name].append({
                "topic": topic,
                "concept": concept
            })
    
    # 找出跨主题共享的概念
    for name, occurrences in all_concepts.items():
        if len(occurrences) > 1:
            topics = [o["topic"] for o in occurrences]
            insights.append({
                "type": "shared_concept",
                "concept": name,
                "topics": topics,
                "insight": f"'{name}' 在 {len(topics)} 个主题中出现：{', '.join(topics)}",
                "significance": "high" if len(topics) > 2 else "medium"
            })
    
    return insights

# ============================================
# 方法复现指南生成 (P2)
# ============================================

def generate_reproduction_guide(paper: Dict) -> str:
    """生成方法复现指南"""
    guide = []
    
    guide.append(f"## 方法复现指南：{paper.get('title', '未知论文')}\n")
    
    # GitHub 链接
    github = paper.get("github", "")
    if github:
        guide.append(f"**GitHub**: {github}\n")
        guide.append("```bash")
        guide.append(f"git clone {github}")
        guide.append("cd $(basename {github} .git)")
        guide.append("```\n")
    
    # 依赖项
    dependencies = paper.get("dependencies", [])
    if dependencies:
        guide.append("**依赖项**：")
        for dep in dependencies:
            guide.append(f"- {dep}")
        guide.append("")
    
    # 核心代码
    code_snippet = paper.get("code_snippet", "")
    if code_snippet:
        guide.append("**核心代码**：")
        guide.append("```python")
        guide.append(code_snippet)
        guide.append("```\n")
    
    # 一键复现
    quick_start = paper.get("quick_start", "")
    if quick_start:
        guide.append("**一键复现**：")
        guide.append("```bash")
        guide.append(quick_start)
        guide.append("```\n")
    
    return "\n".join(guide)

# ============================================
# 增量更新模式 (P3)
# ============================================

def get_last_update_date(topic: str, cache: Dict) -> Optional[str]:
    """获取主题最后更新日期"""
    return cache.get("last_update", {}).get(topic)

def incremental_research_needed(topic: str, cache: Dict) -> bool:
    """判断是否需要增量研究"""
    last_date = get_last_update_date(topic, cache)
    if not last_date:
        return True  # 从未研究过
    
    try:
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        days_since = (datetime.now() - last_dt).days
        return days_since >= 1  # 超过1天就需要更新
    except:
        return True

# ============================================
# 研究进度追踪 (P3)
# ============================================

class ResearchProgress:
    """研究进度追踪器"""
    
    def __init__(self, total_steps: int = 5):
        self.total_steps = total_steps
        self.current_step = 0
        self.step_names = [
            "搜索论文",
            "筛选高质量论文",
            "深度分析",
            "知识图谱更新",
            "IMA同步"
        ]
        self.completed = []
        self.current_paper = ""
    
    def advance(self, paper_name: str = ""):
        """推进进度"""
        self.current_step += 1
        if paper_name:
            self.current_paper = paper_name
    
    def complete_step(self, step_name: str):
        """完成步骤"""
        self.completed.append(step_name)
    
    def render(self) -> str:
        """渲染进度条"""
        bar_length = 20
        filled = int(bar_length * self.current_step / self.total_steps)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        lines = [
            "🔬 深度研究进行中...",
            "",
            f"┌{'─' * 39}┐",
            f"│ {bar} 阶段 {self.current_step}/{self.total_steps} │",
        ]
        
        if self.current_paper:
            lines.append(f"│ 📄 分析：{self.current_paper[:30]}... │")
        
        if self.completed:
            lines.append(f"│ ✅ 已完成：{', '.join(self.completed[:3])} │")
        
        remaining = [s for s in self.step_names if s not in self.completed]
        if remaining:
            lines.append(f"│ ⏳ 待执行：{', '.join(remaining[:2])} │")
        
        lines.append(f"└{'─' * 39}┘")
        
        return "\n".join(lines)

# ============================================
# 主研究执行函数
# ============================================

def execute_direct_research(
    topic: str,
    keywords: List[str],
    research_questions: List[str],
    max_papers: int = 5,
    min_quality: float = 3.0,
    use_cache: bool = True
) -> Dict:
    """
    直接执行深度研究（不依赖 OpenCode）
    
    Args:
        topic: 研究主题
        keywords: 搜索关键词
        research_questions: 研究问题
        max_papers: 最大论文数
        min_quality: 最低质量分数
        use_cache: 是否使用缓存
    
    Returns:
        研究结果
    """
    print("=" * 60)
    print(f"🔬 直接研究执行器")
    print(f"   主题：{topic}")
    print(f"   时间：{now()}")
    print("=" * 60)
    
    # 初始化进度追踪
    progress = ResearchProgress(total_steps=5)
    print(progress.render())
    
    # 加载缓存
    cache = load_cache() if use_cache else {"papers": {}, "last_update": {}}
    
    # 检查是否需要增量更新
    if not incremental_research_needed(topic, cache):
        print("\n✅ 知识库已是最新，无需重新研究")
        return {"success": True, "cached": True}
    
    # 阶段 1：搜索论文
    print("\n📥 阶段 1/5：搜索论文...")
    progress.advance()
    
    # 这里返回搜索结果占位符
    # 实际搜索由主模型通过 web_search 工具执行
    search_results = {
        "stage": "search",
        "keywords": keywords,
        "topic": topic,
        "instruction": f"请使用 web_search 搜索以下关键词的最新论文：{', '.join(keywords)}"
    }
    
    progress.complete_step("搜索论文")
    print(progress.render())
    
    # 阶段 2：筛选高质量论文
    print("\n🔍 阶段 2/5：筛选高质量论文...")
    progress.advance()
    
    filter_instruction = f"""
请对搜索结果进行质量筛选：
1. 评估每篇论文的质量分数（发表场所、引用数、时效性）
2. 只保留质量分数 >= {min_quality} 的论文
3. 按质量分数降序排列
4. 最多保留 {max_papers} 篇

评估标准：
- 顶级会议（NeurIPS/ICML/ICLR/ACL）：+2分
- 高引用（>100）：+1.5分
- 3个月内发表：+1分
"""
    
    progress.complete_step("筛选论文")
    print(progress.render())
    
    # 阶段 3：深度分析
    print("\n🧠 阶段 3/5：深度分析...")
    progress.advance()
    
    analysis_instruction = f"""
对每篇筛选后的论文进行深度分析：

## 研究问题
{chr(10).join([f'- {q}' for q in research_questions])}

## 分析维度
1. **核心方法**：技术原理是什么？实现细节有哪些？
2. **创新点**：相对现有工作的突破在哪里？
3. **实验结果**：关键指标是什么？效果如何？
4. **局限性**：适用场景有哪些？改进方向是什么？
5. **复现指南**：如何复现该方法？（代码、依赖、命令）

## 输出格式
请输出结构化的 Markdown 分析报告。
"""
    
    progress.complete_step("深度分析")
    print(progress.render())
    
    # 阶段 4：知识图谱更新
    print("\n📊 阶段 4/5：知识图谱更新...")
    progress.advance()
    
    graph_instruction = """
基于分析结果更新知识图谱：

1. 提取新概念（方法、系统、技术）
2. 与已有概念匹配或创建
3. 分析与已有知识的关联（补充/验证/矛盾/扩展）
4. 更新关系边

请输出 JSON 格式的知识图谱更新。
"""
    
    progress.complete_step("知识图谱更新")
    print(progress.render())
    
    # 阶段 5：IMA 同步
    print("\n📤 阶段 5/5：IMA 同步...")
    progress.advance()
    
    sync_instruction = """
将研究成果固化到 IMA 知识库：

1. 研究报告（Markdown）→ IMA 笔记
2. 知识图谱（JSON）→ IMA 笔记
3. 方法复现指南 → IMA 笔记

使用 ima_knowledge_solidifier.py 执行同步。
"""
    
    progress.complete_step("IMA同步")
    print(progress.render())
    
    # 更新缓存
    cache["last_update"][topic] = today()
    save_cache(cache)
    
    # 返回完整指令
    return {
        "success": True,
        "cached": False,
        "instructions": {
            "search": search_results,
            "filter": filter_instruction,
            "analysis": analysis_instruction,
            "graph": graph_instruction,
            "sync": sync_instruction
        },
        "progress": {
            "completed": progress.completed,
            "total": progress.total_steps
        }
    }

# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    import argparse
    import yaml
    
    parser = argparse.ArgumentParser(description="直接研究执行器")
    parser.add_argument("--topic", "-t", help="研究主题")
    parser.add_argument("--config", "-c", help="主题配置文件")
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
    
    args = parser.parse_args()
    
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        topics = [t for t in config.get("topics", []) if t.get("enabled", True)]
        
        for topic_config in topics:
            result = execute_direct_research(
                topic=topic_config["name"],
                keywords=topic_config.get("keywords", []),
                research_questions=topic_config.get("research_questions", []),
                use_cache=not args.no_cache
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.topic:
        result = execute_direct_research(
            topic=args.topic,
            keywords=[args.topic],
            research_questions=[f"什么是{args.topic}的核心方法？"],
            use_cache=not args.no_cache
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()