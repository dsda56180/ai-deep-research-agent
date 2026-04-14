#!/usr/bin/env python3
"""
自学习模块
继承 self-improving-agent 的学习机制，实现研究方法的持续进化
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

import yaml

from knowledge_graph import Relation, get_or_create_graph

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
LEARNINGS_DIR = SKILL_DIR / ".learnings"
METHODS_DIR = LEARNINGS_DIR / "methods"
PATTERNS_DIR = LEARNINGS_DIR / "patterns"
ARCHIVE_DIR = LEARNINGS_DIR / "archive"
TOPICS_DIR = SKILL_DIR / "topics"
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

# 确保目录存在
for d in [LEARNINGS_DIR, METHODS_DIR, PATTERNS_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================
# 核心数据结构
# ============================================

class LearningMemory:
    """自学习记忆管理器"""
    
    def __init__(self):
        self.memory_file = LEARNINGS_DIR / "memory.md"
        self.corrections_file = LEARNINGS_DIR / "corrections.md"
        self.usage_stats = LEARNINGS_DIR / "usage_stats.json"
        self._topics_cache = None
        self._load_memory()
    
    def _load_memory(self):
        """加载记忆"""
        if self.memory_file.exists():
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                self.memory_content = f.read()
        else:
            self.memory_content = self._init_memory()
            self._save_memory()
        
        if self.corrections_file.exists():
            with open(self.corrections_file, 'r', encoding='utf-8') as f:
                self.corrections_content = f.read()
        else:
            self.corrections_content = "# 研究纠正记录\n\n"
            self._save_corrections()
        
        if self.usage_stats.exists():
            with open(self.usage_stats, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
        else:
            self.stats = {"patterns": {}, "corrections": {}, "last_promoted": {}, "signal_meta": {}}
            self._save_stats()
        self._ensure_stats_schema()
    
    def _init_memory(self) -> str:
        """初始化记忆模板"""
        return """# 研究最佳实践（自动更新）

> 最后更新：{date}

## 🔍 搜索策略
- 使用组合关键词，避免过于宽泛
- 同时搜索 arXiv 和 Google Scholar
- 检查论文引用关系找到核心工作

## 📊 分析框架
- 必须包含：方法、创新、实验、局限
- 对比至少 2 个基准方法
- 提取可复现的关键代码片段

## ⚠️ 避免模式（来自失败）
- 不要只看摘要就下结论
- 不要忽略 limitations 章节
- 不要遗漏方法论的关键假设
""".format(date=datetime.now().strftime("%Y-%m-%d"))
    
    def _save_memory(self):
        """保存记忆"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            f.write(self.memory_content)

    def _touch_memory_timestamp(self):
        current_date = datetime.now().strftime("%Y-%m-%d")
        updated = re.sub(
            r"(> 最后更新：)(\d{4}-\d{2}-\d{2})",
            rf"\g<1>{current_date}",
            self.memory_content,
            count=1,
        )
        if updated == self.memory_content and "> 最后更新：" not in self.memory_content:
            updated = f"> 最后更新：{current_date}\n\n{self.memory_content.lstrip()}"
        self.memory_content = updated

    def _append_success_pattern(self, pattern: str, context: str, usage_count: int):
        self._touch_memory_timestamp()
        normalized_pattern = pattern.strip()
        if not normalized_pattern:
            return
        if normalized_pattern.lower() in self.memory_content.lower():
            self._save_memory()
            return
        section_title = "## ✅ 成功模式（自动积累）"
        if section_title not in self.memory_content:
            self.memory_content = self.memory_content.rstrip() + f"\n\n{section_title}\n"
        today = datetime.now().strftime("%Y-%m-%d")
        entry = (
            f"\n### {today} 模式 {usage_count}\n"
            f"- PATTERN: {normalized_pattern}\n"
            f"- CONTEXT: {context.strip() or 'general'}\n"
        )
        self.memory_content = self.memory_content.rstrip() + entry + "\n"
        self._save_memory()
    
    def _save_corrections(self):
        """保存纠正记录"""
        with open(self.corrections_file, 'w', encoding='utf-8') as f:
            f.write(self.corrections_content)
    
    def _save_stats(self):
        """保存统计"""
        with open(self.usage_stats, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def _ensure_stats_schema(self):
        self.stats.setdefault("patterns", {})
        self.stats.setdefault("corrections", {})
        self.stats.setdefault("last_promoted", {})
        self.stats.setdefault("signal_meta", {})

    def _touch_signal_meta(self, bucket: str, key: str):
        self._ensure_stats_schema()
        meta = self.stats["signal_meta"].setdefault(key, {})
        now_value = datetime.now().isoformat()
        meta.setdefault("created_at", now_value)
        meta["last_seen"] = now_value
        meta["bucket"] = bucket
        meta["raw_count"] = self.stats.get(bucket, {}).get(key, 0)

    def _effective_signal_score(self, bucket: str, key: str) -> float:
        self._ensure_stats_schema()
        raw_count = self.stats.get(bucket, {}).get(key, 0)
        if raw_count <= 0:
            return 0.0
        meta = self.stats["signal_meta"].get(key, {})
        last_seen = meta.get("last_seen") or meta.get("created_at")
        idle_days = 0
        if last_seen:
            try:
                idle_days = max(0, (datetime.now() - datetime.fromisoformat(last_seen)).days)
            except ValueError:
                idle_days = 0
        decay_factor = 0.88 ** (idle_days // 7)
        return round(raw_count * decay_factor, 2)
    
    # ========================================
    # 学习信号处理
    # ========================================

    def _load_topics(self) -> List[Dict]:
        if self._topics_cache is not None:
            return self._topics_cache
        config_file = SKILL_DIR / "config" / "topics.yaml"
        if not config_file.exists():
            self._topics_cache = []
            return self._topics_cache
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        self._topics_cache = config.get("topics", [])
        return self._topics_cache

    def _resolve_topic(self, context: str) -> Tuple[str, Optional[str]]:
        normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (context or "").lower())
        for topic in self._load_topics():
            candidates = [topic.get("id", ""), topic.get("name", "")]
            candidates.extend(topic.get("keywords", []))
            for candidate in candidates:
                if not candidate:
                    continue
                candidate_normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(candidate).lower())
                if candidate_normalized and candidate_normalized in normalized:
                    return topic.get("name", "self-learning"), topic.get("id")
        return "self-learning", None

    def _get_graph_for_context(self, context: str):
        topic_name, topic_id = self._resolve_topic(context)
        if topic_id:
            return get_or_create_graph(
                topic_name,
                base_dir=TOPICS_DIR / topic_id / "knowledge" / "graphs",
                filename=f"{topic_id}_knowledge_graph.json",
            )
        return get_or_create_graph(topic_name, base_dir=KNOWLEDGE_DIR / "graphs", filename="self_learning_knowledge_graph.json")

    def _sync_signal_to_graph(
        self,
        signal_type: str,
        title: str,
        content: str,
        context: str,
        score: int,
        source_path: Path,
        attributes: Optional[Dict] = None,
    ) -> bool:
        try:
            graph = self._get_graph_for_context(context)
            document = graph.upsert_entity(
                name=source_path.stem,
                entity_type="Document",
                entity_id=f"document-{source_path.stem.lower().replace('_', '-')}",
                description=f"学习信号来源：{source_path.name}",
                summary=str(source_path),
                attributes={"path": str(source_path), "kind": "self-learning"},
                aliases=[str(source_path)],
                layer="warm",
                confidence=1.0,
            )
            entity = graph.add_learning_signal(signal_type, title, content, context, score=score)
            entity.attributes.update(attributes or {})
            entity.source_ids = sorted(set(entity.source_ids + [document.id]))
            graph.add_relation(Relation(
                from_id=document.id,
                to_id=entity.id,
                type="records",
                evidence=content[:160],
                status="EXTRACTED",
                confidence=min(1.0, 0.5 + score * 0.1),
                source_document=document.id,
                extractor_version="self-learning-v3",
            ))
            graph.refresh_views()
            return True
        except Exception:
            return False
    
    def learn_from_correction(self, context: str, reflection: str, lesson: str) -> bool:
        """
        从纠正中学习
        
        Args:
            context: 任务上下文
            reflection: 反思内容
            lesson: 学习要点
        
        Returns:
            是否成功记录
        """
        today = datetime.now().strftime("%Y-%m-%d")
        entry = f"""
## {today}
CONTEXT: {context}
REFLECTION: {reflection}
LESSON: {lesson}

"""
        self.corrections_content += entry
        self._save_corrections()
        
        # 更新使用统计
        lesson_key = lesson[:50].lower()
        self.stats["corrections"][lesson_key] = self.stats["corrections"].get(lesson_key, 0) + 1
        self._touch_signal_meta("corrections", lesson_key)
        self._save_stats()
        self._sync_signal_to_graph(
            signal_type="Lesson",
            title=lesson,
            content=f"REFLECTION: {reflection}\nLESSON: {lesson}",
            context=context,
            score=max(1, round(self._effective_signal_score("corrections", lesson_key))),
            source_path=self.corrections_file,
            attributes={
                "reflection": reflection,
                "kind": "correction",
                "effective_score": self._effective_signal_score("corrections", lesson_key),
            },
        )
        
        # 检查是否需要晋升到 HOT
        self._check_promotion(lesson_key)
        
        return True
    
    def learn_from_success(self, pattern: str, context: str) -> bool:
        """
        从成功模式中学习
        
        Args:
            pattern: 成功模式描述
            context: 应用上下文
        """
        pattern_key = pattern[:50].lower()
        self.stats["patterns"][pattern_key] = self.stats["patterns"].get(pattern_key, 0) + 1
        self._touch_signal_meta("patterns", pattern_key)
        self._save_stats()
        self._append_success_pattern(pattern, context, self.stats["patterns"][pattern_key])
        self._sync_signal_to_graph(
            signal_type="Pattern",
            title=pattern,
            content=f"PATTERN: {pattern}\nCONTEXT: {context}",
            context=context,
            score=max(1, round(self._effective_signal_score("patterns", pattern_key))),
            source_path=self.memory_file,
            attributes={
                "kind": "success-pattern",
                "effective_score": self._effective_signal_score("patterns", pattern_key),
            },
        )
        
        # 检查晋升
        self._check_promotion(pattern_key)
        
        return True
    
    def _check_promotion(self, pattern_key: str):
        """检查是否需要晋升到 HOT memory"""
        usage_count = self._effective_signal_score("patterns", pattern_key)
        corrections_count = self._effective_signal_score("corrections", pattern_key)
        total_count = usage_count + corrections_count
        
        if total_count >= 3:
            last_promoted = self.stats["last_promoted"].get(pattern_key)
            if not last_promoted or (datetime.now() - datetime.fromisoformat(last_promoted)).days >= 7:
                self._promote_to_hot(pattern_key)
                self.stats["last_promoted"][pattern_key] = datetime.now().isoformat()
                self._save_stats()
    
    def _promote_to_hot(self, pattern_key: str):
        """晋升到 HOT memory"""
        section = f"\n### 🔥 {pattern_key.title()}\n"
        section += f"验证次数：{self.stats['patterns'].get(pattern_key, 0)} 次\n"
        section += f"当前有效分：{self._effective_signal_score('patterns', pattern_key) + self._effective_signal_score('corrections', pattern_key):.2f}\n"
        section += f"晋升日期：{datetime.now().strftime('%Y-%m-%d')}\n"
        
        # 避免重复添加
        if pattern_key.lower() not in self.memory_content.lower():
            self.memory_content += section
            self._save_memory()
            self._sync_signal_to_graph(
                signal_type="Pattern",
                title=pattern_key.title(),
                content=section.strip(),
                context=pattern_key,
                score=max(1, round(self._effective_signal_score('patterns', pattern_key) + self._effective_signal_score('corrections', pattern_key))),
                source_path=self.memory_file,
                attributes={
                    "kind": "promotion",
                    "promoted": True,
                    "effective_score": self._effective_signal_score('patterns', pattern_key) + self._effective_signal_score('corrections', pattern_key),
                },
            )
            return True
        return False
    
    # ========================================
    # 自反思机制
    # ========================================
    
    def self_reflect(self, task_type: str, outcome: str, improvements: List[str]) -> Dict:
        """
        自我反思
        
        Args:
            task_type: 任务类型
            outcome: 完成结果
            improvements: 改进建议
        
        Returns:
            反思摘要
        """
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "outcome": outcome,
            "improvements": improvements,
            "lessons": []
        }
        
        # 根据任务类型提取学习要点
        if task_type == "paper_search":
            if "找到" not in outcome and "无关" in outcome:
                lesson = self._extract_search_lesson(outcome, improvements)
                reflection["lessons"].append(lesson)
        
        elif task_type == "paper_analysis":
            if "遗漏" in outcome or "不完整" in outcome:
                lesson = self._extract_analysis_lesson(outcome, improvements)
                reflection["lessons"].append(lesson)
        
        # 记录学习
        for lesson in reflection["lessons"]:
            self.learn_from_correction(
                context=task_type,
                reflection=outcome,
                lesson=lesson
            )
        
        return reflection
    
    def _extract_search_lesson(self, outcome: str, improvements: List[str]) -> str:
        """提取搜索相关的学习要点"""
        if "关键词" in outcome or "关键词" in " ".join(improvements):
            return "使用更精确的组合关键词，避免过于宽泛"
        elif "来源" in outcome:
            return "同时搜索多个数据源（arXiv + Google Scholar）"
        return "优化搜索策略"
    
    def _extract_analysis_lesson(self, outcome: str, improvements: List[str]) -> str:
        """提取分析相关的学习要点"""
        if "方法" in outcome:
            return "分析论文时必须包含核心方法的技术细节"
        elif "局限" in outcome:
            return "必须分析论文的 limitations 章节"
        return "使用更完整的分析框架"
    
    # ========================================
    # 查询接口
    # ========================================
    
    def get_hot_memory(self) -> str:
        """获取 HOT memory"""
        return self.memory_content
    
    def get_corrections(self, limit: int = 10) -> str:
        """获取最近的纠正记录"""
        lines = self.corrections_content.split("\n")
        # 返回最近的条目
        entries = []
        current_entry = []
        for line in lines:
            if line.startswith("## 20"):
                if current_entry:
                    entries.append("\n".join(current_entry))
                current_entry = [line]
            else:
                current_entry.append(line)
        
        return "\n".join(entries[-limit:])
    
    def get_stats(self) -> Dict:
        """获取学习统计"""
        effective_patterns = {
            key: self._effective_signal_score("patterns", key)
            for key in self.stats.get("patterns", {})
        }
        return {
            "hot_entries": len([l for l in self.memory_content.split("\n") if l.startswith("###")]),
            "corrections_count": len([l for l in self.corrections_content.split("\n") if l.startswith("## 20")]),
            "patterns_tracked": len(self.stats.get("patterns", {})),
            "patterns_promoted": len(self.stats.get("last_promoted", {})),
            "patterns_active": len([key for key, score in effective_patterns.items() if score >= 1.5]),
            "max_effective_pattern_score": max(effective_patterns.values(), default=0),
        }
    
    def should_apply_pattern(self, context: str) -> Optional[str]:
        """检查是否有适用的学习模式"""
        context_lower = context.lower()
        
        ranked_patterns = sorted(
            self.stats.get("patterns", {}).keys(),
            key=lambda key: self._effective_signal_score("patterns", key),
            reverse=True,
        )
        for pattern_key in ranked_patterns:
            effective_score = self._effective_signal_score("patterns", pattern_key)
            if effective_score >= 2.5 and pattern_key in context_lower:
                return f"应用已验证模式：{pattern_key}"
        
        return None


# ============================================
# 研究方法库管理
# ============================================

class MethodLibrary:
    """研究方法库"""
    
    def __init__(self):
        self.methods_dir = METHODS_DIR
    
    def list_methods(self) -> List[str]:
        """列出所有研究方法"""
        return [f.stem for f in self.methods_dir.glob("*.md")]
    
    def get_method(self, name: str) -> Optional[str]:
        """获取特定方法"""
        method_file = self.methods_dir / f"{name}.md"
        if method_file.exists():
            with open(method_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def add_method(self, name: str, content: str, source: str = "learned") -> bool:
        """添加新方法"""
        method_file = self.methods_dir / f"{name}.md"
        if method_file.exists():
            return False
        
        full_content = f"""# {name}

> 来源：{source}
> 添加时间：{datetime.now().strftime("%Y-%m-%d")}

{content}
"""
        with open(method_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return True
    
    def update_usage(self, name: str) -> int:
        """更新方法使用次数"""
        stats_file = LEARNINGS_DIR / "method_stats.json"
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
        else:
            stats = {}
        
        stats[name] = stats.get(name, 0) + 1
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return stats[name]
    
    def get_best_methods(self, limit: int = 5) -> List[Tuple[str, int]]:
        """获取最常用的方法"""
        stats_file = LEARNINGS_DIR / "method_stats.json"
        if not stats_file.exists():
            return []
        
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
        
        sorted_methods = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        return sorted_methods[:limit]


# ============================================
# CLI 接口
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="自学习模块")
    sub = parser.add_subparsers(dest="cmd")
    
    # show 命令
    show_parser = sub.add_parser("show", help="显示学习内容")
    show_parser.add_argument("--memory", action="store_true", help="显示 HOT memory")
    show_parser.add_argument("--corrections", action="store_true", help="显示纠正记录")
    show_parser.add_argument("--stats", action="store_true", help="显示统计")
    
    # learn 命令
    learn_parser = sub.add_parser("learn", help="记录学习")
    learn_parser.add_argument("--context", required=True)
    learn_parser.add_argument("--reflection", required=True)
    learn_parser.add_argument("--lesson", required=True)
    
    # reflect 命令
    reflect_parser = sub.add_parser("reflect", help="自我反思")
    reflect_parser.add_argument("--task-type", required=True)
    reflect_parser.add_argument("--outcome", required=True)
    reflect_parser.add_argument("--improvements", nargs="+", required=True)
    
    # methods 命令
    methods_parser = sub.add_parser("methods", help="方法库管理")
    methods_parser.add_argument("--list", action="store_true", help="列出方法")
    methods_parser.add_argument("--best", action="store_true", help="最佳方法")
    methods_parser.add_argument("--add", metavar="NAME", help="添加新方法")
    methods_parser.add_argument("--content", help="方法内容")
    methods_parser.add_argument("--source", default="manual", help="方法来源")
    
    args = parser.parse_args()
    
    memory = LearningMemory()
    
    if args.cmd == "show":
        if args.memory:
            print(memory.get_hot_memory())
        elif args.corrections:
            print(memory.get_corrections())
        elif args.stats:
            stats = memory.get_stats()
            print(f"📊 学习统计")
            print(f"   HOT 条目：{stats['hot_entries']}")
            print(f"   纠正记录：{stats['corrections_count']}")
            print(f"   追踪模式：{stats['patterns_tracked']}")
            print(f"   已晋升：{stats['patterns_promoted']}")
        else:
            print("请指定 --memory, --corrections 或 --stats")
    
    elif args.cmd == "learn":
        success = memory.learn_from_correction(
            context=args.context,
            reflection=args.reflection,
            lesson=args.lesson
        )
        print(f"{'✅' if success else '❌'} 学习已记录")
    
    elif args.cmd == "reflect":
        result = memory.self_reflect(
            task_type=args.task_type,
            outcome=args.outcome,
            improvements=args.improvements
        )
        print(f"📝 反思完成")
        print(f"   任务类型：{result['task_type']}")
        print(f"   学习要点：{len(result['lessons'])} 条")
        for lesson in result['lessons']:
            print(f"   - {lesson}")
    
    elif args.cmd == "methods":
        lib = MethodLibrary()
        
        if getattr(args, 'list', False):
            methods = lib.list_methods()
            print(f"📚 方法库（{len(methods)} 个）")
            for m in methods:
                print(f"   - {m}")
        
        elif getattr(args, 'best', False):
            best = lib.get_best_methods()
            print("🏆 最佳方法")
            for name, count in best:
                print(f"   {name}: {count} 次使用")
        
        elif getattr(args, 'add', None):
            if args.content:
                success = lib.add_method(args.add, args.content, args.source)
                print(f"{'✅' if success else '❌'} 方法已{'添加' if success else '已存在'}")
            else:
                print("请提供 --content")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
