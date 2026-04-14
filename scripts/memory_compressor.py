#!/usr/bin/env python3
"""
记忆自动压缩器
基于 Karpathy 的"迭代优化"原则
- 定期压缩旧数据
- 提取核心要点
- 归档详细内容
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

from knowledge_graph import get_or_create_graph

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
ARCHIVE_DIR = SKILL_DIR / ".archive"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

# ============================================
# 压缩配置
# ============================================

CONFIG = {
    # 报告压缩阈值
    "report_threshold_days": 7,      # 7天前的报告压缩
    "report_keep_summary": True,        # 保留摘要
    "report_max_in_topic": 10,         # 每题材最多保留报告数
    
    # 知识图谱压缩
    "graph_compress_threshold": 50,    # 超过50个概念时压缩
    "graph_keep_core": 30,            # 保留核心30个概念
    "graph_archive_detail": True,      # 归档详细内容
    
    # 概念压缩
    "concept_keep_attributes": ["name", "type", "papers"],  # 保留属性
    
    # 自动执行
    "auto_compress_weekly": True       # 每周自动压缩
}

# ============================================
# 记忆压缩器
# ============================================

class MemoryCompressor:
    """记忆自动压缩器"""
    
    def __init__(self):
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    def should_compress_topic(self, topic_id: str) -> bool:
        topic_path = TOPICS_DIR / topic_id
        if not topic_path.exists():
            return False
        reports_dir = topic_path / "knowledge" / "reports"
        graph_dir = topic_path / "knowledge" / "graphs"
        report_pressure = False
        if reports_dir.exists():
            reports = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
            if len(reports) > CONFIG["report_max_in_topic"]:
                report_pressure = True
            elif reports:
                oldest = datetime.fromtimestamp(reports[0].stat().st_mtime)
                report_pressure = oldest <= datetime.now() - timedelta(days=CONFIG["report_threshold_days"])
        graph_pressure = False
        graph_files = list(graph_dir.glob("*_knowledge_graph.json")) if graph_dir.exists() else []
        if graph_files:
            graph = get_or_create_graph(topic_id, base_dir=graph_dir, filename=graph_files[0].name)
            last_compressed = graph.metadata.get("last_compressed")
            compressed_at = None
            if last_compressed:
                try:
                    compressed_at = datetime.fromisoformat(last_compressed)
                except ValueError:
                    compressed_at = None
            graph_pressure = len(graph.entities) > CONFIG["graph_compress_threshold"] or not compressed_at or (
                CONFIG["auto_compress_weekly"] and compressed_at <= datetime.now() - timedelta(days=7)
            )
        return report_pressure or graph_pressure

    def auto_compress_if_due(self, topic_id: str) -> Dict:
        if not CONFIG["auto_compress_weekly"] or not self.should_compress_topic(topic_id):
            return {"compressed": False, "reason": "not_due"}
        result = self.compress_topic(topic_id)
        result["reason"] = "scheduled"
        return result
    
    def compress_all(self) -> Dict:
        """压缩所有题材的记忆"""
        results = {
            "topics_compressed": 0,
            "reports_archived": 0,
            "concepts_archived": 0,
            "saved_tokens": 0,
            "summary_nodes_created": 0,
        }
        
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            
            result = self.auto_compress_if_due(topic_dir.name)
            if result["compressed"]:
                results["topics_compressed"] += 1
                results["reports_archived"] += result["reports_archived"]
                results["concepts_archived"] += result["concepts_archived"]
                results["saved_tokens"] += result["saved_tokens"]
                results["summary_nodes_created"] += result.get("summary_nodes_created", 0)
        
        return results
    
    def compress_topic(self, topic_id: str) -> Dict:
        """压缩单个题材"""
        topic_path = TOPICS_DIR / topic_id
        if not topic_path.exists():
            return {"compressed": False}
        
        results = {
            "compressed": True,
            "reports_archived": 0,
            "concepts_archived": 0,
            "saved_tokens": 0,
            "summary_nodes_created": 0,
        }
        
        # 1. 压缩旧报告
        report_result = self._compress_reports(topic_path)
        results.update(report_result)
        
        # 2. 压缩知识图谱
        graph_result = self._compress_graph(topic_path)
        results.update(graph_result)
        
        return results
    
    def _compress_reports(self, topic_path: Path) -> Dict:
        """压缩旧报告"""
        reports_dir = topic_path / "knowledge" / "reports"
        if not reports_dir.exists():
            return {"reports_archived": 0, "saved_tokens": 0}
        
        reports = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
        
        if len(reports) <= CONFIG["report_max_in_topic"]:
            return {"reports_archived": 0, "saved_tokens": 0}
        
        # 需要压缩
        archive_dir = ARCHIVE_DIR / topic_path.name / "reports"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archived = 0
        saved_tokens = 0
        
        # 保留最新的 N 个报告
        keep = reports[-CONFIG["report_max_in_topic"]:]
        archive = reports[:-CONFIG["report_max_in_topic"]] or []
        
        for old_report in archive:
            # 读取内容
            with open(old_report, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成摘要
            summary = self._generate_report_summary(content)
            
            # 保存摘要
            summary_file = archive_dir / f"{old_report.stem}_summary.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            # 移动原文到归档
            archive_file = archive_dir / old_report.name
            old_report.rename(archive_file)
            
            archived += 1
            saved_tokens += len(content) // 4  # 估算token节省
        
        return {"reports_archived": archived, "saved_tokens": saved_tokens}
    
    def _generate_report_summary(self, content: str) -> str:
        lines = [line.rstrip() for line in content.split('\n')]
        summary_lines = ["# 报告摘要", ""]
        headings = []
        evidence = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                headings.append(stripped)
                continue
            if any(token in stripped for token in ["论文", "发现", "概念", "方法", "创新", "局限", "缺口", "图谱"]):
                evidence.append(stripped)
                continue
            if stripped.startswith(("- ", "1.", "2.", "3.")) and len(stripped) <= 180:
                evidence.append(stripped)
        if headings:
            summary_lines.append("## 结构")
            summary_lines.extend(f"- {heading.lstrip('#').strip()}" for heading in headings[:8])
            summary_lines.append("")
        if evidence:
            summary_lines.append("## 关键要点")
            summary_lines.extend(f"- {item.lstrip('- ').strip()}" for item in evidence[:12])
            summary_lines.append("")
        summary_lines.append(f"## 统计")
        summary_lines.append(f"- 原始行数：{len(lines)}")
        summary_lines.append(f"- 摘要生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(summary_lines) + "\n"
    
    def _compress_graph(self, topic_path: Path) -> Dict:
        """压缩知识图谱"""
        graph_dir = topic_path / "knowledge" / "graphs"
        if not graph_dir.exists():
            return {"concepts_archived": 0, "summary_nodes_created": 0}
        
        graph_files = list(graph_dir.glob("*_knowledge_graph.json"))
        if not graph_files:
            return {"concepts_archived": 0, "summary_nodes_created": 0}

        graph_path = graph_files[0]
        graph = get_or_create_graph(topic_path.name, base_dir=graph_dir, filename=graph_path.name)
        initial_entities = len(graph.entities)
        graph.compute_communities()
        summary_nodes = graph.create_summary_nodes()
        graph.assign_layers()
        if len(graph.entities) <= CONFIG["graph_compress_threshold"]:
            graph.metadata["last_compressed"] = datetime.now().isoformat()
            graph.save(str(graph_path))
            return {"concepts_archived": 0, "summary_nodes_created": len(summary_nodes)}

        archive_dir = ARCHIVE_DIR / topic_path.name / "concepts"
        archive_dir.mkdir(parents=True, exist_ok=True)
        buckets = graph.collect_layer_buckets()
        archived_entities = buckets.get("cold", [])
        if not archived_entities:
            graph.metadata["last_compressed"] = datetime.now().isoformat()
            graph.save(str(graph_path))
            return {"concepts_archived": 0, "summary_nodes_created": len(summary_nodes)}

        archive_file = archive_dir / f"archived_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        archive_payload = {
            "topic": topic_path.name,
            "archived_at": datetime.now().isoformat(),
            "layers": {layer: len(items) for layer, items in buckets.items()},
            "entities": archived_entities,
            "edges": [
                edge.to_dict()
                for edge in graph.edges
                if edge.from_id in {item["id"] for item in archived_entities} or edge.to_id in {item["id"] for item in archived_entities}
            ],
        }
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archive_payload, f, ensure_ascii=False, indent=2)

        archived_ids = {item["id"] for item in archived_entities}
        retained_entities = {
            entity_id: entity
            for entity_id, entity in graph.entities.items()
            if entity_id not in archived_ids or entity.type == "CommunitySummary"
        }
        graph.entities = retained_entities
        graph.edges = [
            edge for edge in graph.edges
            if edge.from_id in graph.entities and edge.to_id in graph.entities
        ]
        graph.alias_index = {}
        for entity in graph.entities.values():
            graph._register_aliases(entity)
        graph.metadata["archived_count"] = graph.metadata.get("archived_count", 0) + len(archived_entities)
        graph.metadata["last_compressed"] = datetime.now().isoformat()
        graph.metadata["compression"] = {
            "before_entities": initial_entities,
            "after_entities": len(graph.entities),
            "archived_entities": len(archived_entities),
            "summary_nodes_created": len(summary_nodes),
        }
        graph.save(str(graph_path))

        return {"concepts_archived": len(archived_entities), "summary_nodes_created": len(summary_nodes)}
    
    def restore_report(self, topic_id: str, report_name: str) -> bool:
        """恢复归档的报告"""
        archive_dir = ARCHIVE_DIR / topic_id / "reports"
        archive_file = archive_dir / f"{report_name}.md"
        summary_file = archive_dir / f"{report_name}_summary.md"

        if not archive_file.exists() and not summary_file.exists():
            return False

        reports_dir = TOPICS_DIR / topic_id / "knowledge" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        source_file = archive_file if archive_file.exists() else summary_file
        shutil.copy2(source_file, reports_dir / f"{report_name}.md")
        return True

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="记忆压缩器")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("compress", help="压缩所有题材")
    sub.add_parser("status", help="查看压缩状态")
    
    compress_parser = sub.add_parser("compress-topic", help="压缩指定题材")
    compress_parser.add_argument("topic_id")
    
    args = parser.parse_args()
    
    compressor = MemoryCompressor()
    
    if args.cmd == "compress":
        results = compressor.compress_all()
        print("✅ 压缩完成\n")
        print(f"压缩题材：{results['topics_compressed']} 个")
        print(f"归档报告：{results['reports_archived']} 个")
        print(f"归档概念：{results['concepts_archived']} 个")
        print(f"摘要节点：{results['summary_nodes_created']} 个")
        print(f"节省Token：~{results['saved_tokens']:,}")
    
    elif args.cmd == "status":
        print("📊 压缩状态\n")
        print(f"归档目录：{ARCHIVE_DIR}")
        
        # 统计归档内容
        archived_reports = list(ARCHIVE_DIR.glob("*/reports/*.md"))
        archived_concepts = list(ARCHIVE_DIR.glob("*/concepts/*.json"))
        
        print(f"\n归档报告：{len(archived_reports)} 个")
        print(f"归档概念：{len(archived_concepts)} 个")
    
    elif args.cmd == "compress-topic":
        result = compressor.compress_topic(args.topic_id)
        if result["compressed"]:
            print(f"✅ {args.topic_id} 压缩完成")
            print(f"归档报告：{result['reports_archived']} 个")
            print(f"归档概念：{result['concepts_archived']} 个")
            print(f"摘要节点：{result.get('summary_nodes_created', 0)} 个")
