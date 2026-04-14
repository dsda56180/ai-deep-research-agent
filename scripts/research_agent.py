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
from knowledge_graph import get_or_create_graph, resolve_graph_location
from ima_knowledge_solidifier import IMAKnowledgeBase
from global_graph import GlobalKnowledgeGraph
from evolution import control_scheduler_topic, get_scheduler_status, run_batch_evolution, run_scheduled_evolution

# ============================================
# 工具函数
# ============================================

def load_topics_config():
    import yaml
    config_paths = [
        CONFIG_DIR / "optimized_config.yaml",
        CONFIG_DIR / "topics.yaml",
    ]
    merged = {}
    merged_topics = []
    for cfg_file in config_paths:
        if not cfg_file.exists():
            continue
        with open(cfg_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        for key, value in config.items():
            if key == "topics":
                continue
            if key not in merged:
                merged[key] = value
        for topic in config.get("topics", []):
            topic_tokens = {
                normalize_topic_label(topic.get("id", "")),
                normalize_topic_label(topic.get("name", "")),
            } - {""}
            existing_topic = next(
                (
                    item for item in merged_topics
                    if topic_tokens & ({
                        normalize_topic_label(item.get("id", "")),
                        normalize_topic_label(item.get("name", "")),
                    } - {""})
                ),
                None,
            )
            if existing_topic:
                for key, value in topic.items():
                    if value not in (None, "", [], {}):
                        existing_topic[key] = value
                continue
            merged_topics.append(dict(topic))
    merged["topics"] = merged_topics
    return merged

def today():
    return datetime.now().strftime("%Y-%m-%d")

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_topic_label(value: str) -> str:
    return "".join(ch for ch in (value or "").lower() if ch not in {" ", "-", "_"})


def topic_matches(topic: Dict, query: str) -> bool:
    if not query:
        return True
    resolved_name, _, resolved_file = resolve_graph_location(query)
    query_labels = {
        query,
        resolved_name,
        Path(resolved_file).stem.replace("_knowledge_graph", ""),
    }
    topic_labels = {
        topic.get("name", ""),
        topic.get("id", ""),
    }
    normalized_queries = {normalize_topic_label(item) for item in query_labels if item}
    normalized_topics = {normalize_topic_label(item) for item in topic_labels if item}
    return any(
        query_token and topic_token and (query_token in topic_token or topic_token in query_token)
        for query_token in normalized_queries
        for topic_token in normalized_topics
    )


def load_topic_graph(topic_name: str):
    resolved_topic, graph_dir, graph_filename = resolve_graph_location(topic_name)
    return get_or_create_graph(resolved_topic, base_dir=graph_dir, filename=graph_filename)


def build_evolution_snapshot(topic_name: str) -> Dict:
    graph = load_topic_graph(topic_name)
    graph.compute_communities()
    stats = graph.graph_stats()
    raw_graph_path = KNOWLEDGE_DIR / "graphs" / f"{topic_name.replace(' ', '_')}_knowledge_graph.json"
    insights = {}
    if raw_graph_path.exists():
        with open(raw_graph_path, 'r', encoding='utf-8') as f:
            insights = json.load(f).get("insights", {})
    summary_lines = [
        f"实体：{stats.get('entities', 0)}",
        f"关系：{stats.get('edges', 0)}",
        f"社区：{stats.get('communities', 0)}",
        f"文档：{stats.get('documents', 0)}",
        f"更新时间：{(stats.get('updated', 'N/A') or 'N/A')[:19]}",
    ]
    return {
        "summary": "\n".join(summary_lines),
        "insights": insights,
    }

# ============================================
# 核心命令
# ============================================

def cmd_research(topic_name: str = None, force: bool = False, no_ima: bool = False, ingest_path: str = "", query: str = "", budget: int = 1600):
    """统一研究入口，执行可自引导的批量演化闭环。"""
    print("=" * 60)
    print("🔬 AI Deep Research Agent v2 — 自主进化入口")
    print(f"   时间：{now()}")
    print("=" * 60)

    result = run_batch_evolution(
        topic_name=topic_name or "",
        force=force,
        ingest_path=ingest_path or None,
        query=query,
        budget=budget,
        sync=not no_ima,
    )

    if not result.get("processed_topics"):
        print(f"❌ {result.get('error', '没有可执行的主题')}")
        return 1

    print(f"\n{'=' * 60}")
    print(
        f"📊 完成：{result.get('succeeded_topics', 0)}/{result.get('processed_topics', 0)} 个主题"
        f" | 失败：{result.get('failed_topics', 0)}"
    )
    print("=" * 60)

    failed = [item for item in result.get("topics", []) if not item.get("success")]
    if failed:
        for item in failed:
            print(f"❌ {item.get('topic', item.get('topic_id', 'unknown'))}: {item.get('error', '执行失败')}")
        return 1
    return 0


def cmd_schedule(topic_name: str = None, force: bool = False, no_ima: bool = False, ingest_path: str = "", query: str = "", budget: int = 1600, loop: bool = False, interval_minutes: int = 60):
    """统一调度入口，按主题 frequency 执行自治演化。"""
    print("=" * 60)
    print("⏱️ AI Deep Research Agent v2 — 自治调度入口")
    print(f"   时间：{now()}")
    print("=" * 60)

    result = run_scheduled_evolution(
        topic_name=topic_name or "",
        force=force,
        ingest_path=ingest_path or None,
        query=query,
        budget=budget,
        sync=not no_ima,
        loop=loop,
        interval_minutes=interval_minutes,
    )

    if loop:
        return 0

    print(f"\n📌 到期主题：{len(result.get('due_topics', []))}")
    print(f"📌 跳过主题：{len(result.get('skipped_topics', []))}")
    print(f"📌 暂停主题：{len(result.get('paused_topics', []))}")
    if result.get("schedule"):
        print(
            "📌 调度策略："
            f" 每主题最多 {result['schedule'].get('retry_attempts_per_topic', 1)} 次尝试"
            f" | 本轮评估 {result['schedule'].get('evaluated_topics', 0)} 个主题"
        )
    if result.get("global_refresh", {}).get("updated"):
        print(f"📌 已刷新跨主题洞察：{result['global_refresh'].get('insights_path', '')}")
    paused = result.get("paused_topics", [])
    if paused:
        for item in paused[:5]:
            print(
                f"⏸️ {item.get('topic', item.get('topic_id', 'unknown'))}"
                f" | 原因：{item.get('pause_reason', 'paused')}"
                f" | 恢复时间：{item.get('paused_until', 'manual') or 'manual'}"
            )

    failed = [item for item in result.get("topics", []) if not item.get("success")]
    if failed:
        for item in failed:
            print(f"❌ {item.get('topic', item.get('topic_id', 'unknown'))}: {item.get('error', '执行失败')}")
        return 1
    return 0


def cmd_scheduler(action: str, topic_name: str = "", limit: int = 10, hours: int = 24):
    """查看或控制调度状态。"""
    print("=" * 60)
    print("🛰️ AI Deep Research Agent v2 — 调度状态中心")
    print(f"   时间：{now()}")
    print("=" * 60)

    if action == "status":
        result = get_scheduler_status(topic_name=topic_name or "", limit=limit)
        summary = result.get("summary", {})
        print(
            f"\n📊 启用主题：{summary.get('enabled_topics', 0)}"
            f" | 到期/待重试：{summary.get('due_topics', 0)}"
            f" | 暂停：{summary.get('paused_topics', 0)}"
            f" | 失败中：{summary.get('failing_topics', 0)}"
        )
        for item in result.get("topics", [])[:limit]:
            state = "paused" if item.get("paused") else "due" if item.get("due") or item.get("retry_due") else "idle"
            print(
                f" - {item.get('topic', item.get('topic_id', 'unknown'))}"
                f" | 状态：{state}"
                f" | 连续失败：{item.get('consecutive_failures', 0)}"
                f" | 下次运行：{item.get('next_run_at', '')}"
            )
        return 0

    result = control_scheduler_topic(action, topic_name=topic_name or "", hours=hours)
    if not result.get("success"):
        print(f"❌ {result.get('error', '调度控制失败')}")
        return 1
    print(
        f"\n✅ 已执行 {result.get('action')}：{result.get('topic', result.get('topic_id', 'unknown'))}"
        f"\n   暂停到：{result.get('state', {}).get('paused_until', '') or '未暂停'}"
        f"\n   连续失败：{result.get('state', {}).get('consecutive_failures', 0)}"
    )
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
        topics = [t for t in topics if topic_matches(t, topic_name)]

    for t in topics:
        name = t["name"]
        print(f"\n📌 {name}")
        print("-" * 50)

        gf = KNOWLEDGE_DIR / "graphs" / f"{name.replace(' ', '_')}_knowledge_graph.json"
        if not gf.exists():
            print("   ⚠️ 尚未开始研究")
            continue

        snapshot = build_evolution_snapshot(name)
        print(snapshot["summary"])

        # 知识缺口
        gaps = snapshot["insights"].get("gaps", [])
        if gaps:
            print(f"\n🔴 知识缺口（{len(gaps)} 个）：")
            for g in gaps[:5]:
                if isinstance(g, dict):
                    print(f"   - {g.get('title', g)}")
                else:
                    print(f"   - {g}")

        # 矛盾
        contradictions = snapshot["insights"].get("contradictions", [])
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
        topics = [t for t in topics if topic_matches(t, topic_name)]

    for t in topics:
        name = t["name"]
        gf = KNOWLEDGE_DIR / "graphs" / f"{name.replace(' ', '_')}_knowledge_graph.json"
        if gf.exists():
            print(f"\n{'=' * 50}")
            print(f"📊 {name} — 知识进化摘要")
            print("=" * 50)
            print(build_evolution_snapshot(name)["summary"])


def cmd_graph(topic_name: str, action: str, text: str = "", target: str = "", from_node: str = "", to_node: str = "", output: str = "", mode: str = "bfs", depth: int = 2, budget: int = 1600, limit: int = 10):
    graph = load_topic_graph(topic_name)
    if action == "stats":
        graph.compute_communities()
        print(json.dumps(graph.graph_stats(), ensure_ascii=False, indent=2))
    elif action == "query":
        print(json.dumps([entity.to_dict() for entity in graph.search_entities(text, limit=limit)], ensure_ascii=False, indent=2))
    elif action == "navigate":
        print(json.dumps(graph.query_graph(text or topic_name, mode=mode, depth=depth, token_budget=budget, top_k=limit), ensure_ascii=False, indent=2))
    elif action == "neighbors":
        print(json.dumps(graph.get_neighbors(target or text, limit=limit), ensure_ascii=False, indent=2))
    elif action == "path":
        print(json.dumps(graph.shortest_path(from_node, to_node, max_hops=max(4, depth * 2)), ensure_ascii=False, indent=2))
    elif action == "benchmark":
        print(json.dumps(graph.benchmark_context([text] if text else None, mode=mode, depth=depth, token_budget=budget), ensure_ascii=False, indent=2))
    elif action == "god-nodes":
        print(json.dumps(graph.god_nodes(top_n=limit), ensure_ascii=False, indent=2))
    elif action == "surprising":
        print(json.dumps(graph.surprising_connections(top_n=limit), ensure_ascii=False, indent=2))
    elif action == "export":
        if not output:
            print("❌ 请提供 --output")
            return 1
        if output.lower().endswith(".graphml"):
            result = {"path": str(graph.export_graphml(output))}
        else:
            result = graph.export_wiki(output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"❌ 不支持的图谱动作：{action}")
        return 1
    return 0


def cmd_global(action: str, keyword: str = "", topic_id: str = "", limit: int = 10, force: bool = False):
    graph = GlobalKnowledgeGraph()
    if action == "build":
        print(json.dumps(graph.build_from_topics(), ensure_ascii=False, indent=2))
    elif action == "summary":
        print(graph.get_summary())
    elif action == "shared":
        print(json.dumps(graph.get_shared_concepts()[:limit], ensure_ascii=False, indent=2))
    elif action == "search":
        print(json.dumps(graph.search_concept(keyword)[:limit], ensure_ascii=False, indent=2))
    elif action == "relations":
        print(json.dumps(graph.get_topic_relations(topic_id), ensure_ascii=False, indent=2))
    elif action == "stats":
        print(json.dumps(graph.topic_stats(topic_id), ensure_ascii=False, indent=2))
    elif action == "benchmark":
        print(json.dumps(graph.benchmark_all(limit=limit), ensure_ascii=False, indent=2))
    elif action == "bootstrap":
        result = graph.bootstrap_topics(topic_id=topic_id, force=force)
        result["global_stats"] = graph.build_from_topics().get("statistics", {})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"❌ 不支持的全局动作：{action}")
        return 1
    return 0


# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Deep Research Agent v2 — 完整优化版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
命令示例：
  python research_agent.py research                    # 研究所有启用主题
  python research_agent.py research -t "AI Agent记忆"  # 研究指定主题
  python research_agent.py research --force            # 强制重新研究（忽略缓存）
  python research_agent.py research --budget 2200      # 提高上下文预算
  python research_agent.py research --ingest-path d:\data\reports
  python research_agent.py schedule                   # 按 frequency 执行一次自治调度
  python research_agent.py schedule --loop            # 持续无人值守调度
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
    r.add_argument("--ingest-path", default="", help="指定真实 ingest 的文件或目录")
    r.add_argument("--query", default="", help="覆盖默认研究查询意图")
    r.add_argument("--budget", type=int, default=1600, help="project_context 上下文预算")

    # schedule
    sch = sub.add_parser("schedule", help="按 frequency 执行自治调度")
    sch.add_argument("--topic", "-t", default="")
    sch.add_argument("--force", "-f", action="store_true")
    sch.add_argument("--no-ima", action="store_true")
    sch.add_argument("--ingest-path", default="", help="指定真实 ingest 的文件或目录")
    sch.add_argument("--query", default="", help="覆盖默认研究查询意图")
    sch.add_argument("--budget", type=int, default=1600, help="project_context 上下文预算")
    sch.add_argument("--loop", action="store_true", help="持续运行调度器")
    sch.add_argument("--interval-minutes", type=int, default=60, help="循环模式下的调度间隔")

    # scheduler
    ctl = sub.add_parser("scheduler", help="查看或控制自治调度状态")
    ctl.add_argument("--action", choices=["status", "pause", "resume", "reset"], required=True)
    ctl.add_argument("--topic", "-t", default="")
    ctl.add_argument("--limit", type=int, default=10, help="status 模式展示的主题数量")
    ctl.add_argument("--hours", type=int, default=24, help="pause 模式的暂停小时数")

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

    # graph
    g = sub.add_parser("graph", help="统一图谱入口")
    g.add_argument("--topic", "-t", required=True)
    g.add_argument("--action", choices=["stats", "query", "navigate", "neighbors", "path", "benchmark", "god-nodes", "surprising", "export"], required=True)
    g.add_argument("--text", default="")
    g.add_argument("--target", default="")
    g.add_argument("--from-node", default="")
    g.add_argument("--to-node", default="")
    g.add_argument("--output", default="")
    g.add_argument("--mode", choices=["bfs", "dfs"], default="bfs")
    g.add_argument("--depth", type=int, default=2)
    g.add_argument("--budget", type=int, default=1600)
    g.add_argument("--limit", type=int, default=10)

    # global
    gg = sub.add_parser("global", help="全局知识图谱入口")
    gg.add_argument("--action", choices=["build", "summary", "shared", "search", "relations", "stats", "benchmark", "bootstrap"], required=True)
    gg.add_argument("--keyword", "-k", default="")
    gg.add_argument("--topic", "-t", default="")
    gg.add_argument("--limit", type=int, default=10)
    gg.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.cmd == "research":
        sys.exit(cmd_research(args.topic, args.force, args.no_ima, args.ingest_path, args.query, args.budget))
    elif args.cmd == "schedule":
        sys.exit(cmd_schedule(args.topic, args.force, args.no_ima, args.ingest_path, args.query, args.budget, args.loop, args.interval_minutes))
    elif args.cmd == "scheduler":
        sys.exit(cmd_scheduler(args.action, args.topic, args.limit, args.hours))
    elif args.cmd == "list":
        cmd_list()
    elif args.cmd == "progress":
        cmd_progress(args.topic)
    elif args.cmd == "evolution":
        cmd_evolution_summary(args.topic)
    elif args.cmd == "add":
        sys.exit(cmd_add_topic(args.name, args.keywords, args.questions))
    elif args.cmd == "graph":
        sys.exit(cmd_graph(args.topic, args.action, text=args.text, target=args.target, from_node=args.from_node, to_node=args.to_node, output=args.output, mode=args.mode, depth=args.depth, budget=args.budget, limit=args.limit))
    elif args.cmd == "global":
        sys.exit(cmd_global(args.action, keyword=args.keyword, topic_id=args.topic, limit=args.limit, force=args.force))
    else:
        parser.print_help()
