#!/usr/bin/env python3
"""
题材管理器
支持多题材研究，每个题材独立文件夹，全局知识图谱关联
"""

import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
GLOBAL_DIR = SKILL_DIR / "global"
CONFIG_DIR = SKILL_DIR / "config"

# 确保目录存在
TOPICS_DIR.mkdir(parents=True, exist_ok=True)
GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# 题材管理类
# ============================================

class TopicManager:
    """研究题材管理器"""
    
    def __init__(self):
        self.config_file = CONFIG_DIR / "topics.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {"topics": []}
        return {"topics": []}
    
    def _save_config(self):
        """保存配置"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
    
    def _topic_id(self, name: str) -> str:
        """生成题材 ID"""
        import re
        # 转换为小写，替换空格和特殊字符
        id_str = name.lower()
        id_str = re.sub(r'[^\w\s-]', '', id_str)
        id_str = re.sub(r'[\s]+', '-', id_str)
        return id_str.strip('-')
    
    def _topic_path(self, topic_id: str) -> Path:
        """获取题材路径"""
        return TOPICS_DIR / topic_id
    
    # ========================================
    # CRUD 操作
    # ========================================
    
    def list_topics(self) -> List[Dict]:
        """列出所有题材"""
        return self.config.get("topics", [])
    
    def create_topic(self, name: str, keywords: List[str] = None, 
                     frequency: str = "daily", channels: List[str] = None) -> Dict:
        """
        创建新题材
        
        Args:
            name: 题材名称
            keywords: 搜索关键词
            frequency: 研究频率（daily/weekly/monthly）
            channels: 同步渠道（ima/feishu/obsidian）
        
        Returns:
            创建的题材配置
        """
        topic_id = self._topic_id(name)
        
        # 检查是否已存在
        existing = next((t for t in self.config["topics"] if t["id"] == topic_id), None)
        if existing:
            return {"error": f"题材已存在：{name}", "topic": existing}
        
        # 创建题材配置
        topic = {
            "id": topic_id,
            "name": name,
            "keywords": keywords or [name],
            "enabled": True,
            "frequency": frequency,
            "channels": channels or ["ima"],
            "created_at": datetime.now().isoformat(),
            "last_research": None
        }
        
        # 创建文件夹结构
        topic_path = self._topic_path(topic_id)
        (topic_path / "knowledge" / "graphs").mkdir(parents=True, exist_ok=True)
        (topic_path / "knowledge" / "reports").mkdir(parents=True, exist_ok=True)
        (topic_path / ".learnings").mkdir(parents=True, exist_ok=True)
        
        # 初始化题材知识图谱
        self._init_topic_graph(topic_id, name)
        
        # 保存配置
        self.config["topics"].append(topic)
        self._save_config()
        
        # 更新全局知识图谱
        self._update_global_graph()
        
        return topic
    
    def get_topic(self, topic_id: str) -> Optional[Dict]:
        """获取题材详情"""
        return next((t for t in self.config["topics"] if t["id"] == topic_id), None)
    
    def update_topic(self, topic_id: str, **kwargs) -> Optional[Dict]:
        """更新题材配置"""
        for i, t in enumerate(self.config["topics"]):
            if t["id"] == topic_id:
                self.config["topics"][i].update(kwargs)
                self._save_config()
                return self.config["topics"][i]
        return None
    
    def disable_topic(self, topic_id: str) -> bool:
        """禁用题材"""
        return self.update_topic(topic_id, enabled=False) is not None
    
    def enable_topic(self, topic_id: str) -> bool:
        """启用题材"""
        return self.update_topic(topic_id, enabled=True) is not None
    
    def merge_topics(self, topic_id_1: str, topic_id_2: str, 
                     new_name: str = None) -> Dict:
        """
        合并两个题材
        
        Args:
            topic_id_1: 第一个题材 ID
            topic_id_2: 第二个题材 ID（将被合并到第一个）
            new_name: 新题材名称（可选）
        
        Returns:
            合并后的题材配置
        """
        topic_1 = self.get_topic(topic_id_1)
        topic_2 = self.get_topic(topic_id_2)
        
        if not topic_1 or not topic_2:
            return {"error": "题材不存在"}
        
        # 合并关键词
        merged_keywords = list(set(topic_1["keywords"] + topic_2["keywords"]))
        
        # 合并渠道
        merged_channels = list(set(topic_1.get("channels", []) + topic_2.get("channels", [])))
        
        # 更新题材 1
        topic_1["keywords"] = merged_keywords
        topic_1["channels"] = merged_channels
        if new_name:
            topic_1["name"] = new_name
        
        # 合并知识图谱
        self._merge_topic_graphs(topic_id_1, topic_id_2)
        
        # 移除题材 2
        self.config["topics"] = [t for t in self.config["topics"] if t["id"] != topic_id_2]
        
        # 移动题材 2 文件夹内容到题材 1
        topic_2_path = self._topic_path(topic_id_2)
        topic_1_path = self._topic_path(topic_id_1)
        if topic_2_path.exists():
            import shutil
            for item in topic_2_path.iterdir():
                if item.is_dir():
                    shutil.copytree(item, topic_1_path / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, topic_1_path / item.name)
            shutil.rmtree(topic_2_path)
        
        self._save_config()
        self._update_global_graph()
        
        return topic_1
    
    # ========================================
    # 知识图谱操作
    # ========================================
    
    def _init_topic_graph(self, topic_id: str, name: str):
        """初始化题材知识图谱"""
        graph_path = self._topic_path(topic_id) / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
        
        graph = {
            "topic_id": topic_id,
            "topic_name": name,
            "metadata": {
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
                "paper_count": 0,
                "concept_count": 0,
                "relation_count": 0
            },
            "concepts": [],
            "relations": [],
            "insights": {
                "breakthroughs": [],
                "gaps": [],
                "trends": [],
                "contradictions": []
            }
        }
        
        with open(graph_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
    
    def _merge_topic_graphs(self, topic_id_1: str, topic_id_2: str):
        """合并两个题材的知识图谱"""
        graph_1_path = self._topic_path(topic_id_1) / "knowledge" / "graphs" / f"{topic_id_1}_knowledge_graph.json"
        graph_2_path = self._topic_path(topic_id_2) / "knowledge" / "graphs" / f"{topic_id_2}_knowledge_graph.json"
        
        if not graph_1_path.exists() or not graph_2_path.exists():
            return
        
        with open(graph_1_path, 'r', encoding='utf-8') as f:
            graph_1 = json.load(f)
        
        with open(graph_2_path, 'r', encoding='utf-8') as f:
            graph_2 = json.load(f)
        
        # 合并概念（去重）
        existing_ids = {c["id"] for c in graph_1["concepts"]}
        for concept in graph_2["concepts"]:
            if concept["id"] not in existing_ids:
                graph_1["concepts"].append(concept)
        
        # 合并关系
        graph_1["relations"].extend(graph_2["relations"])
        
        # 合并洞察
        for key in ["breakthroughs", "gaps", "trends", "contradictions"]:
            graph_1["insights"][key].extend(graph_2["insights"].get(key, []))
        
        # 更新元数据
        graph_1["metadata"]["concept_count"] = len(graph_1["concepts"])
        graph_1["metadata"]["relation_count"] = len(graph_1["relations"])
        graph_1["metadata"]["updated"] = datetime.now().isoformat()
        
        with open(graph_1_path, 'w', encoding='utf-8') as f:
            json.dump(graph_1, f, ensure_ascii=False, indent=2)
    
    def _update_global_graph(self):
        """更新全局知识图谱"""
        global_graph_path = GLOBAL_DIR / "knowledge_graph.json"
        
        global_graph = {
            "updated": datetime.now().isoformat(),
            "topics": [],
            "global_concepts": [],
            "cross_topic_relations": []
        }
        
        # 收集所有题材的概念
        all_concepts = {}
        for topic in self.config["topics"]:
            topic_id = topic["id"]
            graph_path = self._topic_path(topic_id) / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
            
            if graph_path.exists():
                with open(graph_path, 'r', encoding='utf-8') as f:
                    graph = json.load(f)
                
                topic_summary = {
                    "id": topic_id,
                    "name": topic["name"],
                    "concept_count": len(graph.get("concepts", [])),
                    "relation_count": len(graph.get("relations", [])),
                    "paper_count": graph.get("metadata", {}).get("paper_count", 0),
                    "last_updated": graph.get("metadata", {}).get("updated")
                }
                global_graph["topics"].append(topic_summary)
                
                # 收集概念
                for concept in graph.get("concepts", []):
                    concept_id = concept["id"]
                    if concept_id not in all_concepts:
                        all_concepts[concept_id] = {
                            "id": concept_id,
                            "name": concept["name"],
                            "appears_in": []
                        }
                    all_concepts[concept_id]["appears_in"].append(topic_id)
        
        # 找出跨题材概念
        global_graph["global_concepts"] = [
            c for c in all_concepts.values() if len(c["appears_in"]) > 1
        ]
        
        # 发现跨题材关系
        for concept in global_graph["global_concepts"]:
            if len(concept["appears_in"]) > 1:
                topics = concept["appears_in"]
                for i in range(len(topics)):
                    for j in range(i + 1, len(topics)):
                        global_graph["cross_topic_relations"].append({
                            "concept": concept["name"],
                            "topic_1": topics[i],
                            "topic_2": topics[j],
                            "relation": "shared_concept"
                        })
        
        with open(global_graph_path, 'w', encoding='utf-8') as f:
            json.dump(global_graph, f, ensure_ascii=False, indent=2)
        
        return global_graph
    
    # ========================================
    # 状态查询
    # ========================================
    
    def get_topic_status(self, topic_id: str) -> Dict:
        """获取题材状态"""
        topic = self.get_topic(topic_id)
        if not topic:
            return {"error": "题材不存在"}
        
        topic_path = self._topic_path(topic_id)
        graph_path = topic_path / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
        reports = list((topic_path / "knowledge" / "reports").glob("*.md"))
        
        status = {
            "id": topic_id,
            "name": topic["name"],
            "enabled": topic.get("enabled", True),
            "frequency": topic.get("frequency", "daily"),
            "channels": topic.get("channels", []),
            "last_research": topic.get("last_research"),
            "reports_count": len(reports),
            "latest_report": reports[-1].name if reports else None
        }
        
        if graph_path.exists():
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph = json.load(f)
            status["concepts"] = len(graph.get("concepts", []))
            status["relations"] = len(graph.get("relations", []))
            status["papers"] = graph.get("metadata", {}).get("paper_count", 0)
        
        return status

# ============================================
# CLI 入口
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="题材管理器")
    sub = parser.add_subparsers(dest="cmd")
    
    # list 命令
    sub.add_parser("list", help="列出所有题材")
    
    # create 命令
    create_parser = sub.add_parser("create", help="创建新题材")
    create_parser.add_argument("name", help="题材名称")
    create_parser.add_argument("--keywords", nargs="+", help="搜索关键词")
    create_parser.add_argument("--frequency", choices=["daily", "weekly", "monthly"], default="daily")
    create_parser.add_argument("--channels", nargs="+", choices=["ima", "feishu", "obsidian"])
    
    # status 命令
    status_parser = sub.add_parser("status", help="查看题材状态")
    status_parser.add_argument("topic_id")
    
    # disable/enable 命令
    sub.add_parser("disable", help="禁用题材").add_argument("topic_id")
    sub.add_parser("enable", help="启用题材").add_argument("topic_id")
    
    # merge 命令
    merge_parser = sub.add_parser("merge", help="合并题材")
    merge_parser.add_argument("topic_id_1")
    merge_parser.add_argument("topic_id_2")
    merge_parser.add_argument("--name", help="新题材名称")
    
    args = parser.parse_args()
    
    manager = TopicManager()
    
    if args.cmd == "list":
        topics = manager.list_topics()
        print(f"📋 研究题材列表（{len(topics)} 个）\n")
        for t in topics:
            status = "✅" if t.get("enabled", True) else "⏸️"
            print(f"{status} {t['name']} ({t['id']})")
            print(f"   频率：{t.get('frequency', 'daily')}")
            print(f"   渠道：{', '.join(t.get('channels', []))}")
            print()
    
    elif args.cmd == "create":
        result = manager.create_topic(
            name=args.name,
            keywords=args.keywords,
            frequency=args.frequency,
            channels=args.channels
        )
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ 题材已创建：{result['name']}")
            print(f"   ID：{result['id']}")
            print(f"   频率：{result['frequency']}")
            print(f"   渠道：{', '.join(result['channels'])}")
    
    elif args.cmd == "status":
        status = manager.get_topic_status(args.topic_id)
        if "error" in status:
            print(f"❌ {status['error']}")
        else:
            print(f"📊 {status['name']} 状态")
            print(f"   状态：{'启用' if status['enabled'] else '禁用'}")
            print(f"   频率：{status['frequency']}")
            print(f"   渠道：{', '.join(status['channels'])}")
            print(f"   概念数：{status.get('concepts', 0)}")
            print(f"   关系数：{status.get('relations', 0)}")
            print(f"   论文数：{status.get('papers', 0)}")
            print(f"   报告数：{status['reports_count']}")
    
    elif args.cmd == "disable":
        if manager.disable_topic(args.topic_id):
            print(f"✅ 已禁用：{args.topic_id}")
        else:
            print(f"❌ 禁用失败")
    
    elif args.cmd == "enable":
        if manager.enable_topic(args.topic_id):
            print(f"✅ 已启用：{args.topic_id}")
        else:
            print(f"❌ 启用失败")
    
    elif args.cmd == "merge":
        result = manager.merge_topics(
            args.topic_id_1,
            args.topic_id_2,
            args.name
        )
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ 已合并：{result['name']}")
            print(f"   关键词：{len(result['keywords'])} 个")
            print(f"   渠道：{', '.join(result['channels'])}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()