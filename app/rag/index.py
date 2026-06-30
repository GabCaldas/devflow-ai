"""Dependency-free local retrieval for source-code repositories."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".json", ".jsx", ".kt", ".md", ".php", ".py",
    ".rb", ".rs", ".sh", ".sql", ".toml", ".ts", ".tsx", ".vue",
    ".xml", ".yaml", ".yml",
}
SUPPORTED_NAMES = {"Dockerfile", "Makefile"}
IGNORED_DIRS = {
    ".git", ".idea", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv",
    ".vscode", "__pycache__", "build", "dist", "node_modules", "vendor",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,}|\d+")
DIFF_PATH_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class CodeChunk:
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class RetrievedChunk(CodeChunk):
    score: float

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "score": round(self.score, 4),
        }


def _tokens(text: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(expanded.lower()):
        tokens.extend(part for part in raw.split("_") if len(part) > 1)
    return tokens


def _hashed_embedding(tokens: list[str], dimensions: int = 512) -> list[float]:
    """Create a stable, local feature-hashing vector without an API or model."""
    vector = [0.0] * dimensions
    features = tokens + [f"{a}:{b}" for a, b in zip(tokens, tokens[1:])]
    for feature in features:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % dimensions
        vector[index] += 1.0 if (value >> 32) & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _is_source_file(path: Path) -> bool:
    return path.name in SUPPORTED_NAMES or path.suffix.lower() in SUPPORTED_SUFFIXES


def load_chunks(
    root: str | Path,
    *,
    max_files: int = 1500,
    max_file_bytes: int = 300_000,
    chunk_lines: int = 80,
    overlap_lines: int = 15,
) -> list[CodeChunk]:
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        return []

    chunks: list[CodeChunk] = []
    files_seen = 0
    for path in sorted(root_path.rglob("*")):
        if files_seen >= max_files:
            break
        if not path.is_file() or path.is_symlink() or not _is_source_file(path):
            continue
        relative = path.relative_to(root_path)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files_seen += 1
        lines = text.splitlines()
        step = max(1, chunk_lines - overlap_lines)
        for start in range(0, len(lines), step):
            selected = lines[start : start + chunk_lines]
            if not selected:
                break
            chunks.append(
                CodeChunk(str(relative), start + 1, start + len(selected), "\n".join(selected))
            )
            if start + chunk_lines >= len(lines):
                break
    return chunks


class HybridCodeIndex:
    """Ranks chunks with local hashed vectors plus BM25 lexical relevance."""

    def __init__(self, chunks: list[CodeChunk]):
        self.chunks = chunks
        self.documents = [_tokens(f"{chunk.path} {chunk.content}") for chunk in chunks]
        self.counts = [Counter(document) for document in self.documents]
        self.embeddings = [_hashed_embedding(document) for document in self.documents]
        self.avg_length = (
            sum(len(document) for document in self.documents) / len(self.documents)
            if self.documents else 1.0
        )
        self.document_frequency = Counter()
        for document in self.documents:
            self.document_frequency.update(set(document))

    def _bm25(self, query: list[str], position: int) -> float:
        count = self.counts[position]
        length = len(self.documents[position])
        total = len(self.documents)
        score = 0.0
        for token in set(query):
            frequency = count[token]
            if not frequency:
                continue
            document_frequency = self.document_frequency[token]
            inverse_frequency = math.log(1 + (total - document_frequency + 0.5) / (document_frequency + 0.5))
            score += inverse_frequency * (frequency * 2.2) / (
                frequency + 1.2 * (0.25 + 0.75 * length / self.avg_length)
            )
        return score

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        query_tokens = _tokens(query)
        if not query_tokens or not self.chunks:
            return []
        query_embedding = _hashed_embedding(query_tokens)
        raw_bm25 = [self._bm25(query_tokens, i) for i in range(len(self.chunks))]
        max_bm25 = max(raw_bm25, default=1.0) or 1.0
        changed_paths = set(DIFF_PATH_RE.findall(query))

        ranked: list[RetrievedChunk] = []
        for i, chunk in enumerate(self.chunks):
            vector_score = max(0.0, _cosine(query_embedding, self.embeddings[i]))
            lexical_score = raw_bm25[i] / max_bm25
            path_boost = 0.15 if chunk.path in changed_paths else 0.0
            score = 0.45 * vector_score + 0.55 * lexical_score + path_boost
            if score > 0:
                ranked.append(RetrievedChunk(**chunk.__dict__, score=score))
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]


def retrieve_for_diff(
    root: str | Path,
    diff: str,
    *,
    top_k: int = 5,
    max_files: int = 1500,
) -> list[RetrievedChunk]:
    chunks = load_chunks(root, max_files=max_files)
    return HybridCodeIndex(chunks).search(diff, top_k=top_k)


def format_context(chunks: list[RetrievedChunk], max_chars: int = 7000) -> str:
    sections: list[str] = []
    used = 0
    for chunk in chunks:
        separator_length = 2 if sections else 0
        header = f"### {chunk.path}:{chunk.start_line}-{chunk.end_line}\n"
        available = max_chars - used - separator_length - len(header)
        if available <= 0:
            break
        section = header + chunk.content[:available]
        sections.append(section)
        used += separator_length + len(section)
    return "\n\n".join(sections)
