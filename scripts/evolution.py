#!/usr/bin/env python3
"""
AI Deep Research Agent — 自我进化版
完整的研究系统，实现知识库的自我进化

功能模块：
- 论文搜索与抓取
- 深度分析与报告生成
- 知识图谱进化
- 研究方法论更新
- 知识缺口追踪
- IMA知识库同步
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter

from self_learning import LearningMemory, MethodLibrary

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"
GRAPHS_DIR = KNOWLEDGE_DIR / "graphs"
REPORTS_DIR = KNOWLEDGE_DIR / "reports"
CACHE_DIR = SKILL_DIR / "data" / "cache"
LEARNINGS_DIR = SKILL_DIR / ".learnings"

# 确保目录存在
for d in [GRAPHS_DIR, REPORTS_DIR, CACHE_DIR, LEARNINGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================
# 工具函数
# ============================================

def now(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.now().strftime(fmt)

def today():
    return datetime.now().strftime("%Y-%m-%d")

def load_yaml(path: Path):
    import yaml
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

def load_cache() -> Dict:
    cache_file = CACHE_DIR / "research_cache.json"
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"papers": {}, "last_update": {}, "methodology_version": 1, "gaps_resolved": []}

def save_cache(cache: Dict):
    cache_file = CACHE_DIR / "research_cache.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# ============================================
# 第一阶段：论文搜索
# ============================================

class PaperSearcher:
    """论文搜索器"""
    
    def __init__(self, keywords: List[str]):
        self.keywords = keywords
    
    def search(self, days: int = 90) -> List[Dict]:
        """
        搜索论文（返回搜索指令）
        实际搜索由主模型执行 web_search
        """
        return {
            "stage": "search",
            "keywords": self.keywords,
            "days": days,
            "instruction": f"请使用 web_search 搜索以下关键词的最新论文（最近{days}天）：{', '.join(self.keywords)}"
        }

# ============================================
# 第二阶段：质量筛选
# ============================================

class QualityFilter:
    """论文质量筛选器"""
    
    VENUE_SCORES = {
        # 顶级会议
        "NeurIPS": 2.0, "ICML": 2.0, "ICLR": 2.0,
        "ACL": 2.0, "EMNLP": 2.0, "CVPR": 2.0,
        # 一级会议
        "AAAI": 1.5, "IJCAI": 1.5, "AISTATS": 1.5,
        # arXiv
        "arxiv": 1.0
    }
    
    def evaluate(self, paper: Dict) -> float:
        """评估论文质量分数"""
        score = 0.0
        
        # 1. 发表场所
        venue = paper.get("venue", "").lower()
        for v, s in self.VENUE_SCORES.items():
            if v.lower() in venue:
                score += s
                break
        
        # 2. 引用数
        citations = paper.get("citations", 0)
        if citations > 100:
            score += 1.5
        elif citations > 50:
            score += 1.0
        elif citations > 10:
            score += 0.5
        
        # 3. 时效性
        pub_date = paper.get("pub_date", "")
        if pub_date:
            try:
                pub_dt = datetime.strptime(pub_date[:10], "%Y-%m-%d")
                days_old = (datetime.now() - pub_dt).days
                if days_old < 90:
                    score += 1.0
                elif days_old < 180:
                    score += 0.5
            except:
                pass
        
        return min(score, 5.0)
    
    def filter(self, papers: List[Dict], min_score: float = 3.0, max_papers: int = 5) -> List[Dict]:
        """筛选高质量论文"""
        for paper in papers:
            paper["quality_score"] = self.evaluate(paper)
        
        filtered = [p for p in papers if p.get("quality_score", 0) >= min_score]
        return sorted(filtered, key=lambda x: x.get("quality_score", 0), reverse=True)[:max_papers]

# ============================================
# 第三阶段：深度分析
# ============================================

class DeepAnalyzer:
    """论文深度分析器"""
    
    def analyze(self, paper: Dict) -> Dict:
        """深度分析单篇论文"""
        return {
            "id": paper.get("id", ""),
            "title": paper.get("title", ""),
            "analysis": {
                "basic_info": self._extract_basic_info(paper),
                "core_method": self._extract_method(paper),
                "innovations": self._extract_innovations(paper),
                "experiments": self._extract_experiments(paper),
                "limitations": self._extract_limitations(paper)
            }
        }
    
    def _extract_basic_info(self, paper: Dict) -> Dict:
        return {
            "authors": paper.get("authors", []),
            "institution": paper.get("institution", ""),
            "venue": paper.get("venue", ""),
            "arxiv_id": paper.get("arxiv_id", ""),
            "url": paper.get("url", "")
        }
    
    def _extract_method(self, paper: Dict) -> str:
        # 返回提取指令，由主模型填充
        return paper.get("abstract", "")[:500]
    
    def _extract_innovations(self, paper: Dict) -> List[str]:
        # 从摘要推断创新点
        abstract = paper.get("abstract", "").lower()
        innovations = []
        
        innovation_keywords = ["novel", "propose", "introduce", "first", "new method", "new framework"]
        for kw in innovation_keywords:
            if kw in abstract:
                innovations.append(f"包含关键词：{kw}")
        
        return innovations[:3]
    
    def _extract_experiments(self, paper: Dict) -> str:
        return paper.get("abstract", "")[:300]
    
    def _extract_limitations(self, paper: Dict) -> List[str]:
        abstract = paper.get("abstract", "").lower()
        limitations = []
        
        limitation_keywords = ["limitation", "future work", "remains", "not address"]
        for kw in limitation_keywords:
            if kw in abstract:
                limitations.append(f"发现关键词：{kw}")
        
        return limitations

# ============================================
# 第四阶段：知识图谱进化
# ============================================

class KnowledgeGraphEvolver:
    """知识图谱进化器"""
    
    def __init__(self, topic: str):
        self.topic = topic
        self.graph_path = GRAPHS_DIR / f"{topic.replace(' ', '_')}_knowledge_graph.json"
        self.graph = self._load_graph()
    
    def _load_graph(self) -> Dict:
        if self.graph_path.exists():
            with open(self.graph_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "topic": self.topic,
            "metadata": {"created": datetime.now().isoformat()},
            "concepts": [],
            "relations": [],
            "insights": {"breakthroughs": [], "gaps": [], "trends": [], "contradictions": []}
        }
    
    def _save_graph(self):
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump(self.graph, f, ensure_ascii=False, indent=2)
    
    def evolve(self, paper_analysis: Dict) -> Dict:
        """
        知识图谱进化
        
        Returns:
            进化摘要
        """
        changes = {
            "new_concepts": 0,
            "updated_concepts": 0,
            "new_relations": 0,
            "contradictions_found": 0
        }
        
        # 1. 提取概念
        concepts = self._extract_concepts(paper_analysis)
        existing_ids = {c["id"] for c in self.graph["concepts"]}
        
        for concept in concepts:
            if concept["id"] not in existing_ids:
                self.graph["concepts"].append(concept)
                changes["new_concepts"] += 1
            else:
                # 更新已有概念
                for c in self.graph["concepts"]:
                    if c["id"] == concept["id"]:
                        if paper_analysis.get("id") not in c.get("papers", []):
                            c["papers"].append(paper_analysis.get("id"))
                            changes["updated_concepts"] += 1
        
        # 2. 推断关系
        relations = self._infer_relations(paper_analysis)
        for r in relations:
            self.graph["relations"].append(r)
            changes["new_relations"] += 1
        
        # 3. 检测矛盾
        contradictions = self._detect_contradictions(paper_analysis)
        if contradictions:
            self.graph["insights"]["contradictions"].extend(contradictions)
            changes["contradictions_found"] = len(contradictions)
        
        # 4. 更新元数据
        self.graph["metadata"]["updated"] = datetime.now().isoformat()
        self.graph["metadata"]["concept_count"] = len(self.graph["concepts"])
        self.graph["metadata"]["relation_count"] = len(self.graph["relations"])
        
        self._save_graph()
        return changes
    
    def _extract_concepts(self, analysis: Dict) -> List[Dict]:
        """从论文分析提取概念"""
        concepts = []
        
        # 提取系统/框架名称
        for system in analysis.get("analysis", {}).get("systems", []):
            concepts.append({
                "id": system.lower().replace(" ", "-").replace("/", "-"),
                "name": system,
                "type": "system",
                "description": analysis.get("title", ""),
                "papers": [analysis.get("id", "")],
                "parent": None,
                "children": [],
                "attributes": {}
            })
        
        # 提取方法名称
        for method in analysis.get("analysis", {}).get("methods", []):
            concepts.append({
                "id": method.lower().replace(" ", "-"),
                "name": method,
                "type": "method",
                "description": f"来自 {analysis.get('title', '')}",
                "papers": [analysis.get("id", "")],
                "parent": None,
                "children": [],
                "attributes": {}
            })
        
        return concepts
    
    def _infer_relations(self, analysis: Dict) -> List[Dict]:
        """推断关系"""
        relations = []
        
        # 基于关键词推断
        abstract = analysis.get("analysis", {}).get("core_method", "").lower()
        
        relation_keywords = {
            "improves": "extends",
            "extends": "extends",
            "based on": "implements",
            "builds on": "extends",
            "outperforms": "competes",
            "better than": "competes"
        }
        
        for kw, rel_type in relation_keywords.items():
            if kw in abstract:
                # 找到相关概念
                for concept in self.graph["concepts"]:
                    if concept["name"].lower() in abstract:
                        relations.append({
                            "from": analysis.get("id", ""),
                            "to": concept["id"],
                            "type": rel_type,
                            "evidence": f"关键词暗示：{kw}",
                            "date": today()
                        })
        
        return relations
    
    def _detect_contradictions(self, analysis: Dict) -> List[Dict]:
        """检测矛盾"""
        contradictions = []
        
        negation_keywords = ["cannot", "fail", "limitation", "problem"]
        abstract = analysis.get("analysis", {}).get("core_method", "").lower()
        
        for concept in self.graph["concepts"]:
            if concept["name"].lower() in abstract:
                for kw in negation_keywords:
                    if kw in abstract:
                        contradictions.append({
                            "paper": analysis.get("title"),
                            "concept": concept["name"],
                            "evidence": f"发现否定性关键词：{kw}",
                            "severity": "medium"
                        })
        
        return contradictions
    
    def get_summary(self) -> str:
        """获取知识图谱摘要"""
        lines = [
            f"# {self.topic} 知识图谱",
            "",
            f"- 概念数：{len(self.graph['concepts'])}",
            f"- 关系数：{len(self.graph['relations'])}",
            f"- 论文数：{self.graph['metadata'].get('paper_count', 0)}",
            "",
            "## 💡 核心概念（最新10个）",
            ""
        ]
        
        for c in self.graph["concepts"][-10:]:
            type_emoji = {"system": "🔧", "concept": "💡", "method": "⚙️"}.get(c.get("type", "concept"), "📌")
            lines.append(f"### {type_emoji} {c['name']}")
            if c.get("description"):
                lines.append(f"{c['description'][:150]}")
            lines.append("")
        
        return "\n".join(lines)

# ============================================
# 第五阶段：方法论进化
# ============================================

class MethodologyEvolver:
    """研究方法论进化器"""
    
    def __init__(self):
        self.methodology_path = LEARNINGS_DIR / "METHODOLOGY.md"
    
    def evolve(self, new_insights: List[str]) -> int:
        """
        更新研究方法论
        
        Returns:
            新增洞察数量
        """
        if self.methodology_path.exists():
            with open(self.methodology_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# 研究方法论学习记录\n\n"
        
        # 避免重复
        existing_insights = content.lower()
        new_count = 0
        
        for insight in new_insights:
            if insight.lower() not in existing_insights:
                if "## 新增洞察" not in content or content.count("## 新增洞察") < 10:
                    content += f"\n## {today()} 新增洞察\n\n"
                content += f"- {insight}\n"
                new_count += 1
        
        with open(self.methodology_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return new_count
    
    def extract_insights(self, paper_analysis: Dict) -> List[str]:
        """从论文提取方法论洞察"""
        insights = []
        
        # 检查方法论关键词
        method_keywords = [
            "we propose", "our approach", "we introduce",
            "novel method", "new framework"
        ]
        
        abstract = paper_analysis.get("analysis", {}).get("core_method", "").lower()
        
        for kw in method_keywords:
            if kw in abstract:
                # 提取句子
                sentences = abstract.split(".")
                for s in sentences:
                    if kw in s:
                        insights.append(f"[{paper_analysis.get('title', '')[:30]}] {s.strip()}")
                        break
        
        return insights

# ============================================
# 第六阶段：知识缺口进化
# ============================================

class KnowledgeGapEvolver:
    """知识缺口进化器"""
    
    def __init__(self):
        self.gaps_path = LEARNINGS_DIR / "KNOWLEDGE_GAPS.md"
    
    def evolve(self, new_gaps: List[Dict], resolved_gaps: List[str] = None) -> Tuple[int, int]:
        """
        更新知识缺口
        
        Returns:
            (新增缺口数, 解决缺口数)
        """
        if self.gaps_path.exists():
            with open(self.gaps_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# 知识缺口记录\n\n"
        
        # 标记已解决的缺口
        resolved_count = 0
        if resolved_gaps:
            for gap_id in resolved_gaps:
                if gap_id in content:
                    content = content.replace(
                        f"### 🔴 {gap_id}",
                        f"### ✅ {gap_id} (已解决 {today()})"
                    )
                    resolved_count += 1
        
        # 添加新缺口
        new_count = 0
        if new_gaps:
            content += f"\n## {today()} 新发现缺口\n\n"
            for gap in new_gaps:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                content += f"""### {priority_emoji.get(gap.get('priority', 'medium'), '⚪')} {gap.get('title', '未知缺口')}

**问题**：{gap.get('description', '')}
**来源**：{gap.get('source', '')}
**优先级**：{gap.get('priority', 'medium')}

"""
                new_count += 1
        
        with open(self.gaps_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return new_count, resolved_count
    
    def extract_gaps(self, paper_analysis: Dict) -> List[Dict]:
        """从论文提取知识缺口"""
        gaps = []
        
        limitation_keywords = [
            "future work", "limitation", "remains to be",
            "not addressed", "left for future", "open problem"
        ]
        
        abstract = paper_analysis.get("analysis", {}).get("core_method", "").lower()
        
        for kw in limitation_keywords:
            if kw in abstract:
                sentences = abstract.split(".")
                for s in sentences:
                    if kw in s:
                        gaps.append({
                            "title": f"{paper_analysis.get('title', '')[:30]}...",
                            "description": s.strip(),
                            "source": paper_analysis.get("analysis", {}).get("basic_info", {}).get("arxiv_id", ""),
                            "priority": "high" if "critical" in s or "important" in s else "medium"
                        })
                        break
        
        return gaps

# ============================================
# 第七阶段：IMA同步
# ============================================

class IMASyncer:
    """IMA知识库同步器"""
    
    def __init__(self, kb_id: str = "eImkUmYly1k-NH7Pz8e4syn4zs0UXJZufvCX5CSKvN8="):
        self.kb_id = kb_id
        self._load_credentials()
    
    def _load_credentials(self):
        import subprocess
        result = subprocess.run(
            ["powershell", "-File", r"D:\Program Files\QClaw\resources\openclaw\config\skills\ima\get-token.ps1"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            creds = json.loads(result.stdout.strip())
            self.client_id = creds.get("client_id", "")
            self.api_key = creds.get("api_key", "")
        else:
            self.client_id = ""
            self.api_key = ""
    
    def _api_call(self, endpoint: str, body: dict) -> Dict:
        import urllib.request
        url = f"https://ima.qq.com/openapi/{endpoint}"
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={
                "ima-openapi-clientid": self.client_id,
                "ima-openapi-apikey": self.api_key,
                "Content-Type": "application/json; charset=utf-8"
            }
        )
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {"code": -1, "msg": str(e)}
    
    def sync_report(self, title: str, content: str) -> Optional[str]:
        """同步研究报告"""
        result = self._api_call("note/v1/import_doc", {
            "title": title,
            "content": content,
            "content_format": 1
        })
        if result.get("code") == 0:
            note_id = result.get("data", {}).get("note_id")
            # 添加到知识库
            self._api_call("wiki/v1/add_knowledge", {
                "knowledge_base_id": self.kb_id,
                "media_type": 11,
                "note_info": {"content_id": note_id},
                "title": title
            })
            return note_id
        return None
    
    def sync_graph(self, graph_summary: str, topic: str) -> Optional[str]:
        """同步知识图谱摘要"""
        return self.sync_report(f"{topic} - 知识图谱 [{today()}]", graph_summary)
    
    def sync_methodology(self, content: str) -> Optional[str]:
        """同步方法论更新"""
        return self.sync_report(f"研究方法论更新 [{today()}]", content)
    
    def sync_gaps(self, content: str) -> Optional[str]:
        """同步知识缺口"""
        return self.sync_report(f"知识缺口更新 [{today()}]", content)

# ============================================
# 主进化流程
# ============================================

class EvolutionEngine:
    """知识进化引擎"""
    
    def __init__(self, topic: str, kb_id: str = None):
        self.topic = topic
        config = load_yaml(CONFIG_DIR / "optimized_config.yaml") or load_yaml(CONFIG_DIR / "topics.yaml")
        self.topic_config = next((t for t in config.get("topics", []) if topic.lower() in t.get("name", "").lower()), {})
        self.kb_id = kb_id or self.topic_config.get("target_knowledge_base", "eImkUmYly1k-NH7Pz8e4syn4zs0UXJZufvCX5CSKvN8=")
        
        # 初始化各模块
        self.searcher = PaperSearcher(self.topic_config.get("keywords", [topic]))
        self.filter = QualityFilter()
        self.analyzer = DeepAnalyzer()
        self.graph_evolver = KnowledgeGraphEvolver(topic)
        self.method_evolver = MethodologyEvolver()
        self.gap_evolver = KnowledgeGapEvolver()
        self.syncer = IMASyncer(self.kb_id)
    
    def run(self, force: bool = False) -> Dict:
        """执行完整的进化流程"""
        print("=" * 60)
        print("🔬 AI Deep Research Agent — 自我进化版")
        print(f"   主题：{self.topic}")
        print(f"   时间：{now()}")
        print("=" * 60)
        
        results = {
            "topic": self.topic,
            "date": today(),
            "stages": {}
        }
        
        # 检查缓存
        cache = load_cache()
        if not force and cache.get("last_update", {}).get(self.topic) == today():
            print(f"\n✅ 今日已完成研究，跳过")
            return results
        
        # 阶段 1：搜索论文
        print(f"\n📥 阶段 1/7：搜索论文...")
        search_result = self.searcher.search(90)
        results["stages"]["search"] = search_result
        print(f"   关键词：{', '.join(self.searcher.keywords[:3])}")
        
        # 阶段 2：筛选论文
        print(f"\n🔍 阶段 2/7：筛选高质量论文...")
        # 这里返回筛选指令，实际由主模型执行
        results["stages"]["filter"] = {"instruction": "等待主模型执行 web_search 并返回结果"}
        
        # 阶段 3：深度分析
        print(f"\n🧠 阶段 3/7：深度分析...")
        results["stages"]["analysis"] = {"instruction": "等待主模型执行 web_fetch 并返回论文内容"}
        
        # 阶段 4：知识图谱进化
        print(f"\n📊 阶段 4/7：知识图谱进化...")
        graph_summary = self.graph_evolver.get_summary()
        results["stages"]["graph"] = {
            "concepts": len(self.graph_evolver.graph["concepts"]),
            "relations": len(self.graph_evolver.graph["relations"])
        }
        print(f"   概念：{results['stages']['graph']['concepts']}")
        print(f"   关系：{results['stages']['graph']['relations']}")
        
        # 阶段 5：方法论进化
        print(f"\n📖 阶段 5/7：方法论进化...")
        results["stages"]["methodology"] = {"instruction": "等待主模型提取方法论洞察"}
        
        # 阶段 6：知识缺口进化
        print(f"\n🔴 阶段 6/7：知识缺口进化...")
        results["stages"]["gaps"] = {"instruction": "等待主模型识别知识缺口"}
        
        # 阶段 7：IMA同步
        print(f"\n📤 阶段 7/7：IMA 同步...")
        sync_results = []
        
        # 同步知识图谱
        note_id = self.syncer.sync_graph(graph_summary, self.topic)
        if note_id:
            sync_results.append(f"知识图谱：{note_id}")
        
        results["stages"]["sync"] = sync_results
        print(f"   已同步：{len(sync_results)} 项")
        
        # 更新缓存
        cache["last_update"][self.topic] = today()
        save_cache(cache)
        
        print(f"\n{'=' * 60}")
        print(f"✅ {self.topic} 研究完成")
        print("=" * 60)
        
        return results

# ============================================
# CLI 入口
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="AI Deep Research Agent — 自我进化版",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    sub = parser.add_subparsers(dest="cmd")
    
    # evolve 命令
    e = sub.add_parser("evolve", help="执行知识进化")
    e.add_argument("--topic", "-t", required=True)
    e.add_argument("--force", "-f", action="store_true")
    e.add_argument("--kb-id", "-k")
    
    # list 命令
    sub.add_parser("list", help="列出研究主题")
    
    # graph 命令
    g = sub.add_parser("graph", help="知识图谱操作")
    g.add_argument("--topic", "-t", required=True)
    g.add_argument("--summary", "-s", action="store_true")
    
    # sync 命令
    s = sub.add_parser("sync", help="IMA同步")
    s.add_argument("--topic", "-t", required=True)
    s.add_argument("--type", choices=["report", "graph", "methodology", "gaps"], default="report")
    s.add_argument("--file", "-f")
    
    args = parser.parse_args()
    
    if args.cmd == "evolve":
        engine = EvolutionEngine(args.topic, args.kb_id)
        result = engine.run(args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.cmd == "list":
        config = load_yaml(CONFIG_DIR / "topics.yaml")
        print("📋 研究主题列表\n")
        for t in config.get("topics", []):
            name = t.get("name", "")
            enabled = "✅" if t.get("enabled", True) else "⏸️"
            priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", "medium"), "⚪")
            
            graph_file = GRAPHS_DIR / f"{name.replace(' ', '_')}_knowledge_graph.json"
            if graph_file.exists():
                with open(graph_file, 'r', encoding='utf-8') as f:
                    g = json.load(f)
                info = f"概念:{len(g.get('concepts',[]))} 关系:{len(g.get('relations',[]))}"
            else:
                info = "未开始"
            
            print(f"{priority} {enabled} {name}")
            print(f"   {info}")
            print(f"   关键词：{', '.join(t.get('keywords', [])[:3])}")
            print()
    
    elif args.cmd == "graph":
        evolver = KnowledgeGraphEvolver(args.topic)
        if args.summary:
            print(evolver.get_summary())
    
    elif args.cmd == "sync":
        syncer = IMASyncer()
        if args.file and Path(args.file).exists():
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if args.type == "report":
                note_id = syncer.sync_report(f"{args.topic} 研究报告 [{today()}]", content)
            elif args.type == "graph":
                note_id = syncer.sync_graph(content, args.topic)
            else:
                note_id = syncer.sync_report(f"{args.topic} {args.type} [{today()}]", content)
            
            if note_id:
                print(f"✅ 同步成功：{note_id}")
            else:
                print(f"❌ 同步失败")
        else:
            print(f"❌ 文件不存在：{args.file}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()