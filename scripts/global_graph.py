#!/usr/bin/env python3
"""
全局知识图谱
关联所有研究题材，发现跨题材洞察
"""

import os
import sys
import json
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
GLOBAL_DIR = SKILL_DIR / "global"

sys.path.insert(0, str(SCRIPT_DIR))

from knowledge_graph import KnowledgeGraph, Relation, get_or_create_graph, resolve_graph_location


def load_topics_config() -> Dict:
    config_paths = [
        SKILL_DIR / "config" / "optimized_config.yaml",
        SKILL_DIR / "config" / "topics.yaml",
    ]
    merged = {}
    merged_topics = []
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            for key, value in config.items():
                if key == "topics":
                    continue
                if key not in merged:
                    merged[key] = value
            for topic in config.get("topics", []):
                topic_tokens = {
                    "".join(ch for ch in (topic.get("id", "") or "").lower() if ch not in {" ", "-", "_"}),
                    "".join(ch for ch in (topic.get("name", "") or "").lower() if ch not in {" ", "-", "_"}),
                } - {""}
                existing_topic = next(
                    (
                        item for item in merged_topics
                        if topic_tokens & ({
                            "".join(ch for ch in (item.get("id", "") or "").lower() if ch not in {" ", "-", "_"}),
                            "".join(ch for ch in (item.get("name", "") or "").lower() if ch not in {" ", "-", "_"}),
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

    @staticmethod
    def _normalize_topic_token(value: str) -> str:
        return "".join(ch for ch in (value or "").lower() if ch not in {" ", "-", "_"})

    def _resolve_config_topics(self, topic_id: str = "") -> List[Dict]:
        topics = [topic for topic in load_topics_config().get("topics", []) if topic.get("enabled", True)]
        if not topic_id:
            return topics
        normalized_query = self._normalize_topic_token(topic_id)
        return [
            topic for topic in topics
            if any(
                normalized_query and candidate and (normalized_query in candidate or candidate in normalized_query)
                for candidate in {
                    self._normalize_topic_token(topic.get("id", "")),
                    self._normalize_topic_token(topic.get("name", "")),
                }
            )
        ]

    def _build_bootstrap_brief(self, topic: Dict) -> Dict:
        topic_name = topic.get("name", "")
        topic_id = topic.get("id", "")
        description = topic.get("description") or f"{topic_name} 的研究主题引导图谱"
        keywords = [keyword for keyword in topic.get("keywords", []) if keyword][:5]
        methodologies = [
            f"{topic_name} 代表工作归类",
            f"{topic_name} 评测维度对比",
            f"{topic_name} 系统设计基线",
        ]
        gaps = [
            f"{topic_name} 的规模化落地边界",
            f"{topic_name} 的效果评估标准",
            f"{topic_name} 的工程成本与收益平衡",
        ]
        return {
            "topic_name": topic_name,
            "topic_id": topic_id,
            "description": description,
            "keywords": keywords,
            "methodologies": methodologies,
            "gaps": gaps,
        }

    def _seed_topic_graph(self, graph: KnowledgeGraph, topic: Dict) -> Dict:
        brief = self._build_bootstrap_brief(topic)
        topic_name = brief["topic_name"]
        topic_id = brief["topic_id"] or topic_name
        description = brief["description"]
        document = graph.upsert_entity(
            name=f"{topic_name} Bootstrap Brief",
            entity_type="Document",
            entity_id=f"bootstrap-document-{topic_id}",
            description="由主题配置自动生成的引导文档",
            summary=description,
            attributes={
                "bootstrap": True,
                "source": "config/topics",
                "topic_id": topic_id,
            },
            aliases=[f"{topic_name} brief", f"{topic_id} brief"],
            layer="warm",
            confidence=1.0,
        )
        topic_entity = graph.upsert_entity(
            name=f"{topic_name} 研究主题",
            entity_type="system",
            entity_id=f"topic-{topic_id}",
            description=description,
            summary=description,
            aliases=[topic_name, topic_id],
            tags=["bootstrap", "topic"],
            source_ids=[document.id],
            layer="warm",
            confidence=0.95,
        )
        graph.add_relation(Relation(
            from_id=document.id,
            to_id=topic_entity.id,
            type="mentions",
            evidence=description,
            source_document=document.id,
            source_span=description,
            confidence=0.95,
        ))
        created = {"keywords": 0, "methodologies": 0, "gaps": 0}
        for keyword in brief["keywords"]:
            entity = graph.upsert_entity(
                name=keyword,
                entity_type="concept",
                description=f"{topic_name} 的核心研究关键词",
                summary=keyword,
                source_ids=[document.id],
                tags=["bootstrap", "keyword"],
                confidence=0.85,
            )
            graph.add_relation(Relation(
                from_id=topic_entity.id,
                to_id=entity.id,
                type="focuses_on",
                evidence=keyword,
                source_document=document.id,
                source_span=keyword,
                confidence=0.85,
            ))
            graph.add_relation(Relation(
                from_id=document.id,
                to_id=entity.id,
                type="mentions",
                evidence=keyword,
                source_document=document.id,
                source_span=keyword,
                confidence=0.85,
            ))
            created["keywords"] += 1
        for item in brief["methodologies"]:
            entity = graph.upsert_entity(
                name=item,
                entity_type="Methodology",
                description=f"{topic_name} 的基础研究方法模块",
                summary=item,
                source_ids=[document.id],
                tags=["bootstrap", "methodology"],
                confidence=0.8,
            )
            graph.add_relation(Relation(
                from_id=topic_entity.id,
                to_id=entity.id,
                type="uses",
                evidence=item,
                source_document=document.id,
                source_span=item,
                confidence=0.8,
            ))
            created["methodologies"] += 1
        for item in brief["gaps"]:
            entity = graph.upsert_entity(
                name=item,
                entity_type="Gap",
                description=f"{topic_name} 当前仍需持续验证的关键问题",
                summary=item,
                source_ids=[document.id],
                tags=["bootstrap", "gap"],
                confidence=0.78,
            )
            graph.add_relation(Relation(
                from_id=topic_entity.id,
                to_id=entity.id,
                type="has_gap",
                evidence=item,
                source_document=document.id,
                source_span=item,
                confidence=0.78,
                status="INFERRED",
            ))
            created["gaps"] += 1
        return {
            "document_id": document.id,
            "topic_entity_id": topic_entity.id,
            **created,
        }

    @staticmethod
    def _is_bootstrap_only_graph(graph: KnowledgeGraph) -> bool:
        meaningful_entities = [
            entity for entity in graph.entities.values()
            if entity.type != "CommunitySummary"
        ]
        if not meaningful_entities:
            return True
        return all("bootstrap" in entity.tags or entity.id.startswith("bootstrap-document-") for entity in meaningful_entities)

    def bootstrap_topics(self, topic_id: str = "", force: bool = False) -> Dict:
        topics = self._resolve_config_topics(topic_id)
        results = []
        for topic in topics:
            topic_key = topic.get("id") or topic.get("name", "")
            topic_name, graph_dir, graph_filename = resolve_graph_location(topic_key)
            graph = get_or_create_graph(topic_name, base_dir=graph_dir, filename=graph_filename)
            before_entities = len(graph.entities)
            before_edges = len(graph.edges)
            if (before_entities > 0 or before_edges > 0) and not force:
                results.append({
                    "topic": topic_name,
                    "topic_id": topic.get("id", ""),
                    "status": "skipped_existing",
                    "entities": before_entities,
                    "edges": before_edges,
                })
                continue
            if force and self._is_bootstrap_only_graph(graph):
                graph = KnowledgeGraph(topic_name, graph_path=graph_dir / graph_filename)
            seed_result = self._seed_topic_graph(graph, topic)
            refresh_result = graph.refresh_views()
            validation = graph.validate()
            graph.save()
            stats = graph.graph_stats()
            results.append({
                "topic": topic_name,
                "topic_id": topic.get("id", ""),
                "status": "bootstrapped",
                "entities": stats.get("entities", 0),
                "edges": stats.get("edges", 0),
                "communities": stats.get("communities", 0),
                "seed": seed_result,
                "refresh": refresh_result,
                "validation": validation,
            })
        return {
            "processed_topics": len(results),
            "bootstrapped_topics": len([item for item in results if item["status"] == "bootstrapped"]),
            "skipped_topics": len([item for item in results if item["status"] == "skipped_existing"]),
            "topics": results,
        }
    
    # ========================================
    # 图谱构建
    # ========================================
    
    def build_from_topics(self) -> Dict:
        """从所有题材构建全局图谱"""
        self.graph["topics"] = []
        all_concepts = {}
        topic_stats = {}
        
        # 遍历所有题材
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            
            topic_id = topic_dir.name
            graph_path = topic_dir / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
            
            if not graph_path.exists():
                continue
            
            topic_graph = KnowledgeGraph.load(str(graph_path))
            
            # 添加题材摘要
            topic_summary = {
                "id": topic_id,
                "name": topic_graph.topic,
                "concept_count": len(topic_graph.concepts),
                "relation_count": len(topic_graph.relations),
                "paper_count": len([e for e in topic_graph.entities.values() if e.type == "Paper"]),
                "entity_count": len(topic_graph.entities),
                "community_count": len(topic_graph.compute_communities()),
                "last_updated": topic_graph.metadata.get("updated")
            }
            self.graph["topics"].append(topic_summary)
            topic_stats[topic_id] = topic_graph.graph_stats()
            
            # 收集概念
            for concept in topic_graph.concepts.values():
                concept_id = concept.id
                if concept_id not in all_concepts:
                    all_concepts[concept_id] = {
                        "id": concept_id,
                        "name": concept.name,
                        "type": concept.type or "concept",
                        "appears_in": [],
                        "definitions": {},
                        "communities": {},
                    }
                all_concepts[concept_id]["appears_in"].append(topic_id)
                
                # 记录定义（可能不同题材有不同理解）
                if concept.description:
                    all_concepts[concept_id]["definitions"][topic_id] = concept.description[:200]
                if concept.attributes.get("community_id"):
                    all_concepts[concept_id]["communities"][topic_id] = concept.attributes["community_id"]
        
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
            "shared_concepts": len(self.graph["global_concepts"]),
            "avg_entities_per_topic": round(sum(t["entity_count"] for t in self.graph["topics"]) / max(1, len(self.graph["topics"])), 2),
        }
        self.graph["topic_stats"] = topic_stats
        
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
                            "significance": "medium" if len(topics) == 2 else "high",
                            "shared_count": len(topics),
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

    def topic_stats(self, topic_id: str = "") -> Dict:
        if not self.graph.get("topic_stats"):
            self.build_from_topics()
        if topic_id:
            return self.graph.get("topic_stats", {}).get(topic_id, {})
        return self.graph.get("topic_stats", {})

    def benchmark_all(self, limit: int = 10) -> Dict:
        topic_results = []
        total_corpus = 0
        total_query = 0
        processed = 0
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            graph_path = topic_dir / "knowledge" / "graphs" / f"{topic_dir.name}_knowledge_graph.json"
            if not graph_path.exists():
                continue
            graph = KnowledgeGraph.load(str(graph_path))
            benchmark = graph.benchmark_context()
            if benchmark.get("error"):
                continue
            topic_results.append({
                "topic_id": topic_dir.name,
                "topic": graph.topic,
                "corpus_tokens": benchmark.get("corpus_tokens", 0),
                "avg_query_tokens": benchmark.get("avg_query_tokens", 0),
                "reduction_ratio": benchmark.get("reduction_ratio", 0),
            })
            total_corpus += benchmark.get("corpus_tokens", 0)
            total_query += benchmark.get("avg_query_tokens", 0)
            processed += 1
        ordered = sorted(topic_results, key=lambda item: item["reduction_ratio"], reverse=True)
        return {
            "topics": ordered[:limit],
            "processed_topics": processed,
            "avg_reduction_ratio": round(sum(item["reduction_ratio"] for item in ordered) / max(1, len(ordered)), 2),
            "aggregate_reduction_ratio": round(total_corpus / max(1, total_query), 2),
        }
    
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
    parser = argparse.ArgumentParser(description="全局知识图谱")
    parser.add_argument("action", choices=["build", "summary", "shared", "search", "relations", "stats", "benchmark", "bootstrap"])
    parser.add_argument("--topic", "-t", help="题材 ID")
    parser.add_argument("--keyword", "-k", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    
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
    elif args.action == "stats":
        print(json.dumps(graph.topic_stats(args.topic or ""), ensure_ascii=False, indent=2))
    elif args.action == "benchmark":
        print(json.dumps(graph.benchmark_all(limit=args.limit), ensure_ascii=False, indent=2))
    elif args.action == "bootstrap":
        print(json.dumps(graph.bootstrap_topics(topic_id=args.topic or "", force=args.force), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
