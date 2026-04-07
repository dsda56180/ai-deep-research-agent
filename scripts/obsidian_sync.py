#!/usr/bin/env python3
"""
Obsidian 同步模块
将研究成果导出到本地 Obsidian vault
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
GLOBAL_DIR = SKILL_DIR / "global"
EXPORTS_DIR = SKILL_DIR / "exports" / "obsidian"

# ============================================
# Obsidian 导出器
# ============================================

class ObsidianExporter:
    """Obsidian vault 导出器"""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = Path(vault_path) if vault_path else Path(os.environ.get("OBSIDIAN_VAULT", "D:/Obsidian/MyVault"))
        self.research_folder = self.vault_path / os.environ.get("OBSIDIAN_FOLDER", "AI Research")
        
        # 确保 vault 存在
        if not self.vault_path.exists():
            print(f"⚠️  Obsidian vault 不存在：{self.vault_path}")
            print(f"   请设置环境变量 OBSIDIAN_VAULT 或传入 vault_path")
        
        self.research_folder.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _slugify(self, text: str) -> str:
        """生成文件名友好的 slug"""
        # 移除特殊字符
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'\s+', '-', text)
        return text.strip('-')[:100]
    
    def _add_frontmatter(self, content: str, metadata: Dict) -> str:
        """添加 YAML frontmatter"""
        frontmatter = [
            "---",
            f"title: \"{metadata.get('title', 'Untitled')}\"",
            f"date: {metadata.get('date', datetime.now().strftime('%Y-%m-%d'))}",
            f"tags: [{', '.join(metadata.get('tags', []))}]",
            "---",
            ""
        ]
        return "\n".join(frontmatter) + content
    
    def _add_wikilinks(self, content: str, concepts: List[str]) -> str:
        """将概念转换为 Obsidian wikilinks"""
        for concept in concepts:
            # [[Concept]] 格式
            pattern = re.compile(re.escape(concept), re.IGNORECASE)
            content = pattern.sub(f"[[{concept}]]", content)
        return content
    
    # ========================================
    # 导出方法
    # ========================================
    
    def export_topic(self, topic_id: str) -> Dict:
        """
        导出单个题材到 Obsidian
        
        Returns:
            导出结果
        """
        topic_path = TOPICS_DIR / topic_id
        if not topic_path.exists():
            return {"error": f"题材不存在：{topic_id}"}
        
        # 创建题材文件夹
        topic_folder = self.research_folder / self._slugify(topic_id)
        topic_folder.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        # 1. 导出知识图谱
        graph_path = topic_path / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
        if graph_path.exists():
            graph_file = self._export_graph(topic_id, graph_path, topic_folder)
            exported_files.append(graph_file)
        
        # 2. 导出研究报告
        reports = list((topic_path / "knowledge" / "reports").glob("*.md"))
        for report in reports:
            report_file = self._export_report(report, topic_folder, topic_id)
            exported_files.append(report_file)
        
        # 3. 创建题材索引
        index_file = self._create_topic_index(topic_id, topic_folder, len(reports))
        exported_files.append(index_file)
        
        # 记录导出日志
        log_path = EXPORTS_DIR / f"{topic_id}_export_log.json"
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                "topic_id": topic_id,
                "exported_at": datetime.now().isoformat(),
                "files": [str(f) for f in exported_files],
                "vault_path": str(self.vault_path)
            }, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "topic_id": topic_id,
            "files": len(exported_files),
            "folder": str(topic_folder)
        }
    
    def _export_graph(self, topic_id: str, graph_path: Path, output_folder: Path) -> Path:
        """导出知识图谱"""
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph = json.load(f)
        
        # 生成 Markdown 格式
        lines = [
            f"# {topic_id} - 知识图谱",
            "",
            f"> 更新时间：{graph.get('metadata', {}).get('updated', 'N/A')[:10]}",
            "",
            "## 📊 统计",
            "",
            f"- 概念：{len(graph.get('concepts', []))} 个",
            f"- 关系：{len(graph.get('relations', []))} 条",
            f"- 论文：{graph.get('metadata', {}).get('paper_count', 0)} 篇",
            "",
            "## 💡 核心概念",
            ""
        ]
        
        concepts = []
        for c in graph.get("concepts", []):
            type_emoji = {"system": "🔧", "concept": "💡", "method": "⚙️"}.get(c.get("type", "concept"), "📌")
            lines.append(f"### {type_emoji} {c['name']}")
            concepts.append(c["name"])
            if c.get("description"):
                lines.append(f"{c['description'][:200]}")
            lines.append("")
        
        # 添加 frontmatter
        content = self._add_frontmatter("\n".join(lines), {
            "title": f"{topic_id} 知识图谱",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "tags": concepts[:10]
        })
        
        # 写入文件
        output_file = output_folder / f"{self._slugify(topic_id)}_graph.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file
    
    def _export_report(self, report_path: Path, output_folder: Path, topic_id: str) -> Path:
        """导出研究报告"""
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 添加 frontmatter
        content = self._add_frontmatter(content, {
            "title": report_path.stem,
            "date": datetime.now().strftime('%Y-%m-%d'),
            "tags": [topic_id, "research"]
        })
        
        # 写入文件
        output_file = output_folder / self._slugify(report_path.name)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file
    
    def _create_topic_index(self, topic_id: str, topic_folder: Path, reports_count: int) -> Path:
        """创建题材索引页"""
        lines = [
            f"# {topic_id}",
            "",
            f"> 研究进度追踪",
            "",
            "## 📊 概览",
            "",
            f"- 研究报告：{reports_count} 份",
            f"- 同步时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📂 内容",
            "",
            f"- [[{self._slugify(topic_id)}_graph|知识图谱]]",
            ""
        ]
        
        # 列出所有报告
        for f in topic_folder.glob("*.md"):
            if not f.name.endswith("_graph.md") and not f.name == "index.md":
                name = f.stem
                lines.append(f"- [[{name}]]")
        
        content = self._add_frontmatter("\n".join(lines), {
            "title": topic_id,
            "date": datetime.now().strftime('%Y-%m-%d'),
            "tags": [topic_id, "index"]
        })
        
        output_file = topic_folder / "index.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file
    
    def export_all_topics(self) -> Dict:
        """导出所有题材"""
        results = {
            "exported": [],
            "failed": [],
            "total": 0,
            "success_count": 0
        }
        
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            
            result = self.export_topic(topic_dir.name)
            results["total"] += 1
            
            if result.get("success"):
                results["exported"].append({
                    "topic_id": topic_dir.name,
                    "files": result["files"]
                })
                results["success_count"] += 1
            else:
                results["failed"].append({
                    "topic_id": topic_dir.name,
                    "error": result.get("error")
                })
        
        # 创建全局索引
        self._create_global_index(results)
        
        return results
    
    def _create_global_index(self, results: Dict):
        """创建全局研究索引"""
        lines = [
            "# AI 研究索引",
            "",
            f"> 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📊 统计",
            "",
            f"- 研究题材：{results['total']} 个",
            f"- 成功导出：{results['success_count']} 个",
            "",
            "## 📚 题材列表",
            ""
        ]
        
        for item in results["exported"]:
            lines.append(f"- [[{self._slugify(item['topic_id'])}/index|{item['topic_id']}]]")
        
        content = self._add_frontmatter("\n".join(lines), {
            "title": "AI 研究索引",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "tags": ["research", "index"]
        })
        
        output_file = self.research_folder / "index.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

# ============================================
# CLI 入口
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Obsidian 同步")
    parser.add_argument("action", choices=["export", "export-all", "status"])
    parser.add_argument("--topic", "-t", help="题材 ID")
    parser.add_argument("--vault", "-v", help="Obsidian vault 路径")
    
    args = parser.parse_args()
    
    exporter = ObsidianExporter(args.vault)
    
    if args.action == "export":
        if not args.topic:
            print("请提供 --topic")
            return
        result = exporter.export_topic(args.topic)
        if result.get("success"):
            print(f"✅ 导出成功：{result['files']} 个文件")
            print(f"   文件夹：{result['folder']}")
        else:
            print(f"❌ 导出失败：{result.get('error')}")
    
    elif args.action == "export-all":
        results = exporter.export_all_topics()
        print(f"📤 导出完成")
        print(f"   成功：{results['success_count']}/{results['total']}")
        print(f"   Vault：{exporter.vault_path}")
        for item in results["exported"]:
            print(f"   ✅ {item['topic_id']} ({item['files']} 文件)")
    
    elif args.action == "status":
        logs = list(EXPORTS_DIR.glob("*_export_log.json"))
        print(f"📋 Obsidian 导出状态\n")
        print(f"Vault：{exporter.vault_path}")
        print(f"文件夹：{exporter.research_folder}")
        print(f"\n已导出题材：{len(logs)} 个\n")
        for log in logs[:10]:
            with open(log, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"- {data['topic_id']}")
            print(f"  时间：{data['exported_at'][:19]}")
            print(f"  文件：{len(data['files'])} 个")
            print()

if __name__ == "__main__":
    main()