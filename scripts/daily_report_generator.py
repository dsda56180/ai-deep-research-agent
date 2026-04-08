#!/usr/bin/env python3
"""
每日报告生成器
确保每天生成新的研究报告
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"

# ============================================
# 报告生成器
# ============================================

class DailyReportGenerator:
    """每日研究报告生成器"""
    
    def __init__(self):
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.today_short = datetime.now().strftime('%Y-%m-%d')
    
    def get_latest_report(self, topic_id: str) -> Optional[Path]:
        """获取最新报告路径"""
        reports_dir = TOPICS_DIR / topic_id / "knowledge" / "reports"
        if not reports_dir.exists():
            return None
        
        reports = list(reports_dir.glob("*.md"))
        if not reports:
            return None
        
        # 按修改时间排序，返回最新的
        latest = max(reports, key=lambda p: p.stat().st_mtime)
        return latest
    
    def is_today_report_exists(self, topic_id: str) -> bool:
        """检查今天是否已有报告"""
        reports_dir = TOPICS_DIR / topic_id / "knowledge" / "reports"
        if not reports_dir.exists():
            return False
        
        # 检查是否有今天日期的报告
        pattern = f"*_{self.today}*.md"
        today_reports = list(reports_dir.glob(pattern))
        return len(today_reports) > 0
    
    def generate_daily_report(self, topic_id: str, research_data: Dict) -> Path:
        """
        生成每日研究报告
        
        Args:
            topic_id: 题材ID
            research_data: 研究数据，包含 keywords, papers, findings 等
        
        Returns:
            生成的报告路径
        """
        reports_dir = TOPICS_DIR / topic_id / "knowledge" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        filename = f"{topic_id}_Research_{self.today}.md"
        report_path = reports_dir / filename
        
        # 生成报告内容
        content = self._build_report_content(topic_id, research_data)
        
        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 报告已生成：{filename}")
        return report_path
    
    def _build_report_content(self, topic_id: str, data: Dict) -> str:
        """构建报告内容"""
        lines = [
            f"# {topic_id} 研究日报",
            "",
            f"**日期**: {self.today}",
            f"**更新时间**: {datetime.now().strftime('%H:%M:%S')}",
            "",
            "---",
            "",
            "## 📊 研究概览",
            "",
        ]
        
        # 研究关键词
        if "keywords" in data:
            lines.append("### 搜索关键词")
            for kw in data["keywords"]:
                lines.append(f"- {kw}")
            lines.append("")
        
        # 论文列表
        if "papers" in data:
            lines.append("### 最新论文")
            for i, paper in enumerate(data["papers"], 1):
                lines.append(f"**{i}. {paper.get('title', 'N/A')}**")
                if paper.get("url"):
                    lines.append(f"   - URL: {paper['url']}")
                if paper.get("date"):
                    lines.append(f"   - 日期: {paper['date']}")
                lines.append("")
        
        # 核心发现
        if "findings" in data:
            lines.append("## 🔍 核心发现")
            lines.append("")
            for finding in data["findings"]:
                lines.append(f"### {finding.get('title', '发现')}")
                lines.append(finding.get('description', ''))
                if finding.get('source'):
                    lines.append(f"**来源**: {finding['source']}")
                lines.append("")
        
        # 知识图谱更新
        if "graph_updates" in data:
            lines.append("## 🧠 知识图谱更新")
            updates = data["graph_updates"]
            if "new_concepts" in updates:
                lines.append(f"- 新增概念：{updates['new_concepts']} 个")
            if "new_relations" in updates:
                lines.append(f"- 新增关系：{updates['new_relations']} 条")
            lines.append("")
        
        # 学习记录
        if "learnings" in data:
            lines.append("## 📝 学习记录")
            for learning in data["learnings"]:
                lines.append(f"- {learning}")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        return "\n".join(lines)
    
    def update_topic_index(self, topic_id: str):
        """更新题材索引"""
        reports_dir = TOPICS_DIR / topic_id / "knowledge" / "reports"
        if not reports_dir.exists():
            return
        
        # 获取所有报告，按时间排序
        reports = sorted(
            reports_dir.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # 生成索引内容
        lines = [
            f"# {topic_id} - 研究报告索引",
            "",
            f"**最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"**报告总数**: {len(reports)}",
            "",
            "---",
            "",
            "## 📚 报告列表（最新在前）",
            ""
        ]
        
        for report in reports[:20]:  # 只显示最近20个
            date = datetime.fromtimestamp(report.stat().st_mtime).strftime('%Y-%m-%d')
            name = report.stem
            lines.append(f"- [{name}](reports/{report.name}) - {date}")
        
        index_path = TOPICS_DIR / topic_id / "knowledge" / "index.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        print(f"✅ 索引已更新：{len(reports)} 个报告")

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="每日报告生成器")
    sub = parser.add_subparsers(dest="cmd")
    
    # 检查今天报告
    check_parser = sub.add_parser("check", help="检查今天报告是否存在")
    check_parser.add_argument("--topic", required=True)
    
    # 生成报告
    gen_parser = sub.add_parser("generate", help="生成今日报告")
    gen_parser.add_argument("--topic", required=True)
    
    # 更新索引
    index_parser = sub.add_parser("index", help="更新报告索引")
    index_parser.add_argument("--topic", required=True)
    
    args = parser.parse_args()
    
    generator = DailyReportGenerator()
    
    if args.cmd == "check":
        exists = generator.is_today_report_exists(args.topic)
        if exists:
            print(f"✅ 今天已有报告：{args.topic}")
        else:
            print(f"❌ 今天没有报告：{args.topic}")
    
    elif args.cmd == "generate":
        # 示例数据，实际使用时由主流程传入
        sample_data = {
            "keywords": ["AI agent memory", "MemGPT", "context window"],
            "findings": [
                {
                    "title": "记忆系统新进展",
                    "description": "主流Agent框架持续优化记忆管理机制",
                    "source": "研究汇总"
                }
            ]
        }
        path = generator.generate_daily_report(args.topic, sample_data)
        generator.update_topic_index(args.topic)
    
    elif args.cmd == "index":
        generator.update_topic_index(args.topic)