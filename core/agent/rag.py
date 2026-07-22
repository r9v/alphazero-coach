"""Hybrid retrieval pipeline for the Connect 4 strategy knowledge base.

A single `StrategyKB.search()` call runs a modern multi-stage retrieval stack:

  1. Dense retrieval   — sentence-transformers bi-encoder over ChromaDB
  2. Sparse retrieval   — Okapi BM25 lexical scoring (rank_bm25)
  3. Fusion             — Reciprocal Rank Fusion (RRF) merges the two rankings
  4. Re-ranking         — a cross-encoder re-scores the fused candidates
  5. Contextual chunks  — each chunk is prefixed with document/section context
                          before indexing (Anthropic "contextual retrieval")

Query-side expansion (HyDE) is optional and pluggable via `query_expansion`.

For a corpus this small a flat semantic search is already sufficient — the full
pipeline is here to mirror the retrieval stack used on production-scale corpora,
and every stage can be toggled through `RetrievalConfig` (env-driven).
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

STRATEGY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "strategy"
COLLECTION_NAME = "connect4_strategy"

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer used for BM25 indexing and querying."""
    return _WORD_RE.findall(text.lower())


def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class RetrievalConfig:
    """Toggles and hyperparameters for the retrieval pipeline."""
    use_hybrid: bool = True            # dense + BM25 fused with RRF
    use_reranker: bool = True          # cross-encoder re-scoring
    use_hyde: bool = False             # HyDE query expansion (needs an LLM)
    use_contextual_chunks: bool = True # prepend doc/section context before indexing
    dense_top_k: int = 10
    sparse_top_k: int = 10
    rrf_k: int = 60                    # RRF smoothing constant
    final_k: int = 3
    dense_model: str = "all-MiniLM-L6-v2"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @classmethod
    def from_env(cls) -> "RetrievalConfig":
        return cls(
            use_hybrid=_bool_env("RAG_HYBRID", True),
            use_reranker=_bool_env("RAG_RERANK", True),
            use_hyde=_bool_env("RAG_HYDE", False),
            use_contextual_chunks=_bool_env("RAG_CONTEXTUAL", True),
        )


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse several ranked lists of chunk ids into one ranking.

    RRF score for a document = sum over lists of 1 / (k + rank), with a 0-based
    rank. It needs no score calibration between retrievers, which is why it is
    the standard way to combine dense and lexical results. Returns
    (chunk_id, score) pairs sorted by descending fused score.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class StrategyKB:
    """Connect 4 strategy knowledge base with hybrid dense+sparse retrieval."""

    def __init__(
        self,
        strategy_dir: str | Path | None = None,
        config: RetrievalConfig | None = None,
        hyde=None,
    ):
        self.strategy_dir = Path(strategy_dir) if strategy_dir else STRATEGY_DIR
        self.config = config or RetrievalConfig.from_env()
        self.hyde = hyde  # optional query_expansion.HyDEExpander

        self.embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=self.config.dense_model,
        )
        self.client = chromadb.Client()  # in-memory, rebuilt each startup
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )

        self._chunks: dict[str, dict] = {}   # chunk_id -> {id,text,indexed_text,source,section}
        self._chunk_ids: list[str] = []       # BM25 corpus order
        self._bm25 = None
        self._reranker = None                 # lazily loaded CrossEncoder (or False if unavailable)

        self._index_documents()

    # ------------------------------------------------------------------ indexing

    def _index_documents(self) -> None:
        """Load, chunk, contextualize, and index all strategy markdown files."""
        if not self.strategy_dir.exists():
            print(f"[rag] Warning: strategy dir not found: {self.strategy_dir}")
            return

        docs, ids, metadatas = [], [], []

        for md_file in sorted(self.strategy_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            title = md_file.stem.replace("_", " ").title()
            chunks = self._chunk_by_sections(text, md_file.stem)

            for i, (chunk_text, section_title) in enumerate(chunks):
                chunk_id = f"{md_file.stem}_{i}"
                indexed_text = self._contextualize(chunk_text, title, section_title)
                self._chunks[chunk_id] = {
                    "id": chunk_id,
                    "text": chunk_text,
                    "indexed_text": indexed_text,
                    "source": md_file.name,
                    "section": section_title,
                }
                docs.append(indexed_text)
                ids.append(chunk_id)
                metadatas.append({"source": md_file.name, "section": section_title})

        if docs:
            self.collection.add(documents=docs, ids=ids, metadatas=metadatas)
            self._chunk_ids = list(self._chunks.keys())
            self._build_bm25()
            n_files = len(list(self.strategy_dir.glob("*.md")))
            print(f"[rag] Indexed {len(docs)} chunks from {n_files} documents "
                  f"(hybrid={self.config.use_hybrid}, rerank={self.config.use_reranker}, "
                  f"contextual={self.config.use_contextual_chunks})")

    def _contextualize(self, chunk_text: str, doc_title: str, section: str) -> str:
        """Prepend situating context to a chunk before it is indexed.

        This is a lightweight take on Anthropic's "contextual retrieval": a chunk
        embedded in isolation loses the document it came from, which hurts both
        dense and lexical matching. Prepending the document title and section
        anchors the chunk in its surroundings. Swap the heuristic prefix for an
        LLM-generated blurb when indexing a larger, less self-describing corpus.
        """
        if not self.config.use_contextual_chunks:
            return chunk_text
        context = f"Connect 4 strategy — {doc_title} / {section}."
        return f"{context}\n\n{chunk_text}"

    def _build_bm25(self) -> None:
        if not self.config.use_hybrid:
            return
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            print("[rag] rank_bm25 not installed — falling back to dense-only retrieval")
            return
        corpus = [_tokenize(self._chunks[cid]["indexed_text"]) for cid in self._chunk_ids]
        self._bm25 = BM25Okapi(corpus)

    def _chunk_by_sections(self, text: str, filename: str) -> list[tuple[str, str]]:
        """Split a markdown document into chunks by ## headers."""
        chunks = []
        current_section = filename
        current_lines: list[str] = []

        for line in text.split("\n"):
            if line.startswith("## "):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if len(chunk_text) > 50:
                        chunks.append((chunk_text, current_section))
                current_section = line.lstrip("# ").strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if len(chunk_text) > 50:
                chunks.append((chunk_text, current_section))

        if not chunks:
            chunks.append((text.strip(), filename))

        return chunks

    # --------------------------------------------------------------- retrieval

    def _dense_search(self, query_text: str, top_k: int) -> list[str]:
        results = self.collection.query(query_texts=[query_text], n_results=top_k)
        return list(results["ids"][0]) if results.get("ids") else []

    def _sparse_search(self, query: str, top_k: int) -> list[str]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self._chunk_ids[i] for i in ranked[:top_k] if scores[i] > 0]

    def _get_reranker(self):
        """Lazily load the cross-encoder. Returns None if unavailable/disabled."""
        if not self.config.use_reranker:
            return None
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder(self.config.cross_encoder_model)
                print(f"[rag] Loaded cross-encoder reranker: {self.config.cross_encoder_model}")
            except Exception as e:  # model download / import failure — degrade gracefully
                print(f"[rag] cross-encoder unavailable ({e}); skipping rerank")
                self._reranker = False
        return self._reranker or None

    def _rerank(self, query: str, chunk_ids: list[str]) -> list[str]:
        reranker = self._get_reranker()
        if reranker is None or not chunk_ids:
            return chunk_ids
        pairs = [(query, self._chunks[cid]["text"]) for cid in chunk_ids]
        scores = reranker.predict(pairs)
        order = sorted(range(len(chunk_ids)), key=lambda i: scores[i], reverse=True)
        return [chunk_ids[i] for i in order]

    def _hit(self, chunk_id: str) -> dict:
        c = self._chunks[chunk_id]
        return {
            "content": c["text"],
            "source": c["source"],
            "section": c["section"],
            "chunk_id": chunk_id,
        }

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """Retrieve the most relevant strategy chunks for a query.

        Runs dense + (optional) BM25 retrieval, fuses them with RRF, then
        re-ranks the candidates with a cross-encoder. Backward-compatible with
        the previous flat-search interface: returns a list of dicts with
        `content`, `source`, and `section`.
        """
        cfg = self.config

        # Query-side expansion: HyDE embeds a hypothetical answer for the dense arm.
        dense_query = query
        if cfg.use_hyde and self.hyde is not None:
            hypothetical = self.hyde.expand(query)
            if hypothetical:
                dense_query = hypothetical

        dense_ids = self._dense_search(dense_query, cfg.dense_top_k)

        if cfg.use_hybrid and self._bm25 is not None:
            sparse_ids = self._sparse_search(query, cfg.sparse_top_k)
            fused = [cid for cid, _ in reciprocal_rank_fusion([dense_ids, sparse_ids], cfg.rrf_k)]
        else:
            fused = dense_ids

        candidates = fused[: max(cfg.dense_top_k, cfg.sparse_top_k)]
        if cfg.use_reranker:
            candidates = self._rerank(query, candidates)

        return [self._hit(cid) for cid in candidates[:n_results]]
