#!/usr/bin/env python3
"""
记忆自动压缩器
基于 Karpathy 的"迭代优化"原则
- 定期压缩旧数据
- 提取核心要点
- 归档详细内容
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
ARCHIVE_DIR = SKILL_DIR / ".archive"

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
    
    def compress_all(self) -> Dict:
        """压缩所有题材的记忆"""
        results = {
            "topics_compressed": 0,
            "reports_archived": 0,
            "concepts_archived": 0,
            "saved_tokens": 0
        }
        
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            
            result = self.compress_topic(topic_dir.name)
            if result["compressed"]:
                results["topics_compressed"] += 1
                results["reports_archived"] += result["reports_archived"]
                results["concepts_archived"] += result["concepts_archived"]
                results["saved_tokens"] += result["saved_tokens"]
        
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
            "saved_tokens": 0
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
        archive = reports[:-CONFIG["report_max_in_topic"] or []
        
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
        """生成报告摘要"""
        lines = content.split('\n')
        
        # 提取核心信息
        summary_lines = ["# 报告摘要\n"]
        
        for line in lines:
            if line.startswith('# ') or line.startswith('## '):
                summary_lines.append(line + '\n')
            elif any(kw in line for kw in ['论文', '发现', '概念', '方法']):
                if len(line) < 200:
                    summary_lines.append(line + '\n')
        
        return ''.join(summary_lines[:20])  # 最多20行
    
    def _compress_graph(self, topic_path: Path) -> Dict:
        """压缩知识图谱"""
        graph_dir = topic_path / "knowledge" / "graphs"
        if not graph_dir.exists():
            return {"concepts_archived": 0}
        
        graph_files = list(graph_dir.glob("*_knowledge_graph.json"))
        if not graph_files:
            return {"concepts_archived": 0}
        
        graph_path = graph_files[0]
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
        
        concepts = graph.get("concepts", [])
        
        # 检查是否需要压缩
        if len(concepts) <= CONFIG["graph_compress_threshold"]:
            return {"concepts_archived": 0}
        
        # 归档详细概念
        archive_dir = ARCHIVE_DIR / topic_path.name / "concepts"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 保留核心概念
        core = concepts[-CONFIG["graph_keep_core"]:]
        archived = concepts[:-CONFIG["graph_keep_core"]]
        
        # 保存归档的概念详情
        archive_file = archive_dir / f"archived_{datetime.now().strftime('%Y%m%d')}.json"
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archived, f, ensure_ascii=False, indent=2)
        
        # 更新图谱
        graph["concepts"] = core
        graph["metadata"]["concept_count"] = len(core)
        graph["metadata"]["archived_count"] = len(archived)
        graph["metadata"]["last_compressed"] = datetime.now().isoformat()
        
        with open(graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
        
        return {"concepts_archived": len(archived)}
    
    def restore_report(self, topic_id: str, report_name: str) -> bool:
        """恢复归档的报告"""
        archive_dir = ARCHIVE_DIR / topic_id / "reports"
        summary_file = archive_dir / f"{report_name}_summary.md"
        
        if not summary_file.exists():
            return False
        
        # 复制摘要到报告目录
        reports_dir = TOPICS_DIR / topic_id / "knowledge" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(summary_file, reports_dir / f"{report_name}.md")
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