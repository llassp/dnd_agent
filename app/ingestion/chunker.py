import hashlib
import json
import re
from pathlib import Path
from typing import Any, Generator

from app.core.config import get_settings

settings = get_settings()


class Chunk:
    def __init__(
        self,
        text: str,
        source_doc_id: str,
        metadata: dict[str, Any],
        token_count: int,
    ):
        self.text = text
        self.source_doc_id = source_doc_id
        self.metadata = metadata
        self.token_count = token_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_text": self.text,
            "source_doc_id": self.source_doc_id,
            "metadata_json": self.metadata,
            "token_count": self.token_count,
        }


class Chunker:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        text = self._normalize_text(text)
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                boundary = self._find_sentence_boundary(text, end)
                if boundary > start:
                    end = boundary

            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap

            if start >= len(text):
                break

        return chunks

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    @staticmethod
    def _find_sentence_boundary(text: str, position: int) -> int:
        search_start = max(0, position - 100)
        search_text = text[search_start:position + 100]

        for match in reversed(list(re.finditer(r"[.!?]\s+", search_text))):
            if search_start + match.end() <= position + 20:
                return search_start + match.end()

        return position

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return len(text.split())

    def process_file(
        self,
        file_path: Path,
        source_doc_id: str,
        metadata: dict[str, Any],
    ) -> Generator[Chunk, None, None]:
        suffix = file_path.suffix.lower()

        if suffix == ".md":
            text = self._read_markdown(file_path)
        elif suffix == ".txt":
            text = self._read_plain_text(file_path)
        elif suffix == ".json":
            text = self._read_json(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        for i, chunk_text in enumerate(self.chunk_text(text)):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
            }
            yield Chunk(
                text=chunk_text,
                source_doc_id=source_doc_id,
                metadata=chunk_metadata,
                token_count=self.estimate_tokens(chunk_text),
            )

    @staticmethod
    def _read_markdown(path: Path) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _read_plain_text(path: Path) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _read_json(path: Path) -> str:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif isinstance(data, dict):
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return str(data)


def compute_checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
