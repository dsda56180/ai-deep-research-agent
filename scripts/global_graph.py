#!/usr/bin/env python3
"""
全局知识图谱
关联所有研究题材，发现跨题材洞察
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
GLOBAL_DIR = SKILL_DIR / "global"

# ============================================
# 全局知识图谱类
# ============================================

class GlobalKnowledgeGraph:
    """全局知识图谱管理器"""
    
    def __init__(self):
        self.global_graph_path = GLOBAL_DIR / "knowledge_graph.json"
        self.insights_path = GLOBAL_DIR / "cross_topic_insights.md"
        self.concept_index_path = GLOBAL_DIR / "concept_index.json"
        
        GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
        
        self.graph = self._load_or_create_graph()
    
    def _load_or_create_graph(self) -> Dict:
        """加载或创建全局图谱"""
        if self.global_graph_path.exists():
            with open(self.global_graph_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            "updated": datetime.now().isoformat(),
            "topics": [],
            "global_concepts": [],
            "cross_topic_relations": [],
            "statistics": {
                "total_topics": 0,
                "total_concepts": 0,
                "total_relations": 0,
                "shared_concepts": 0
            }
        }
    
    def _save_graph(self):
        """保存全局图谱"""
        with open(self.global_graph_path, 'w', encoding='utf-8') as f:
            json.dump(self.graph, f, ensure_ascii=False, indent=2)
    
    # ========================================
    # 图谱构建
    # ========================================
    
    def build_from_topics(self) -> Dict:
        """从所有题材构建全局图谱"""
        self.graph["topics"] = []
        all_concepts = {}
        
        # 遍历所有题材
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            
            topic_id = topic_dir.name
            graph_path = topic_dir / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
            
            if not graph_path.exists():
                continue
            
            with open(graph_path, 'r', encoding='utf-8') as f:
                topic_graph = json.load(f)
            
            # 添加题材摘要
            topic_summary = {
                "id": topic_id,
                "name": topic_graph.get("topic_name", topic_id),
                "concept_count": len(topic_graph.get("concepts", [])),
                "relation_count": len(topic_graph.get("relations", [])),
                "paper_count": topic_graph.get("metadata", {}).get("paper_count", 0),
                "last_updated": topic_graph.get("metadata", {}).get("updated")
            }
            self.graph["topics"].append(topic_summary)
            
            # 收集概念
            for concept in topic_graph.get("concepts", []):
                concept_id = concept["id"]
                if concept_id not in all_concepts:
                    all_concepts[concept_id] = {
                        "id": concept_id,
                        "name": concept["name"],
                        "type": concept.get("type", "concept"),
                        "appears_in": [],
                        "definitions": {}
                    }
                all_concepts[concept_id]["appears_in"].append(topic_id)
                
                # 记录定义（可能不同题材有不同理解）
                if concept.get("description"):
                    all_concepts[concept_id]["definitions"][topic_id] = concept["description"][:200]
        
        # 找出跨题材共享概念
        self.graph["global_concepts"] = [
            c for c in all_concepts.values() 
            if len(c["appears_in"]) > 1
        ]
        
        # 发现跨题材关系
        self.graph["cross_topic_relations"] = self._discover_relations(all_concepts)
        
        # 更新统计
        self.graph["statistics"] = {
            "total_topics": len(self.graph["topics"]),
            "total_concepts": len(all_concepts),
            "total_relations": sum(t["relation_count"] for t in self.graph["topics"]),
            "shared_concepts": len(self.graph["global_concepts"])
        }
        
        self.graph["updated"] = datetime.now().isoformat()
        self._save_graph()
        
        # 生成概念索引
        self._build_concept_index(all_concepts)
        
        # 生成跨题材洞察
        self._generate_insights()
        
        return self.graph
    
    def _discover_relations(self, all_concepts: Dict) -> List[Dict]:
        """发现跨题材关系"""
        relations = []
        
        for concept in all_concepts.values():
            if len(concept["appears_in"]) > 1:
                topics = concept["appears_in"]
                # 每对题材之间的关系
                for i in range(len(topics)):
                    for j in range(i + 1, len(topics)):
                        relations.append({
                            "type": "shared_concept",
                            "concept": concept["name"],
                            "topic_1": topics[i],
                            "topic_2": topics[j],
                            "significance": "medium" if len(topics) == 2 else "high"
                        })
        
        return relations
    
    def _build_concept_index(self, all_concepts: Dict):
        """构建概念索引"""
        index = {
            "updated": datetime.now().isoformat(),
            "concepts": []
        }
        
        # 按出现次数排序
        sorted_concepts = sorted(
            all_concepts.values(),
            key=lambda c: len(c["appears_in"]),
            reverse=True
        )
        
        for concept in sorted_concepts:
            index["concepts"].append({
                "id": concept["id"],
                "name": concept["name"],
                "type": concept["type"],
                "topics": concept["appears_in"],
                "is_shared": len(concept["appears_in"]) > 1
            })
        
        with open(self.concept_index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def _generate_insights(self):
        """生成跨题材洞察报告"""
        lines = [
            "# 跨题材洞察报告",
            "",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📊 总体统计",
            "",
            f"- 研究题材：{self.graph['statistics']['total_topics']} 个",
            f"- 总概念数：{self.graph['statistics']['total_concepts']} 个",
            f"- 总关系数：{self.graph['statistics']['total_relations']} 条",
            f"- 跨题材共享概念：{self.graph['statistics']['shared_concepts']} 个",
            ""
        ]
        
        # 共享概念
        if self.graph["global_concepts"]:
            lines.append("## 🔗 跨题材共享概念")
            lines.append("")
            for concept in self.graph["global_concepts"][:10]:
                topics_str = ", ".join(concept["appears_in"])
                lines.append(f"### {concept['name']}")
                lines.append(f"- 出现题材：{topics_str}")
                if concept.get("definitions"):
                    lines.append("- 定义：")
                    for topic_id, definition in concept["definitions"].items():
                        lines.append(f"  - {topic_id}: {definition[:100]}")
                lines.append("")
        
        # 跨题材关系
        if self.graph["cross_topic_relations"]:
            lines.append("## 🔍 跨题材关联发现")
            lines.append("")
            for rel in self.graph["cross_topic_relations"][:10]:
                lines.append(f"- **{rel['concept']}** 连接")
                lines.append(f"  - {rel['topic_1']} ↔ {rel['topic_2']}")
                lines.append(f"  - 类型：{rel['type']}")
                lines.append("")
        
        # 题材概览
        lines.append("## 📚 题材概览")
        lines.append("")
        for topic in self.graph["topics"]:
            lines.append(f"### {topic['name']}")
            lines.append(f"- 概念：{topic['concept_count']} | 关系：{topic['relation_count']} | 论文：{topic['paper_count']}")
            lines.append("")
        
        with open(self.insights_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    # ========================================
    # 查询接口
    # ========================================
    
    def get_shared_concepts(self) -> List[Dict]:
        """获取所有共享概念"""
        return self.graph.get("global_concepts", [])
    
    def search_concept(self, keyword: str) -> List[Dict]:
        """搜索概念"""
        keyword_lower = keyword.lower()
        results = []
        
        for concept in self.graph.get("global_concepts", []):
            if keyword_lower in concept["name"].lower():
                results.append(concept)
        
        return results
    
    def get_topic_relations(self, topic_id: str) -> List[Dict]:
        """获取题材的所有跨题材关系"""
        return [
            r for r in self.graph.get("cross_topic_relations", [])
            if r["topic_1"] == topic_id or r["topic_2"] == topic_id
        ]
    
    def get_summary(self) -> str:
        """获取图谱摘要"""
        stats = self.graph.get("statistics", {})
        lines = [
            "# 🌐 全局知识图谱",
            "",
            f"- 题材数：{stats.get('total_topics', 0)}",
            f"- 概念数：{stats.get('total_concepts', 0)}",
            f"- 关系数：{stats.get('total_relations', 0)}",
            f"- 共享概念：{stats.get('shared_concepts', 0)}",
            f"- 更新时间：{self.graph.get('updated', 'N/A')[:10]}",
            ""
        ]
        return "\n".join(lines)

# ============================================
# CLI 入口
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="全局知识图谱")
    parser.add_argument("action", choices=["build", "summary", "shared", "search", "relations"])
    parser.add_argument("--topic", "-t", help="题材 ID")
    parser.add_argument("--keyword", "-k", help="搜索关键词")
    
    args = parser.parse_args()
    
    graph = GlobalKnowledgeGraph()
    
    if args.action == "build":
        result = graph.build_from_topics()
        print(f"✅ 全局图谱已构建")
        print(f"   题材：{result['statistics']['total_topics']}")
        print(f"   概念：{result['statistics']['total_concepts']}")
        print(f"   共享：{result['statistics']['shared_concepts']}")
    
    elif args.action == "summary":
        print(graph.get_summary())
    
    elif args.action == "shared":
        concepts = graph.get_shared_concepts()
        print(f"🔗 跨题材共享概念（{len(concepts)} 个）\n")
        for c in concepts[:10]:
            print(f"- {c['name']} ({len(c['appears_in'])} 个题材)")
    
    elif args.action == "search":
        if not args.keyword:
            print("请提供 --keyword")
            return
        results = graph.search_concept(args.keyword)
        print(f"🔍 搜索结果（{len(results)} 个）\n")
        for r in results:
            print(f"- {r['name']}")
            print(f"  出现：{', '.join(r['appears_in'])}")
    
    elif args.action == "relations":
        if not args.topic:
            print("请提供 --topic")
            return
        relations = graph.get_topic_relations(args.topic)
        print(f"🔗 {args.topic} 的跨题材关系（{len(relations)} 个）\n")
        for r in relations:
            other_topic = r["topic_2"] if r["topic_1"] == args.topic else r["topic_1"]
            print(f"- ↔ {other_topic}（通过「{r['concept']}」）")

if __name__ == "__main__":
    main()