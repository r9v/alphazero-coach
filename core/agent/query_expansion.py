"""HyDE (Hypothetical Document Embeddings) query expansion.

Instead of embedding a terse user question, HyDE first asks an LLM to draft a
short hypothetical answer, then embeds *that*. The hypothetical passage lives in
the same semantic space as the corpus documents, so dense retrieval matches it
more reliably than the bare question does. (Gao et al., 2022,
"Precise Zero-Shot Dense Retrieval without Relevance Labels".)

The expander is optional and degrades to a no-op when no LLM is configured, so
retrieval never hard-depends on an API key.
"""

_HYDE_PROMPT = (
    "You are a Connect 4 strategy expert. Write a short, factual paragraph "
    "(2-4 sentences) that would directly answer the following question, as if "
    "it were an excerpt from a strategy reference. Do not hedge or add caveats — "
    "just state the strategic content.\n\nQuestion: {query}\n\nPassage:"
)


class HyDEExpander:
    """Generates a hypothetical answer passage to steer dense retrieval."""

    def __init__(self, llm=None):
        self.llm = llm  # a LangChain chat model, or None to disable

    @classmethod
    def from_env(cls) -> "HyDEExpander":
        """Build an expander from whatever LLM the coach is configured to use."""
        try:
            from core.agent.coach import _make_llm
            return cls(_make_llm(temperature=0.3))
        except Exception:
            return cls(None)

    def expand(self, query: str) -> str | None:
        if self.llm is None:
            return None
        try:
            resp = self.llm.invoke(_HYDE_PROMPT.format(query=query))
            content = getattr(resp, "content", resp)
            if isinstance(content, list):  # some providers return content blocks
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            content = (content or "").strip()
            # Concatenate the query so lexical anchors from the question survive.
            return f"{query}\n{content}" if content else None
        except Exception:
            return None
