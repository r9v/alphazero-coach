"""RAG pipeline for Connect 4 strategy knowledge base.

Loads strategy documents, chunks them, embeds with sentence-transformers,
and stores in ChromaDB for retrieval by the coaching agent.
"""

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

STRATEGY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "strategy"
COLLECTION_NAME = "connect4_strategy"


class StrategyKB:
    """Connect 4 strategy knowledge base backed by ChromaDB."""

    def __init__(self, strategy_dir: str | Path | None = None):
        self.strategy_dir = Path(strategy_dir) if strategy_dir else STRATEGY_DIR
        self.embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )
        self.client = chromadb.Client()  # in-memory, rebuilt each startup
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )
        self._index_documents()

    def _index_documents(self) -> None:
        """Load and index all strategy markdown files."""
        if not self.strategy_dir.exists():
            print(f"[rag] Warning: strategy dir not found: {self.strategy_dir}")
            return

        docs = []
        ids = []
        metadatas = []

        for md_file in sorted(self.strategy_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            chunks = self._chunk_by_sections(text, md_file.stem)

            for i, (chunk_text, section_title) in enumerate(chunks):
                chunk_id = f"{md_file.stem}_{i}"
                docs.append(chunk_text)
                ids.append(chunk_id)
                metadatas.append({
                    "source": md_file.name,
                    "section": section_title,
                })

        if docs:
            self.collection.add(documents=docs, ids=ids, metadatas=metadatas)
            print(f"[rag] Indexed {len(docs)} chunks from {len(list(self.strategy_dir.glob('*.md')))} documents")

    def _chunk_by_sections(self, text: str, filename: str) -> list[tuple[str, str]]:
        """Split a markdown document into chunks by ## headers."""
        chunks = []
        current_section = filename
        current_lines: list[str] = []

        for line in text.split("\n"):
            if line.startswith("## "):
                # Save previous chunk
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if len(chunk_text) > 50:  # skip tiny chunks
                        chunks.append((chunk_text, current_section))
                current_section = line.lstrip("# ").strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        # Save last chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if len(chunk_text) > 50:
                chunks.append((chunk_text, current_section))

        # If no ## headers found, return the whole doc as one chunk
        if not chunks:
            chunks.append((text.strip(), filename))

        return chunks

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """Search the knowledge base for relevant strategy content."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        hits = []
        for i in range(len(results["documents"][0])):
            hits.append({
                "content": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "section": results["metadatas"][0][i]["section"],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })

        return hits
