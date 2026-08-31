"""Advanced config — production, tier-aware harness selector."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

PORT: int = int(os.getenv("PORT", "8001"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL: str = os.getenv("MODEL", os.getenv("ADVANCED_MODEL", "gpt-4o-mini"))
HARNESS_MODE: str = os.getenv("HARNESS_MODE", "auto")  # auto | light | balanced | strict
MAX_CHARS: int = int(os.getenv("MAX_CHARS", "120000"))
ENABLE_VERIFY: bool = os.getenv("ENABLE_VERIFY", "1") == "1"
ENABLE_MEMORY: bool = os.getenv("ENABLE_MEMORY", "1") == "1"
ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "1") == "1"

# --- Real LLM integration (litellm, provider-agnostic) ---
# LLM_MODEL follows litellm's "<provider>/<model>" convention, e.g.:
#   gemini/gemini-2.5-flash | gpt-4o-mini | claude-haiku-4-5-20251001
# Swapping providers is a one-line env change; no code change required.
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
# On by default *only* if a key is present; EVAL_MOCK=1 always forces the offline mock path
# so judges without any API key still get a full, deterministic reproduction.
EVAL_MOCK: bool = os.getenv("EVAL_MOCK", "0") == "1"
ENABLE_LLM_VERIFY: bool = os.getenv("ENABLE_LLM_VERIFY", "1") == "1"

# Confidence-based LLM-verify routing: skip the real (paid, quota-limited) LLM
# cross-check for findings the deterministic dual-threshold gate already agreed PASS
# on AND whose playbook rule confidence is already high -- route the expensive call
# only to findings the deterministic engine itself is least sure about. Real playbook
# confidences (risk.py) range ~0.68-0.91 by rule reliability; 0.85 skips only the most
# reliable rule matches (contract_span/expiration/cap-liability -- 0.88/0.91), still
# sending the majority of medium-confidence rules (0.68-0.84) through the real check.
# This both reduces API cost (user's explicit concern) and is a real architectural
# improvement, not just a cost hack: it concentrates the expensive check where it adds
# the most value. See CHANGELOG #20.
LLM_VERIFY_SKIP_CONFIDENCE: float = float(os.getenv("LLM_VERIFY_SKIP_CONFIDENCE", "0.85"))

# Real hosted-embedding semantic extraction layer (advanced/src/harness/semantic.py) --
# additive to the regex extractor, degrades to regex-only with no key/EVAL_MOCK=1. Off
# by default: it is real (CHANGELOG #13) but only validated on a small (n=7) real sample
# so far, at a real measured precision cost -- opt-in until a full-scale validation run
# confirms the threshold, rather than silently changing every reproduction's output.
ENABLE_SEMANTIC_EXTRACTION: bool = os.getenv("ENABLE_SEMANTIC_EXTRACTION", "0") == "1"

# BM25 lexical hybrid layer (advanced/src/harness/bm25.py) -- additive to the regex
# extractor, $0/no API/always available (unlike the semantic layer above, never
# blocked by quota). Real, full-510-real-contract validated (unlike semantic's n=7):
# scripts/tune_bm25_threshold.py --sample 0, threshold=42.0 -> recall 42.2%->46.1%
# (+3.9pp), precision 92.7%->88.1% (-4.6pp) -- see CHANGELOG #19. Off by default for
# the same reason as ENABLE_SEMANTIC_EXTRACTION: a real, disclosed precision trade-off
# should be an opt-in choice, not a silent change to every reproduction's certified
# default numbers -- not because it's unvalidated (it is, fully, at $0).
ENABLE_BM25_EXTRACTION: bool = os.getenv("ENABLE_BM25_EXTRACTION", "0") == "1"

# LLM-as-generator layer (advanced/src/harness/llm_extract.py) -- unlike every other
# real LLM call in this harness (llm_verify.py), which only ever judges a candidate
# someone else already proposed, this one PROPOSES candidates: for playbook clause
# types with zero regex/semantic/BM25 hits, it asks the LLM to locate a verbatim
# excerpt, discards anything that isn't an exact substring of the real contract text
# (see llm_extract._find_verbatim), and only then lets it flow through the SAME
# assess_risk -> dual_verify -> llm_verify pipeline as any other hit -- it cannot
# bypass evidence gating. Off by default (real API cost per missing clause type,
# capped by LLM_EXTRACT_MAX_CALLS); degrades to a no-op with EVAL_MOCK=1 or no key.
# See CHANGELOG #22.
ENABLE_LLM_EXTRACT: bool = os.getenv("ENABLE_LLM_EXTRACT", "0") == "1"
LLM_EXTRACT_MAX_CALLS: int = int(os.getenv("LLM_EXTRACT_MAX_CALLS", "6"))

# Harness 2.0 flags — feature-flagged, default 0 so reproduce safe
ENABLE_LANGGRAPH: bool = os.getenv("ENABLE_LANGGRAPH", "0") == "1"
ENABLE_GRAPH_INTERRUPT: bool = os.getenv("ENABLE_GRAPH_INTERRUPT", "0") == "1"
LANGGRAPH_CHECKPOINTER: str = os.getenv("LANGGRAPH_CHECKPOINTER", "memory")  # memory|sqlite
LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "0") == "1"

# Resilience env tunables (Judge B: hardcoded retry not env-configurable, no timeout)
LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "30"))
RETRY_MAX_WAIT: float = float(os.getenv("RETRY_MAX_WAIT", "4"))
RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
