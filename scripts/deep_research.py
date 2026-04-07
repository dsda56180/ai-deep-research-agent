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

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from opencode_runner import run_deep_research, load_topics
from ima_sync import sync_report_to_ima
from knowledge_graph import get_or_create_graph

# ============================================
# 配置
# ============================================

SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"

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
        topics = [t for t in topics if topic_name.lower() in t["name"].lower()]
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
        topics = [t for t in topics if topic_name.lower() in t["name"].lower()]
    
    for topic in topics:
        print(f"\n📌 {topic['name']}")
        print("-" * 40)
        
        # 检查知识图谱
        graph_file = KNOWLEDGE_DIR / "graphs" / f"{topic['name'].replace(' ', '_')}_knowledge_graph.json"
        if graph_file.exists():
            with open(graph_file, 'r', encoding='utf-8') as f:
                graph = json.load(f)
            print(f"   📊 概念: {len(graph.get('concepts', []))}")
            print(f"   🔗 关系: {len(graph.get('relations', []))}")
            print(f"   📄 论文: {graph.get('metadata', {}).get('paper_count', 0)}")
            print(f"   🕐 更新: {graph.get('metadata', {}).get('updated', 'N/A')[:10]}")
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
    
    args = parser.parse_args()
    
    if args.command == "research":
        sys.exit(cmd_deep_research(args.topic, not args.no_ima))
    elif args.command == "list":
        cmd_list_topics()
    elif args.command == "progress":
        cmd_research_progress(args.topic)
    elif args.command == "add":
        sys.exit(cmd_add_topic(args.name, args.keywords, args.questions))
    else:
        parser.print_help()
        sys.exit(1)