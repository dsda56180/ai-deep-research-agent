#!/usr/bin/env python3
"""
Token 消耗监控器
基于 Karpathy 的"了解模型限制"原则
- 每周预算控制
- 异常检测
- 自动优化建议
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
STATS_FILE = SKILL_DIR / ".learnings" / "token_stats.json"

# ============================================
# Token 预算配置
# ============================================

BUDGET = {
    "daily_limit": 50000,      # 每天最大
    "weekly_limit": 300000,    # 每周最大
    "alert_threshold": 0.8,     # 告警阈值 80%
    "critical_threshold": 0.95  # 严重阈值 95%
}

# ============================================
# Token 统计类
# ============================================

class TokenMonitor:
    """Token 消耗监控"""
    
    def __init__(self):
        self.stats = self._load_stats()
    
    def _load_stats(self) -> dict:
        if STATS_FILE.exists():
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        return {
            "daily": defaultdict(int),
            "weekly": defaultdict(int),
            "monthly": defaultdict(int),
            "by_operation": defaultdict(int),
            "last_reset": datetime.now().isoformat()
        }
    
    def _save_stats(self):
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATS_FILE, 'w') as f:
            json.dump(dict(self.stats), f, indent=2)
    
    def record(self, operation: str, tokens: int):
        """记录 Token 消耗"""
        today = datetime.now().strftime('%Y-%m-%d')
        week = datetime.now().strftime('%Y-W%W')
        month = datetime.now().strftime('%Y-%m')
        
        self.stats["daily"][today] += tokens
        self.stats["weekly"][week] += tokens
        self.stats["monthly"][month] += tokens
        self.stats["by_operation"][operation] += tokens
        self._save_stats()
    
    def get_status(self) -> dict:
        """获取当前状态"""
        today = datetime.now().strftime('%Y-%m-%d')
        week = datetime.now().strftime('%Y-W%W')
        
        daily_used = self.stats["daily"].get(today, 0)
        weekly_used = self.stats["weekly"].get(week, 0)
        
        return {
            "daily": {
                "used": daily_used,
                "limit": BUDGET["daily_limit"],
                "percent": daily_used / BUDGET["daily_limit"] * 100
            },
            "weekly": {
                "used": weekly_used,
                "limit": BUDGET["weekly_limit"],
                "percent": weekly_used / BUDGET["weekly_limit"] * 100
            },
            "by_operation": dict(sorted(
                self.stats["by_operation"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5])
        }
    
    def check_alerts(self) -> list:
        """检查是否需要告警"""
        alerts = []
        status = self.get_status()
        
        # 每日告警
        if status["daily"]["percent"] >= BUDGET["critical_threshold"]:
            alerts.append({
                "level": "critical",
                "message": f"今日Token消耗已达 {status['daily']['percent']:.0f}%",
                "action": "建议减少搜索量或切换到周模式"
            })
        elif status["daily"]["percent"] >= BUDGET["alert_threshold"]:
            alerts.append({
                "level": "warning", 
                "message": f"今日Token消耗已达 {status['daily']['percent']:.0f}%",
                "action": "注意控制搜索量"
            })
        
        # 每周告警
        if status["weekly"]["percent"] >= BUDGET["critical_threshold"]:
            alerts.append({
                "level": "critical",
                "message": f"本周Token消耗已达 {status['weekly']['percent']:.0f}%",
                "action": "建议暂停非必要研究"
            })
        
        return alerts
    
    def get_optimization_tips(self) -> list:
        """获取优化建议"""
        tips = []
        status = self.get_status()
        
        # 基于消耗最高的操作
        top_ops = list(status["by_operation"].keys())[:2]
        if "search" in top_ops:
            tips.append("搜索Token消耗高，建议：减少搜索关键词数量")
        if "analysis" in top_ops:
            tips.append("分析Token消耗高，建议：减少每批分析论文数")
        
        # 基于消耗趋势
        if status["daily"]["percent"] > 50:
            tips.append("当前消耗较高，可考虑：1)延迟非紧急研究 2)开启压缩模式")
        
        return tips
    
    def reset_daily(self):
        """重置每日统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        self.stats["daily"] = defaultdict(int)
        self.stats["daily"][today] = 0
        self._save_stats()

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Token消耗监控")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("status", help="显示消耗状态")
    sub.add_parser("alerts", help="检查告警")
    sub.add_parser("tips", help="获取优化建议")
    
    record_parser = sub.add_parser("record", help="记录消耗")
    record_parser.add_argument("--operation", required=True)
    record_parser.add_argument("--tokens", type=int, required=True)
    
    args = parser.parse_args()
    
    monitor = TokenMonitor()
    
    if args.cmd == "status":
        status = monitor.get_status()
        print("📊 Token消耗状态\n")
        print(f"今日：{status['daily']['used']:,} / {status['daily']['limit']:,} ({status['daily']['percent']:.1f}%)")
        print(f"本周：{status['weekly']['used']:,} / {status['weekly']['limit']:,} ({status['weekly']['percent']:.1f}%)\n")
        print("Top 5 操作：")
        for op, count in status["by_operation"].items():
            print(f"  {op}: {count:,}")
    
    elif args.cmd == "alerts":
        alerts = monitor.check_alerts()
        if not alerts:
            print("✅ 无告警")
        else:
            for a in alerts:
                icon = "🔴" if a["level"] == "critical" else "🟡"
                print(f"{icon} {a['message']}")
                print(f"   建议：{a['action']}\n")
    
    elif args.cmd == "tips":
        tips = monitor.get_optimization_tips()
        if tips:
            print("💡 优化建议：")
            for t in tips:
                print(f"  - {t}")
        else:
            print("✅ 消耗正常，无需优化")
    
    elif args.cmd == "record":
        monitor.record(args.operation, args.tokens)
        print(f"✅ 已记录：{args.operation} = {args.tokens:,} tokens")