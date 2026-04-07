#!/usr/bin/env python3
"""
IMA 知识固化服务
将深度研究成果持久化到 IMA 知识库，支持多种知识类型
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ============================================
# 配置
# ============================================

SCRIPT_DIR = Path(__file__).parent
IMA_SKILL_PATH = Path("D:/Program Files/QClaw/resources/openclaw/config/skills/ima")
IMA_TOKEN_SCRIPT = IMA_SKILL_PATH / "get-token.ps1"

# 默认知识库 ID
DEFAULT_KB_ID = "eImkUmYly1k-NH7Pz8e4syn4zs0UXJZufvCX5CSKvN8="

# ============================================
# IMA API 封装
# ============================================

def get_ima_credentials() -> Dict[str, str]:
    """获取 IMA API 凭证"""
    try:
        result = subprocess.run(
            ["powershell", "-File", str(IMA_TOKEN_SCRIPT)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            creds = json.loads(result.stdout.strip())
            return {
                "client_id": creds.get("client_id", ""),
                "api_key": creds.get("api_key", "")
            }
    except Exception as e:
        print(f"❌ 获取 IMA 凭证失败: {e}")
    return {"client_id": "", "api_key": ""}


def ima_api(endpoint: str, body: dict, creds: Dict[str, str]) -> dict:
    """调用 IMA API"""
    import urllib.request
    
    url = f"https://ima.qq.com/openapi/{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={
            "ima-openapi-clientid": creds["client_id"],
            "ima-openapi-apikey": creds["api_key"],
            "Content-Type": "application/json; charset=utf-8"
        }
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": -1, "msg": str(e)}


# ============================================
# 知识固化方法
# ============================================

class IMAKnowledgeBase:
    """IMA 知识库管理器"""
    
    def __init__(self, kb_id: str = DEFAULT_KB_ID):
        self.kb_id = kb_id
        self.creds = get_ima_credentials()
        if not self.creds["client_id"]:
            raise RuntimeError("IMA 凭证获取失败")
    
    # ========== 1. 研究报告（笔记）==========
    
    def create_research_note(self, title: str, content: str) -> Optional[str]:
        """创建研究报告笔记（带去重检查）"""
        # 先检查是否已存在同名笔记
        existing = self._find_note_by_title(title)
        if existing:
            print(f"   ⚠️ 已存在同名笔记，更新内容而非创建新笔记")
            # 使用新标题（带时间戳）
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            title = f"{title} [{timestamp}]"
            print(f"   📝 新标题：{title}")
        
        result = ima_api("note/v1/import_doc", {
            "title": title,
            "content": content,
            "content_format": 1  # Markdown
        }, self.creds)
        
        if result.get("code") == 0:
            note_id = result.get("data", {}).get("note_id")
            print(f"   ✅ 笔记已创建: {note_id}")
            return note_id
        else:
            print(f"   ❌ 创建笔记失败: {result.get('msg')}")
            return None
    
    def add_note_to_kb(self, note_id: str, title: str) -> bool:
        """将笔记添加到知识库"""
        result = ima_api("wiki/v1/add_knowledge", {
            "knowledge_base_id": self.kb_id,
            "media_type": 11,  # 笔记
            "note_info": {"content_id": note_id},
            "title": title
        }, self.creds)
        
        if result.get("code") == 0:
            print(f"   ✅ 已添加到知识库")
            return True
        else:
            print(f"   ❌ 添加失败: {result.get('msg')}")
            return False
    
    # ========== 2. 知识图谱（JSON 文件）==========
    
    def upload_knowledge_graph(self, graph_path: str, title: str) -> bool:
        """上传知识图谱 JSON 文件（带去重）"""
        # 检查是否已存在
        note_title = f"{title} - 知识图谱"
        existing = self._find_note_by_title(note_title)
        if existing:
            print(f"   ✅ 知识图谱已存在，跳过重复创建")
            return True  # 视为成功
        
        # IMA 暂不支持直接上传 JSON，转换为笔记
        with open(graph_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        # 转换为 Markdown 格式
        content = self._graph_to_markdown(graph_data)
        
        # 创建笔记
        result = ima_api("note/v1/import_doc", {
            "title": note_title,
            "content": content,
            "content_format": 1
        }, self.creds)
        
        if result.get("code") != 0:
            print(f"   ❌ 创建笔记失败: {result.get('msg')}")
            return False
        
        note_id = result.get("data", {}).get("note_id")
        print(f"   ✅ 笔记已创建: {note_id}")
        
        # 添加到知识库
        return self.add_note_to_kb(note_id, note_title)
    
    def _find_note_by_title(self, title: str) -> Optional[str]:
        """查找知识库中是否已存在指定标题的笔记"""
        result = ima_api('wiki/v1/get_knowledge_list', {
            'knowledge_base_id': self.kb_id,
            'limit': 50
        }, self.creds)
        
        if result.get('code') == 0:
            items = result.get('data', {}).get('knowledge_list', [])
            for item in items:
                if item.get('title') == title:
                    return item.get('media_id')
        return None
    
    def _graph_to_markdown(self, graph: dict) -> str:
        """将知识图谱转换为 Markdown"""
        lines = [
            f"# {graph['topic']} - 知识图谱",
            f"\n> 更新时间: {graph.get('metadata', {}).get('updated', 'N/A')[:10]}",
            f"\n## 📊 概览",
            f"- 概念数量: {len(graph.get('concepts', []))}",
            f"- 关系数量: {len(graph.get('relations', []))}",
            f"- 论文数量: {graph.get('metadata', {}).get('paper_count', 0)}",
            f"\n## 💡 核心概念\n"
        ]
        
        for concept in graph.get('concepts', []):
            type_emoji = {"system": "🔧", "concept": "💡", "method": "⚙️", "dataset": "📊", "metric": "📈"}.get(concept['type'], "📌")
            lines.append(f"### {type_emoji} {concept['name']}")
            if concept.get('description'):
                lines.append(f"{concept['description'][:200]}")
            if concept.get('papers'):
                lines.append(f"相关论文: {', '.join(concept['papers'][:3])}")
            lines.append("")
        
        # 洞察
        insights = graph.get('insights', {})
        if insights.get('breakthroughs'):
            lines.append("## 🚀 突破性发现")
            for b in insights['breakthroughs']:
                lines.append(f"- {b}")
            lines.append("")
        
        if insights.get('gaps'):
            lines.append("## 🔴 知识缺口")
            for g in insights['gaps']:
                lines.append(f"- {g}")
            lines.append("")
        
        if insights.get('trends'):
            lines.append("## 📈 趋势预测")
            for t in insights['trends']:
                lines.append(f"- {t}")
            lines.append("")
        
        return "\n".join(lines)
    
    # ========== 3. 知识缺口（待解决问题）==========
    
    def sync_knowledge_gaps(self, gaps_path: str) -> bool:
        """同步知识缺口"""
        with open(gaps_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        note_id = self.create_research_note(
            "AI Agent 记忆系统 - 知识缺口",
            content
        )
        
        if note_id:
            return self.add_note_to_kb(note_id, "知识缺口与待解决问题")
        return False
    
    # ========== 4. 研究方法论 ==========
    
    def sync_methodology(self, method_path: str) -> bool:
        """同步研究方法论"""
        with open(method_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        note_id = self.create_research_note(
            "AI Deep Research - 方法论",
            content
        )
        
        if note_id:
            return self.add_note_to_kb(note_id, "研究方法论")
        return False
    
    # ========== 5. 搜索已有知识 ==========
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[dict]:
        """搜索知识库"""
        result = ima_api("wiki/v1/search_knowledge", {
            "knowledge_base_id": self.kb_id,
            "query": query,
            "limit": limit
        }, self.creds)
        
        if result.get("code") == 0:
            return result.get("data", {}).get("list", [])
        return []
    
    # ========== 6. 统一固化接口 ==========
    
    def solidify_research(self, topic: str, report_path: str = None, graph_path: str = None) -> Dict:
        """
        固化研究成果到 IMA
        
        Args:
            topic: 研究主题
            report_path: 研究报告路径（可选）
            graph_path: 知识图谱路径（可选）
        
        Returns:
            {"success": bool, "synced": list, "errors": list}
        """
        print(f"\n📤 固化研究成果到 IMA 知识库...")
        print(f"   知识库 ID: {self.kb_id[:20]}...")
        
        results = {"success": True, "synced": [], "errors": []}
        
        # 1. 研究报告
        if report_path and Path(report_path).exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            note_id = self.create_research_note(
                f"{topic} 深度研究 — {date_str}",
                content
            )
            
            if note_id and self.add_note_to_kb(note_id, f"{topic} 深度研究"):
                results["synced"].append("研究报告")
            else:
                results["errors"].append("研究报告")
                results["success"] = False
        
        # 2. 知识图谱
        if graph_path and Path(graph_path).exists():
            if self.upload_knowledge_graph(graph_path, topic):
                results["synced"].append("知识图谱")
            else:
                results["errors"].append("知识图谱")
        
        # 3. 汇总
        if results["synced"]:
            print(f"\n✅ 已固化: {', '.join(results['synced'])}")
        if results["errors"]:
            print(f"⚠️ 失败: {', '.join(results['errors'])}")
        
        return results


# ============================================
# CLI 入口
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="IMA 知识固化服务")
    parser.add_argument("--report", "-r", help="研究报告路径")
    parser.add_argument("--graph", "-g", help="知识图谱路径")
    parser.add_argument("--topic", "-t", default="AI Agent 记忆系统", help="研究主题")
    parser.add_argument("--search", "-s", help="搜索知识库")
    parser.add_argument("--kb-id", "-k", default=DEFAULT_KB_ID, help="知识库 ID")
    
    args = parser.parse_args()
    
    try:
        kb = IMAKnowledgeBase(args.kb_id)
        
        if args.search:
            results = kb.search_knowledge(args.search)
            print(f"🔍 搜索结果: {len(results)} 条")
            for r in results[:5]:
                print(f"  - {r.get('title', 'N/A')}")
        
        elif args.report or args.graph:
            result = kb.solidify_research(
                args.topic,
                report_path=args.report,
                graph_path=args.graph
            )
            sys.exit(0 if result["success"] else 1)
        
        else:
            print("请指定 --report 或 --search 参数")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)