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

import json
import argparse
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from knowledge_graph import get_or_create_graph, resolve_graph_location, safe_fetch_url
from global_graph import GlobalKnowledgeGraph
from lean_context import LeanContext
from self_learning import LearningMemory

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

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

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


def normalize_topic_label(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (value or "").lower())


def load_topics_config() -> Dict:
    import yaml

    config_paths = [
        CONFIG_DIR / "optimized_config.yaml",
        CONFIG_DIR / "topics.yaml",
    ]
    merged = {}
    merged_topics = []
    for config_path in config_paths:
        if not config_path.exists():
            continue
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        for key, value in config.items():
            if key == "topics":
                continue
            if key not in merged:
                merged[key] = value
        for topic in config.get("topics", []):
            topic_tokens = {
                normalize_topic_label(topic.get("id", "")),
                normalize_topic_label(topic.get("name", "")),
            } - {""}
            existing_topic = next(
                (
                    item for item in merged_topics
                    if topic_tokens & ({
                        normalize_topic_label(item.get("id", "")),
                        normalize_topic_label(item.get("name", "")),
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


def topic_matches(topic: Dict, query: str) -> bool:
    if not query:
        return True
    resolved_name, _, resolved_file = resolve_graph_location(query)
    query_labels = {
        query,
        resolved_name,
        Path(resolved_file).stem.replace("_knowledge_graph", ""),
    }
    topic_labels = {
        topic.get("name", ""),
        topic.get("id", ""),
    }
    normalized_queries = {normalize_topic_label(item) for item in query_labels if item}
    normalized_topics = {normalize_topic_label(item) for item in topic_labels if item}
    return any(
        query_token and topic_token and (query_token in topic_token or topic_token in query_token)
        for query_token in normalized_queries
        for topic_token in normalized_topics
    )


def build_default_query(topic: Dict) -> str:
    research_questions = topic.get("research_questions", [])
    if research_questions:
        return str(research_questions[0])
    keywords = [str(item).strip() for item in topic.get("keywords", []) if str(item).strip()]
    if keywords:
        return f"{topic.get('name', '')} 的最新研究进展，重点关注 {', '.join(keywords[:3])}"
    return f"{topic.get('name', '')} 的最新研究进展"


def _deep_merge(base: Dict, override: Dict) -> Dict:
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_scheduler_policy(config: Optional[Dict] = None) -> Dict:
    config = config or load_topics_config()
    defaults = {
        "retry_policy": {
            "max_attempts_per_cycle": 2,
            "retry_backoff_minutes": [15, 60, 180],
        },
        "circuit_breaker": {
            "enabled": True,
            "failure_threshold": 3,
            "pause_minutes": 720,
        },
        "history_limit": 20,
    }
    scheduler_cfg = config.get("scheduler", {}) if isinstance(config, dict) else {}
    return _deep_merge(defaults, scheduler_cfg)


def parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def schedule_interval_days(frequency: str) -> int:
    return {
        "daily": 1,
        "weekly": 7,
        "monthly": 30,
    }.get((frequency or "daily").lower(), 1)


def topic_schedule_status(topic: Dict, cache: Dict, reference_time: Optional[datetime] = None) -> Dict:
    reference_time = reference_time or datetime.now()
    frequency = (topic.get("frequency") or "daily").lower()
    last_value = cache.get("last_update", {}).get(topic.get("name", "")) or cache.get("last_update", {}).get(topic.get("id", ""))
    last_dt = parse_date(last_value)
    interval_days = schedule_interval_days(frequency)
    if not last_dt:
        return {
            "frequency": frequency,
            "due": True,
            "reason": "never_researched",
            "last_update": last_value or "",
            "interval_days": interval_days,
            "overdue_days": None,
        }
    delta_days = max(0, (reference_time.date() - last_dt.date()).days)
    return {
        "frequency": frequency,
        "due": delta_days >= interval_days,
        "reason": "due" if delta_days >= interval_days else "cooldown",
        "last_update": last_dt.strftime("%Y-%m-%d"),
        "interval_days": interval_days,
        "overdue_days": max(0, delta_days - interval_days),
    }


def refresh_cross_topic_insights() -> Dict:
    graph = GlobalKnowledgeGraph()
    result = graph.build_from_topics()
    return {
        "updated": True,
        "insights_path": str(graph.insights_path),
        "topic_count": result.get("statistics", {}).get("total_topics", 0),
        "shared_concepts": result.get("statistics", {}).get("shared_concepts", 0),
        "cross_topic_relations": len(result.get("cross_topic_relations", [])),
    }


def load_scheduler_state() -> Dict:
    policy = resolve_scheduler_policy()
    state_file = CACHE_DIR / "scheduler_state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {}
    state.setdefault("updated", "")
    state.setdefault("cycles", [])
    state.setdefault("topics", {})
    state["retry_policy"] = _deep_merge(policy.get("retry_policy", {}), state.get("retry_policy", {}))
    state["circuit_breaker"] = _deep_merge(policy.get("circuit_breaker", {}), state.get("circuit_breaker", {}))
    state["history_limit"] = int(state.get("history_limit") or policy.get("history_limit", 20))
    return state


def save_scheduler_state(state: Dict):
    state["updated"] = now()
    state_file = CACHE_DIR / "scheduler_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _scheduler_topic_key(topic: Dict) -> str:
    return str(topic.get("id") or topic.get("name") or "")


def _retry_delay_minutes(failure_count: int, policy: Dict) -> int:
    backoff = policy.get("retry_backoff_minutes", [15, 60, 180])
    index = max(0, min(max(1, failure_count) - 1, len(backoff) - 1))
    return int(backoff[index])


def scheduler_pause_status(topic: Dict, scheduler_state: Dict, reference_time: Optional[datetime] = None) -> Dict:
    reference_time = reference_time or datetime.now()
    key = _scheduler_topic_key(topic)
    topic_state = scheduler_state.get("topics", {}).get(key, {})
    paused_until = parse_date(topic_state.get("paused_until", ""))
    manually_paused = bool(topic_state.get("manual_pause", False))
    paused = manually_paused or bool(paused_until and reference_time < paused_until)
    return {
        "paused": paused,
        "manual_pause": manually_paused,
        "paused_until": topic_state.get("paused_until", ""),
        "pause_reason": topic_state.get("pause_reason", ""),
    }


def scheduler_retry_status(topic: Dict, scheduler_state: Dict, reference_time: Optional[datetime] = None) -> Dict:
    reference_time = reference_time or datetime.now()
    key = _scheduler_topic_key(topic)
    topic_state = scheduler_state.get("topics", {}).get(key, {})
    next_retry_at = parse_date(topic_state.get("next_retry_at", ""))
    retry_due = bool(next_retry_at and reference_time >= next_retry_at)
    return {
        "consecutive_failures": topic_state.get("consecutive_failures", 0),
        "last_run_status": topic_state.get("last_run_status", ""),
        "last_error": topic_state.get("last_error", ""),
        "retry_due": retry_due,
        "next_retry_at": topic_state.get("next_retry_at", ""),
    }


def scheduler_next_run(topic: Dict, cache: Dict, scheduler_state: Dict, reference_time: Optional[datetime] = None) -> Dict:
    reference_time = reference_time or datetime.now()
    schedule = topic_schedule_status(topic, cache, reference_time=reference_time)
    retry_status = scheduler_retry_status(topic, scheduler_state, reference_time=reference_time)
    pause_status = scheduler_pause_status(topic, scheduler_state, reference_time=reference_time)
    if pause_status.get("paused"):
        return {"next_run_at": pause_status.get("paused_until", ""), "source": "paused"}
    if retry_status.get("retry_due"):
        return {"next_run_at": now(), "source": "retry_due"}
    if retry_status.get("next_retry_at"):
        return {"next_run_at": retry_status.get("next_retry_at"), "source": "retry_backoff"}
    last_dt = parse_date(schedule.get("last_update", ""))
    if last_dt:
        next_dt = last_dt + timedelta(days=schedule.get("interval_days", 1))
        return {"next_run_at": next_dt.strftime("%Y-%m-%d %H:%M:%S"), "source": "frequency"}
    return {"next_run_at": now(), "source": "bootstrap"}


def persist_scheduler_cycle(result: Dict, evaluated_topics: List[Dict], scheduler_state: Dict, started_at: Optional[datetime] = None) -> Dict:
    started_at = started_at or datetime.now()
    policy = scheduler_state.get("retry_policy", {})
    circuit_breaker = scheduler_state.get("circuit_breaker", {})
    topics_state = scheduler_state.setdefault("topics", {})
    evaluated_lookup = {_scheduler_topic_key(topic): topic for topic in evaluated_topics}

    for item in result.get("topics", []):
        topic_ref = evaluated_lookup.get(str(item.get("topic_id") or item.get("topic")))
        topic_name = item.get("topic", "")
        topic_key = str(item.get("topic_id") or topic_name)
        existing = topics_state.get(topic_key, {})
        attempts = int(item.get("attempts", 1))
        topic_state = {
            **existing,
            "topic": topic_name,
            "topic_id": item.get("topic_id", ""),
            "last_run_at": now(),
            "last_run_status": "success" if item.get("success") else "failed",
            "last_attempts": attempts,
        }
        if item.get("success"):
            topic_state["consecutive_failures"] = 0
            topic_state["last_success_at"] = now()
            topic_state["last_error"] = ""
            topic_state["next_retry_at"] = ""
            topic_state["paused_until"] = ""
            topic_state["pause_reason"] = ""
            topic_state["manual_pause"] = False
        else:
            failure_count = int(existing.get("consecutive_failures", 0)) + 1
            delay_minutes = _retry_delay_minutes(failure_count, policy)
            topic_state["consecutive_failures"] = failure_count
            topic_state["last_failure_at"] = now()
            topic_state["last_error"] = item.get("error", "")
            topic_state["next_retry_at"] = (datetime.now() + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            if circuit_breaker.get("enabled", True) and failure_count >= int(circuit_breaker.get("failure_threshold", 3)):
                pause_minutes = int(circuit_breaker.get("pause_minutes", 720))
                topic_state["paused_until"] = (datetime.now() + timedelta(minutes=pause_minutes)).strftime("%Y-%m-%d %H:%M:%S")
                topic_state["pause_reason"] = "circuit_breaker"
                topic_state["manual_pause"] = False
        if topic_ref:
            topic_state["frequency"] = topic_ref.get("frequency", "daily")
        topics_state[topic_key] = topic_state

    cycle_entry = {
        "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": now(),
        "processed_topics": result.get("processed_topics", 0),
        "succeeded_topics": result.get("succeeded_topics", 0),
        "failed_topics": result.get("failed_topics", 0),
        "due_topics": [item.get("topic", "") for item in result.get("due_topics", [])],
        "skipped_topics": [item.get("topic", "") for item in result.get("skipped_topics", [])],
        "global_refresh": result.get("global_refresh", {}),
        "success": result.get("success", False),
    }
    cycles = scheduler_state.setdefault("cycles", [])
    cycles.append(cycle_entry)
    scheduler_state["cycles"] = cycles[-int(scheduler_state.get("history_limit", 20)):]
    save_scheduler_state(scheduler_state)
    return scheduler_state


def get_scheduler_status(topic_name: str = "", limit: int = 10) -> Dict:
    config = load_topics_config()
    cache = load_cache()
    scheduler_state = load_scheduler_state()
    topics = [topic for topic in config.get("topics", []) if topic.get("enabled", True)]
    if topic_name:
        topics = [topic for topic in topics if topic_matches(topic, topic_name)]
    topic_items = []
    for topic in topics:
        schedule = topic_schedule_status(topic, cache)
        retry_status = scheduler_retry_status(topic, scheduler_state)
        pause_status = scheduler_pause_status(topic, scheduler_state)
        next_run = scheduler_next_run(topic, cache, scheduler_state)
        topic_items.append({
            "topic": topic.get("name", ""),
            "topic_id": topic.get("id", ""),
            **schedule,
            **retry_status,
            **pause_status,
            **next_run,
        })
    paused = [item for item in topic_items if item.get("paused")]
    due = [item for item in topic_items if item.get("due") or item.get("retry_due")]
    ordered = sorted(
        topic_items,
        key=lambda item: (
            0 if item.get("paused") else 1,
            0 if (item.get("due") or item.get("retry_due")) else 1,
            -int(item.get("consecutive_failures", 0)),
            item.get("topic", ""),
        ),
    )
    return {
        "updated": scheduler_state.get("updated", ""),
        "policy": {
            "retry_policy": scheduler_state.get("retry_policy", {}),
            "circuit_breaker": scheduler_state.get("circuit_breaker", {}),
            "history_limit": scheduler_state.get("history_limit", 20),
        },
        "summary": {
            "enabled_topics": len(topic_items),
            "due_topics": len(due),
            "paused_topics": len(paused),
            "failing_topics": len([item for item in topic_items if item.get("consecutive_failures", 0) > 0]),
        },
        "topics": ordered[:limit] if limit else ordered,
        "recent_cycles": scheduler_state.get("cycles", [])[-min(max(limit, 1), 10):],
    }


def control_scheduler_topic(action: str, topic_name: str, hours: int = 24) -> Dict:
    if not topic_name:
        return {"success": False, "error": "需要提供主题名称"}
    config = load_topics_config()
    matched_topics = [topic for topic in config.get("topics", []) if topic_matches(topic, topic_name)]
    if not matched_topics:
        return {"success": False, "error": f"未找到主题：{topic_name}"}
    topic = matched_topics[0]
    state = load_scheduler_state()
    key = _scheduler_topic_key(topic)
    topics_state = state.setdefault("topics", {})
    topic_state = topics_state.get(key, {
        "topic": topic.get("name", ""),
        "topic_id": topic.get("id", ""),
        "consecutive_failures": 0,
    })
    if action == "pause":
        topic_state["manual_pause"] = True
        topic_state["paused_until"] = (datetime.now() + timedelta(hours=max(1, hours))).strftime("%Y-%m-%d %H:%M:%S")
        topic_state["pause_reason"] = "manual"
    elif action == "resume":
        topic_state["manual_pause"] = False
        topic_state["paused_until"] = ""
        topic_state["pause_reason"] = ""
    elif action == "reset":
        topic_state["consecutive_failures"] = 0
        topic_state["last_error"] = ""
        topic_state["next_retry_at"] = ""
        topic_state["paused_until"] = ""
        topic_state["pause_reason"] = ""
        topic_state["manual_pause"] = False
    else:
        return {"success": False, "error": f"不支持的调度控制动作：{action}"}
    topics_state[key] = topic_state
    save_scheduler_state(state)
    return {
        "success": True,
        "action": action,
        "topic": topic.get("name", ""),
        "topic_id": topic.get("id", ""),
        "state": topic_state,
    }

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


def split_sentences(text: str) -> List[str]:
    chunks = re.split(r"(?<=[。！？.!?])\s+|\n+", text or "")
    return [chunk.strip(" -•\t") for chunk in chunks if chunk.strip()]


def trim_text(text: str, limit: int = 240) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

# ============================================
# 第一阶段：论文搜索
# ============================================

class PaperSearcher:
    """论文搜索器"""
    
    def __init__(self, keywords: List[str]):
        self.keywords = keywords
    
    def _build_query(self) -> str:
        primary = [keyword.strip() for keyword in self.keywords if keyword.strip()][:4]
        if not primary:
            return "artificial intelligence"
        return " OR ".join(f'all:"{item}"' for item in primary)

    def _fetch_arxiv(self, days: int = 90, max_results: int = 12) -> List[Dict]:
        url = (
            "https://export.arxiv.org/api/query?"
            + urllib.parse.urlencode({
                "search_query": self._build_query(),
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            })
        )
        raw = safe_fetch_url(
            url,
            max_bytes=3_145_728,
            timeout=20,
            headers={"User-Agent": "ai-deep-research-agent/6.0"},
        )
        root = ET.fromstring(raw)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = " ".join((entry.findtext("atom:title", "", ns) or "").split())
            abstract = " ".join((entry.findtext("atom:summary", "", ns) or "").split())
            published = entry.findtext("atom:published", "", ns)
            try:
                published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                published_dt = None
            if published_dt and (datetime.now(published_dt.tzinfo) - published_dt).days > days:
                continue
            entry_id = entry.findtext("atom:id", "", ns)
            categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ns)]
            authors = [author.findtext("atom:name", "", ns) for author in entry.findall("atom:author", ns)]
            url_value = ""
            for link in entry.findall("atom:link", ns):
                href = link.attrib.get("href", "")
                if href and ("abs" in href or link.attrib.get("rel") == "alternate"):
                    url_value = href
                    break
            combined_text = f"{title} {abstract}".lower()
            relevance = sum(1 for keyword in self.keywords if keyword.lower() in combined_text)
            papers.append({
                "id": entry_id.rsplit("/", 1)[-1],
                "title": title,
                "abstract": abstract,
                "authors": [author for author in authors if author],
                "venue": f"arXiv {categories[0]}" if categories else "arXiv",
                "pub_date": published[:10],
                "url": url_value or entry_id,
                "arxiv_id": entry_id.rsplit("/", 1)[-1],
                "citations": 0,
                "categories": categories,
                "relevance": relevance,
            })
        deduped = {}
        for paper in papers:
            key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", paper["title"].lower())
            previous = deduped.get(key)
            if not previous or paper.get("relevance", 0) >= previous.get("relevance", 0):
                deduped[key] = paper
        return sorted(deduped.values(), key=lambda item: (item.get("relevance", 0), item.get("pub_date", "")), reverse=True)

    def search(self, days: int = 90, max_results: int = 12) -> Dict:
        result = {
            "stage": "search",
            "keywords": self.keywords,
            "days": days,
            "papers": [],
            "count": 0,
            "query": self._build_query(),
        }
        try:
            papers = self._fetch_arxiv(days=days, max_results=max_results)
            result["papers"] = papers
            result["count"] = len(papers)
            result["source"] = "arXiv"
        except Exception as exc:
            result["error"] = str(exc)
            result["instruction"] = f"真实搜索失败，请回退到手动搜索：{', '.join(self.keywords)}"
        return result

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
        abstract = paper.get("abstract", "")
        return {
            "id": paper.get("id", ""),
            "title": paper.get("title", ""),
            "analysis": {
                "basic_info": self._extract_basic_info(paper),
                "core_method": self._extract_method(paper),
                "innovations": self._extract_innovations(paper),
                "experiments": self._extract_experiments(paper),
                "limitations": self._extract_limitations(paper),
                "datasets": self._extract_datasets(abstract),
                "methods": self._extract_methods(paper),
                "systems": self._extract_systems(paper),
                "summary": trim_text(abstract, 260),
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
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        for sentence in split_sentences(f"{title}. {abstract}"):
            lower = sentence.lower()
            if any(token in lower for token in ["propose", "present", "introduce", "framework", "architecture", "approach", "model"]):
                return trim_text(sentence, 320)
        return trim_text(abstract, 320)
    
    def _extract_innovations(self, paper: Dict) -> List[str]:
        innovations = []
        seen = set()
        for sentence in split_sentences(paper.get("abstract", "")):
            lower = sentence.lower()
            if any(token in lower for token in ["novel", "propose", "introduce", "first", "outperform", "new framework", "state-of-the-art"]):
                normalized = sentence.lower()
                if normalized not in seen:
                    innovations.append(trim_text(sentence, 180))
                    seen.add(normalized)
        return innovations[:4]
    
    def _extract_experiments(self, paper: Dict) -> str:
        for sentence in split_sentences(paper.get("abstract", "")):
            lower = sentence.lower()
            if any(token in lower for token in ["experiment", "benchmark", "evaluate", "result", "outperform", "accuracy"]):
                return trim_text(sentence, 240)
        return trim_text(paper.get("abstract", ""), 240)
    
    def _extract_limitations(self, paper: Dict) -> List[str]:
        limitations = []
        seen = set()
        for sentence in split_sentences(paper.get("abstract", "")):
            lower = sentence.lower()
            if any(token in lower for token in ["limitation", "future work", "remains", "not address", "challenge", "bottleneck"]):
                normalized = sentence.lower()
                if normalized not in seen:
                    limitations.append(trim_text(sentence, 180))
                    seen.add(normalized)
        return limitations[:4]

    def _extract_datasets(self, text: str) -> List[str]:
        datasets = []
        candidates = re.findall(r"\b([A-Z][A-Za-z0-9+-]{2,}(?:[- ][A-Z0-9][A-Za-z0-9+-]{1,}){0,2})\b", text or "")
        for item in candidates:
            lower = item.lower()
            if any(token in lower for token in ["dataset", "bench", "wiki", "glue", "mmlu", "gsm", "arena"]):
                datasets.append(item)
        return sorted(dict.fromkeys(datasets))[:6]

    def _extract_methods(self, paper: Dict) -> List[str]:
        title = paper.get("title", "")
        methods = []
        for item in re.findall(r"\b([A-Z][A-Za-z0-9]+(?:[- ][A-Z][A-Za-z0-9]+){0,3})\b", title):
            if any(token in item.lower() for token in ["framework", "method", "retrieval", "memory", "reason", "agent"]):
                methods.append(item)
        if not methods and ":" in title:
            methods.append(title.split(":", 1)[0].strip())
        return sorted(dict.fromkeys(methods))[:5]

    def _extract_systems(self, paper: Dict) -> List[str]:
        title = paper.get("title", "")
        systems = []
        for item in re.findall(r"\b([A-Z][A-Za-z0-9]+(?:[- ][A-Z][A-Za-z0-9]+){0,3})\b", title):
            if any(token in item.lower() for token in ["agent", "system", "architecture", "model"]):
                systems.append(item)
        return sorted(dict.fromkeys(systems))[:5]

# ============================================
# 第四阶段：知识图谱进化
# ============================================

class KnowledgeGraphEvolver:
    """知识图谱进化器"""
    
    def __init__(self, topic: str):
        resolved_topic, graph_dir, graph_filename = resolve_graph_location(topic)
        self.topic = resolved_topic
        self.graph = get_or_create_graph(resolved_topic, base_dir=graph_dir, filename=graph_filename)
    
    def evolve(self, paper_analysis: Dict) -> Dict:
        analysis = paper_analysis.get("analysis", {})
        basic_info = analysis.get("basic_info", {})
        before_entities = len(self.graph.entities)
        before_edges = len(self.graph.edges)
        self.graph.extract_from_paper({
            "id": paper_analysis.get("id", ""),
            "title": paper_analysis.get("title", ""),
            "abstract": analysis.get("core_method", ""),
            "core_method": analysis.get("core_method", ""),
            "authors": basic_info.get("authors", []),
            "venue": basic_info.get("venue", ""),
            "arxiv_id": basic_info.get("arxiv_id", ""),
            "url": basic_info.get("url", ""),
            "innovations": analysis.get("innovations", []),
            "limitations": analysis.get("limitations", []),
            "datasets": analysis.get("datasets", []),
        })
        refresh = self.graph.refresh_views()
        return {
            "new_concepts": max(0, len(self.graph.entities) - before_entities),
            "updated_concepts": 0,
            "new_relations": max(0, len(self.graph.edges) - before_edges),
            "contradictions_found": 0,
            "refresh": refresh,
        }
    
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

    def _iter_known_concepts(self):
        return list(self.graph.concepts.values())
    
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
                for concept in self._iter_known_concepts():
                    if concept.name.lower() in abstract:
                        relations.append({
                            "from": analysis.get("id", ""),
                            "to": concept.id,
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
        
        for concept in self._iter_known_concepts():
            if concept.name.lower() in abstract:
                for kw in negation_keywords:
                    if kw in abstract:
                        contradictions.append({
                            "paper": analysis.get("title"),
                            "concept": concept.name,
                            "evidence": f"发现否定性关键词：{kw}",
                            "severity": "medium"
                        })
        
        return contradictions
    
    def get_summary(self) -> str:
        """获取知识图谱摘要"""
        self.graph.refresh_views()
        return self.graph.generate_graph_report()

# ============================================
# 第五阶段：方法论进化
# ============================================

class MethodologyEvolver:
    """研究方法论进化器"""
    
    def __init__(self, topic: str):
        self.methodology_path = LEARNINGS_DIR / "METHODOLOGY.md"
        resolved_topic, graph_dir, graph_filename = resolve_graph_location(topic)
        self.graph = get_or_create_graph(resolved_topic, base_dir=graph_dir, filename=graph_filename)
    
    def evolve(self, new_insights: List[str], source_title: str = "", source_id: str = "") -> int:
        if self.methodology_path.exists():
            with open(self.methodology_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# 研究方法论学习记录\n\n"

        existing_insights = content.lower()
        new_count = 0
        
        for insight in new_insights:
            if insight.lower() not in existing_insights:
                if "## 新增洞察" not in content or content.count("## 新增洞察") < 10:
                    content += f"\n## {today()} 新增洞察\n\n"
                content += f"- {insight}\n"
                entity = self.graph.upsert_entity(
                    name=trim_text(insight, 80),
                    entity_type="Methodology",
                    description=insight,
                    summary=trim_text(source_title or insight, 160),
                    attributes={"source_title": source_title, "source_id": source_id, "kind": "methodology"},
                    tags=["methodology", today()],
                    layer="warm",
                    confidence=0.85,
                )
                if source_id:
                    paper_entity = self.graph.find_entity(entity_id=f"paper-{source_id}")
                    if paper_entity:
                        self.graph.connect_entities(
                            paper_entity.id,
                            entity.id,
                            relation_type="distills_methodology",
                            evidence=trim_text(insight, 160),
                            confidence=0.78,
                        )
                new_count += 1
        
        with open(self.methodology_path, 'w', encoding='utf-8') as f:
            f.write(content)
        if new_count:
            self.graph.refresh_views()
        
        return new_count
    
    def extract_insights(self, paper_analysis: Dict) -> List[str]:
        """从论文提取方法论洞察"""
        insights = []
        analysis = paper_analysis.get("analysis", {})
        title = trim_text(paper_analysis.get("title", ""), 40)
        core_method = analysis.get("core_method", "")
        if core_method:
            insights.append(f"[{title}] 核心方法：{trim_text(core_method, 160)}")
        for innovation in analysis.get("innovations", [])[:3]:
            insights.append(f"[{title}] 创新点：{trim_text(innovation, 160)}")
        return list(dict.fromkeys(insights))[:5]

# ============================================
# 第六阶段：知识缺口进化
# ============================================

class KnowledgeGapEvolver:
    """知识缺口进化器"""
    
    def __init__(self, topic: str):
        self.gaps_path = LEARNINGS_DIR / "KNOWLEDGE_GAPS.md"
        resolved_topic, graph_dir, graph_filename = resolve_graph_location(topic)
        self.graph = get_or_create_graph(resolved_topic, base_dir=graph_dir, filename=graph_filename)
    
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
        
        resolved_count = 0
        if resolved_gaps:
            for gap_id in resolved_gaps:
                if gap_id in content:
                    content = content.replace(
                        f"### 🔴 {gap_id}",
                        f"### ✅ {gap_id} (已解决 {today()})"
                    )
                    resolved_count += 1
                entity = self.graph.find_entity(name=gap_id)
                if entity:
                    entity.attributes["status"] = "resolved"
                    entity.attributes["resolved_at"] = today()
        
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
                entity = self.graph.upsert_entity(
                    name=gap.get("title", "未知缺口"),
                    entity_type="Gap",
                    description=gap.get("description", ""),
                    summary=gap.get("source", ""),
                    attributes={
                        "priority": gap.get("priority", "medium"),
                        "status": "open",
                        "source": gap.get("source", ""),
                    },
                    tags=["gap", gap.get("priority", "medium"), today()],
                    layer="hot" if gap.get("priority") == "high" else "warm",
                    confidence=0.82,
                )
                source_id = gap.get("paper_id")
                if source_id:
                    paper_entity = self.graph.find_entity(entity_id=f"paper-{source_id}")
                    if paper_entity:
                        self.graph.connect_entities(
                            paper_entity.id,
                            entity.id,
                            relation_type="reveals_gap",
                            evidence=trim_text(gap.get("description", ""), 160),
                            confidence=0.75,
                        )
                new_count += 1
        
        with open(self.gaps_path, 'w', encoding='utf-8') as f:
            f.write(content)
        if new_count or resolved_count:
            self.graph.refresh_views()
        
        return new_count, resolved_count
    
    def extract_gaps(self, paper_analysis: Dict) -> List[Dict]:
        """从论文提取知识缺口"""
        gaps = []
        
        analysis = paper_analysis.get("analysis", {})
        limitations = analysis.get("limitations", [])
        source_id = paper_analysis.get("id", "")
        source_ref = analysis.get("basic_info", {}).get("arxiv_id", "") or analysis.get("basic_info", {}).get("url", "")
        for limitation in limitations[:4]:
            priority = "high" if any(token in limitation.lower() for token in ["critical", "important", "safety", "robust"]) else "medium"
            gaps.append({
                "title": trim_text(f"{paper_analysis.get('title', '')} 缺口", 50),
                "description": limitation,
                "source": source_ref,
                "paper_id": source_id,
                "priority": priority,
            })
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
        self.client_id = os.getenv("IMA_CLIENT_ID", "")
        self.api_key = os.getenv("IMA_API_KEY", "")
        if self.client_id and self.api_key:
            return
        candidates = [
            os.getenv("IMA_TOKEN_SCRIPT", ""),
            str(SKILL_DIR / "config" / "skills" / "ima" / "get-token.ps1"),
            str(SCRIPT_DIR.parent / "config" / "skills" / "ima" / "get-token.ps1"),
            r"D:\Program Files\QClaw\resources\openclaw\config\skills\ima\get-token.ps1",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            script_path = Path(candidate)
            if not script_path.exists():
                continue
            try:
                result = subprocess.run(
                    ["powershell", "-File", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                continue
            if result.returncode == 0 and result.stdout.strip():
                creds = json.loads(result.stdout.strip())
                self.client_id = creds.get("client_id", "")
                self.api_key = creds.get("api_key", "")
                if self.client_id and self.api_key:
                    return
    
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
        self.original_topic = topic
        config = load_topics_config()
        self.topic_config = self._resolve_topic_config(topic, config.get("topics", []))
        resolved_topic, graph_dir, graph_filename = resolve_graph_location(self.topic_config.get("id") or self.topic_config.get("name") or topic)
        self.topic = resolved_topic
        self.topic_id = self.topic_config.get("id") or graph_filename.replace("_knowledge_graph.json", "")
        self.graph_dir = graph_dir
        self.graph_filename = graph_filename
        self.topic_root = SKILL_DIR / "topics" / self.topic_id
        self.report_dir = self.topic_root / "knowledge" / "reports"
        self.external_report_dir = self.report_dir / "external"
        self.internal_report_dir = self.report_dir / "internal"
        self.kb_id = kb_id or self.topic_config.get("target_knowledge_base") or self.topic_config.get("kb_id") or "eImkUmYly1k-NH7Pz8e4syn4zs0UXJZufvCX5CSKvN8="
        self.searcher = PaperSearcher(self.topic_config.get("keywords", [self.topic]))
        self.filter = QualityFilter()
        self.analyzer = DeepAnalyzer()
        self.graph_evolver = KnowledgeGraphEvolver(self.topic)
        self.method_evolver = MethodologyEvolver(self.topic)
        self.gap_evolver = KnowledgeGapEvolver(self.topic)
        self.syncer = None
        self.learning_memory = LearningMemory()
        self.graph = self._load_graph()
        self.context_builder = LeanContext(self.topic)
        self._prepare_report_dirs()

    @staticmethod
    def _normalize_topic(value: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (value or "").lower())

    def _resolve_topic_config(self, topic: str, topics: List[Dict]) -> Dict:
        target = self._normalize_topic(topic)
        for item in topics:
            candidates = [item.get("id", ""), item.get("name", "")]
            candidates.extend(item.get("keywords", []))
            for candidate in candidates:
                normalized = self._normalize_topic(str(candidate))
                if normalized and (normalized == target or normalized in target or target in normalized):
                    return item
        return {}

    def _load_graph(self):
        return get_or_create_graph(self.topic, base_dir=self.graph_dir, filename=self.graph_filename)

    def _reload_runtime_views(self):
        self.graph = self._load_graph()
        self.context_builder = LeanContext(self.topic)

    def _prepare_report_dirs(self):
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.external_report_dir.mkdir(parents=True, exist_ok=True)
        self.internal_report_dir.mkdir(parents=True, exist_ok=True)

    def _is_internal_report_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.internal_report_dir.resolve())
            return True
        except ValueError:
            return "_Evolution_" in path.name

    def _resolve_ingest_targets(self, ingest_path: Optional[str]) -> List[Path]:
        if ingest_path:
            return [Path(ingest_path)]
        targets: List[Path] = []
        if self.external_report_dir.exists():
            targets.append(self.external_report_dir)
        if self.report_dir.exists():
            for path in sorted(self.report_dir.iterdir()):
                if not path.is_file():
                    continue
                if self._is_internal_report_path(path):
                    continue
                targets.append(path)
        if not targets and REPORTS_DIR.exists():
            targets.append(REPORTS_DIR)
        return targets

    def _ensure_bootstrap_seed(self, force: bool = False) -> Dict:
        if self.graph.entities or self.graph.edges:
            return {
                "bootstrapped": False,
                "reason": "graph_already_initialized",
                "entities": len(self.graph.entities),
                "edges": len(self.graph.edges),
            }
        result = GlobalKnowledgeGraph().bootstrap_topics(topic_id=self.topic_id or self.topic, force=force)
        topic_result = next(
            (item for item in result.get("topics", []) if item.get("status") == "bootstrapped"),
            {},
        )
        self._reload_runtime_views()
        return {
            "bootstrapped": bool(topic_result),
            "reason": "empty_graph_seeded" if topic_result else "no_bootstrap_topic",
            "entities": len(self.graph.entities),
            "edges": len(self.graph.edges),
            "seed": topic_result.get("seed", {}),
        }

    def _collect_ingest_sources(self, ingest_targets: List[Path]) -> List[str]:
        sources: List[str] = []
        for ingest_target in ingest_targets:
            if not ingest_target.exists():
                continue
            if ingest_target.is_file():
                sources.append(ingest_target.name)
                continue
            for path in sorted(ingest_target.glob("*")):
                if path.is_file():
                    sources.append(f"{ingest_target.name}/{path.name}")
                if len(sources) >= 10:
                    return sources
        return sources[:10]

    def _run_ingest_target(self, ingest_target: Path, full_ingest: bool) -> Dict:
        if not ingest_target.exists():
            return {"path": str(ingest_target), "exists": False, "processed": 0, "updated": 0, "skipped": 0, "files": []}
        if ingest_target.is_file():
            result = self.graph.ingest_file(str(ingest_target), root_dir=str(ingest_target.parent), update=not full_ingest)
            self.graph.save()
            return {
                "path": str(ingest_target),
                "exists": True,
                "processed": 1,
                "updated": 1 if result.get("updated") else 0,
                "skipped": 0 if result.get("updated") else 1,
                "files": [result],
            }
        result = self.graph.ingest_path(str(ingest_target), update=not full_ingest)
        result["path"] = str(ingest_target)
        result["exists"] = True
        return result

    def _run_ingest(self, ingest_targets: List[Path], full_ingest: bool) -> Dict:
        aggregate = {
            "path": json.dumps([str(path) for path in ingest_targets], ensure_ascii=False),
            "paths": [str(path) for path in ingest_targets],
            "exists": any(path.exists() for path in ingest_targets),
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "files": [],
            "source_policy": "external_only",
        }
        if not ingest_targets:
            aggregate["exists"] = False
            return aggregate
        for ingest_target in ingest_targets:
            result = self._run_ingest_target(ingest_target, full_ingest=full_ingest)
            aggregate["processed"] += result.get("processed", 0)
            aggregate["updated"] += result.get("updated", 0)
            aggregate["skipped"] += result.get("skipped", 0)
            aggregate["files"].extend(result.get("files", []))
        return aggregate

    def _repair_graph(self) -> Dict:
        invalid_edges = [
            edge for edge in self.graph.edges
            if edge.from_id not in self.graph.entities or edge.to_id not in self.graph.entities
        ]
        if invalid_edges:
            self.graph.edges = [
                edge for edge in self.graph.edges
                if edge.from_id in self.graph.entities and edge.to_id in self.graph.entities
            ]
            self.graph.save()
        return {"removed_invalid_edges": len(invalid_edges)}

    def _build_projection(self, query: str, budget: int) -> Dict:
        self._reload_runtime_views()
        projection = self.graph.project_context(task_type="report", query=query or self.topic, budget=budget)
        prompt = self.context_builder.get_full_prompt(query=query or self.topic, budget=budget)
        return {
            "query": query or self.topic,
            "budget": budget,
            "items": len(projection.get("items", [])),
            "used_budget": projection.get("used_budget", 0),
            "entity_types": projection.get("entity_types", {}),
            "prompt": projection.get("prompt", ""),
            "mode": projection.get("mode", "bfs"),
            "depth": projection.get("depth", 2),
            "start_nodes": projection.get("start_nodes", []),
            "graph_slice_edges": len(projection.get("graph_slice", {}).get("edges", [])),
            "full_prompt_preview": prompt[:1200],
        }

    def _run_search_analysis(self, query: str = "", budget: int = 1600) -> Dict:
        days = self.topic_config.get("recent_days", 90)
        search_result = self.searcher.search(days=days)
        filtered_papers = self.filter.filter(
            search_result.get("papers", []),
            min_score=self.topic_config.get("min_quality_score", 1.5),
            max_papers=self.topic_config.get("max_papers_per_session", 5),
        )
        analyses = []
        graph_delta = {"new_concepts": 0, "new_relations": 0}
        methodology_insights = []
        gaps = []
        for paper in filtered_papers:
            analysis = self.analyzer.analyze(paper)
            analyses.append(analysis)
            evolve_result = self.graph_evolver.evolve(analysis)
            graph_delta["new_concepts"] += evolve_result.get("new_concepts", 0)
            graph_delta["new_relations"] += evolve_result.get("new_relations", 0)
            methodology_insights.extend(self.method_evolver.extract_insights(analysis))
            gaps.extend(self.gap_evolver.extract_gaps(analysis))
        methodology_added = self.method_evolver.evolve(
            methodology_insights,
            source_title=analyses[0]["title"] if analyses else "",
            source_id=analyses[0]["id"] if analyses else "",
        ) if methodology_insights else 0
        gaps_added, gaps_resolved = self.gap_evolver.evolve(gaps) if gaps else (0, 0)
        self._reload_runtime_views()
        return {
            "search": {
                **search_result,
                "prompt_preview": self.context_builder.get_search_prompt(query=query or self.topic, budget=min(1200, budget))[:800],
                "selected_count": len(filtered_papers),
                "selected_titles": [paper.get("title", "") for paper in filtered_papers],
            },
            "analysis": {
                "selected_count": len(filtered_papers),
                "graph_delta": graph_delta,
                "methodology_added": methodology_added,
                "gaps_added": gaps_added,
                "gaps_resolved": gaps_resolved,
                "papers": [
                    {
                        "id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "core_method": item.get("analysis", {}).get("core_method", ""),
                        "innovations": item.get("analysis", {}).get("innovations", []),
                        "limitations": item.get("analysis", {}).get("limitations", []),
                    }
                    for item in analyses
                ],
            },
        }

    def _load_methodology_content(self) -> str:
        if self.method_evolver.methodology_path.exists():
            return self.method_evolver.methodology_path.read_text(encoding="utf-8")
        return ""

    def _load_gap_content(self) -> str:
        if self.gap_evolver.gaps_path.exists():
            return self.gap_evolver.gaps_path.read_text(encoding="utf-8")
        return ""

    def _build_exec_summary(self, search_result: Dict, analysis_result: Dict, refresh_result: Dict) -> List[str]:
        lines = []
        if analysis_result.get("selected_count", 0):
            lines.append(
                f"已从 {search_result.get('count', 0)} 篇候选论文中筛出 {analysis_result.get('selected_count', 0)} 篇高质量论文并完成结构化分析。"
            )
        if analysis_result.get("graph_delta", {}).get("new_concepts", 0):
            lines.append(
                f"知识图谱新增 {analysis_result['graph_delta']['new_concepts']} 个实体、{analysis_result['graph_delta']['new_relations']} 条关系。"
            )
        if analysis_result.get("methodology_added", 0):
            lines.append(f"方法论库新增 {analysis_result['methodology_added']} 条可复用洞察。")
        if analysis_result.get("gaps_added", 0):
            lines.append(f"知识缺口库新增 {analysis_result['gaps_added']} 条待跟踪问题。")
        if refresh_result.get("validation", {}).get("ok"):
            lines.append("图谱刷新与校验通过，投影上下文可直接用于后续研究。")
        return lines or ["本轮以图谱刷新和闭环验证为主，未发现新的高置信研究增量。"]

    def _build_report_markdown(self, search_result: Dict, analysis_result: Dict, ingest_result: Dict, refresh_result: Dict, cycle_report: Dict, learning_result: Dict, compression_result: Dict) -> str:
        executive_summary = self._build_exec_summary(search_result, analysis_result, refresh_result)
        lines = [
            f"# {self.topic} 演化闭环报告",
            "",
            f"- 日期：{today()}",
            f"- 主题ID：{self.topic_id}",
            f"- 搜索候选：{search_result.get('count', 0)}",
            f"- 深度分析：{analysis_result.get('selected_count', 0)}",
            f"- ingest 路径：{ingest_result.get('path', '')}",
            f"- ingest 处理文件：{ingest_result.get('processed', 0)}",
            f"- ingest 更新文件：{ingest_result.get('updated', 0)}",
            f"- refresh 社区数：{refresh_result.get('communities', 0)}",
            f"- refresh 摘要节点：{refresh_result.get('summary_nodes', 0)}",
            f"- refresh 清理无效关系：{refresh_result.get('removed_invalid_edges', 0)}",
            f"- 图谱校验：{'通过' if refresh_result.get('validation', {}).get('ok') else '失败'}",
            "",
            "## 执行摘要",
            "",
        ]
        lines.extend([f"- {item}" for item in executive_summary])
        lines.extend([
            "",
            "## 搜索与分析",
            "",
            f"- 搜索源：{search_result.get('source', search_result.get('instruction', 'fallback'))}",
            f"- 选中论文：{json.dumps(search_result.get('selected_titles', []), ensure_ascii=False)}",
            f"- 方法论新增：{analysis_result.get('methodology_added', 0)}",
            f"- 缺口新增：{analysis_result.get('gaps_added', 0)}",
            "",
        ])
        for paper in analysis_result.get("papers", [])[:5]:
            lines.extend([
                f"### {paper.get('title', '')}",
                f"- 核心方法：{paper.get('core_method', '')}",
                f"- 创新点：{json.dumps(paper.get('innovations', []), ensure_ascii=False)}",
                f"- 局限：{json.dumps(paper.get('limitations', []), ensure_ascii=False)}",
                "",
            ])
        lines.extend([
            "## Query-time 投影",
            "",
            f"- 查询：{cycle_report['projection'].get('query', '')}",
            f"- 条目数：{cycle_report['projection'].get('items', 0)}",
            f"- 已用预算：{cycle_report['projection'].get('used_budget', 0)}",
            f"- 导航模式：{cycle_report['projection'].get('mode', 'bfs')}",
            f"- 遍历深度：{cycle_report['projection'].get('depth', 2)}",
            f"- 种子节点：{json.dumps(cycle_report['projection'].get('start_nodes', []), ensure_ascii=False)}",
            f"- 子图边数：{cycle_report['projection'].get('graph_slice_edges', 0)}",
            f"- 实体类型：{json.dumps(cycle_report['projection'].get('entity_types', {}), ensure_ascii=False)}",
            "",
            cycle_report["projection"].get("prompt", "") or "暂无图谱投影上下文",
            "",
            "## 图谱报告",
            "",
            cycle_report["graph_report"],
            "",
            "## 图谱指标",
            "",
            f"- 统计：{json.dumps(cycle_report.get('graph_stats', {}), ensure_ascii=False)}",
            f"- God Nodes：{json.dumps(cycle_report.get('god_nodes', []), ensure_ascii=False)}",
            f"- Surprising Connections：{json.dumps(cycle_report.get('surprising_connections', []), ensure_ascii=False)}",
            f"- Context Benchmark：{json.dumps(cycle_report.get('benchmark', {}), ensure_ascii=False)}",
            "",
            "## 方法论与缺口",
            "",
            trim_text(self._load_methodology_content(), 800) or "暂无方法论更新",
            "",
            trim_text(self._load_gap_content(), 800) or "暂无知识缺口更新",
            "",
            "## 自学习回写",
            "",
            f"- 模式：{learning_result.get('mode', '')}",
            f"- 已记录：{learning_result.get('recorded', False)}",
            f"- 内容：{learning_result.get('content', '')}",
            f"- 上下文：{learning_result.get('context', '')}",
        ])
        if learning_result.get("reflection"):
            lines.extend(["", f"- 反思：{learning_result['reflection']}"])
        lines.extend([
            "",
            "## 自动压缩",
            "",
            f"- 已执行：{compression_result.get('compressed', False)}",
            f"- 归档报告：{compression_result.get('reports_archived', 0)}",
            f"- 归档概念：{compression_result.get('concepts_archived', 0)}",
            f"- 摘要节点：{compression_result.get('summary_nodes_created', 0)}",
        ])
        return "\n".join(lines)

    def _write_cycle_report(self, search_result: Dict, analysis_result: Dict, ingest_result: Dict, refresh_result: Dict, cycle_report: Dict, learning_result: Dict, compression_result: Dict) -> Path:
        self._prepare_report_dirs()
        report_path = self.internal_report_dir / f"{self.topic_id}_Evolution_{today()}.md"
        content = self._build_report_markdown(search_result, analysis_result, ingest_result, refresh_result, cycle_report, learning_result, compression_result)
        report_path.write_text(content, encoding="utf-8")
        return report_path

    def _record_learning(self, validation: Dict, ingest_result: Dict, projection: Dict) -> Dict:
        context = f"{self.topic} evolution cycle {today()}"
        if validation.get("ok"):
            pattern = (
                f"{self.topic} 先对真实报告执行 ingest，再 refresh_views，再用 project_context 汇总 "
                f"{projection.get('items', 0)} 条上下文，最后把结果写回 self_learning 图谱"
            )
            recorded = self.learning_memory.learn_from_success(pattern, context)
            return {
                "recorded": recorded,
                "mode": "success",
                "content": pattern,
                "context": context,
                "updated_files": ingest_result.get("updated", 0),
            }
        reflection = " -> ".join(validation.get("errors", [])[:5]) or "图谱校验失败"
        lesson = f"{self.topic} 在 evolution 闭环里必须先 refresh_views 再生成 report，并处理无效关系"
        recorded = self.learning_memory.learn_from_correction(context, reflection, lesson)
        return {
            "recorded": recorded,
            "mode": "correction",
            "content": lesson,
            "reflection": reflection,
            "context": context,
        }

    def _build_cycle_report(self, query: str, budget: int, projection: Optional[Dict] = None) -> Dict:
        if projection is None:
            self._reload_runtime_views()
            projection_data = self.graph.project_context(task_type="report", query=query or self.topic, budget=budget)
            projection = {
                "query": projection_data.get("query", ""),
                "items": len(projection_data.get("items", [])),
                "used_budget": projection_data.get("used_budget", 0),
                "entity_types": projection_data.get("entity_types", {}),
                "prompt": projection_data.get("prompt", ""),
                "mode": projection_data.get("mode", "bfs"),
                "depth": projection_data.get("depth", 2),
                "start_nodes": projection_data.get("start_nodes", []),
                "graph_slice_edges": len(projection_data.get("graph_slice", {}).get("edges", [])),
            }
        graph_report = self.graph.generate_graph_report()
        stats = self.graph.graph_stats()
        god_nodes = self.graph.god_nodes(top_n=5)
        surprising = self.graph.surprising_connections(top_n=5)
        benchmark = self.graph.benchmark_context(
            questions=[
                query or self.topic,
                f"{self.topic} 的核心方法",
                f"{self.topic} 的关键缺口",
            ],
            token_budget=max(600, min(budget, 1800)),
        )
        return {
            "graph_report": graph_report,
            "projection": projection,
            "graph_stats": stats,
            "god_nodes": god_nodes,
            "surprising_connections": surprising,
            "benchmark": benchmark,
            "context_prompt_preview": self.context_builder.get_full_prompt(query=query or self.topic, budget=budget)[:1200],
        }

    def run(self, force: bool = False, ingest_path: Optional[str] = None, query: str = "", budget: int = 1600, sync: bool = True) -> Dict:
        """执行完整的进化流程"""
        print("=" * 60)
        print("🔬 AI Deep Research Agent — 自我进化版")
        print(f"   主题：{self.topic}")
        print(f"   时间：{now()}")
        print("=" * 60)
        
        results = {
            "topic": self.topic,
            "topic_id": self.topic_id,
            "date": today(),
            "stages": {}
        }
        
        cache = load_cache()
        if not force and cache.get("last_update", {}).get(self.topic) == today():
            print(f"\n✅ 今日已完成研究，跳过")
            return results

        print(f"\n🌱 阶段 0/8：空图自引导...")
        bootstrap_result = self._ensure_bootstrap_seed(force=force)
        results["stages"]["bootstrap"] = bootstrap_result
        print(f"   已引导：{'是' if bootstrap_result.get('bootstrapped') else '否'}")
        print(f"   实体：{bootstrap_result.get('entities', 0)}")
        print(f"   关系：{bootstrap_result.get('edges', 0)}")
        
        print(f"\n📥 阶段 1/8：真实搜索与筛选...")
        search_and_analysis = self._run_search_analysis(query=query, budget=budget)
        results["stages"]["search"] = search_and_analysis["search"]
        results["stages"]["analysis"] = search_and_analysis["analysis"]
        print(f"   候选论文：{results['stages']['search'].get('count', 0)}")
        print(f"   深度分析：{results['stages']['analysis'].get('selected_count', 0)}")
        
        print(f"\n📥 阶段 2/8：真实 ingest ...")
        ingest_targets = self._resolve_ingest_targets(ingest_path)
        ingest_result = self._run_ingest(ingest_targets, full_ingest=force)
        results["stages"]["ingest"] = {
            "path": ingest_result.get("path"),
            "paths": ingest_result.get("paths", []),
            "exists": ingest_result.get("exists", True),
            "processed": ingest_result.get("processed", 0),
            "updated": ingest_result.get("updated", 0),
            "skipped": ingest_result.get("skipped", 0),
            "sample_sources": self._collect_ingest_sources(ingest_targets),
            "source_policy": ingest_result.get("source_policy", "external_only"),
        }
        print(f"   处理：{results['stages']['ingest']['processed']}")
        print(f"   更新：{results['stages']['ingest']['updated']}")
        
        print(f"\n🔄 阶段 3/8：refresh 视图...")
        repair_result = self._repair_graph()
        refresh_result = self.graph.refresh_views()
        validation = self.graph.validate()
        results["stages"]["refresh"] = {
            **repair_result,
            **refresh_result,
            "validation": validation,
            "entities": len(self.graph.entities),
            "relations": len(self.graph.edges),
            "documents": self.graph.metadata.get("document_count", 0),
        }
        print(f"   社区：{refresh_result.get('communities', 0)}")
        print(f"   清理无效关系：{repair_result.get('removed_invalid_edges', 0)}")
        print(f"   校验：{'通过' if validation.get('ok') else '失败'}")
        
        print(f"\n🧠 阶段 4/8：project_context + report ...")
        pre_learning_projection = self._build_projection(query=query, budget=budget)
        cycle_report = self._build_cycle_report(query=query, budget=budget, projection=pre_learning_projection)
        results["stages"]["report"] = {
            "projection": pre_learning_projection,
            "graph_report": cycle_report["graph_report"],
            "graph_stats": cycle_report["graph_stats"],
            "god_nodes": cycle_report["god_nodes"],
            "surprising_connections": cycle_report["surprising_connections"],
            "benchmark": cycle_report["benchmark"],
            "context_prompt_preview": cycle_report["context_prompt_preview"],
        }
        print(f"   投影条目：{pre_learning_projection['items']}")
        print(f"   God Nodes：{len(cycle_report['god_nodes'])}")
        print(f"   意外连接：{len(cycle_report['surprising_connections'])}")
        
        print(f"\n📚 阶段 5/8：self_learning 回写...")
        learning_result = self._record_learning(validation, ingest_result, pre_learning_projection)
        self._reload_runtime_views()
        post_learning_refresh = self.graph.refresh_views()
        post_learning_validation = self.graph.validate()
        post_learning_report = self._build_cycle_report(query=query, budget=budget)
        print(f"   记录：{'成功' if learning_result.get('recorded') else '失败'}")

        print(f"\n🗜️ 阶段 6/8：自动压缩...")
        from memory_compressor import MemoryCompressor
        compression_result = MemoryCompressor().auto_compress_if_due(self.topic_id)
        results["stages"]["compression"] = compression_result
        print(f"   已执行：{compression_result.get('compressed', False)}")

        print(f"\n📝 阶段 7/8：写出演化报告...")
        report_path = self._write_cycle_report(
            search_result=results["stages"]["search"],
            analysis_result=results["stages"]["analysis"],
            ingest_result=ingest_result,
            refresh_result={**repair_result, **refresh_result, "validation": validation},
            cycle_report=post_learning_report,
            learning_result=learning_result,
            compression_result=compression_result,
        )
        results["stages"]["self_learning"] = {
            **learning_result,
            "post_refresh": post_learning_refresh,
            "post_validation": post_learning_validation,
            "post_projection_items": post_learning_report["projection"]["items"],
            "post_projection_types": post_learning_report["projection"]["entity_types"],
            "post_benchmark": post_learning_report["benchmark"],
        }
        print(f"   报告：{report_path}")

        results["stages"]["report"]["report_path"] = str(report_path)
        
        print(f"\n📤 阶段 8/8：IMA 同步...")
        sync_results = []
        sync_errors = []
        if sync:
            if self.syncer is None:
                self.syncer = IMASyncer(self.kb_id)
            note_id = self.syncer.sync_graph(post_learning_report["graph_report"], self.topic)
            if note_id:
                sync_results.append(f"知识图谱：{note_id}")
            else:
                sync_errors.append("知识图谱同步失败")
        results["stages"]["sync"] = {
            "enabled": sync,
            "synced": sync_results,
            "errors": sync_errors,
        }
        print(f"   已同步：{len(sync_results)} 项")
        
        cache["last_update"][self.topic] = today()
        save_cache(cache)
        
        print(f"\n{'=' * 60}")
        print(f"✅ {self.topic} 研究完成")
        print("=" * 60)
        
        return results


def _execute_topic_batch(topics: List[Dict], force: bool = False, ingest_path: Optional[str] = None, query: str = "", budget: int = 1600, sync: bool = True, kb_id: str = None, retry_attempts: int = 0) -> Dict:
    results = []
    for topic in topics:
        target = topic.get("id") or topic.get("name", "")
        max_attempts = max(1, int(retry_attempts) + 1)
        errors = []
        topic_payload = {
            "topic": topic.get("name", ""),
            "topic_id": topic.get("id", ""),
            "success": False,
            "attempts": 0,
        }
        for attempt in range(1, max_attempts + 1):
            topic_payload["attempts"] = attempt
            try:
                engine = EvolutionEngine(target, kb_id or topic.get("target_knowledge_base") or topic.get("kb_id"))
                topic_result = engine.run(
                    force=force,
                    ingest_path=ingest_path,
                    query=query or build_default_query(topic),
                    budget=budget,
                    sync=sync,
                )
                topic_payload.update({
                    "topic": topic_result.get("topic", topic.get("name", "")),
                    "topic_id": topic_result.get("topic_id", topic.get("id", "")),
                    "success": True,
                    "skipped": not bool(topic_result.get("stages")),
                    "stages": topic_result.get("stages", {}),
                    "errors": errors,
                    "retried": attempt > 1,
                })
                break
            except Exception as exc:
                errors.append(str(exc))
                topic_payload.update({
                    "success": False,
                    "error": str(exc),
                    "errors": errors[:],
                    "retried": attempt > 1,
                })
        results.append(topic_payload)

    succeeded_topics = len([item for item in results if item.get("success")])
    refreshed = None
    if results and succeeded_topics:
        refreshed = refresh_cross_topic_insights()
    return {
        "success": succeeded_topics == len(results) and bool(results),
        "processed_topics": len(results),
        "succeeded_topics": succeeded_topics,
        "failed_topics": len(results) - succeeded_topics,
        "topics": results,
        "global_refresh": refreshed or {"updated": False},
    }


def run_batch_evolution(topic_name: str = "", force: bool = False, ingest_path: Optional[str] = None, query: str = "", budget: int = 1600, sync: bool = True, kb_id: str = None) -> Dict:
    config = load_topics_config()
    topics = [topic for topic in config.get("topics", []) if topic.get("enabled", True)]
    if topic_name:
        topics = [topic for topic in topics if topic_matches(topic, topic_name)]
        if not topics:
            return {
                "success": False,
                "processed_topics": 0,
                "succeeded_topics": 0,
                "failed_topics": 0,
                "topics": [],
                "error": f"未找到主题：{topic_name}",
            }
    return _execute_topic_batch(
        topics,
        force=force,
        ingest_path=ingest_path,
        query=query,
        budget=budget,
        sync=sync,
        kb_id=kb_id,
        retry_attempts=0,
    )


def run_scheduled_evolution(topic_name: str = "", force: bool = False, ingest_path: Optional[str] = None, query: str = "", budget: int = 1600, sync: bool = True, kb_id: str = None, loop: bool = False, interval_minutes: int = 60) -> Dict:
    def run_cycle() -> Dict:
        started_at = datetime.now()
        config = load_topics_config()
        cache = load_cache()
        scheduler_state = load_scheduler_state()
        retry_policy = scheduler_state.get("retry_policy", {})
        max_attempts = max(1, int(retry_policy.get("max_attempts_per_cycle", 2)))
        topics = [topic for topic in config.get("topics", []) if topic.get("enabled", True)]
        if topic_name:
            topics = [topic for topic in topics if topic_matches(topic, topic_name)]
            if not topics:
                result = {
                    "success": False,
                    "processed_topics": 0,
                    "succeeded_topics": 0,
                    "failed_topics": 0,
                    "topics": [],
                    "due_topics": [],
                    "skipped_topics": [],
                    "error": f"未找到主题：{topic_name}",
                }
                persist_scheduler_cycle(result, [], scheduler_state, started_at=started_at)
                return result

        due_topics = []
        skipped_topics = []
        paused_topics = []
        for topic in topics:
            schedule = topic_schedule_status(topic, cache, reference_time=started_at)
            retry_status = scheduler_retry_status(topic, scheduler_state, reference_time=started_at)
            pause_status = scheduler_pause_status(topic, scheduler_state, reference_time=started_at)
            next_run = scheduler_next_run(topic, cache, scheduler_state, reference_time=started_at)
            topic_view = {
                "topic": topic.get("name", ""),
                "topic_id": topic.get("id", ""),
                **schedule,
                **retry_status,
                **pause_status,
                **next_run,
            }
            if pause_status.get("paused") and not force:
                paused_topics.append(topic_view)
            elif force or schedule.get("due") or retry_status.get("retry_due"):
                topic["retry_reason"] = "scheduler_retry" if retry_status.get("retry_due") and not schedule.get("due") else schedule.get("reason", "due")
                due_topics.append(topic)
            else:
                skipped_topics.append(topic_view)

        if not due_topics:
            result = {
                "success": True,
                "processed_topics": 0,
                "succeeded_topics": 0,
                "failed_topics": 0,
                "topics": [],
                "due_topics": [],
                "skipped_topics": skipped_topics,
                "paused_topics": paused_topics,
                "global_refresh": {"updated": False},
                "schedule": {
                    "loop": loop,
                    "interval_minutes": interval_minutes,
                    "evaluated_topics": len(topics),
                    "due_count": 0,
                    "paused_count": len(paused_topics),
                    "retry_attempts_per_topic": max_attempts,
                },
            }
            persist_scheduler_cycle(result, topics, scheduler_state, started_at=started_at)
            return result

        batch_result = _execute_topic_batch(
            due_topics,
            force=force,
            ingest_path=ingest_path,
            query=query,
            budget=budget,
            sync=sync,
            kb_id=kb_id,
            retry_attempts=max_attempts - 1,
        )
        batch_result["due_topics"] = [
            {
                "topic": item.get("name", ""),
                "topic_id": item.get("id", ""),
                **topic_schedule_status(item, cache, reference_time=started_at),
                **scheduler_retry_status(item, scheduler_state, reference_time=started_at),
                **scheduler_pause_status(item, scheduler_state, reference_time=started_at),
                **scheduler_next_run(item, cache, scheduler_state, reference_time=started_at),
                "retry_reason": item.get("retry_reason", ""),
            }
            for item in due_topics
        ]
        batch_result["skipped_topics"] = skipped_topics
        batch_result["paused_topics"] = paused_topics
        batch_result["schedule"] = {
            "loop": loop,
            "interval_minutes": interval_minutes,
            "evaluated_topics": len(topics),
            "due_count": len(due_topics),
            "paused_count": len(paused_topics),
            "retry_attempts_per_topic": max_attempts,
        }
        persist_scheduler_cycle(batch_result, topics, scheduler_state, started_at=started_at)
        return batch_result

    if not loop:
        return run_cycle()

    while True:
        cycle_result = run_cycle()
        print(json.dumps(cycle_result, ensure_ascii=False, indent=2))
        time.sleep(max(1, interval_minutes) * 60)

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
    e.add_argument("--topic", "-t", default="")
    e.add_argument("--all", action="store_true", help="对所有启用主题执行闭环进化")
    e.add_argument("--force", "-f", action="store_true")
    e.add_argument("--kb-id", "-k")
    e.add_argument("--ingest-path", help="指定真实 ingest 的文件或目录")
    e.add_argument("--query", default="", help="用于 project_context 的查询意图")
    e.add_argument("--budget", type=int, default=1600, help="上下文预算")
    e.add_argument("--no-sync", action="store_true", help="跳过 IMA 同步")

    # schedule 命令
    sch = sub.add_parser("schedule", help="按 frequency 执行自治调度")
    sch.add_argument("--topic", "-t", default="")
    sch.add_argument("--force", "-f", action="store_true")
    sch.add_argument("--kb-id", "-k")
    sch.add_argument("--ingest-path", help="指定真实 ingest 的文件或目录")
    sch.add_argument("--query", default="", help="用于 project_context 的查询意图")
    sch.add_argument("--budget", type=int, default=1600, help="上下文预算")
    sch.add_argument("--no-sync", action="store_true", help="跳过 IMA 同步")
    sch.add_argument("--loop", action="store_true", help="持续运行调度器")
    sch.add_argument("--interval-minutes", type=int, default=60, help="循环模式下的调度间隔")

    # scheduler 命令
    ctl = sub.add_parser("scheduler", help="查看或控制自治调度状态")
    ctl.add_argument("--action", choices=["status", "pause", "resume", "reset"], required=True)
    ctl.add_argument("--topic", "-t", default="")
    ctl.add_argument("--limit", type=int, default=10, help="status 模式展示的主题数量")
    ctl.add_argument("--hours", type=int, default=24, help="pause 模式的暂停小时数")
    
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
        if not args.all and not args.topic:
            parser.error("evolve 需要提供 --topic 或 --all")
        result = run_batch_evolution(
            topic_name="" if args.all else args.topic,
            force=args.force,
            ingest_path=args.ingest_path,
            query=args.query,
            budget=args.budget,
            sync=not args.no_sync,
            kb_id=args.kb_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "schedule":
        result = run_scheduled_evolution(
            topic_name=args.topic,
            force=args.force,
            ingest_path=args.ingest_path,
            query=args.query,
            budget=args.budget,
            sync=not args.no_sync,
            kb_id=args.kb_id,
            loop=args.loop,
            interval_minutes=args.interval_minutes,
        )
        if not args.loop:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.cmd == "scheduler":
        if args.action == "status":
            result = get_scheduler_status(topic_name=args.topic, limit=args.limit)
        else:
            result = control_scheduler_topic(args.action, args.topic, hours=args.hours)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.cmd == "list":
        config = load_topics_config()
        print("📋 研究主题列表\n")
        for t in config.get("topics", []):
            name = t.get("name", "")
            enabled = "✅" if t.get("enabled", True) else "⏸️"
            priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.get("priority", "medium"), "⚪")

            graph_topic, graph_dir, graph_filename = resolve_graph_location(t.get("id") or name)
            graph = get_or_create_graph(graph_topic, base_dir=graph_dir, filename=graph_filename)
            stats = graph.graph_stats()
            if stats.get("entities", 0) or stats.get("edges", 0):
                info = f"实体:{stats.get('entities', 0)} 关系:{stats.get('edges', 0)} 文档:{stats.get('documents', 0)}"
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
