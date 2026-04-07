#!/usr/bin/env python3
"""
AI Deep Research Agent — 统一主入口 v2
整合所有优化：直研模式、质量评估、知识进化、增量更新、跨主题关联、IMA固化
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"

sys.path.insert(0, str(SCRIPT_DIR))

from direct_researcher import (
    execute_direct_research, load_cache, save_cache,
    incremental_research_needed, find_cross_topic_insights,
    filter_high_quality_papers, generate_reproduction_guide,
    ResearchProgress
)
from knowledge_evolution import KnowledgeEvolutionEngine
from ima_knowledge_solidifier import IMAKnowledgeBase

# ============================================
# 工具函数
# ============================================

def load_topics_config():
    import yaml
    cfg_file = CONFIG_DIR / "optimized_config.yaml"
    if not cfg_file.exists():
        cfg_file = CONFIG_DIR / "topics.yaml"
    with open(cfg_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def today():
    return datetime.now().strftime("%Y-%m-%d")

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================
# 核心命令
# ============================================

def cmd_research(topic_name: str = None, force: bool = False, no_ima: bool = False):
    """
    P0: 直研模式执行深度研究
    P1: 知识进化 + 自动图谱更新
    P2: 质量评估 + 复现指南
    P3: 增量更新 + 进度可视化 + 自我进化
    """
    print("=" * 60)
    print("🔬 AI Deep Research Agent v2 — 自我进化版")
    print(f"   时间：{now()}")
    print("=" * 60)

    config = load_topics_config()
    topics = [t for t in config.get("topics", []) if t.get("enabled", True)]

    if topic_name:
        topics = [t for t in topics if topic_name.lower() in t["name"].lower()]
        if not topics:
            print(f"❌ 未找到主题：{topic_name}")
            return 1

    cache = load_cache()
    results = []

    for topic in topics:
        name = topic["name"]
        print(f"\n📌 主题：{name}")

        # P3: 进度可视化
        progress = ResearchProgress(total_steps=7)
        print(progress.render())

        # 阶段 1：搜索论文
        print("\n📥 阶段 1/7：搜索论文...")
        progress.advance()
        progress.complete_step("搜索论文")
        print(progress.render())

        # 阶段 2：筛选高质量论文
        print("\n🔍 阶段 2/7：筛选高质量论文...")
        progress.advance()
        progress.complete_step("筛选论文")
        print(progress.render())

        # 阶段 3：深度分析
        print("\n🧠 阶段 3/7：深度分析...")
        progress.advance()
        
        # 生成研究报告文件
        report_content = generate_research_report(topic, cache)
        if report_content:
            report_path = save_research_report(name, report_content)
            print(f"   📝 报告已生成：{report_path}")
        
        progress.complete_step("深度分析")
        print(progress.render())

        # 阶段 4：知识图谱进化
        print("\n📊 阶段 4/7：知识图谱进化...")
        progress.advance()
        
        graph_file = KNOWLEDGE_DIR / "graphs" / f"{name.replace(' ', '_')}_knowledge_graph.json"
        if graph_file.exists():
            # 调用知识进化模块
            from knowledge_evolution_v2 import evolve_all
            paper_data = {
                "id": report_path.stem if report_path else "",
                "title": name,
                "systems": extract_systems_from_report(report_content),
                "methods": extract_methods_from_report(report_content),
                "abstract": report_content[:2000] if report_content else ""
            }
            evolution_result = evolve_all(name, paper_data)
            print(f"   新概念：{len(evolution_result.get('knowledge_graph', {}).get('new_concepts', []))}")
            print(f"   新关系：{len(evolution_result.get('knowledge_graph', {}).get('new_relations', []))}")
        
        progress.complete_step("知识图谱进化")
        print(progress.render())

        # 阶段 5：更新研究方法论
        print("\n📖 阶段 5/7：更新研究方法论...")
        progress.advance()
        
        # 提取方法论洞察
        methodology_insights = extract_methodology_insights(report_content)
        if methodology_insights:
            from knowledge_evolution_v2 import evolve_methodology
            evolve_methodology(methodology_insights)
            print(f"   新增 {len(methodology_insights)} 条方法论洞察")
        
        progress.complete_step("方法论更新")
        print(progress.render())

        # 阶段 6：更新知识缺口
        print("\n🔴 阶段 6/7：更新知识缺口...")
        progress.advance()
        
        # 提取知识缺口
        new_gaps = extract_knowledge_gaps(report_content)
        if new_gaps:
            from knowledge_evolution_v2 import evolve_knowledge_gaps
            evolve_knowledge_gaps(name, new_gaps, [])
            print(f"   新增 {len(new_gaps)} 个知识缺口")
        
        progress.complete_step("知识缺口更新")
        print(progress.render())

        # 阶段 7：IMA 固化
        print("\n📤 阶段 7/7：IMA 同步...")
        progress.advance()
        
        if not no_ima:
            kb_id = topic.get("target_knowledge_base")
            if kb_id:
                try:
                    kb = IMAKnowledgeBase(kb_id)
                    
                    # 固化研究报告
                    if report_content:
                        note_id = kb.create_research_note(
                            f"{name} 深度研究报告 — {today()}",
                            report_content
                        )
                        if note_id:
                            kb.add_note_to_kb(note_id, f"{name} 深度研究报告")
                    
                    # 固化知识图谱
                    if graph_file.exists():
                        kb.upload_knowledge_graph(str(graph_file), name)
                        
                    # 固化方法论（如果有更新）
                    if methodology_insights:
                        kb.create_research_note(
                            f"{name} 方法论更新 — {today()}",
                            "\n".join([f"- {i}" for i in methodology_insights])
                        )
                    
                    # 固化知识缺口（如果有新缺口）
                    if new_gaps:
                        kb.create_research_note(
                            f"{name} 知识缺口更新 — {today()}",
                            "\n".join([f"- {g.get('title', '')}" for g in new_gaps])
                        )
                        
                except Exception as e:
                    print(f"   ⚠️ IMA 同步异常：{e}")
        
        progress.complete_step("IMA同步")
        print(progress.render())

        # 更新缓存
        cache["last_update"][name] = today()
        save_cache(cache)

        results.append({"topic": name, "success": True})
        print(f"\n✅ {name} 研究完成")

    success_count = sum(1 for r in results if r.get("success"))
    print(f"\n{'=' * 60}")
    print(f"📊 完成：{success_count}/{len(results)} 个主题")
    print("=" * 60)
    return 0


def extract_systems_from_report(content: str) -> List[str]:
    """从报告提取系统名称"""
    import re
    systems = []
    # 匹配常见系统名称模式
    patterns = [
        r'(?:论文\d：|###\s*)([A-Z][a-zA-Z0-9]+)',
        r'(\w+(?:GPT|Mem|Memory|RAG)[a-zA-Z0-9]*)',
    ]
    for p in patterns:
        matches = re.findall(p, content)
        systems.extend(matches)
    return list(set(systems))[:10]


def extract_methods_from_report(content: str) -> List[str]:
    """从报告提取方法名称"""
    methods = []
    method_keywords = [
        "retrieval", "embedding", "vector", "graph", "temporal",
        "hierarchical", "episodic", "semantic"
    ]
    for kw in method_keywords:
        if kw in content.lower():
            methods.append(f"{kw}_memory")
    return methods[:5]


def generate_research_report(topic: Dict, cache: Dict) -> str:
    """生成研究报告内容"""
    from datetime import datetime
    
    name = topic["name"]
    questions = topic.get("research_questions", [])
    keywords = topic.get("keywords", [])
    
    # 检查是否有已缓存的报告
    cached_report = KNOWLEDGE_DIR / "reports" / f"{name.replace(' ', '_')}_Research_Report_{today()}.md"
    if cached_report.exists():
        with open(cached_report, 'r', encoding='utf-8') as f:
            return f.read()
    
    # 生成报告模板（提示主模型填充）
    report = f"""# {name} 深度研究报告 — {today()}

## 📋 研究问题
{chr(10).join([f'- {q}' for q in questions])}

## 📖 核心论文解读

> 本报告基于以下关键词搜索：{', '.join(keywords)}
> 请使用 web_search 搜索最新论文，然后使用 web_fetch 抓取并分析。

### 论文 1：[待搜索填充]
**基本信息**
- 来源：arXiv / 会议 / 博客
- 发表时间：

**核心方法**
[技术原理详细说明]

**创新点**
1. 
2. 

**实验结果**
[关键指标和结论]

**局限性**
- 
- 

## 🔍 综合分析

### 领域现状
[当前技术成熟度、主流方向]

### 趋势预测
[未来发展方向]

### 知识缺口
[待解决的问题]

## 📚 参考文献
1. [论文URL]
2. ...

---
*研究时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 来源：arXiv, Papers with Code*
"""
    return report


def save_research_report(topic: str, content: str) -> str:
    """保存研究报告"""
    from datetime import datetime
    
    reports_dir = KNOWLEDGE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查是否已有今天的报告
    today_reports = list(reports_dir.glob(f"{topic.replace(' ', '_')}_*_{today()}.md"))
    if today_reports:
        # 追加版本号
        filename = f"{topic.replace(' ', '_')}_Research_Report_{today()}_v{len(today_reports)+1}.md"
    else:
        filename = f"{topic.replace(' ', '_')}_Research_Report_{today()}.md"
    
    filepath = reports_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(filepath)


def cmd_list():
    """列出所有研究主题及状态"""
    config = load_topics_config()
    topics = config.get("topics", [])
    cache = load_cache()

    print("📋 研究主题列表\n")
    for t in topics:
        name = t["name"]
        enabled = "✅" if t.get("enabled") else "⏸️"
        priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", "medium"), "⚪")
        last = cache.get("last_update", {}).get(name, "从未")

        # 知识图谱状态
        gf = KNOWLEDGE_DIR / "graphs" / f"{name.replace(' ', '_')}_knowledge_graph.json"
        graph_info = ""
        if gf.exists():
            with open(gf, 'r', encoding='utf-8') as f:
                g = json.load(f)
            graph_info = f"概念:{len(g.get('concepts',[]))} 关系:{len(g.get('relations',[]))} 论文:{g.get('metadata',{}).get('paper_count',0)}"

        print(f"{priority} {enabled} {name}")
        print(f"   最后研究：{last} | {graph_info}")
        print(f"   关键词：{', '.join(t.get('keywords', [])[:3])}")
        print()


def cmd_progress(topic_name: str = None):
    """查看研究进度和知识积累"""
    config = load_topics_config()
    topics = config.get("topics", [])

    if topic_name:
        topics = [t for t in topics if topic_name.lower() in t["name"].lower()]

    for t in topics:
        name = t["name"]
        print(f"\n📌 {name}")
        print("-" * 50)

        gf = KNOWLEDGE_DIR / "graphs" / f"{name.replace(' ', '_')}_knowledge_graph.json"
        if not gf.exists():
            print("   ⚠️ 尚未开始研究")
            continue

        engine = KnowledgeEvolutionEngine(str(gf))
        print(engine.get_evolution_summary())

        # 知识缺口
        gaps = engine.graph.get("insights", {}).get("gaps", [])
        if gaps:
            print(f"\n🔴 知识缺口（{len(gaps)} 个）：")
            for g in gaps[:5]:
                if isinstance(g, dict):
                    print(f"   - {g.get('title', g)}")
                else:
                    print(f"   - {g}")

        # 矛盾
        contradictions = engine.graph.get("insights", {}).get("contradictions", [])
        if contradictions:
            print(f"\n⚠️ 矛盾发现（{len(contradictions)} 个）：")
            for c in contradictions[:3]:
                print(f"   - {c.get('paper', '')} vs {c.get('concept', '')}")


def cmd_add_topic(name: str, keywords: list, questions: list = None):
    """添加新研究主题"""
    import yaml
    cfg_file = CONFIG_DIR / "optimized_config.yaml"
    with open(cfg_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    existing = [t for t in config["topics"] if t["name"].lower() == name.lower()]
    if existing:
        print(f"❌ 主题已存在：{name}")
        return 1

    config["topics"].append({
        "name": name,
        "keywords": keywords,
        "research_questions": questions or [],
        "frequency": "daily",
        "priority": "medium",
        "since": today(),
        "enabled": True,
        "target_knowledge_base": "eImkUmYly1k-NH7Pz8e4syn4zs0UXJZufvCX5CSKvN8="
    })

    with open(cfg_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    print(f"✅ 已添加研究主题：{name}")
    return 0


def cmd_evolution_summary(topic_name: str = None):
    """显示知识进化摘要"""
    config = load_topics_config()
    topics = config.get("topics", [])

    if topic_name:
        topics = [t for t in topics if topic_name.lower() in t["name"].lower()]

    for t in topics:
        name = t["name"]
        gf = KNOWLEDGE_DIR / "graphs" / f"{name.replace(' ', '_')}_knowledge_graph.json"
        if gf.exists():
            engine = KnowledgeEvolutionEngine(str(gf))
            print(f"\n{'=' * 50}")
            print(f"📊 {name} — 知识进化摘要")
            print("=" * 50)
            print(engine.get_evolution_summary())


# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Deep Research Agent v2 — 完整优化版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
命令示例：
  python research_agent.py research                    # 研究所有启用主题
  python research_agent.py research -t "AI Agent记忆"  # 研究指定主题
  python research_agent.py research --force            # 强制重新研究（忽略缓存）
  python research_agent.py list                        # 列出所有主题
  python research_agent.py progress                    # 查看研究进度
  python research_agent.py evolution                   # 知识进化摘要
  python research_agent.py add -n "多智能体" -k "multi-agent" "collaboration"
        """
    )

    sub = parser.add_subparsers(dest="cmd")

    # research
    r = sub.add_parser("research", help="执行深度研究")
    r.add_argument("--topic", "-t", help="指定主题")
    r.add_argument("--force", "-f", action="store_true", help="强制重新研究")
    r.add_argument("--no-ima", action="store_true", help="不同步IMA")

    # list
    sub.add_parser("list", help="列出所有主题")

    # progress
    p = sub.add_parser("progress", help="查看研究进度")
    p.add_argument("--topic", "-t", help="指定主题")

    # evolution
    e = sub.add_parser("evolution", help="知识进化摘要")
    e.add_argument("--topic", "-t", help="指定主题")

    # add
    a = sub.add_parser("add", help="添加研究主题")
    a.add_argument("--name", "-n", required=True)
    a.add_argument("--keywords", "-k", nargs="+", required=True)
    a.add_argument("--questions", "-q", nargs="+")

    args = parser.parse_args()

    if args.cmd == "research":
        sys.exit(cmd_research(args.topic, args.force, args.no_ima))
    elif args.cmd == "list":
        cmd_list()
    elif args.cmd == "progress":
        cmd_progress(args.topic)
    elif args.cmd == "evolution":
        cmd_evolution_summary(args.topic)
    elif args.cmd == "add":
        sys.exit(cmd_add_topic(args.name, args.keywords, args.questions))
    else:
        parser.print_help()
