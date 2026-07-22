"""LLM-as-a-judge for generation quality.

Scores a coach answer on two axes, 1-5 each:
  * faithfulness — is every claim grounded in the retrieved context?
  * relevance    — does the answer actually address the question?

Judge bias is a known failure mode, so it is mitigated deliberately: a fixed
rubric, faithfulness scored against the *retrieved context* (not the judge's own
prior knowledge), and a required rationale. For pairwise A/B judging, randomize
answer order to cancel position bias — see `answer_from_context` for the minimal
RAG generation path this scores.
"""

import json
import re

_JUDGE_PROMPT = """You are grading a Connect 4 coaching answer. Score it strictly.

QUESTION:
{question}

RETRIEVED CONTEXT (the only source of truth for faithfulness):
{context}

ANSWER:
{answer}

Grade on a 1-5 integer scale:
- faithfulness: 5 = every claim is supported by the context; 1 = contradicts or invents.
- relevance: 5 = directly and fully answers the question; 1 = off-topic.

Respond with ONLY a JSON object:
{{"faithfulness": <int>, "relevance": <int>, "rationale": "<one sentence>"}}"""

_ANSWER_PROMPT = """Answer the question using ONLY the context below. Be concise (2-3 sentences).
If the context does not contain the answer, say so.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def _llm_text(resp) -> str:
    content = getattr(resp, "content", resp)
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return (content or "").strip()


def answer_from_context(llm, question: str, context: str) -> str:
    """Minimal RAG generation: answer strictly from retrieved context."""
    return _llm_text(llm.invoke(_ANSWER_PROMPT.format(context=context, question=question)))


def judge_answer(llm, question: str, context: str, answer: str) -> dict:
    """Return {faithfulness, relevance, rationale} from an LLM judge."""
    raw = _llm_text(llm.invoke(_JUDGE_PROMPT.format(
        question=question, context=context, answer=answer,
    )))
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"faithfulness": None, "relevance": None, "rationale": raw[:200]}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"faithfulness": None, "relevance": None, "rationale": raw[:200]}
