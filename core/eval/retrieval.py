"""Retrieval-quality evaluation, kept separate from generation quality.

When an answer is wrong you need to know *where* it broke: did the retriever
miss the relevant context, or did the generator ignore context it was given?
This module scores only the retriever, against a golden set of question ->
relevant-source labels.

Metrics (source-level, computed at cutoff k):
  * hit@k    — did any relevant source appear in the top k?
  * recall@k — fraction of the query's relevant sources found in the top k
  * MRR      — mean reciprocal rank of the first relevant source
  * nDCG@k   — rank-weighted gain, rewarding relevant sources placed higher
"""

import math


def _dedupe(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(retrieved[:k]) & relevant else 0.0


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for i, src in enumerate(retrieved):
        if src in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(
        1.0 / math.log2(i + 2)
        for i, src in enumerate(retrieved[:k])
        if src in relevant
    )
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def evaluate_retrieval(kb, dataset: list[dict], k: int = 3, depth: int = 10):
    """Score a knowledge base over a golden set.

    Returns (aggregate_metrics, per_query_rows). `depth` controls how many hits
    are pulled for rank-based metrics (MRR); `k` is the reported cutoff.
    """
    rows = []
    for item in dataset:
        question = item["question"]
        relevant = set(item["sources"])
        hits = kb.search(question, n_results=max(k, depth))
        retrieved = _dedupe([h["source"] for h in hits])
        rows.append({
            "question": question,
            "hit@k": hit_at_k(retrieved, relevant, k),
            "recall@k": recall_at_k(retrieved, relevant, k),
            "mrr": reciprocal_rank(retrieved, relevant),
            "ndcg@k": ndcg_at_k(retrieved, relevant, k),
            "top": retrieved[:k],
            "expected": sorted(relevant),
        })

    metrics = ("hit@k", "recall@k", "mrr", "ndcg@k")
    aggregate = {
        m: (sum(r[m] for r in rows) / len(rows) if rows else 0.0)
        for m in metrics
    }
    return aggregate, rows
