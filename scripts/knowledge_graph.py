#!/usr/bin/env python3
"""
知识图谱管理模块
构建和维护研究知识图谱
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ============================================
# 配置
# ============================================

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"
GRAPHS_DIR = KNOWLEDGE_DIR / "graphs"

# ============================================
# 数据结构
# ============================================

class Concept:
    """概念节点"""
    def __init__(self, id: str, name: str, concept_type: str = "concept"):
        self.id = id
        self.name = name
        self.type = concept_type  # system, concept, method, dataset, metric
        self.description = ""
        self.papers = []  # 相关论文
        self.parent = None  # 父概念
        self.children = []  # 子概念
        self.attributes = {}  # 其他属性
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "papers": self.papers,
            "parent": self.parent,
            "children": self.children,
            "attributes": self.attributes
        }


class Relation:
    """概念关系"""
    def __init__(self, from_id: str, to_id: str, relation_type: str):
        self.from_id = from_id
        self.to_id = to_id
        self.type = relation_type  # implements, extends, competes, combines, validates, contradicts
        self.evidence = ""  # 证据/来源
        self.attributes = {}
    
    def to_dict(self) -> dict:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "type": self.type,
            "evidence": self.evidence,
            "attributes": self.attributes
        }


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self, topic: str):
        self.topic = topic
        self.concepts: Dict[str, Concept] = {}
        self.relations: List[Relation] = []
        self.insights = {
            "breakthroughs": [],  # 突破性发现
            "gaps": [],           # 知识缺口
            "trends": [],         # 趋势预测
            "questions": []       # 待解决问题
        }
        self.metadata = {
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "paper_count": 0,
            "concept_count": 0
        }
    
    def add_concept(self, concept: Concept):
        """添加概念"""
        self.concepts[concept.id] = concept
        self.metadata["concept_count"] = len(self.concepts)
        self.metadata["updated"] = datetime.now().isoformat()
    
    def add_relation(self, relation: Relation):
        """添加关系"""
        self.relations.append(relation)
        self.metadata["updated"] = datetime.now().isoformat()
    
    def find_concept(self, name: str) -> Optional[Concept]:
        """查找概念"""
        for concept in self.concepts.values():
            if concept.name.lower() == name.lower():
                return concept
        return None
    
    def get_related_concepts(self, concept_id: str) -> List[Concept]:
        """获取相关概念"""
        related = []
        for relation in self.relations:
            if relation.from_id == concept_id:
                if relation.to_id in self.concepts:
                    related.append(self.concepts[relation.to_id])
            elif relation.to_id == concept_id:
                if relation.from_id in self.concepts:
                    related.append(self.concepts[relation.from_id])
        return related
    
    def extract_from_paper(self, paper_data: dict):
        """从论文数据提取概念和关系"""
        # 提取核心方法
        if "core_method" in paper_data:
            method_name = paper_data.get("method_name", "")
            if method_name:
                concept = Concept(
                    id=self._generate_id(method_name),
                    name=method_name,
                    concept_type="method"
                )
                concept.description = paper_data.get("core_method", "")[:500]
                concept.papers.append(paper_data.get("arxiv_id", ""))
                self.add_concept(concept)
        
        # 提取创新点
        for innovation in paper_data.get("innovations", []):
            concept = Concept(
                id=self._generate_id(innovation[:30]),
                name=innovation[:50],
                concept_type="concept"
            )
            concept.description = innovation
            concept.papers.append(paper_data.get("arxiv_id", ""))
            self.add_concept(concept)
        
        # 提取实验数据集
        for dataset in paper_data.get("datasets", []):
            concept = Concept(
                id=self._generate_id(dataset),
                name=dataset,
                concept_type="dataset"
            )
            concept.papers.append(paper_data.get("arxiv_id", ""))
            self.add_concept(concept)
        
        self.metadata["paper_count"] += 1
    
    def _generate_id(self, name: str) -> str:
        """生成概念 ID"""
        import re
        # 转换为小写，替换空格和特殊字符
        id_str = re.sub(r'[^a-z0-9]+', '-', name.lower())
        id_str = id_str.strip('-')
        # 确保唯一性
        base_id = id_str
        counter = 1
        while base_id in self.concepts:
            base_id = f"{id_str}-{counter}"
            counter += 1
        return base_id
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "topic": self.topic,
            "metadata": self.metadata,
            "concepts": [c.to_dict() for c in self.concepts.values()],
            "relations": [r.to_dict() for r in self.relations],
            "insights": self.insights
        }
    
    def save(self, filepath: str = None):
        """保存知识图谱"""
        if not filepath:
            GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"{self.topic.replace(' ', '_')}_knowledge_graph.json"
            filepath = GRAPHS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        return filepath
    
    @classmethod
    def load(cls, filepath: str) -> 'KnowledgeGraph':
        """加载知识图谱"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        graph = cls(data["topic"])
        graph.metadata = data["metadata"]
        graph.insights = data["insights"]
        
        # 加载概念
        for concept_data in data["concepts"]:
            concept = Concept(
                id=concept_data["id"],
                name=concept_data["name"],
                concept_type=concept_data["type"]
            )
            concept.description = concept_data.get("description", "")
            concept.papers = concept_data.get("papers", [])
            concept.parent = concept_data.get("parent")
            concept.children = concept_data.get("children", [])
            concept.attributes = concept_data.get("attributes", {})
            graph.concepts[concept.id] = concept
        
        # 加载关系
        for relation_data in data["relations"]:
            relation = Relation(
                from_id=relation_data["from"],
                to_id=relation_data["to"],
                relation_type=relation_data["type"]
            )
            relation.evidence = relation_data.get("evidence", "")
            relation.attributes = relation_data.get("attributes", {})
            graph.relations.append(relation)
        
        return graph


# ============================================
# 工具函数
# ============================================

def get_or_create_graph(topic: str) -> KnowledgeGraph:
    """获取或创建知识图谱"""
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{topic.replace(' ', '_')}_knowledge_graph.json"
    filepath = GRAPHS_DIR / filename
    
    if filepath.exists():
        return KnowledgeGraph.load(str(filepath))
    else:
        return KnowledgeGraph(topic)


def merge_graphs(graph1: KnowledgeGraph, graph2: KnowledgeGraph) -> KnowledgeGraph:
    """合并两个知识图谱"""
    # 以 graph1 为主体
    for concept_id, concept in graph2.concepts.items():
        if concept_id not in graph1.concepts:
            graph1.add_concept(concept)
        else:
            # 合并论文列表
            existing = graph1.concepts[concept_id]
            existing.papers = list(set(existing.papers + concept.papers))
    
    # 合并关系（去重）
    existing_pairs = {(r.from_id, r.to_id, r.type) for r in graph1.relations}
    for relation in graph2.relations:
        key = (relation.from_id, relation.to_id, relation.type)
        if key not in existing_pairs:
            graph1.add_relation(relation)
    
    # 合并洞察
    for key in ["breakthroughs", "gaps", "trends", "questions"]:
        graph1.insights[key] = list(set(graph1.insights[key] + graph2.insights[key]))
    
    return graph1


# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="知识图谱管理")
    parser.add_argument("--topic", "-t", required=True, help="研究主题")
    parser.add_argument("--stats", "-s", action="store_true", help="显示统计信息")
    
    args = parser.parse_args()
    
    graph = get_or_create_graph(args.topic)
    
    if args.stats:
        print(f"📊 知识图谱统计: {args.topic}")
        print(f"   概念数量: {len(graph.concepts)}")
        print(f"   关系数量: {len(graph.relations)}")
        print(f"   论文数量: {graph.metadata['paper_count']}")
        print(f"   更新时间: {graph.metadata['updated']}")
    else:
        print(f"知识图谱路径: {graph.save()}")