#!/usr/bin/env python3
"""
AI Deep Research Agent 主入口
基于 OpenCode + Oh My OpenCode 实现深度研究
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"
DEFAULT_KB_ID = ""

sys.path.insert(0, str(SCRIPT_DIR))

from direct_researcher import execute_direct_research, load_cache
from knowledge_graph import get_or_create_graph, resolve_graph_location
from global_graph import GlobalKnowledgeGraph


def load_topic_graph(topic_name: str):
    resolved_topic, graph_dir, graph_filename = resolve_graph_location(topic_name)
    return get_or_create_graph(resolved_topic, base_dir=graph_dir, filename=graph_filename)


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


def load_topics() -> List[Dict]:
    import yaml
    config_paths = [
        CONFIG_DIR / "optimized_config.yaml",
        CONFIG_DIR / "topics.yaml",
    ]
    topics = []
    for topics_file in config_paths:
        if not topics_file.exists():
            continue
        with open(topics_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        for topic in config.get("topics", []):
            topic_tokens = {
                normalize_topic_label(topic.get("id", "")),
                normalize_topic_label(topic.get("name", "")),
            } - {""}
            existing_topic = next(
                (
                    item for item in topics
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
            topics.append(dict(topic))
    return topics


def run_deep_research(topic_name: str = None) -> Dict:
    topics = [topic for topic in load_topics() if topic.get("enabled", True)]
    if topic_name:
        topics = [topic for topic in topics if topic_matches(topic, topic_name)]
    reports = []
    cache = load_cache()
    reports_dir = KNOWLEDGE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    for topic in topics:
        result = execute_direct_research(
            topic=topic["name"],
            keywords=topic.get("keywords", []),
            research_questions=topic.get("research_questions", []),
        )
        report_path = reports_dir / f"{topic['name'].replace(' ', '_')}_Deep_Research_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False, indent=2))
        reports.append({
            "topic": topic["name"],
            "success": result.get("success", False),
            "report_path": str(report_path),
            "cached": result.get("cached", False),
        })
    return {
        "success": all(item["success"] for item in reports) if reports else False,
        "reports": reports,
        "cache_snapshot": cache.get("last_update", {}),
    }

# ============================================
# 核心命令
# ============================================

def cmd_deep_research(topic_name: str = None, sync_ima: bool = True):
    """
    执行深度研究
    
    Args:
        topic_name: 研究主题名称（可选）
        sync_ima: 是否同步到 IMA 知识库
    """
    print("=" * 60)
    print("🔬 AI Deep Research Agent — 深度研究系统")
    print(f"   基于 OpenCode + Oh My OpenCode 多智能体架构")
    print(f"   知识固化: IMA 知识库")
    print("=" * 60)
    
    # 加载研究主题
    import yaml
    topics_file = CONFIG_DIR / "topics.yaml"
    with open(topics_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    topics = [t for t in config.get("topics", []) if t.get("enabled", True)]
    
    if topic_name:
        topics = [t for t in topics if topic_matches(t, topic_name)]
        if not topics:
            print(f"❌ 未找到研究主题: {topic_name}")
            return 1
    
    # 执行研究
    result = run_deep_research(topic_name)
    
    if not result["success"]:
        print(f"\n❌ 研究任务失败")
        return 1
    
    # 固化到 IMA 知识库
    if sync_ima:
        from ima_knowledge_solidifier import IMAKnowledgeBase
        
        for report in result["reports"]:
            if report["success"]:
                topic_config = next(
                    (t for t in topics if t["name"] == report["topic"]), 
                    None
                )
                kb_id = topic_config.get("target_knowledge_base", DEFAULT_KB_ID) if topic_config else DEFAULT_KB_ID
                if not kb_id:
                    print("   ⚠️ 未配置目标知识库，跳过 IMA 固化")
                    continue
                
                print(f"\n📤 固化到 IMA 知识库...")
                
                try:
                    kb = IMAKnowledgeBase(kb_id)
                    
                    # 固化研究报告和知识图谱
                    graph_file = KNOWLEDGE_DIR / "graphs" / f"{report['topic'].replace(' ', '_')}_knowledge_graph.json"
                    
                    sync_result = kb.solidify_research(
                        report["topic"],
                        report_path=report["report_path"],
                        graph_path=str(graph_file) if graph_file.exists() else None
                    )
                    
                    if sync_result["success"]:
                        print(f"   ✅ 知识已固化到 IMA")
                    else:
                        print(f"   ⚠️ 部分固化失败: {sync_result['errors']}")
                        
                except Exception as e:
                    print(f"   ❌ IMA 同步异常: {e}")
    
    print(f"\n✅ 深度研究完成！知识已固化到 IMA 知识库")
    return 0


def cmd_list_topics():
    """列出所有研究主题"""
    topics = load_topics()
    
    print("📋 已配置的研究主题：")
    print("-" * 40)
    
    for topic in topics:
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        status = "✅ 启用" if topic.get("enabled", True) else "⏸️ 暂停"
        
        print(f"\n{priority_emoji.get(topic.get('priority', 'medium'), '⚪')} {topic['name']}")
        print(f"   状态: {status}")
        print(f"   频率: {topic.get('frequency', 'daily')}")
        print(f"   关键词: {', '.join(topic.get('keywords', [])[:3])}")
        print(f"   研究问题: {len(topic.get('research_questions', []))} 个")


def cmd_research_progress(topic_name: str = None):
    """显示研究进度"""
    topics = load_topics()
    
    if topic_name:
        topics = [t for t in topics if topic_matches(t, topic_name)]
    
    for topic in topics:
        print(f"\n📌 {topic['name']}")
        print("-" * 40)
        
        # 检查知识图谱
        graph_file = KNOWLEDGE_DIR / "graphs" / f"{topic['name'].replace(' ', '_')}_knowledge_graph.json"
        if graph_file.exists():
            graph = load_topic_graph(topic["name"])
            stats = graph.graph_stats()
            print(f"   📊 实体: {stats.get('entities', 0)}")
            print(f"   🔗 关系: {stats.get('edges', 0)}")
            print(f"   🧩 社区: {stats.get('communities', 0)}")
            print(f"   📄 文档: {stats.get('documents', 0)}")
            print(f"   🕐 更新: {(stats.get('updated', 'N/A') or 'N/A')[:10]}")
        else:
            print("   ⚠️ 尚未开始研究")
        
        # 检查报告
        reports_dir = KNOWLEDGE_DIR / "reports"
        if reports_dir.exists():
            reports = list(reports_dir.glob(f"{topic['name'].replace(' ', '_')}*.md"))
            print(f"   📝 研究报告: {len(reports)} 份")


def cmd_add_topic(name: str, keywords: list, questions: list = None):
    """添加研究主题"""
    import yaml
    
    topics_file = CONFIG_DIR / "topics.yaml"
    with open(topics_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查是否已存在
    existing = [t for t in config["topics"] if t["name"].lower() == name.lower()]
    if existing:
        print(f"❌ 研究主题已存在: {name}")
        return 1
    
    # 添加新主题
    new_topic = {
        "name": name,
        "keywords": keywords,
        "research_questions": questions or [],
        "frequency": "daily",
        "priority": "medium",
        "since": datetime.now().strftime("%Y-%m-%d"),
        "enabled": True
    }
    
    config["topics"].append(new_topic)
    
    with open(topics_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✅ 已添加研究主题: {name}")
    print(f"   关键词: {', '.join(keywords[:5])}")
    return 0


def cmd_graph(topic_name: str, action: str, text: str = "", output: str = "", mode: str = "bfs", depth: int = 2, budget: int = 1600, limit: int = 10, target: str = "", from_node: str = "", to_node: str = ""):
    graph = load_topic_graph(topic_name)
    if action == "stats":
        print(json.dumps(graph.graph_stats(), ensure_ascii=False, indent=2))
    elif action == "query":
        print(json.dumps([entity.to_dict() for entity in graph.search_entities(text, limit=limit)], ensure_ascii=False, indent=2))
    elif action == "navigate":
        print(json.dumps(graph.query_graph(text or topic_name, mode=mode, depth=depth, token_budget=budget, top_k=limit), ensure_ascii=False, indent=2))
    elif action == "benchmark":
        print(json.dumps(graph.benchmark_context([text] if text else None, mode=mode, depth=depth, token_budget=budget), ensure_ascii=False, indent=2))
    elif action == "neighbors":
        print(json.dumps(graph.get_neighbors(target or text, limit=limit), ensure_ascii=False, indent=2))
    elif action == "path":
        print(json.dumps(graph.shortest_path(from_node, to_node, max_hops=max(4, depth * 2)), ensure_ascii=False, indent=2))
    elif action == "export":
        if not output:
            print("❌ 请提供 --output")
            return 1
        result = {"path": str(graph.export_graphml(output))} if output.lower().endswith(".graphml") else graph.export_wiki(output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"❌ 不支持的图谱动作: {action}")
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
        print(f"❌ 不支持的全局动作: {action}")
        return 1
    return 0


# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Deep Research Agent — 基于 OpenCode 的深度研究系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行深度研究
  python deep_research.py research --topic "AI Agent 记忆系统"
  
  # 列出所有研究主题
  python deep_research.py list
  
  # 查看研究进度
  python deep_research.py progress
  
  # 添加新研究主题
  python deep_research.py add --name "多智能体协作" --keywords "multi-agent" "collaboration"
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # research 命令
    research_parser = subparsers.add_parser("research", help="执行深度研究")
    research_parser.add_argument("--topic", "-t", help="指定研究主题")
    research_parser.add_argument("--no-ima", action="store_true", help="不同步到 IMA")
    
    # list 命令
    subparsers.add_parser("list", help="列出所有研究主题")
    
    # progress 命令
    progress_parser = subparsers.add_parser("progress", help="查看研究进度")
    progress_parser.add_argument("--topic", "-t", help="指定研究主题")
    
    # add 命令
    add_parser = subparsers.add_parser("add", help="添加研究主题")
    add_parser.add_argument("--name", "-n", required=True, help="主题名称")
    add_parser.add_argument("--keywords", "-k", nargs="+", required=True, help="关键词")
    add_parser.add_argument("--questions", "-q", nargs="+", help="研究问题")

    graph_parser = subparsers.add_parser("graph", help="图谱统一入口")
    graph_parser.add_argument("--topic", "-t", required=True, help="主题名称")
    graph_parser.add_argument("--action", choices=["stats", "query", "navigate", "benchmark", "neighbors", "path", "export"], required=True)
    graph_parser.add_argument("--text", default="")
    graph_parser.add_argument("--target", default="")
    graph_parser.add_argument("--from-node", default="")
    graph_parser.add_argument("--to-node", default="")
    graph_parser.add_argument("--output", default="")
    graph_parser.add_argument("--mode", choices=["bfs", "dfs"], default="bfs")
    graph_parser.add_argument("--depth", type=int, default=2)
    graph_parser.add_argument("--budget", type=int, default=1600)
    graph_parser.add_argument("--limit", type=int, default=10)

    global_parser = subparsers.add_parser("global", help="全局图谱统一入口")
    global_parser.add_argument("--action", choices=["build", "summary", "shared", "search", "relations", "stats", "benchmark", "bootstrap"], required=True)
    global_parser.add_argument("--keyword", "-k", default="")
    global_parser.add_argument("--topic", "-t", default="")
    global_parser.add_argument("--limit", type=int, default=10)
    global_parser.add_argument("--force", action="store_true")
    
    args = parser.parse_args()
    
    if args.command == "research":
        sys.exit(cmd_deep_research(args.topic, not args.no_ima))
    elif args.command == "list":
        cmd_list_topics()
    elif args.command == "progress":
        cmd_research_progress(args.topic)
    elif args.command == "add":
        sys.exit(cmd_add_topic(args.name, args.keywords, args.questions))
    elif args.command == "graph":
        sys.exit(cmd_graph(args.topic, args.action, text=args.text, output=args.output, mode=args.mode, depth=args.depth, budget=args.budget, limit=args.limit, target=args.target, from_node=args.from_node, to_node=args.to_node))
    elif args.command == "global":
        sys.exit(cmd_global(args.action, keyword=args.keyword, topic_id=args.topic, limit=args.limit, force=args.force))
    else:
        parser.print_help()
        sys.exit(1)
