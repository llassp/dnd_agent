import pytest
from app.ingestion.chunker import Chunker


class TestChunker:
    def test_chunk_text_simple(self):
        chunker = Chunker(chunk_size=100, chunk_overlap=20)
        text = "This is a simple test. It has multiple sentences. Each sentence should be chunked properly."
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_text_empty(self):
        chunker = Chunker()
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0

    def test_chunk_text_whitespace(self):
        chunker = Chunker()
        chunks = chunker.chunk_text("   \n\n   ")
        assert len(chunks) == 0

    def test_estimate_tokens(self):
        chunker = Chunker()
        text = "This is a test of token estimation"
        tokens = chunker.estimate_tokens(text)
        assert tokens == 6

    def test_read_markdown(self, tmp_path):
        chunker = Chunker()
        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello\n\nThis is a test.")
        chunks = list(chunker.process_file(test_file, "doc-1", {}))
        assert len(chunks) > 0

    def test_read_json(self, tmp_path):
        chunker = Chunker()
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')
        chunks = list(chunker.process_file(test_file, "doc-1", {}))
        assert len(chunks) > 0
