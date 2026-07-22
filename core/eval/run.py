"""Run the AlphaZero Coach evaluation suite.

    python -m core.eval.run              # retrieval metrics only (no API key needed)
    python -m core.eval.run --k 5        # report at cutoff k=5
    python -m core.eval.run --judge      # also run LLM-as-judge on generated answers

Retrieval eval scores the hybrid RAG pipeline against a golden set of
question -> relevant-source labels. The optional judge pass exercises the
retrieve -> generate path and grades faithfulness/relevance with an LLM judge.
"""

import argparse
import json
from pathlib import Path

from core.agent.rag import StrategyKB
from core.eval.retrieval import evaluate_retrieval

_GOLDEN = Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "golden_qa.jsonl"


def _load_dataset(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _print_retrieval(aggregate: dict, rows: list[dict], k: int) -> None:
    print(f"\n=== Retrieval eval (n={len(rows)}, k={k}) ===")
    print(f"  hit@{k}:    {aggregate['hit@k']:.3f}")
    print(f"  recall@{k}: {aggregate['recall@k']:.3f}")
    print(f"  MRR:       {aggregate['mrr']:.3f}")
    print(f"  nDCG@{k}:   {aggregate['ndcg@k']:.3f}")
    print("\n  Per-query:")
    for r in rows:
        flag = "ok " if r["hit@k"] else "MISS"
        print(f"   [{flag}] {r['question'][:52]:<52} top={r['top']}")


def _run_judge(dataset: list[dict], kb: StrategyKB, k: int) -> None:
    from core.agent.coach import _make_llm
    from core.eval.judge import answer_from_context, judge_answer

    llm = _make_llm(temperature=0.0)
    print("\n=== LLM-as-judge (retrieve -> generate -> grade) ===")
    faith, rel, n = 0.0, 0.0, 0
    for item in dataset:
        q = item["question"]
        hits = kb.search(q, n_results=k)
        context = "\n\n".join(f"[{h['source']}] {h['content']}" for h in hits)
        answer = answer_from_context(llm, q, context)
        verdict = judge_answer(llm, q, context, answer)
        f, r = verdict.get("faithfulness"), verdict.get("relevance")
        if isinstance(f, int) and isinstance(r, int):
            faith += f; rel += r; n += 1
        print(f"   {q[:52]:<52} faith={f} rel={r}")
    if n:
        print(f"\n  Mean faithfulness: {faith / n:.2f}/5   Mean relevance: {rel / n:.2f}/5")


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaZero Coach eval suite")
    parser.add_argument("--k", type=int, default=3, help="retrieval cutoff")
    parser.add_argument("--judge", action="store_true", help="run LLM-as-judge pass")
    args = parser.parse_args()

    dataset = _load_dataset(_GOLDEN)
    kb = StrategyKB()

    aggregate, rows = evaluate_retrieval(kb, dataset, k=args.k)
    _print_retrieval(aggregate, rows, args.k)

    if args.judge:
        _run_judge(dataset, kb, args.k)


if __name__ == "__main__":
    main()
