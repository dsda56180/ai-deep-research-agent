#!/usr/bin/env python3

import argparse
from difflib import SequenceMatcher
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

import yaml

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
KNOWLEDGE_DIR = SKILL_DIR / "knowledge"
GRAPHS_DIR = KNOWLEDGE_DIR / "graphs"
DATA_DIR = SKILL_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
TOPICS_DIR = SKILL_DIR / "topics"

PRIMARY_ENTITY_TYPES = {"system", "concept", "method", "dataset", "metric"}
DEFAULT_EDGE_STATUS = "EXTRACTED"
ENTITY_TYPE_ALIASES = {
    "paper": "Paper",
    "document": "Document",
    "lesson": "Lesson",
    "pattern": "Pattern",
    "methodology": "Methodology",
    "gap": "Gap",
    "claim": "Claim",
    "communitysummary": "CommunitySummary",
    "researchsession": "ResearchSession",
    "session": "ResearchSession",
    "method": "method",
    "system": "system",
    "concept": "concept",
    "dataset": "dataset",
    "metric": "metric",
}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".json", ".yml", ".yaml",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs",
    ".java", ".c", ".cpp", ".rb", ".cs", ".kt", ".scala",
    ".php", ".swift", ".lua", ".zig", ".ps1", ".ex", ".exs",
    ".m", ".mm", ".csv"
}
MEDIA_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
DEFAULT_IGNORES = {
    ".git", "__pycache__", "node_modules", "dist", "build",
    ".venv", "venv", ".archive", "graphify-out"
}


def now_iso() -> str:
    return datetime.now().isoformat()


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.lower())
    return cleaned.strip("-") or "item"


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


SEMANTIC_EQUIVALENTS = {
    "llm": ["large language model", "foundation model", "大模型"],
    "rag": ["retrieval augmented generation", "检索增强生成"],
    "kg": ["knowledge graph", "知识图谱"],
    "multi agent": ["multi-agent", "agent swarm", "多智能体"],
    "long term memory": ["long-term memory", "persistent memory", "长期记忆"],
    "ai agent": ["agentic ai", "llm agent", "智能体"],
}


def tokenize_text(value: str) -> List[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value or "")
    return [token for token in re.split(r"[\s,;:|/\\(){}\[\]<>+&=_-]+", spaced.lower()) if token]


def expand_search_terms(value: str) -> List[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    terms = set(tokenize_text(raw))
    compact = normalize_name(raw)
    if compact:
        terms.add(compact)
    words = tokenize_text(raw)
    if len(words) >= 2:
        acronym = "".join(word[0] for word in words if word and word[0].isalnum())
        if len(acronym) >= 2:
            terms.add(acronym.lower())
            terms.add(acronym.upper())
    compact_terms = {normalize_name(term) for term in terms if term}
    for seed, variants in SEMANTIC_EQUIVALENTS.items():
        family = [seed, *variants]
        family_compact = {normalize_name(item) for item in family}
        if compact in family_compact or compact_terms & family_compact:
            for item in family:
                terms.update(tokenize_text(item))
                normalized = normalize_name(item)
                if normalized:
                    terms.add(normalized)
    return sorted(term for term in terms if term)


def text_similarity(left: str, right: str) -> float:
    left_terms = set(expand_search_terms(left))
    right_terms = set(expand_search_terms(right))
    overlap = 0.0
    if left_terms and right_terms:
        overlap = len(left_terms & right_terms) / max(1, len(left_terms | right_terms))
    sequence = SequenceMatcher(None, normalize_name(left), normalize_name(right)).ratio()
    return max(overlap, sequence)


def generate_alias_candidates(value: str) -> List[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    variants = {raw}
    words = tokenize_text(raw)
    if len(words) >= 2:
        variants.add(" ".join(words))
        variants.add("-".join(words))
        acronym = "".join(word[0] for word in words if word and word[0].isalnum())
        if len(acronym) >= 2:
            variants.add(acronym.lower())
            variants.add(acronym.upper())
    compact = normalize_name(raw)
    for seed, related in SEMANTIC_EQUIVALENTS.items():
        family = [seed, *related]
        if compact in {normalize_name(item) for item in family}:
            variants.update(family)
    return sorted(item for item in variants if item)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def trim_text(value: str, limit: int = 400) -> str:
    value = (value or "").strip()
    return value if len(value) <= limit else value[: limit - 3] + "..."


def estimate_tokens(value: str) -> int:
    return max(1, len((value or "").strip()) // 4) if value else 0


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", (value or "").strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned.strip("._-") or "item"


BLOCKED_REMOTE_HOSTS = {
    "metadata.google.internal",
    "metadata.google.com",
    "169.254.169.254",
}


def validate_remote_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"不支持的 URL 协议: {parsed.scheme}")
    hostname = parsed.hostname or ""
    if hostname.lower() in BLOCKED_REMOTE_HOSTS:
        raise ValueError(f"禁止访问的主机: {hostname}")
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        infos = []
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"禁止访问内部地址: {address}")
    return url


def safe_fetch_url(url: str, max_bytes: int = 10_485_760, timeout: int = 20, headers: Optional[Dict[str, str]] = None) -> bytes:
    validated = validate_remote_url(url)
    request = urllib.request.Request(validated, headers=headers or {"User-Agent": "ai-deep-research-agent/6.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        chunks = []
        total = 0
        while True:
            chunk = response.read(65_536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise OSError(f"响应内容超过限制: {max_bytes} bytes")
            chunks.append(chunk)
    return b"".join(chunks)


def canonicalize_entity_type(entity_type: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", (entity_type or "").lower())
    return ENTITY_TYPE_ALIASES.get(normalized, entity_type or "concept")


def resolve_graph_location(topic: str) -> Tuple[str, Path, str]:
    config_path = SKILL_DIR / "config" / "topics.yaml"
    topic_id = slugify(topic)
    topic_name = topic
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        for item in config.get("topics", []):
            item_id = item.get("id", "")
            item_name = item.get("name", "")
            if normalize_name(topic) in {normalize_name(item_id), normalize_name(item_name)}:
                topic_id = item_id or topic_id
                topic_name = item_name or topic_name
                break
    topic_graph_dir = TOPICS_DIR / topic_id / "knowledge" / "graphs"
    topic_graph_file = f"{topic_id}_knowledge_graph.json"
    if topic_graph_dir.exists() or (topic_graph_dir / topic_graph_file).exists():
        return topic_name, topic_graph_dir, topic_graph_file
    return topic_name, GRAPHS_DIR, f"{topic.replace(' ', '_')}_knowledge_graph.json"


@dataclass
class Entity:
    id: str
    name: str
    type: str
    description: str = ""
    summary: str = ""
    papers: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    layer: str = "warm"
    confidence: float = 1.0
    attributes: Dict = field(default_factory=dict)
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "summary": self.summary,
            "papers": self.papers,
            "parent": self.parent,
            "children": self.children,
            "tags": self.tags,
            "aliases": self.aliases,
            "source_ids": self.source_ids,
            "layer": self.layer,
            "confidence": self.confidence,
            "attributes": self.attributes,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Entity":
        return cls(
            id=data["id"],
            name=data["name"],
            type=data.get("type", "concept"),
            description=data.get("description", ""),
            summary=data.get("summary", ""),
            papers=data.get("papers", []),
            parent=data.get("parent"),
            children=data.get("children", []),
            tags=data.get("tags", []),
            aliases=data.get("aliases", []),
            source_ids=data.get("source_ids", []),
            layer=data.get("layer", "warm"),
            confidence=float(data.get("confidence", 1.0)),
            attributes=data.get("attributes", {}),
            created=data.get("created", now_iso()),
            updated=data.get("updated", now_iso()),
        )


class Concept(Entity):
    def __init__(self, id: str, name: str, concept_type: str = "concept"):
        super().__init__(id=id, name=name, type=concept_type)


@dataclass
class Relation:
    from_id: str
    to_id: str
    type: str
    evidence: str = ""
    status: str = DEFAULT_EDGE_STATUS
    confidence: float = 1.0
    source_span: str = ""
    source_document: str = ""
    extractor_version: str = "manual-v1"
    created: str = field(default_factory=now_iso)
    attributes: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "type": self.type,
            "evidence": self.evidence,
            "status": self.status,
            "confidence": self.confidence,
            "source_span": self.source_span,
            "source_document": self.source_document,
            "extractor_version": self.extractor_version,
            "created": self.created,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Relation":
        return cls(
            from_id=data["from"],
            to_id=data["to"],
            type=data.get("type", "related_to"),
            evidence=data.get("evidence", ""),
            status=data.get("status", DEFAULT_EDGE_STATUS),
            confidence=float(data.get("confidence", 1.0)),
            source_span=data.get("source_span", ""),
            source_document=data.get("source_document", ""),
            extractor_version=data.get("extractor_version", "legacy-v1"),
            created=data.get("created", now_iso()),
            attributes=data.get("attributes", {}),
        )


class IngestCache:
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {"files": {}, "urls": {}, "updated": now_iso()}

    def get_file(self, key: str) -> Dict:
        return self.data.get("files", {}).get(key, {})

    def set_file(self, key: str, value: Dict):
        self.data.setdefault("files", {})[key] = value
        self.data["updated"] = now_iso()

    def get_url(self, key: str) -> Dict:
        return self.data.get("urls", {}).get(key, {})

    def set_url(self, key: str, value: Dict):
        self.data.setdefault("urls", {})[key] = value
        self.data["updated"] = now_iso()

    def save(self):
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


class KnowledgeGraph:
    def __init__(self, topic: str, graph_path: Optional[Path] = None):
        self.topic = topic
        self.graph_path = Path(graph_path) if graph_path else GRAPHS_DIR / f"{topic.replace(' ', '_')}_knowledge_graph.json"
        self.entities: Dict[str, Entity] = {}
        self.edges: List[Relation] = []
        self.insights = {
            "breakthroughs": [],
            "gaps": [],
            "trends": [],
            "questions": [],
            "contradictions": [],
        }
        self.communities: List[Dict] = []
        self.summaries: List[Dict] = []
        self.alias_index: Dict[str, str] = {}
        self.metadata = {
            "created": now_iso(),
            "updated": now_iso(),
            "paper_count": 0,
            "concept_count": 0,
            "relation_count": 0,
            "document_count": 0,
            "entity_count": 0,
            "graph_version": 2,
        }

    @property
    def concepts(self) -> Dict[str, Entity]:
        return {entity_id: entity for entity_id, entity in self.entities.items() if entity.type in PRIMARY_ENTITY_TYPES}

    @property
    def relations(self) -> List[Relation]:
        return self.edges

    def _touch(self):
        self.metadata["updated"] = now_iso()

    def _refresh_metadata(self):
        self.metadata["entity_count"] = len(self.entities)
        self.metadata["concept_count"] = len(self.concepts)
        self.metadata["relation_count"] = len(self.edges)
        self.metadata["document_count"] = len([e for e in self.entities.values() if e.type == "Document"])
        self._touch()

    def _register_aliases(self, entity: Entity):
        candidates = [entity.name, *entity.aliases]
        for value in list(candidates):
            candidates.extend(generate_alias_candidates(value))
        for alias in candidates:
            normalized = normalize_name(alias)
            if normalized:
                self.alias_index[normalized] = entity.id

    def _generate_id(self, name: str, entity_type: str = "concept") -> str:
        base = f"{slugify(entity_type)}-{slugify(name)}"
        candidate = base
        counter = 2
        while candidate in self.entities:
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def find_entity(self, name: Optional[str] = None, entity_id: Optional[str] = None) -> Optional[Entity]:
        if entity_id and entity_id in self.entities:
            return self.entities[entity_id]
        if not name:
            return None
        alias_key = normalize_name(name)
        if alias_key in self.alias_index:
            return self.entities.get(self.alias_index[alias_key])
        for entity in self.entities.values():
            if normalize_name(entity.name) == alias_key:
                return entity
        return None

    def _find_near_duplicate(self, entity: Entity) -> Optional[Entity]:
        entity_type = canonicalize_entity_type(entity.type)
        for existing in self.entities.values():
            existing_type = canonicalize_entity_type(existing.type)
            compatible = existing_type == entity_type or (
                existing_type in PRIMARY_ENTITY_TYPES and entity_type in PRIMARY_ENTITY_TYPES
            )
            if not compatible:
                continue
            aliases = [existing.name, *existing.aliases]
            similarity = max(text_similarity(entity.name, alias) for alias in aliases if alias)
            if similarity >= 0.92:
                return existing
        return None

    def add_entity(self, entity: Entity) -> Entity:
        existing = self.entities.get(entity.id) or self.find_entity(entity.name) or self._find_near_duplicate(entity)
        if existing:
            existing.description = entity.description or existing.description
            existing.summary = entity.summary or existing.summary
            existing.papers = sorted(set(existing.papers + entity.papers))
            existing.children = sorted(set(existing.children + entity.children))
            existing.tags = sorted(set(existing.tags + entity.tags))
            existing.aliases = sorted(set(existing.aliases + entity.aliases + generate_alias_candidates(entity.name)))
            existing.source_ids = sorted(set(existing.source_ids + entity.source_ids))
            existing.layer = entity.layer or existing.layer
            existing.confidence = max(existing.confidence, entity.confidence)
            existing.attributes.update(entity.attributes)
            existing.updated = now_iso()
            self._register_aliases(existing)
            self._refresh_metadata()
            return existing
        entity.aliases = sorted(set(entity.aliases + generate_alias_candidates(entity.name)))
        self.entities[entity.id] = entity
        self._register_aliases(entity)
        self._refresh_metadata()
        return entity

    def upsert_entity(
        self,
        name: str,
        entity_type: str,
        description: str = "",
        entity_id: Optional[str] = None,
        summary: str = "",
        attributes: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        aliases: Optional[List[str]] = None,
        source_ids: Optional[List[str]] = None,
        papers: Optional[List[str]] = None,
        layer: str = "warm",
        confidence: float = 1.0,
    ) -> Entity:
        entity_type = canonicalize_entity_type(entity_type)
        entity = Entity(
            id=entity_id or self._generate_id(name, entity_type),
            name=name,
            type=entity_type,
            description=description,
            summary=summary,
            attributes=attributes or {},
            tags=tags or [],
            aliases=aliases or [],
            source_ids=source_ids or [],
            papers=papers or [],
            layer=layer,
            confidence=confidence,
        )
        return self.add_entity(entity)

    def add_relation(self, relation: Relation) -> Relation:
        if relation.from_id not in self.entities or relation.to_id not in self.entities:
            raise ValueError(f"关系端点不存在: {relation.from_id} -> {relation.to_id}")
        for existing in self.edges:
            if (
                existing.from_id == relation.from_id
                and existing.to_id == relation.to_id
                and existing.type == relation.type
                and existing.status == relation.status
                and existing.source_document == relation.source_document
                and existing.source_span == relation.source_span
            ):
                existing.evidence = relation.evidence or existing.evidence
                existing.confidence = max(existing.confidence, relation.confidence)
                existing.attributes.update(relation.attributes)
                self._refresh_metadata()
                return existing
        self.edges.append(relation)
        self._refresh_metadata()
        return relation

    def get_related_concepts(self, concept_id: str) -> List[Entity]:
        related = []
        for edge in self.edges:
            if edge.from_id == concept_id and edge.to_id in self.entities:
                related.append(self.entities[edge.to_id])
            elif edge.to_id == concept_id and edge.from_id in self.entities:
                related.append(self.entities[edge.from_id])
        return related

    def rank_entities(self, query: str, types: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Tuple[float, Entity]]:
        query_terms = set(expand_search_terms(query))
        candidates = []
        for entity in self.entities.values():
            if types and entity.type not in types:
                continue
            haystack_parts = [
                entity.name,
                entity.description,
                entity.summary,
                " ".join(entity.tags),
                " ".join(entity.aliases),
            ]
            haystack = " ".join(haystack_parts).lower()
            entity_terms = set()
            for part in haystack_parts:
                entity_terms.update(expand_search_terms(part))
            score = sum(4 for token in query_terms if token in expand_search_terms(entity.name))
            score += sum(2 for token in query_terms if token in entity_terms)
            semantic_score = max(
                [text_similarity(query, entity.name)]
                + [text_similarity(query, alias) for alias in entity.aliases[:6]]
            )
            score += round(semantic_score * 6, 2)
            score += min(len(self.get_related_concepts(entity.id)), 5)
            if score > 0:
                candidates.append((score, entity))
        ranked = sorted(candidates, key=lambda item: item[0], reverse=True)
        return ranked[:limit] if limit is not None else ranked

    def search_entities(self, query: str, types: Optional[List[str]] = None, limit: int = 10) -> List[Entity]:
        return [entity for _, entity in self.rank_entities(query, types=types, limit=limit)]

    def validate(self) -> Dict:
        errors = []
        valid_statuses = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
        for edge in self.edges:
            if edge.from_id not in self.entities:
                errors.append(f"缺少 from 实体: {edge.from_id}")
            if edge.to_id not in self.entities:
                errors.append(f"缺少 to 实体: {edge.to_id}")
            if edge.status not in valid_statuses:
                errors.append(f"非法关系状态: {edge.status}")
            if not 0.0 <= edge.confidence <= 1.0:
                errors.append(f"非法置信度: {edge.confidence}")
        return {
            "ok": not errors,
            "errors": errors,
            "entities": len(self.entities),
            "edges": len(self.edges),
        }

    def extract_from_paper(self, paper_data: Dict):
        paper_id = paper_data.get("arxiv_id") or paper_data.get("id") or self._generate_id(paper_data.get("title", "paper"), "paper")
        paper = self.upsert_entity(
            name=paper_data.get("title", paper_id),
            entity_type="Paper",
            entity_id=paper_id,
            description=trim_text(paper_data.get("abstract", "") or paper_data.get("core_method", ""), 600),
            summary=trim_text(paper_data.get("abstract", "") or paper_data.get("core_method", ""), 200),
            attributes={
                "url": paper_data.get("url", ""),
                "venue": paper_data.get("venue", ""),
                "authors": paper_data.get("authors", []),
                "published_at": paper_data.get("pub_date", ""),
            },
            layer="hot",
        )
        if "core_method" in paper_data:
            method_name = paper_data.get("method_name") or paper_data.get("title", "")[:60]
            method = self.upsert_entity(
                name=method_name,
                entity_type="method",
                description=trim_text(paper_data.get("core_method", ""), 500),
                papers=[paper_id],
                source_ids=[paper_id],
                layer="hot",
            )
            self.add_relation(Relation(
                from_id=paper.id,
                to_id=method.id,
                type="proposes",
                evidence=trim_text(paper_data.get("core_method", ""), 240),
                status="EXTRACTED",
                confidence=0.9,
                source_document=paper.id,
                extractor_version="paper-v2",
            ))
        for innovation in paper_data.get("innovations", []):
            concept = self.upsert_entity(
                name=innovation[:80],
                entity_type="concept",
                description=innovation,
                papers=[paper_id],
                source_ids=[paper_id],
            )
            self.add_relation(Relation(
                from_id=paper.id,
                to_id=concept.id,
                type="introduces",
                evidence=innovation,
                status="EXTRACTED",
                confidence=0.9,
                source_document=paper.id,
                extractor_version="paper-v2",
            ))
        for dataset in paper_data.get("datasets", []):
            dataset_entity = self.upsert_entity(
                name=dataset,
                entity_type="dataset",
                papers=[paper_id],
                source_ids=[paper_id],
            )
            self.add_relation(Relation(
                from_id=paper.id,
                to_id=dataset_entity.id,
                type="evaluates_on",
                evidence=dataset,
                status="EXTRACTED",
                confidence=0.95,
                source_document=paper.id,
                extractor_version="paper-v2",
            ))
        for limitation in paper_data.get("limitations", []):
            gap = self.upsert_entity(
                name=trim_text(limitation, 80),
                entity_type="Gap",
                description=limitation,
                attributes={"priority": "medium", "source": paper_id},
                source_ids=[paper_id],
                layer="hot",
            )
            self.add_relation(Relation(
                from_id=paper.id,
                to_id=gap.id,
                type="reveals_gap",
                evidence=limitation,
                status="EXTRACTED",
                confidence=0.88,
                source_document=paper.id,
                extractor_version="paper-v2",
            ))
        self.metadata["paper_count"] += 1
        self._refresh_metadata()

    def add_learning_signal(self, signal_type: str, title: str, content: str, context: str = "", score: int = 1) -> Entity:
        entity = self.upsert_entity(
            name=title,
            entity_type=signal_type,
            description=content,
            summary=trim_text(content, 160),
            attributes={"context": context, "score": score},
            tags=[signal_type.lower(), "self-improving"],
            layer="hot",
            confidence=min(1.0, 0.5 + score * 0.1),
        )
        if context:
            session = self.upsert_entity(
                name=context,
                entity_type="ResearchSession",
                description=context,
                entity_id=f"session-{slugify(context)}",
                layer="warm",
                confidence=0.8,
            )
            self.add_relation(Relation(
                from_id=entity.id,
                to_id=session.id,
                type="learned_from",
                evidence=context,
                status="EXTRACTED",
                confidence=0.85,
                extractor_version="self-learning-v2",
            ))
        return entity

    def _read_text_content(self, file_path: Path) -> str:
        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            return ""
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="ignore")

    def _extract_markdown_terms(self, text: str) -> List[Dict]:
        items = []
        for heading in re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE):
            heading = trim_text(heading, 100)
            if len(heading) >= 3:
                items.append({
                    "name": heading,
                    "type": "concept",
                    "evidence": heading,
                    "confidence": 0.82,
                })
        return items[:20]

    def _extract_code_symbols(self, text: str, suffix: str) -> List[Dict]:
        items = []
        patterns = [
            (r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", "system"),
            (r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)", "method"),
            (r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)", "method"),
            (r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", "method"),
        ]
        for pattern, entity_type in patterns:
            for match in re.findall(pattern, text, flags=re.MULTILINE):
                items.append({
                    "name": match,
                    "type": entity_type,
                    "evidence": match,
                    "confidence": 0.88 if suffix in {".py", ".ts", ".js"} else 0.8,
                })
        return items[:25]

    def _extract_paper_like_terms(self, text: str) -> List[Dict]:
        items = []
        sentences = re.split(r"[。\n\.]", text)
        for sentence in sentences:
            lower = sentence.lower()
            if "future work" in lower or "limitation" in lower or "open problem" in lower:
                items.append({
                    "name": trim_text(sentence, 80),
                    "type": "Gap",
                    "description": trim_text(sentence, 200),
                    "evidence": trim_text(sentence, 120),
                    "confidence": 0.76,
                })
            if "we propose" in lower or "our approach" in lower or "novel" in lower:
                items.append({
                    "name": trim_text(sentence, 80),
                    "type": "Claim",
                    "description": trim_text(sentence, 200),
                    "evidence": trim_text(sentence, 120),
                    "confidence": 0.72,
                })
        return items[:15]

    def _extract_named_phrases(self, text: str) -> List[Dict]:
        items = []
        patterns = [
            r"\b([A-Z][A-Za-z0-9]+(?:[- ][A-Z][A-Za-z0-9]+){0,4})\b",
            r"“([^”]{3,80})”",
            r"\"([^\"]{3,80})\"",
        ]
        seen = set()
        for pattern in patterns:
            for match in re.findall(pattern, text):
                phrase = trim_text(match.strip(), 80)
                normalized = normalize_name(phrase)
                if len(normalized) < 4 or normalized in seen:
                    continue
                lower = phrase.lower()
                entity_type = "concept"
                if any(word in lower for word in ["dataset", "benchmark"]):
                    entity_type = "dataset"
                elif any(word in lower for word in ["framework", "model", "architecture", "agent", "system"]):
                    entity_type = "system"
                elif any(word in lower for word in ["method", "algorithm", "retrieval", "memory"]):
                    entity_type = "method"
                items.append({
                    "name": phrase,
                    "type": entity_type,
                    "description": trim_text(phrase, 160),
                    "evidence": phrase,
                    "confidence": 0.68,
                })
                seen.add(normalized)
        return items[:20]

    def _extract_terms_from_text(self, text: str, suffix: str) -> List[Dict]:
        items = []
        items.extend(self._extract_markdown_terms(text))
        items.extend(self._extract_code_symbols(text, suffix))
        items.extend(self._extract_paper_like_terms(text))
        items.extend(self._extract_named_phrases(text))
        deduped = {}
        for item in items:
            key = (normalize_name(item["name"]), item["type"])
            if key not in deduped:
                deduped[key] = item
        return list(deduped.values())[:30]

    def ingest_file(self, file_path: str, root_dir: Optional[str] = None, cache: Optional[IngestCache] = None, update: bool = True) -> Dict:
        path = Path(file_path)
        relative = str(path.relative_to(Path(root_dir))) if root_dir else path.name
        raw_bytes = path.read_bytes()
        checksum = sha256_bytes(raw_bytes)
        cache_key = relative.replace("\\", "/")
        if cache:
            cached = cache.get_file(cache_key)
            if update and cached.get("checksum") == checksum:
                return {"path": relative, "updated": False, "reason": "unchanged"}
        modality = "text"
        if path.suffix.lower() in MEDIA_EXTENSIONS:
            modality = "media"
        document = self.upsert_entity(
            name=path.stem,
            entity_type="Document",
            entity_id=f"document-{slugify(relative)}",
            description=f"来源文件：{relative}",
            summary=relative,
            attributes={
                "path": str(path),
                "relative_path": relative,
                "checksum": checksum,
                "modality": modality,
                "size": len(raw_bytes),
                "suffix": path.suffix.lower(),
            },
            aliases=[relative],
            layer="warm",
            confidence=1.0,
        )
        extracted_entities = []
        text = self._read_text_content(path)
        if text:
            document.summary = trim_text(text.splitlines()[0] if text.splitlines() else relative, 120)
            document.attributes["content_preview"] = trim_text(text, 500)
            for item in self._extract_terms_from_text(text, path.suffix.lower()):
                entity = self.upsert_entity(
                    name=item["name"],
                    entity_type=item["type"],
                    description=item.get("description", ""),
                    source_ids=[document.id],
                    layer="warm",
                    confidence=item.get("confidence", 0.7),
                )
                extracted_entities.append(entity.id)
                self.add_relation(Relation(
                    from_id=document.id,
                    to_id=entity.id,
                    type="mentions",
                    evidence=item.get("evidence", entity.name),
                    status="EXTRACTED",
                    confidence=item.get("confidence", 0.7),
                    source_span=item.get("evidence", entity.name),
                    source_document=document.id,
                    extractor_version="ingest-v2",
                ))
        if cache:
            cache.set_file(cache_key, {
                "checksum": checksum,
                "document_id": document.id,
                "entities": extracted_entities,
                "updated": now_iso(),
            })
        self._refresh_metadata()
        return {"path": relative, "updated": True, "entities": extracted_entities, "document_id": document.id}

    def ingest_url(self, url: str, cache: Optional[IngestCache] = None, update: bool = True) -> Dict:
        if cache:
            cached = cache.get_url(url)
            if update and cached.get("etag"):
                pass
        content = safe_fetch_url(url, max_bytes=10_485_760, timeout=20)
        text = content.decode("utf-8", errors="ignore")
        checksum = sha256_bytes(content)
        document = self.upsert_entity(
            name=url,
            entity_type="Document",
            entity_id=f"url-{slugify(url)}",
            description=f"来源 URL：{url}",
            summary=trim_text(text, 120),
            attributes={"url": url, "checksum": checksum, "modality": "web"},
            aliases=[url],
            layer="warm",
        )
        extracted_entities = []
        for item in self._extract_terms_from_text(text, ".md"):
            entity = self.upsert_entity(
                name=item["name"],
                entity_type=item["type"],
                description=item.get("description", ""),
                source_ids=[document.id],
                confidence=item.get("confidence", 0.7),
            )
            extracted_entities.append(entity.id)
            self.add_relation(Relation(
                from_id=document.id,
                to_id=entity.id,
                type="mentions",
                evidence=item.get("evidence", entity.name),
                status="INFERRED" if item["type"] in {"Gap", "Claim"} else "EXTRACTED",
                confidence=item.get("confidence", 0.7),
                source_span=item.get("evidence", entity.name),
                source_document=document.id,
                extractor_version="web-ingest-v1",
            ))
        if cache:
            cache.set_url(url, {
                "checksum": checksum,
                "document_id": document.id,
                "entities": extracted_entities,
                "updated": now_iso(),
            })
        self._refresh_metadata()
        return {"url": url, "updated": True, "entities": extracted_entities, "document_id": document.id}

    def ingest_path(self, root_dir: str, update: bool = True) -> Dict:
        root = Path(root_dir)
        cache = IngestCache(CACHE_DIR / f"{slugify(self.topic)}_ingest_cache.json")
        results = {"processed": 0, "updated": 0, "skipped": 0, "files": []}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in DEFAULT_IGNORES for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS | MEDIA_EXTENSIONS:
                continue
            result = self.ingest_file(str(path), root_dir=str(root), cache=cache, update=update)
            results["processed"] += 1
            if result.get("updated"):
                results["updated"] += 1
            else:
                results["skipped"] += 1
            results["files"].append(result)
        cache.save()
        self.save()
        return results

    def _adjacency(self) -> Dict[str, List[Tuple[str, Relation]]]:
        adjacency: Dict[str, List[Tuple[str, Relation]]] = defaultdict(list)
        for edge in self.edges:
            if edge.from_id not in self.entities or edge.to_id not in self.entities:
                continue
            adjacency[edge.from_id].append((edge.to_id, edge))
            adjacency[edge.to_id].append((edge.from_id, edge))
        return adjacency

    def shortest_path(self, start: str, end: str, max_hops: int = 8) -> Dict:
        start_entity = self.find_entity(name=start) or self.find_entity(entity_id=start)
        end_entity = self.find_entity(name=end) or self.find_entity(entity_id=end)
        if not start_entity or not end_entity:
            return {"found": False, "reason": "节点不存在"}
        adjacency = self._adjacency()
        queue = deque([(start_entity.id, [start_entity.id])])
        visited = {start_entity.id}
        while queue:
            current, path = queue.popleft()
            if current == end_entity.id:
                resolved = [self.entities[node_id].name for node_id in path]
                hops = len(path) - 1
                if hops > max_hops:
                    return {"found": False, "reason": f"路径超过最大跳数 {max_hops}", "hops": hops}
                segments = []
                for index in range(len(path) - 1):
                    source_id = path[index]
                    target_id = path[index + 1]
                    matched = None
                    for edge in self.edges:
                        if {edge.from_id, edge.to_id} == {source_id, target_id}:
                            matched = edge
                            break
                    if matched:
                        segments.append({
                            "from": self.entities[source_id].name,
                            "to": self.entities[target_id].name,
                            "relation": matched.type,
                            "status": matched.status,
                            "confidence": matched.confidence,
                        })
                return {"found": True, "path_ids": path, "path_names": resolved, "hops": hops, "segments": segments}
            for neighbor, _ in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return {"found": False, "reason": "无连接路径"}

    def explain(self, target: str, limit: int = 10) -> Dict:
        entity = self.find_entity(name=target) or self.find_entity(entity_id=target)
        if not entity:
            return {"found": False}
        neighbors = []
        for edge in self.edges:
            if edge.from_id == entity.id and edge.to_id in self.entities:
                neighbors.append({"relation": edge.type, "target": self.entities[edge.to_id].name, "status": edge.status, "confidence": edge.confidence})
            elif edge.to_id == entity.id and edge.from_id in self.entities:
                neighbors.append({"relation": edge.type, "target": self.entities[edge.from_id].name, "status": edge.status, "confidence": edge.confidence})
        degree = len(neighbors)
        return {
            "found": True,
            "entity": entity.to_dict(),
            "degree": degree,
            "neighbors": sorted(neighbors, key=lambda item: (item["confidence"], item["target"]), reverse=True)[:limit],
        }

    def _weighted_degree_map(self, adjacency: Optional[Dict[str, List[Tuple[str, Relation]]]] = None) -> Dict[str, float]:
        adjacency = adjacency or self._adjacency()
        scores = {}
        for entity_id, neighbors in adjacency.items():
            total = 0.0
            for _, edge in neighbors:
                weight = max(0.2, edge.confidence)
                weight += {"EXTRACTED": 0.35, "INFERRED": 0.2, "AMBIGUOUS": 0.1}.get(edge.status, 0.1)
                if edge.type in {"summarizes", "mentions", "records"}:
                    weight *= 0.45
                total += weight
            scores[entity_id] = round(total, 3)
        return scores

    def _bounded_distances(self, start_id: str, allowed: set, adjacency: Dict[str, List[Tuple[str, Relation]]]) -> Dict[str, int]:
        distances = {start_id: 0}
        queue = deque([start_id])
        while queue:
            current = queue.popleft()
            for neighbor, _ in adjacency.get(current, []):
                if neighbor not in allowed or neighbor in distances:
                    continue
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
        return distances

    def _split_large_group(self, members: List[str], adjacency: Dict[str, List[Tuple[str, Relation]]], max_size: int) -> List[List[str]]:
        if len(members) <= max_size:
            return [members]
        allowed = set(members)
        local_degree = {
            member: sum(1 for neighbor, _ in adjacency.get(member, []) if neighbor in allowed)
            for member in members
        }
        seed_count = max(2, ceil(len(members) / max_size))
        ordered = sorted(members, key=lambda item: (-local_degree[item], self.entities[item].name.lower(), item))
        seeds = ordered[:seed_count]
        assignments = {seed: [seed] for seed in seeds}
        distance_maps = {seed: self._bounded_distances(seed, allowed, adjacency) for seed in seeds}
        for member in members:
            if member in assignments:
                continue
            ranked = []
            for index, seed in enumerate(seeds):
                ranked.append((
                    distance_maps[seed].get(member, 10_000),
                    len(assignments[seed]),
                    -local_degree[seed],
                    index,
                    seed,
                ))
            chosen = sorted(ranked)[0][-1]
            assignments.setdefault(chosen, []).append(member)
        subgroups = [sorted(nodes, key=lambda item: (-local_degree[item], self.entities[item].name.lower(), item)) for nodes in assignments.values() if nodes]
        if len(subgroups) == 1 and len(subgroups[0]) == len(members):
            return [ordered[index:index + max_size] for index in range(0, len(ordered), max_size)]
        flattened = []
        for group in subgroups:
            if len(group) > max_size and len(group) < len(members):
                flattened.extend(self._split_large_group(group, adjacency, max_size))
            else:
                flattened.append(group)
        return flattened

    def _partition_communities(self, adjacency: Dict[str, List[Tuple[str, Relation]]]) -> List[List[str]]:
        labels = {entity_id: entity_id for entity_id in self.entities}
        degrees = {entity_id: len(adjacency.get(entity_id, [])) for entity_id in self.entities}
        ordered = sorted(self.entities, key=lambda item: (-degrees[item], self.entities[item].name.lower(), item))
        for _ in range(24):
            changed = 0
            for entity_id in ordered:
                votes = Counter()
                for neighbor, edge in adjacency.get(entity_id, []):
                    weight = max(0.2, edge.confidence)
                    weight += {"EXTRACTED": 0.35, "INFERRED": 0.2, "AMBIGUOUS": 0.1}.get(edge.status, 0.1)
                    if self.entities[neighbor].type == self.entities[entity_id].type:
                        weight += 0.25
                    if edge.type in {"summarizes", "mentions", "records"}:
                        weight *= 0.45
                    votes[labels[neighbor]] += weight
                if not votes:
                    continue
                best_label = sorted(votes.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), item[0]))[0][0]
                if best_label != labels[entity_id]:
                    labels[entity_id] = best_label
                    changed += 1
            if not changed:
                break
        grouped = defaultdict(list)
        for entity_id, label in labels.items():
            grouped[label].append(entity_id)
        max_size = max(12, int(max(1, len(self.entities)) * 0.28))
        communities = []
        for members in grouped.values():
            ordered_members = sorted(members, key=lambda item: (-degrees[item], self.entities[item].name.lower(), item))
            communities.extend(self._split_large_group(ordered_members, adjacency, max_size))
        return communities

    def _community_lookup(self) -> Dict[str, str]:
        lookup = {}
        for community in self.communities:
            for member in community.get("members", []):
                lookup[member] = community["id"]
        return lookup

    def graph_stats(self) -> Dict:
        if not self.communities:
            self.compute_communities()
        confidence = Counter(edge.status for edge in self.edges)
        layer_counts = Counter(entity.layer for entity in self.entities.values())
        type_counts = Counter(canonicalize_entity_type(entity.type) for entity in self.entities.values())
        degree_map = self._weighted_degree_map()
        avg_degree = round(sum(degree_map.values()) / max(1, len(degree_map)), 2)
        return {
            "topic": self.topic,
            "entities": len(self.entities),
            "edges": len(self.edges),
            "communities": len(self.communities),
            "documents": self.metadata.get("document_count", 0),
            "papers": len([entity for entity in self.entities.values() if canonicalize_entity_type(entity.type) == "Paper"]),
            "layers": dict(layer_counts),
            "entity_types": dict(type_counts),
            "confidence": dict(confidence),
            "avg_weighted_degree": avg_degree,
            "updated": self.metadata.get("updated"),
        }

    def god_nodes(self, top_n: int = 10) -> List[Dict]:
        if not self.communities:
            self.compute_communities()
        adjacency = self._adjacency()
        weights = self._weighted_degree_map(adjacency)
        community_lookup = self._community_lookup()
        excluded_types = {"Document", "CommunitySummary", "ResearchSession"}
        ranked = []
        for entity in self.entities.values():
            if entity.type in excluded_types:
                continue
            neighbors = adjacency.get(entity.id, [])
            if not neighbors:
                continue
            bridge_count = len({
                community_lookup.get(neighbor)
                for neighbor, _ in neighbors
                if community_lookup.get(neighbor) and community_lookup.get(neighbor) != community_lookup.get(entity.id)
            })
            score = weights.get(entity.id, 0.0) + bridge_count * 1.5 + (1.0 if entity.layer == "hot" else 0.0)
            ranked.append((score, entity, bridge_count))
        result = []
        for score, entity, bridge_count in sorted(ranked, key=lambda item: item[0], reverse=True)[:top_n]:
            result.append({
                "id": entity.id,
                "label": entity.name,
                "type": entity.type,
                "score": round(score, 3),
                "bridges": bridge_count,
                "layer": entity.layer,
                "degree": round(weights.get(entity.id, 0.0), 3),
            })
        return result

    def surprising_connections(self, top_n: int = 5) -> List[Dict]:
        if not self.communities:
            self.compute_communities()
        adjacency = self._adjacency()
        weights = self._weighted_degree_map(adjacency)
        community_lookup = self._community_lookup()
        results = []
        excluded_types = {"Document", "CommunitySummary"}
        skipped_relations = {"mentions", "summarizes", "records"}
        for edge in self.edges:
            source = self.entities.get(edge.from_id)
            target = self.entities.get(edge.to_id)
            if not source or not target:
                continue
            if source.type in excluded_types or target.type in excluded_types:
                continue
            if edge.type in skipped_relations:
                continue
            score = 0.0
            reasons = []
            if edge.status == "AMBIGUOUS":
                score += 3
                reasons.append("关系状态为 AMBIGUOUS")
            elif edge.status == "INFERRED":
                score += 2
                reasons.append("关系状态为 INFERRED")
            else:
                score += 1
            if source.type != target.type:
                score += 2
                reasons.append(f"跨类型 {source.type}→{target.type}")
            if community_lookup.get(source.id) != community_lookup.get(target.id):
                score += 1.5
                reasons.append("跨社区连接")
            if source.layer != target.layer:
                score += 1
                reasons.append(f"跨层级 {source.layer}→{target.layer}")
            low = min(weights.get(source.id, 0.0), weights.get(target.id, 0.0))
            high = max(weights.get(source.id, 0.0), weights.get(target.id, 0.0))
            if low <= 2.0 and high >= 5.0:
                score += 1
                reasons.append("边缘节点连接核心节点")
            if score <= 1:
                continue
            results.append({
                "source": source.name,
                "target": target.name,
                "relation": edge.type,
                "status": edge.status,
                "confidence": edge.confidence,
                "score": round(score, 3),
                "why": "；".join(reasons),
            })
        return sorted(results, key=lambda item: (item["score"], item["confidence"]), reverse=True)[:top_n]

    def get_neighbors(self, target: str, relation_filter: str = "", limit: int = 20) -> Dict:
        entity = self.find_entity(name=target) or self.find_entity(entity_id=target)
        if not entity:
            return {"found": False, "reason": "节点不存在"}
        relation_filter = relation_filter.lower().strip()
        results = []
        for edge in self.edges:
            neighbor = None
            if edge.from_id == entity.id and edge.to_id in self.entities:
                neighbor = self.entities[edge.to_id]
            elif edge.to_id == entity.id and edge.from_id in self.entities:
                neighbor = self.entities[edge.from_id]
            if not neighbor:
                continue
            if relation_filter and relation_filter not in edge.type.lower():
                continue
            results.append({
                "target": neighbor.name,
                "target_id": neighbor.id,
                "type": neighbor.type,
                "relation": edge.type,
                "status": edge.status,
                "confidence": edge.confidence,
                "layer": neighbor.layer,
            })
        ordered = sorted(results, key=lambda item: (item["confidence"], item["target"]), reverse=True)[:limit]
        return {"found": True, "entity": entity.name, "count": len(ordered), "neighbors": ordered}

    def get_community(self, community_id: str, limit: int = 25) -> Dict:
        if not self.communities:
            self.compute_communities()
        wanted = str(community_id).strip()
        selected = None
        for community in self.communities:
            if community["id"] == wanted or community["id"].split("-")[-1] == wanted:
                selected = community
                break
        if not selected:
            return {"found": False, "reason": f"社区不存在: {community_id}"}
        members = []
        adjacency = self._adjacency()
        for member_id in selected["members"][:limit]:
            entity = self.entities.get(member_id)
            if not entity:
                continue
            members.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "layer": entity.layer,
                "degree": len(adjacency.get(entity.id, [])),
            })
        return {
            "found": True,
            "community": {
                "id": selected["id"],
                "size": selected["size"],
                "labels": selected["labels"],
                "dominant_types": selected["dominant_types"],
                "members": members,
            },
        }

    def query_graph(self, question: str, mode: str = "bfs", depth: int = 2, token_budget: int = 1600, top_k: int = 4) -> Dict:
        ranked = self.rank_entities(question, limit=max(1, top_k))
        if not ranked:
            return {
                "question": question,
                "mode": mode,
                "depth": depth,
                "start_nodes": [],
                "nodes": [],
                "edges": [],
                "rendered_context": "",
                "reason": "没有匹配节点",
            }
        adjacency = self._adjacency()
        start_nodes = [entity.id for _, entity in ranked[:top_k]]
        queue = deque((node_id, 0) for node_id in start_nodes) if mode != "dfs" else None
        stack = [(node_id, 0) for node_id in reversed(start_nodes)] if mode == "dfs" else None
        visited_depth = {node_id: 0 for node_id in start_nodes}
        traversed_edges = []
        while (queue and mode != "dfs") or (stack and mode == "dfs"):
            current, current_depth = (stack.pop() if mode == "dfs" else queue.popleft())
            if current_depth >= depth:
                continue
            for neighbor, edge in adjacency.get(current, []):
                next_depth = current_depth + 1
                if neighbor not in visited_depth or next_depth < visited_depth[neighbor]:
                    visited_depth[neighbor] = next_depth
                    if mode == "dfs":
                        stack.append((neighbor, next_depth))
                    else:
                        queue.append((neighbor, next_depth))
                traversed_edges.append((current, neighbor, edge))
        selected_nodes = set(visited_depth)
        unique_edges = {}
        for source_id, target_id, edge in traversed_edges:
            if source_id not in selected_nodes or target_id not in selected_nodes:
                continue
            edge_key = tuple(sorted([source_id, target_id]) + [edge.type, edge.status])
            unique_edges[edge_key] = {
                "from_id": source_id,
                "to_id": target_id,
                "from": self.entities[source_id].name,
                "to": self.entities[target_id].name,
                "relation": edge.type,
                "status": edge.status,
                "confidence": edge.confidence,
            }
        node_rank = []
        for entity_id in selected_nodes:
            entity = self.entities[entity_id]
            query_score = next((score for score, candidate in ranked if candidate.id == entity_id), 0.0)
            score = query_score + max(0, depth - visited_depth.get(entity_id, depth)) + (1 if entity.layer == "hot" else 0)
            node_rank.append((score, entity))
        rendered_lines = []
        used_budget = 0
        for _, entity in sorted(node_rank, key=lambda item: item[0], reverse=True):
            line = f"NODE [{entity.type}] {entity.name} (layer={entity.layer}, community={entity.attributes.get('community_id', '')})"
            cost = max(16, len(line) // 2)
            if used_budget + cost > token_budget:
                break
            rendered_lines.append(line)
            used_budget += cost
        for edge_data in sorted(unique_edges.values(), key=lambda item: item["confidence"], reverse=True):
            line = f"EDGE {edge_data['from']} --{edge_data['relation']} [{edge_data['status']} {edge_data['confidence']:.2f}]--> {edge_data['to']}"
            cost = max(14, len(line) // 2)
            if used_budget + cost > token_budget:
                break
            rendered_lines.append(line)
            used_budget += cost
        ordered_nodes = [entity.to_dict() for _, entity in sorted(node_rank, key=lambda item: item[0], reverse=True)]
        return {
            "question": question,
            "mode": mode,
            "depth": depth,
            "token_budget": token_budget,
            "used_budget": used_budget,
            "start_nodes": [self.entities[node_id].name for node_id in start_nodes],
            "nodes": ordered_nodes,
            "edges": list(unique_edges.values()),
            "rendered_context": "\n".join(rendered_lines),
        }

    def compute_communities(self) -> List[Dict]:
        adjacency = self._adjacency()
        communities = []
        weights = self._weighted_degree_map(adjacency)
        groups = self._partition_communities(adjacency) if adjacency else [[entity_id] for entity_id in self.entities]
        ordered_groups = sorted(groups, key=lambda members: (len(members), sum(weights.get(member, 0.0) for member in members)), reverse=True)
        for members in ordered_groups:
            type_counter = Counter(self.entities[member].type for member in members if member in self.entities)
            ranked = sorted(members, key=lambda member: (weights.get(member, 0.0), self.entities[member].name.lower()), reverse=True)
            cohesion_total = 0.0
            internal_edges = 0
            member_set = set(members)
            for member in members:
                for neighbor, edge in adjacency.get(member, []):
                    if neighbor in member_set:
                        cohesion_total += max(0.2, edge.confidence)
                        internal_edges += 1
            community = {
                "id": f"community-{len(communities) + 1}",
                "size": len(members),
                "members": members,
                "labels": [self.entities[member].name for member in ranked[:5]],
                "dominant_types": dict(type_counter.most_common(5)),
                "god_nodes": ranked[:5],
                "cohesion": round(cohesion_total / max(1, internal_edges), 3),
            }
            for member in members:
                self.entities[member].attributes["community_id"] = community["id"]
                self.entities[member].attributes["community_rank"] = len(communities) + 1
                self.entities[member].attributes["community_cohesion"] = community["cohesion"]
            communities.append(community)
        self.communities = sorted(communities, key=lambda item: item["size"], reverse=True)
        self.summaries = [{
            "community_id": community["id"],
            "summary": f"{', '.join(community['labels'][:3])} 形成 {community['size']} 节点社区，凝聚度 {community.get('cohesion', 0):.2f}",
            "labels": community["labels"],
            "cohesion": community.get("cohesion", 0),
        } for community in self.communities]
        self._refresh_metadata()
        return self.communities

    def generate_graph_report(self) -> str:
        if not self.communities:
            self.compute_communities()
        stats = self.graph_stats()
        god_nodes = self.god_nodes(top_n=5)
        surprising = self.surprising_connections(top_n=5)
        lines = [
            f"# {self.topic} 图谱报告",
            "",
            f"- 实体数：{stats['entities']}",
            f"- 关系数：{stats['edges']}",
            f"- 社区数：{stats['communities']}",
            f"- 文档数：{stats['documents']}",
            f"- 平均加权度：{stats['avg_weighted_degree']}",
            "",
            "## God Nodes",
        ]
        lines.extend([f"- {item['label']} [{item['type']}] score={item['score']} bridges={item['bridges']}" for item in god_nodes] or ["- 暂无"])
        lines.extend(["", "## Communities"])
        for community in self.communities[:5]:
            lines.append(f"- {community['id']}: {', '.join(community['labels'][:4])} ({community['size']} 节点, cohesion={community.get('cohesion', 0):.2f})")
        lines.extend(["", "## Surprising Connections"])
        lines.extend([
            f"- {item['source']} --{item['relation']}/{item['status']}--> {item['target']} ({item['why']})"
            for item in surprising
        ] or ["- 暂无"])
        return "\n".join(lines)

    def refresh_views(self) -> Dict:
        communities = self.compute_communities()
        summary_nodes = self.create_summary_nodes()
        layers = self.assign_layers()
        self.save()
        return {
            "communities": len(communities),
            "summary_nodes": len(summary_nodes),
            "layers": layers,
        }

    def collect_layer_buckets(self) -> Dict[str, List[Dict]]:
        buckets = {"hot": [], "warm": [], "cold": []}
        for entity in self.entities.values():
            buckets.setdefault(entity.layer, []).append(entity.to_dict())
        for layer in buckets:
            buckets[layer] = sorted(
                buckets[layer],
                key=lambda item: (
                    item.get("attributes", {}).get("score", 0),
                    item.get("updated", ""),
                    item.get("confidence", 0),
                ),
                reverse=True,
            )
        return buckets

    def project_context(self, task_type: str, query: str = "", budget: int = 1600, mode: str = "bfs", depth: Optional[int] = None) -> Dict:
        type_weights = {
            "search": {"Pattern": 4, "Lesson": 3, "Methodology": 3, "Gap": 2, "Document": 1, "Paper": 1, "concept": 1},
            "analysis": {"Paper": 4, "Claim": 4, "Methodology": 3, "method": 3, "Gap": 3, "Lesson": 2, "Pattern": 2, "concept": 1},
            "report": {"CommunitySummary": 4, "Claim": 3, "Methodology": 3, "Gap": 3, "Lesson": 2, "Pattern": 2, "Paper": 2},
            "default": {"Lesson": 3, "Pattern": 3, "Methodology": 2, "Gap": 2, "Document": 1, "Paper": 1, "concept": 1},
        }
        weights = type_weights.get(task_type, type_weights["default"])
        query = query or self.topic
        tokens = expand_search_terms(query)
        depth = depth if depth is not None else {"search": 1, "analysis": 2, "report": 2, "default": 2}.get(task_type, 2)
        graph_slice = self.query_graph(query, mode=mode, depth=depth, token_budget=max(320, budget // 2), top_k=4)
        traversed_ids = {item["id"] for item in graph_slice.get("nodes", [])}
        ranked = []
        for entity in self.entities.values():
            entity_type = canonicalize_entity_type(entity.type)
            score = weights.get(entity_type, weights.get(entity.type, 0))
            if score <= 0 and entity.type not in PRIMARY_ENTITY_TYPES:
                continue
            text = " ".join([entity.name, entity.description, entity.summary]).lower()
            score += sum(2 for token in tokens if token in entity.name.lower())
            score += sum(1 for token in tokens if token in text)
            score += round(text_similarity(query, entity.name) * 4, 2)
            if entity.id in traversed_ids:
                score += 3
            if entity.layer == "hot":
                score += 2
            if entity.attributes.get("community_id"):
                score += 1
            score += min(len(self.get_related_concepts(entity.id)), 4)
            if score > 0:
                ranked.append((score, entity))
        selected = []
        current_budget = 0
        for score, entity in sorted(ranked, key=lambda item: item[0], reverse=True):
            evidence_bits = []
            if entity.tags:
                evidence_bits.append(f"tags={','.join(entity.tags[:3])}")
            if entity.attributes.get("community_id"):
                evidence_bits.append(f"community={entity.attributes['community_id']}")
            if entity.source_ids:
                evidence_bits.append(f"source={','.join(entity.source_ids[:2])}")
            if entity.layer:
                evidence_bits.append(f"layer={entity.layer}")
            details = f" ({'; '.join(evidence_bits)})" if evidence_bits else ""
            snippet = f"[{canonicalize_entity_type(entity.type)}] {entity.name}: {trim_text(entity.summary or entity.description, 140)}{details}"
            cost = max(20, len(snippet) // 2)
            if current_budget + cost > budget:
                continue
            selected.append({"score": score, "entity": entity.to_dict(), "snippet": snippet})
            current_budget += cost
            if len(selected) >= 12:
                break
        prompt = "\n".join(item["snippet"] for item in selected)
        return {
            "task_type": task_type,
            "query": query,
            "budget": budget,
            "used_budget": current_budget,
            "items": selected,
            "prompt": prompt,
            "entity_types": dict(Counter(canonicalize_entity_type(item["entity"]["type"]) for item in selected)),
            "mode": mode,
            "depth": depth,
            "start_nodes": graph_slice.get("start_nodes", []),
            "graph_slice": graph_slice,
        }

    def assign_layers(self) -> Dict[str, int]:
        if not self.communities:
            self.compute_communities()
        adjacency = self._adjacency()
        counts = {"hot": 0, "warm": 0, "cold": 0}
        now = datetime.now()
        for entity in self.entities.values():
            updated = datetime.fromisoformat(entity.updated)
            age_days = (now - updated).days
            degree = len(adjacency.get(entity.id, []))
            if entity.type in {"Lesson", "Pattern", "Gap", "Claim", "ResearchSession"} or age_days <= 7:
                entity.layer = "hot"
            elif degree >= 3 or age_days <= 30:
                entity.layer = "warm"
            else:
                entity.layer = "cold"
            counts[entity.layer] += 1
        self._refresh_metadata()
        return counts

    def create_summary_nodes(self) -> List[str]:
        if not self.communities:
            self.compute_communities()
        created = []
        for community in self.communities[:10]:
            summary_text = (
                f"{', '.join(community['labels'][:4])} 构成主要主题，覆盖 {community['size']} 个节点，"
                f"凝聚度 {community.get('cohesion', 0):.2f}"
            )
            summary = self.upsert_entity(
                name=f"{community['id']} Summary",
                entity_type="CommunitySummary",
                entity_id=f"summary-{community['id']}",
                description=summary_text,
                summary=summary_text,
                attributes={"community_id": community["id"], "size": community["size"]},
                layer="warm",
                confidence=0.85,
            )
            created.append(summary.id)
            for member in community["members"][:15]:
                self.add_relation(Relation(
                    from_id=summary.id,
                    to_id=member,
                    type="summarizes",
                    evidence=summary_text,
                    status="INFERRED",
                    confidence=0.7,
                    extractor_version="summary-v1",
                ))
        self._refresh_metadata()
        return created

    def benchmark_context(self, questions: Optional[List[str]] = None, mode: str = "bfs", depth: int = 2, token_budget: int = 1600) -> Dict:
        if not self.entities:
            return {"error": "图谱为空"}
        corpus_lines = []
        for entity in self.entities.values():
            corpus_lines.append(f"{entity.type} {entity.name} {entity.summary or entity.description}")
        for edge in self.edges:
            if edge.from_id in self.entities and edge.to_id in self.entities:
                corpus_lines.append(
                    f"{self.entities[edge.from_id].name} --{edge.type}/{edge.status}--> {self.entities[edge.to_id].name}"
                )
        corpus_tokens = estimate_tokens("\n".join(corpus_lines))
        questions = questions or [
            f"{self.topic} 的核心方法是什么",
            f"{self.topic} 的关键知识缺口有哪些",
            f"{self.topic} 中最重要的概念如何关联",
        ]
        per_question = []
        for question in questions:
            result = self.query_graph(question, mode=mode, depth=depth, token_budget=token_budget)
            context_tokens = estimate_tokens(result.get("rendered_context", ""))
            if context_tokens <= 0:
                continue
            per_question.append({
                "question": question,
                "query_tokens": context_tokens,
                "reduction": round(corpus_tokens / max(1, context_tokens), 2),
                "start_nodes": result.get("start_nodes", []),
            })
        if not per_question:
            return {"error": "没有可评估的查询结果", "corpus_tokens": corpus_tokens}
        avg_query_tokens = sum(item["query_tokens"] for item in per_question) // len(per_question)
        return {
            "topic": self.topic,
            "corpus_tokens": corpus_tokens,
            "entities": len(self.entities),
            "edges": len(self.edges),
            "avg_query_tokens": avg_query_tokens,
            "reduction_ratio": round(corpus_tokens / max(1, avg_query_tokens), 2),
            "per_question": per_question,
        }

    def export_graphml(self, output_path: str) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not self.communities:
            self.compute_communities()
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '<key id="label" for="node" attr.name="label" attr.type="string"/>',
            '<key id="type" for="node" attr.name="type" attr.type="string"/>',
            '<key id="layer" for="node" attr.name="layer" attr.type="string"/>',
            '<key id="community" for="node" attr.name="community" attr.type="string"/>',
            '<key id="relation" for="edge" attr.name="relation" attr.type="string"/>',
            '<key id="status" for="edge" attr.name="status" attr.type="string"/>',
            '<key id="confidence" for="edge" attr.name="confidence" attr.type="double"/>',
            '<graph id="knowledge" edgedefault="undirected">',
        ]
        for entity in self.entities.values():
            lines.extend([
                f'<node id="{xml_escape(entity.id)}">',
                f'<data key="label">{xml_escape(entity.name)}</data>',
                f'<data key="type">{xml_escape(entity.type)}</data>',
                f'<data key="layer">{xml_escape(entity.layer)}</data>',
                f'<data key="community">{xml_escape(str(entity.attributes.get("community_id", "")))}</data>',
                '</node>',
            ])
        for index, edge in enumerate(self.edges, 1):
            if edge.from_id not in self.entities or edge.to_id not in self.entities:
                continue
            lines.extend([
                f'<edge id="e{index}" source="{xml_escape(edge.from_id)}" target="{xml_escape(edge.to_id)}">',
                f'<data key="relation">{xml_escape(edge.type)}</data>',
                f'<data key="status">{xml_escape(edge.status)}</data>',
                f'<data key="confidence">{edge.confidence:.4f}</data>',
                '</edge>',
            ])
        lines.extend(['</graph>', '</graphml>'])
        target.write_text("\n".join(lines), encoding="utf-8")
        return target

    def export_wiki(self, output_dir: str) -> Dict:
        if not self.communities:
            self.compute_communities()
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        god_nodes = self.god_nodes(top_n=10)
        index_lines = [
            f"# {self.topic} Knowledge Wiki",
            "",
            f"- 实体数：{len(self.entities)}",
            f"- 关系数：{len(self.edges)}",
            f"- 社区数：{len(self.communities)}",
            "",
            "## 社区导航",
            "",
        ]
        written = 0
        adjacency = self._adjacency()
        for community in self.communities:
            name = community["id"]
            filename = f"{safe_filename(name)}.md"
            page_lines = [
                f"# {name}",
                "",
                f"- 节点数：{community['size']}",
                f"- 凝聚度：{community.get('cohesion', 0):.2f}",
                f"- 标签：{', '.join(community['labels'][:5])}",
                "",
                "## 关键节点",
                "",
            ]
            for member_id in community["members"][:25]:
                entity = self.entities.get(member_id)
                if not entity:
                    continue
                page_lines.append(
                    f"- {entity.name} [{entity.type}] layer={entity.layer} degree={len(adjacency.get(entity.id, []))}"
                )
            (output / filename).write_text("\n".join(page_lines) + "\n", encoding="utf-8")
            index_lines.append(f"- [{name}]({filename})")
            written += 1
        if god_nodes:
            index_lines.extend(["", "## God Nodes", ""])
            for item in god_nodes:
                filename = f"{safe_filename(item['label'])}.md"
                neighbors = self.get_neighbors(item["id"], limit=20)
                page_lines = [
                    f"# {item['label']}",
                    "",
                    f"- 类型：{item['type']}",
                    f"- 分数：{item['score']}",
                    f"- 桥接数：{item['bridges']}",
                    "",
                    "## 连接",
                    "",
                ]
                for neighbor in neighbors.get("neighbors", []):
                    page_lines.append(
                        f"- {neighbor['target']} --{neighbor['relation']}/{neighbor['status']}--> confidence={neighbor['confidence']}"
                    )
                (output / filename).write_text("\n".join(page_lines) + "\n", encoding="utf-8")
                index_lines.append(f"- [{item['label']}]({filename})")
                written += 1
        (output / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        return {"written": written, "output_dir": str(output)}

    def watch(self, root_dir: str, interval: float = 5.0, cycles: int = 0, update: bool = True) -> Dict:
        root = Path(root_dir)
        snapshot = {}
        for path in root.rglob("*"):
            if path.is_file() and not any(part in DEFAULT_IGNORES for part in path.parts):
                snapshot[str(path)] = path.stat().st_mtime
        checks = 0
        updates = 0
        while cycles <= 0 or checks < cycles:
            checks += 1
            time.sleep(max(0.1, interval))
            changed = False
            new_snapshot = {}
            for path in root.rglob("*"):
                if not path.is_file() or any(part in DEFAULT_IGNORES for part in path.parts):
                    continue
                new_snapshot[str(path)] = path.stat().st_mtime
                if snapshot.get(str(path)) != new_snapshot[str(path)]:
                    changed = True
            removed = set(snapshot) - set(new_snapshot)
            if removed:
                changed = True
            snapshot = new_snapshot
            if changed:
                self.ingest_path(str(root), update=update)
                self.refresh_views()
                self.save()
                updates += 1
        return {"watch_path": str(root), "checks": checks, "updates": updates}

    def to_dict(self) -> Dict:
        self._refresh_metadata()
        return {
            "topic": self.topic,
            "metadata": self.metadata,
            "entities": [entity.to_dict() for entity in self.entities.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "concepts": [entity.to_dict() for entity in self.entities.values() if entity.type in PRIMARY_ENTITY_TYPES],
            "relations": [edge.to_dict() for edge in self.edges],
            "insights": self.insights,
            "communities": self.communities,
            "summaries": self.summaries,
            "alias_index": self.alias_index,
        }

    def save(self, filepath: Optional[str] = None):
        target = Path(filepath) if filepath else self.graph_path
        target.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path = target
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return target

    @classmethod
    def load(cls, filepath: str) -> "KnowledgeGraph":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        graph = cls(data.get("topic", Path(filepath).stem), graph_path=Path(filepath))
        graph.metadata.update(data.get("metadata", {}))
        graph.insights.update(data.get("insights", {}))
        graph.communities = data.get("communities", [])
        graph.summaries = data.get("summaries", [])
        if data.get("entities"):
            for entity_data in data.get("entities", []):
                entity = Entity.from_dict(entity_data)
                graph.entities[entity.id] = entity
                graph._register_aliases(entity)
            for edge_data in data.get("edges", data.get("relations", [])):
                graph.edges.append(Relation.from_dict(edge_data))
        else:
            for concept_data in data.get("concepts", []):
                entity = Entity(
                    id=concept_data["id"],
                    name=concept_data["name"],
                    type=concept_data.get("type", "concept"),
                    description=concept_data.get("description", ""),
                    summary=trim_text(concept_data.get("description", ""), 180),
                    papers=concept_data.get("papers", []),
                    parent=concept_data.get("parent"),
                    children=concept_data.get("children", []),
                    attributes=concept_data.get("attributes", {}),
                    layer=concept_data.get("layer", "warm"),
                )
                graph.entities[entity.id] = entity
                graph._register_aliases(entity)
            for relation_data in data.get("relations", []):
                graph.edges.append(Relation.from_dict(relation_data))
        graph.alias_index.update(data.get("alias_index", {}))
        graph._refresh_metadata()
        return graph


def get_or_create_graph(topic: str, base_dir: Optional[Path] = None, filename: Optional[str] = None) -> KnowledgeGraph:
    target_dir = Path(base_dir) if base_dir else GRAPHS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (filename or f"{topic.replace(' ', '_')}_knowledge_graph.json")
    if target.exists():
        return KnowledgeGraph.load(str(target))
    return KnowledgeGraph(topic, graph_path=target)


def merge_graphs(graph1: KnowledgeGraph, graph2: KnowledgeGraph) -> KnowledgeGraph:
    for entity in graph2.entities.values():
        graph1.add_entity(Entity.from_dict(entity.to_dict()))
    for edge in graph2.edges:
        if edge.from_id in graph1.entities and edge.to_id in graph1.entities:
            graph1.add_relation(Relation.from_dict(edge.to_dict()))
    for key, values in graph2.insights.items():
        graph1.insights.setdefault(key, [])
        graph1.insights[key] = list(dict.fromkeys(graph1.insights[key] + values))
    graph1.compute_communities()
    graph1.assign_layers()
    return graph1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="知识图谱管理")
    sub = parser.add_subparsers(dest="cmd")

    stats = sub.add_parser("stats", help="显示统计信息")
    stats.add_argument("--topic", "-t", required=True)

    ingest = sub.add_parser("ingest", help="导入目录")
    ingest.add_argument("--topic", "-t", required=True)
    ingest.add_argument("--path", "-p", required=True)
    ingest.add_argument("--full", action="store_true")

    add_url = sub.add_parser("add-url", help="导入 URL")
    add_url.add_argument("--topic", "-t", required=True)
    add_url.add_argument("--url", required=True)

    query = sub.add_parser("query", help="搜索实体")
    query.add_argument("--topic", "-t", required=True)
    query.add_argument("--text", required=True)

    path = sub.add_parser("path", help="查询最短路径")
    path.add_argument("--topic", "-t", required=True)
    path.add_argument("--from-node", required=True)
    path.add_argument("--to-node", required=True)
    path.add_argument("--max-hops", type=int, default=8)

    explain = sub.add_parser("explain", help="解释节点")
    explain.add_argument("--topic", "-t", required=True)
    explain.add_argument("--target", required=True)

    neighbors = sub.add_parser("neighbors", help="查看邻居节点")
    neighbors.add_argument("--topic", "-t", required=True)
    neighbors.add_argument("--target", required=True)
    neighbors.add_argument("--relation", default="")
    neighbors.add_argument("--limit", type=int, default=20)

    community = sub.add_parser("community", help="查看社区详情")
    community.add_argument("--topic", "-t", required=True)
    community.add_argument("--community-id", required=True)
    community.add_argument("--limit", type=int, default=25)

    navigate = sub.add_parser("navigate", help="按图谱导航查询")
    navigate.add_argument("--topic", "-t", required=True)
    navigate.add_argument("--text", required=True)
    navigate.add_argument("--mode", choices=["bfs", "dfs"], default="bfs")
    navigate.add_argument("--depth", type=int, default=2)
    navigate.add_argument("--budget", type=int, default=1600)
    navigate.add_argument("--top-k", type=int, default=4)

    report = sub.add_parser("report", help="生成图谱报告")
    report.add_argument("--topic", "-t", required=True)

    refresh = sub.add_parser("refresh", help="刷新社区、摘要与分层")
    refresh.add_argument("--topic", "-t", required=True)

    project = sub.add_parser("project", help="生成 query-time 上下文投影")
    project.add_argument("--topic", "-t", required=True)
    project.add_argument("--task-type", default="default", choices=["search", "analysis", "report", "default"])
    project.add_argument("--query", default="")
    project.add_argument("--budget", type=int, default=1600)
    project.add_argument("--mode", choices=["bfs", "dfs"], default="bfs")
    project.add_argument("--depth", type=int)

    benchmark = sub.add_parser("benchmark", help="评估图谱上下文压缩收益")
    benchmark.add_argument("--topic", "-t", required=True)
    benchmark.add_argument("--question", nargs="*")
    benchmark.add_argument("--mode", choices=["bfs", "dfs"], default="bfs")
    benchmark.add_argument("--depth", type=int, default=2)
    benchmark.add_argument("--budget", type=int, default=1600)

    export = sub.add_parser("export", help="导出图谱")
    export.add_argument("--topic", "-t", required=True)
    export.add_argument("--format", choices=["graphml", "wiki"], required=True)
    export.add_argument("--output", required=True)

    god_nodes = sub.add_parser("god-nodes", help="查看图谱核心桥接节点")
    god_nodes.add_argument("--topic", "-t", required=True)
    god_nodes.add_argument("--limit", type=int, default=10)

    surprising = sub.add_parser("surprising", help="查看意外连接")
    surprising.add_argument("--topic", "-t", required=True)
    surprising.add_argument("--limit", type=int, default=5)

    watch = sub.add_parser("watch", help="监控目录变化并增量刷新图谱")
    watch.add_argument("--topic", "-t", required=True)
    watch.add_argument("--path", "-p", required=True)
    watch.add_argument("--interval", type=float, default=5.0)
    watch.add_argument("--cycles", type=int, default=0)

    validate = sub.add_parser("validate", help="验证图谱")
    validate.add_argument("--topic", "-t", required=True)

    return parser


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        raise SystemExit(0)

    resolved_topic, graph_dir, graph_filename = resolve_graph_location(args.topic)
    graph = get_or_create_graph(resolved_topic, base_dir=graph_dir, filename=graph_filename)

    if args.cmd == "stats":
        graph.compute_communities()
        print(json.dumps(graph.graph_stats(), ensure_ascii=False, indent=2))
    elif args.cmd == "ingest":
        result = graph.ingest_path(args.path, update=not args.full)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "add-url":
        cache = IngestCache(CACHE_DIR / f"{slugify(graph.topic)}_ingest_cache.json")
        result = graph.ingest_url(args.url, cache=cache)
        cache.save()
        graph.save()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "query":
        results = [entity.to_dict() for entity in graph.search_entities(args.text)]
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.cmd == "path":
        print(json.dumps(graph.shortest_path(args.from_node, args.to_node, max_hops=args.max_hops), ensure_ascii=False, indent=2))
    elif args.cmd == "explain":
        print(json.dumps(graph.explain(args.target), ensure_ascii=False, indent=2))
    elif args.cmd == "neighbors":
        print(json.dumps(graph.get_neighbors(args.target, relation_filter=args.relation, limit=args.limit), ensure_ascii=False, indent=2))
    elif args.cmd == "community":
        print(json.dumps(graph.get_community(args.community_id, limit=args.limit), ensure_ascii=False, indent=2))
    elif args.cmd == "navigate":
        print(json.dumps(graph.query_graph(args.text, mode=args.mode, depth=args.depth, token_budget=args.budget, top_k=args.top_k), ensure_ascii=False, indent=2))
    elif args.cmd == "report":
        graph.compute_communities()
        graph.create_summary_nodes()
        graph.assign_layers()
        graph.save()
        print(graph.generate_graph_report())
    elif args.cmd == "refresh":
        print(json.dumps(graph.refresh_views(), ensure_ascii=False, indent=2))
    elif args.cmd == "project":
        print(json.dumps(graph.project_context(args.task_type, args.query, args.budget, mode=args.mode, depth=args.depth), ensure_ascii=False, indent=2))
    elif args.cmd == "benchmark":
        print(json.dumps(graph.benchmark_context(args.question, mode=args.mode, depth=args.depth, token_budget=args.budget), ensure_ascii=False, indent=2))
    elif args.cmd == "export":
        if args.format == "graphml":
            result = {"path": str(graph.export_graphml(args.output))}
        else:
            result = graph.export_wiki(args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "god-nodes":
        print(json.dumps(graph.god_nodes(top_n=args.limit), ensure_ascii=False, indent=2))
    elif args.cmd == "surprising":
        print(json.dumps(graph.surprising_connections(top_n=args.limit), ensure_ascii=False, indent=2))
    elif args.cmd == "watch":
        print(json.dumps(graph.watch(args.path, interval=args.interval, cycles=args.cycles), ensure_ascii=False, indent=2))
    elif args.cmd == "validate":
        print(json.dumps(graph.validate(), ensure_ascii=False, indent=2))
