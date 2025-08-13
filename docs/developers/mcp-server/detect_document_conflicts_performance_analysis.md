# MCP Server detect_document_conflicts: Performance Analysis and Remediation Plan

## Executive summary

- Root causes: unbounded pair analysis, sequential LLM checks with long per-pair timeouts, and per-document vector retrieval in a loop. Combined, these can exceed typical client timeouts.
- Primary hotspots: candidate pair generation/tier limits, per-pair LLM invocation (35s cap), and sequential Qdrant vector `retrieve` calls (5s per doc).
- Plan: add a top-level analysis budget with partial results, reduce/parametrize pair caps, prune earlier, batch/parallelize vector retrieval with limits, strictly gate LLM usage, and add observability. Default behavior should complete <= 8s with limit <= 10.

---

### Call path and where the time is spent

1. MCP entry → `IntelligenceHandler`

```439:496:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/mcp/intelligence_handler.py
    async def handle_detect_document_conflicts(
        self, request_id: str | int | None, params: dict[str, Any]
    ) -> dict[str, Any]:
        ...
            conflict_results = await self.search_engine.detect_document_conflicts(
                query=params["query"],
                limit=params.get("limit", 15),
                source_types=params.get("source_types"),
                project_ids=params.get("project_ids"),
            )
        ...
```

1. Orchestration → `SearchEngine`

```645:739:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/engine.py
    async def detect_document_conflicts(
        self,
        query: str,
        limit: int = 15,
        ...
    ) -> dict[str, Any]:
        ...
            documents = await self.hybrid_search.search(
                query=query,
                limit=limit,
                ...
            )
        ...
            conflicts = await self.hybrid_search.detect_document_conflicts(documents)
        ...
```

1. Cross-doc analysis → `HybridSearchEngine` → `ConflictDetector`

```549:566:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/hybrid_search.py
    async def detect_document_conflicts(
        self, documents: list[HybridSearchResult]
    ) -> dict[str, Any]:
        ...
            conflict_analysis = (
                await self.cross_document_engine.conflict_detector.detect_conflicts(
                    documents
                )
            )
```

1. Conflict analysis core → `ConflictDetector`

```2565:2632:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/enhanced/cross_document_intelligence.py
    async def detect_conflicts(self, documents: list[SearchResult]) -> ConflictAnalysis:
        ...
        candidate_pairs = await self._get_tiered_analysis_pairs(documents)
        ...
        for doc1, doc2, analysis_tier, tier_score in candidate_pairs:
            ...
            if self.llm_enabled and analysis_tier in ["primary", "secondary"]:
                try:
                    conflict_info = await asyncio.wait_for(
                        self._llm_analyze_conflicts(doc1, doc2, tier_score),
                        timeout=35.0,
                    )
                except (TimeoutError, Exception):
                    ...
            if conflict_info is None:
                conflict_info = self._analyze_document_pair_for_conflicts(doc1, doc2)
            ...
```

1. Tier generation caps are high; many pairs may be analyzed

```2471:2484:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/enhanced/cross_document_intelligence.py
        # Combine tiers with limits to ensure reasonable performance
        max_primary = 50
        max_secondary = 30
        max_tertiary = 20
        max_fallback = 10
        all_pairs.extend(primary_pairs[:max_primary])
        all_pairs.extend(secondary_pairs[:max_secondary])
        all_pairs.extend(tertiary_pairs[:max_tertiary])
        all_pairs.extend(fallback_pairs[:max_fallback])
```

1. Vector retrieval is sequential and per-document with a 5s timeout

```2298:2315:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/enhanced/cross_document_intelligence.py
            for doc_id in document_ids:
                try:
                    result = await asyncio.wait_for(
                        self.qdrant_client.retrieve(
                            collection_name=self.collection_name,
                            ids=[doc_id],
                            with_vectors=True,
                            with_payload=False,
                        ),
                        timeout=5.0,
                    )
```

1. LLM request uses a heavyweight model and large token budget

```2685:2700:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/enhanced/cross_document_intelligence.py
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[...],
                    temperature=0.1,
                    max_tokens=1500,
                ),
                timeout=30.0,
            )
```

1. Tool default asks for 15 docs (O(n²) pairs on pre-LLM checks)

```443:471:packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/mcp/schemas.py
    def get_detect_conflicts_tool_schema() -> dict[str, Any]:
        return {
            "name": "detect_document_conflicts",
            ...
            "inputSchema": {
                ...
                "properties": {
                    ...
                    "limit": { "type": "integer", "default": 15 },
```

---

### Findings and suspected root causes

- Unbounded total work at request level
  - No overall time/compute budget; loop continues until all candidate pairs processed or `max_conflicts` reached.
  - With default `limit=15`, candidate pairs can be large (O(n²)) and tier caps allow up to 110 pairs.

- LLM-in-the-loop is expensive and sequential
  - LLM check applied for both primary and secondary tiers; each pair can wait up to 35s.
  - No global “max LLM pairs”, no concurrency control, no short-circuit on elapsed time.
  - Heavy model (`gpt-4`) and large `max_tokens` (1500) increase latency and variability.

- Vector retrieval is performed per document sequentially
  - Each `retrieve` call is awaited individually with a 5s timeout; worst case N*5s before analysis begins.
  - No batching, no parallel fetching with capped concurrency.

- Candidate generation and similarity checks are broad
  - Tier thresholds and caps are generous; many pairs make it to the analysis stage.
  - Fallback text similarity uses full tokenized words; on long texts, this is costly (improve by truncation/windowing).

- Default `limit=15` is high relative to the compute intensity
  - 15 documents lead to 105 raw pairs before tiering; even with pruning, this is too large for default UX.

---

### Risk/impact analysis

- Even with modest corpora, requests may exceed typical client timeouts due to sequential per-pair LLM checks and pre-LLM overhead.
- Erratic behavior (timeouts vs. success) depends on corpus overlap (more primary/secondary pairs → more LLM calls) and OpenAI latency.
- Without budgets/partial-results, a slow path returns late or fails instead of degrading gracefully.

---

### Detailed remediation plan (phased, measurable)

Phase 0 – Instrumentation and reproducibility (Day 1)

- Add structured timing/metrics at key stages:
  - counts: docs, total pairs, pairs per tier, LLM_calls_attempted/completed/timeouts
  - timings: search_ms, embeddings_ms, pair_selection_ms, llm_ms_total, fallback_ms_total, total_ms
  - outcome flags: partial_results, budget_exhausted
- Create an integration test/benchmark harness that runs `detect_document_conflicts` with seeded data and asserts P95 latency under configurable budget.
- Log budget and caps chosen per run to aid investigation.

Phase 1 – Introduce a top-level analysis budget with partial results (Day 2)

- Add optional params (thread through handler → engine → conflict detector):
  - `overall_timeout_s` (default 9), `use_llm` (default false), `max_llm_pairs` (default 2–3), `max_pairs_total` (default 24), `max_conflicts` (default 10), `text_window_chars` (default 2000)
- Track `deadline = now + overall_timeout_s`. After each major step and per pair, check time; if exceeded:
  - set `partial_results=True`; return best-effort results collected so far.
  - include `budget_exhausted` in metadata.

Phase 2 – Reduce default work and sharpen pruning (Day 3)

- Lower default `limit` in schema and handler from 15 → 10.
- Tighten tier caps (config-driven):
  - `max_primary=12`, `max_secondary=8`, `max_tertiary=4`, `max_fallback=0–2` (disabled by default for latency)
- Add prefilter: run `_filter_by_vector_similarity` first and intersect with tiered pairs to keep only top-K likely conflicts (e.g., K=12).
- Truncate text for lexical similarity (e.g., first 1,500–2,000 chars) to bound CPU.

Phase 3 – Optimize embeddings retrieval (Day 3–4)

- Batch retrieval: attempt a single `retrieve(ids=document_ids, with_vectors=True)` if supported; else parallelize with `asyncio.gather` and a small semaphore (e.g., 5) and a shorter per-call timeout (2s).
- Skip embeddings path entirely if < 2 vectors retrieved; use text-only similarity in that case.

Phase 4 – Gate and optimize LLM usage (Day 4)

- Default `use_llm=False` unless explicitly requested or corpus is small.
- When `use_llm=True`:
  - Only run on the top-N highest confidence pairs (e.g., N=2–3).
  - Use `asyncio.Semaphore` to cap concurrency (e.g., 2).
  - Lower `max_tokens` (e.g., 400–600) and switch to a faster model (e.g., `gpt-4o-mini`).
  - Reduce `wait_for` timeout to ~12s per pair; honor the overall deadline.

Phase 5 – Return structure and UX (Day 5)

- Add `query_metadata` fields: `pairs_considered`, `pairs_analyzed`, `llm_pairs`, `elapsed_ms`, `partial_results`, `budget_exhausted`.
- Ensure formatters handle partial results and show “analysis truncated due to time budget; adjust parameters to see more”.

Phase 6 – Tests and docs (Day 5)

- Unit tests:
  - budget honored with partial results
  - LLM disabled path correctness
  - vector retrieval fallback path
  - candidate caps respected
- Integration tests:
  - end-to-end conflict detection <= 8s (with default config and synthetic data)
  - optional LLM enabled with `max_llm_pairs=2` remains <= 8–12s
- Documentation updates in `docs/users/detailed-guides/mcp-server/`:
  - new parameters, defaults, performance tips, examples

---

### Configuration surface (proposal)

- Extend `SearchConfig` with:
  - `conflict_limit_default: int = 10`
  - `conflict_max_pairs_total: int = 24`
  - `conflict_tier_caps: dict = {primary: 12, secondary: 8, tertiary: 4, fallback: 0}`
  - `conflict_use_llm: bool = False`
  - `conflict_max_llm_pairs: int = 2`
  - `conflict_llm_model: str = "gpt-4o-mini"`
  - `conflict_llm_timeout_s: float = 12.0`
  - `conflict_overall_timeout_s: float = 8.0`
  - `conflict_text_window_chars: int = 2000`
  - `conflict_embeddings_timeout_s: float = 2.0`
  - `conflict_embeddings_max_concurrency: int = 5`

Environment variables can override these for ops without code changes.

---

### Rollout and safety

- Ship with LLM disabled by default and strict budgets/caps.
- Add verbose logging behind a debug flag to avoid noisy logs in prod.
- If problems persist, progressively tighten caps or disable tiers beyond primary.

---

### Latency target confirmation

Target P95 latency is 8–10 seconds. Defaults in this plan (e.g., `overall_timeout_s=9`, reduced pair caps, and LLM gating) are calibrated to meet this range. We will validate via integration tests and adjust caps if needed.
