#!/usr/bin/env python3
"""
知识进化引擎
每天自动更新知识图谱、研究方法论、知识缺口
实现知识库的自我进化
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"
GRAPHS_DIR = KNOWLEDGE_DIR / "graphs"
REPORTS_DIR = KNOWLEDGE_DIR / "reports"
LEARNINGS_DIR = SKILL_DIR / ".learnings"

# ============================================
# 知识图谱进化
# ============================================

def evolve_knowledge_graph(topic: str, new_paper_data: Dict) -> Dict:
    """
    知识图谱进化：添加新概念、更新关系、检测矛盾
    
    Args:
        topic: 研究主题
        new_paper_data: 新论文分析数据
    
    Returns:
        进化摘要
    """
    graph_path = GRAPHS_DIR / f"{topic.replace(' ', '_')}_knowledge_graph.json"
    
    if not graph_path.exists():
        return {"error": "知识图谱不存在"}
    
    with open(graph_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)
    
    changes = {
        "new_concepts": [],
        "updated_concepts": [],
        "new_relations": [],
        "contradictions": []
    }
    
    # 1. 提取新概念
    paper_concepts = extract_concepts_from_paper(new_paper_data)
    
    existing_ids = {c["id"] for c in graph["concepts"]}
    
    for new_concept in paper_concepts:
        if new_concept["id"] not in existing_ids:
            graph["concepts"].append(new_concept)
            changes["new_concepts"].append(new_concept["name"])
        else:
            # 更新已有概念（添加新论文引用）
            for c in graph["concepts"]:
                if c["id"] == new_concept["id"]:
                    if new_paper_data.get("id") not in c.get("papers", []):
                        c["papers"].append(new_paper_data.get("id"))
                        changes["updated_concepts"].append(c["name"])
    
    # 2. 推断新关系
    new_relations = infer_relations(new_paper_data, graph["concepts"])
    for r in new_relations:
        graph["relations"].append(r)
        changes["new_relations"].append(f"{r['from']} -> {r['to']}")
    
    # 3. 检测矛盾
    contradictions = detect_contradictions(new_paper_data, graph)
    if contradictions:
        graph["insights"]["contradictions"].extend(contradictions)
        changes["contradictions"] = contradictions
    
    # 4. 更新元数据
    graph["metadata"]["updated"] = datetime.now().isoformat()
    graph["metadata"]["concept_count"] = len(graph["concepts"])
    graph["metadata"]["relation_count"] = len(graph["relations"])
    graph["metadata"]["paper_count"] = graph["metadata"].get("paper_count", 0) + 1
    
    # 保存
    with open(graph_path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    return changes


def extract_concepts_from_paper(paper: Dict) -> List[Dict]:
    """从论文提取概念"""
    concepts = []
    
    # 系统名称
    for system in paper.get("systems", []):
        concepts.append({
            "id": system.lower().replace(" ", "-").replace("/", "-"),
            "name": system,
            "type": "system",
            "description": paper.get("title", ""),
            "papers": [paper.get("id", "")],
            "parent": None,
            "children": [],
            "attributes": {"source": paper.get("url", "")}
        })
    
    # 方法名称
    for method in paper.get("methods", []):
        concepts.append({
            "id": method.lower().replace(" ", "-"),
            "name": method,
            "type": "method",
            "description": f"来自 {paper.get('title', '')}",
            "papers": [paper.get("id", "")],
            "parent": None,
            "children": [],
            "attributes": {}
        })
    
    return concepts


def infer_relations(paper: Dict, concepts: List[Dict]) -> List[Dict]:
    """推断关系"""
    relations = []
    concept_names = {c["name"].lower() for c in concepts}
    
    # 检查论文摘要中的关键词
    abstract = paper.get("abstract", "").lower()
    
    relation_keywords = {
        "improves": "extends",
        "extends": "extends",
        "enhances": "enhances",
        "based on": "implements",
        "builds on": "extends",
        "outperforms": "competes",
        "better than": "competes",
        "contradicts": "contradicts",
        "challenges": "contradicts"
    }
    
    for keyword, rel_type in relation_keywords.items():
        if keyword in abstract:
            # 找到相关概念
            for c in concepts:
                if c["name"].lower() in abstract:
                    relations.append({
                        "from": paper.get("id", ""),
                        "to": c["id"],
                        "type": rel_type,
                        "evidence": f"论文关键词暗示：{keyword}",
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
    
    return relations


def detect_contradictions(paper: Dict, graph: Dict) -> List[Dict]:
    """检测矛盾"""
    contradictions = []
    
    # 检查论文结论是否与现有洞察矛盾
    negation_keywords = ["cannot", "fail", "limitation", "problem", "challenge"]
    abstract = paper.get("abstract", "").lower()
    
    for c in graph["concepts"]:
        if c["name"].lower() in abstract:
            for kw in negation_keywords:
                if kw in abstract:
                    contradictions.append({
                        "paper": paper.get("title"),
                        "concept": c["name"],
                        "evidence": f"论文对 {c['name']} 提出质疑",
                        "severity": "high" if "contradict" in abstract else "medium"
                    })
    
    return contradictions


# ============================================
# 研究方法论进化
# ============================================

def evolve_methodology(new_insights: List[str]) -> str:
    """
    更新研究方法论学习记录
    
    Args:
        new_insights: 新的方法论洞察
    
    Returns:
        更新后的内容
    """
    methodology_path = LEARNINGS_DIR / "METHODOLOGY.md"
    
    if methodology_path.exists():
        with open(methodology_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "# 研究方法论学习记录\n\n"
    
    # 添加新洞察
    today = datetime.now().strftime("%Y-%m-%d")
    new_section = f"\n## {today} 新增洞察\n\n"
    
    for insight in new_insights:
        new_section += f"- {insight}\n"
    
    content += new_section
    
    with open(methodology_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return content


# ============================================
# 知识缺口进化
# ============================================

def evolve_knowledge_gaps(topic: str, new_gaps: List[Dict], resolved_gaps: List[str]) -> str:
    """
    更新知识缺口记录
    
    Args:
        topic: 研究主题
        new_gaps: 新发现的缺口
        resolved_gaps: 已解决的缺口
    
    Returns:
        更新后的内容
    """
    gaps_path = LEARNINGS_DIR / "KNOWLEDGE_GAPS.md"
    
    if gaps_path.exists():
        with open(gaps_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "# 知识缺口记录\n\n"
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 标记已解决的缺口
    for gap_id in resolved_gaps:
        content = content.replace(
            f"### 🔴 {gap_id}",
            f"### ✅ {gap_id} (已解决 {today})"
        )
    
    # 添加新缺口
    if new_gaps:
        content += f"\n## {today} 新发现缺口\n\n"
        for gap in new_gaps:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            content += f"""### {priority_emoji.get(gap.get('priority', 'medium'), '⚪')} {gap.get('title', '未知缺口')}

**问题**：{gap.get('description', '')}
**来源**：{gap.get('source', '')}
**优先级**：{gap.get('priority', 'medium')}
**建议**：{gap.get('suggestion', '待研究')}

"""
    
    with open(gaps_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return content


# ============================================
# 主进化函数
# ============================================

def evolve_all(topic: str, paper_data: Dict) -> Dict:
    """
    执行完整的知识进化流程
    
    Args:
        topic: 研究主题
        paper_data: 新论文数据
    
    Returns:
        进化摘要
    """
    results = {
        "date": datetime.now().isoformat(),
        "topic": topic
    }
    
    # 1. 知识图谱进化
    graph_changes = evolve_knowledge_graph(topic, paper_data)
    results["knowledge_graph"] = graph_changes
    
    # 2. 提取方法论洞察
    methodology_insights = extract_methodology_insights(paper_data)
    if methodology_insights:
        evolve_methodology(methodology_insights)
        results["methodology"] = f"新增 {len(methodology_insights)} 条方法论洞察"
    
    # 3. 提取知识缺口
    new_gaps = extract_knowledge_gaps(paper_data)
    if new_gaps:
        evolve_knowledge_gaps(topic, new_gaps, [])
        results["gaps"] = f"新增 {len(new_gaps)} 个知识缺口"
    
    return results


def extract_methodology_insights(paper: Dict) -> List[str]:
    """从论文提取方法论洞察"""
    insights = []
    
    # 检查方法论关键词
    method_keywords = [
        "we propose", "our approach", "we introduce",
        "novel method", "new framework", "our contribution"
    ]
    
    abstract = paper.get("abstract", "").lower()
    
    for kw in method_keywords:
        if kw in abstract:
            # 提取包含关键词的句子
            sentences = abstract.split(".")
            for s in sentences:
                if kw in s:
                    insights.append(f"[{paper.get('title', '')}] {s.strip()}")
                    break
    
    return insights


def extract_knowledge_gaps(paper: Dict) -> List[Dict]:
    """从论文提取知识缺口"""
    gaps = []
    
    # 检查局限性关键词
    limitation_keywords = [
        "future work", "limitation", "remains to be",
        "not addressed", "left for future", "open problem"
    ]
    
    abstract = paper.get("abstract", "").lower()
    
    for kw in limitation_keywords:
        if kw in abstract:
            sentences = abstract.split(".")
            for s in sentences:
                if kw in s:
                    gaps.append({
                        "title": f"{paper.get('title', '')[:30]}...",
                        "description": s.strip(),
                        "source": paper.get("arxiv_id", paper.get("url", "")),
                        "priority": "high" if "critical" in s or "important" in s else "medium",
                        "suggestion": "后续研究重点关注"
                    })
                    break
    
    return gaps


# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="知识进化引擎")
    parser.add_argument("--topic", "-t", required=True, help="研究主题")
    parser.add_argument("--paper", "-p", help="新论文 JSON 路径")
    parser.add_argument("--summary", "-s", action="store_true", help="显示进化摘要")
    
    args = parser.parse_args()
    
    if args.summary:
        graph_path = GRAPHS_DIR / f"{args.topic.replace(' ', '_')}_knowledge_graph.json"
        if graph_path.exists():
            with open(graph_path, 'r', encoding='utf-8') as f:
                g = json.load(f)
            print(f"📊 {args.topic} 知识进化摘要")
            print(f"   概念：{len(g.get('concepts', []))}")
            print(f"   关系：{len(g.get('relations', []))}")
            print(f"   论文：{g.get('metadata', {}).get('paper_count', 0)}")
    
    elif args.paper:
        with open(args.paper, 'r', encoding='utf-8') as f:
            paper = json.load(f)
        
        result = evolve_all(args.topic, paper)
        print(json.dumps(result, ensure_ascii=False, indent=2))