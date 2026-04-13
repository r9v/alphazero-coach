"""Tests for RAG pipeline markdown chunking."""

from core.agent.rag import StrategyKB


class TestChunkBySections:
    def _chunk(self, text, filename="test"):
        kb = StrategyKB.__new__(StrategyKB)  # skip __init__ (no ChromaDB)
        return kb._chunk_by_sections(text, filename)

    def test_splits_on_headers(self):
        text = """# Title

Some intro text that is long enough to pass the 50 char minimum threshold for chunking.

## Section One

Content for section one that is also long enough to pass the minimum threshold.

## Section Two

Content for section two that is also long enough to pass the minimum threshold."""
        chunks = self._chunk(text)
        assert len(chunks) == 3
        assert chunks[0][1] == "test"  # intro uses filename
        assert chunks[1][1] == "Section One"
        assert chunks[2][1] == "Section Two"

    def test_skips_tiny_chunks(self):
        text = """## Short

Tiny.

## Long Section

This section has enough content to pass the fifty character minimum threshold for inclusion."""
        chunks = self._chunk(text)
        # "Tiny." chunk is < 50 chars, should be skipped
        assert all(len(c[0]) > 50 for c in chunks)

    def test_no_headers_returns_whole_doc(self):
        text = "This is a document with no headers but enough content to be meaningful and pass thresholds."
        chunks = self._chunk(text, "myfile")
        assert len(chunks) == 1
        assert chunks[0][1] == "myfile"
        assert chunks[0][0] == text

    def test_empty_input(self):
        chunks = self._chunk("", "empty")
        assert len(chunks) == 1
        assert chunks[0][1] == "empty"

    def test_header_text_extraction(self):
        text = """## Center Control

Center control is the most important concept in Connect 4 strategy and should be prioritized."""
        chunks = self._chunk(text)
        assert chunks[0][1] == "Center Control"
