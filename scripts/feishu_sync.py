#!/usr/bin/env python3
"""
飞书同步模块
将研究成果同步到飞书云文档
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SKILL_DIR / "topics"
EXPORTS_DIR = SKILL_DIR / "exports" / "feishu"

# ============================================
# 飞书 API 客户端
# ============================================

class FeishuClient:
    """飞书 API 客户端"""
    
    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET", "")
        self.access_token = None
        self.folder_token = os.environ.get("FEISHU_FOLDER_TOKEN", "")
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        import urllib.request
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            if result.get("code") == 0:
                self.access_token = result.get("tenant_access_token")
                return self.access_token
        except Exception as e:
            print(f"获取飞书令牌失败：{e}")
        
        return ""
    
    def _api_call(self, endpoint: str, data: dict, method: str = "POST") -> Dict:
        """调用飞书 API"""
        import urllib.request
        
        if not self.access_token:
            self._get_access_token()
        
        url = f"https://open.feishu.cn/open-apis/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            method=method
        )
        
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {"code": -1, "msg": str(e)}
    
    def create_document(self, title: str, content: str, folder_token: str = None) -> Optional[str]:
        """
        创建飞书文档
        
        Args:
            title: 文档标题
            content: 文档内容（Markdown）
            folder_token: 文件夹令牌
        
        Returns:
            文档 token 或 None
        """
        folder_token = folder_token or self.folder_token
        
        # 飞书文档创建 API（简化版）
        result = self._api_call("docx/v1/documents", {
            "title": title,
            "folder_token": folder_token
        })
        
        if result.get("code") != 0:
            print(f"创建文档失败：{result.get('msg')}")
            return None
        
        doc_token = result.get("data", {}).get("document", {}).get("document_id")
        
        # 写入内容（需要分段处理）
        if doc_token and content:
            self._write_content(doc_token, content)
        
        return doc_token
    
    def _write_content(self, doc_token: str, content: str):
        """写入文档内容"""
        # 将 Markdown 转换为飞书文档格式（简化实现）
        paragraphs = content.split("\n\n")
        
        blocks = []
        for para in paragraphs[:100]:  # 限制段落数
            if para.strip():
                blocks.append({
                    "type": "text",
                    "text": para.strip()[:5000]  # 飞书限制
                })
        
        # 批量写入
        self._api_call(f"docx/v1/documents/{doc_token}/blocks/batch_update", {
            "blocks": blocks
        })

# ============================================
# 同步管理器
# ============================================

class FeishuSyncer:
    """飞书同步管理器"""
    
    def __init__(self):
        self.client = FeishuClient()
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def sync_topic(self, topic_id: str) -> Dict:
        """
        同步单个题材到飞书
        
        Returns:
            同步结果
        """
        topic_path = TOPICS_DIR / topic_id
        if not topic_path.exists():
            return {"error": f"题材不存在：{topic_id}"}
        
        # 收集题材内容
        reports = list((topic_path / "knowledge" / "reports").glob("*.md"))
        graph_path = topic_path / "knowledge" / "graphs" / f"{topic_id}_knowledge_graph.json"
        
        # 创建汇总文档
        all_content = self._build_topic_document(topic_id, reports, graph_path)
        
        # 同步到飞书
        doc_token = self.client.create_document(
            title=f"AI研究：{topic_id}",
            content=all_content
        )
        
        if doc_token:
            # 记录同步日志
            log_path = EXPORTS_DIR / f"{topic_id}_sync_log.json"
            log_data = {
                "topic_id": topic_id,
                "doc_token": doc_token,
                "synced_at": datetime.now().isoformat(),
                "reports_count": len(reports)
            }
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "doc_token": doc_token}
        
        return {"error": "同步失败"}
    
    def sync_all_topics(self) -> Dict:
        """同步所有启用的题材"""
        results = {
            "synced": [],
            "failed": [],
            "total": 0,
            "success_count": 0
        }
        
        for topic_dir in TOPICS_DIR.iterdir():
            if not topic_dir.is_dir():
                continue
            
            topic_id = topic_dir.name
            result = self.sync_topic(topic_id)
            
            if result.get("success"):
                results["synced"].append({
                    "topic_id": topic_id,
                    "doc_token": result["doc_token"]
                })
                results["success_count"] += 1
            else:
                results["failed"].append({
                    "topic_id": topic_id,
                    "error": result.get("error")
                })
            
            results["total"] += 1
        
        # 创建汇总文档
        if results["synced"]:
            self._create_summary_document(results)
        
        return results
    
    def _build_topic_document(self, topic_id: str, reports: List[Path], graph_path: Path) -> str:
        """构建题材文档"""
        lines = [
            f"# AI 研究：{topic_id}",
            "",
            f"> 同步时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📊 知识图谱摘要",
            ""
        ]
        
        # 知识图谱摘要
        if graph_path.exists():
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph = json.load(f)
            
            lines.append(f"- 概念数：{len(graph.get('concepts', []))}")
            lines.append(f"- 关系数：{len(graph.get('relations', []))}")
            lines.append(f"- 论文数：{graph.get('metadata', {}).get('paper_count', 0)}")
            lines.append("")
            
            # 核心概念
            lines.append("### 💡 核心概念")
            lines.append("")
            for c in graph.get("concepts", [])[:10]:
                type_emoji = {"system": "🔧", "concept": "💡", "method": "⚙️"}.get(c.get("type", "concept"), "📌")
                lines.append(f"- {type_emoji} **{c['name']}**")
                if c.get("description"):
                    lines.append(f"  - {c['description'][:100]}")
            lines.append("")
        
        # 研究报告
        lines.append("## 📖 研究报告")
        lines.append("")
        
        for report in reports[-5:]:  # 最近5份报告
            with open(report, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines.append(f"### {report.stem}")
            lines.append("")
            lines.append(content[:2000])  # 截断
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _create_summary_document(self, results: Dict):
        """创建汇总文档"""
        lines = [
            "# AI 研究汇总",
            "",
            f"> 同步时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"- 总题材数：{results['total']}",
            f"- 成功同步：{results['success_count']}",
            "",
            "## 📚 同步详情",
            ""
        ]
        
        for item in results["synced"]:
            lines.append(f"- ✅ {item['topic_id']}（文档：{item['doc_token'][:20]}...）")
        
        for item in results["failed"]:
            lines.append(f"- ❌ {item['topic_id']}（{item['error']}）")
        
        self.client.create_document(
            title="AI研究汇总报告",
            content="\n".join(lines)
        )

# ============================================
# CLI 入口
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="飞书同步")
    parser.add_argument("action", choices=["sync", "sync-all", "status"])
    parser.add_argument("--topic", "-t", help="题材 ID")
    
    args = parser.parse_args()
    
    syncer = FeishuSyncer()
    
    if args.action == "sync":
        if not args.topic:
            print("请提供 --topic")
            return
        result = syncer.sync_topic(args.topic)
        if result.get("success"):
            print(f"✅ 同步成功：{result['doc_token']}")
        else:
            print(f"❌ 同步失败：{result.get('error')}")
    
    elif args.action == "sync-all":
        results = syncer.sync_all_topics()
        print(f"📤 同步完成")
        print(f"   成功：{results['success_count']}/{results['total']}")
        for item in results["synced"]:
            print(f"   ✅ {item['topic_id']}")
        for item in results["failed"]:
            print(f"   ❌ {item['topic_id']}: {item['error']}")
    
    elif args.action == "status":
        logs = list(EXPORTS_DIR.glob("*_sync_log.json"))
        print(f"📋 飞书同步状态\n")
        for log in logs[:10]:
            with open(log, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"- {data['topic_id']}")
            print(f"  文档：{data['doc_token'][:20]}...")
            print(f"  时间：{data['synced_at'][:19]}")
            print()

if __name__ == "__main__":
    main()