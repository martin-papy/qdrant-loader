from __future__ import annotations

from typing import Any


def _create_llm_provider_from_env(logger: Any | None = None) -> Any | None:
    """Create an embeddings provider from qdrant-loader-core settings if available.

    This mirrors the legacy dynamic import behavior and falls back to None when
    unavailable. No exceptions propagate to callers.
    """
    try:
        import os
        from importlib import import_module

        core_settings_mod = import_module("qdrant_loader_core.llm.settings")
        core_factory_mod = import_module("qdrant_loader_core.llm.factory")
        LLMSettings = core_settings_mod.LLMSettings
        create_provider = core_factory_mod.create_provider

        # 1) Try to load LLM settings from the MCP server config file (global.llm)
        llm_cfg: dict | None = None
        try:
            cfg_loader_mod = import_module("qdrant_loader_mcp_server.config_loader")
            load_config = getattr(cfg_loader_mod, "load_config", None)
            if callable(load_config):
                _cfg, effective, _used_file = load_config(None)
                if isinstance(effective, dict):
                    maybe_llm = (effective.get("global") or {}).get("llm")
                    if isinstance(maybe_llm, dict) and maybe_llm:
                        # Make a shallow copy so we can safely overlay defaults/env
                        llm_cfg = dict(maybe_llm)
        except Exception:
            # Non-fatal: fall through to env-only defaults
            llm_cfg = None

        # 2) If no file config present, construct from environment (legacy behavior)
        if not llm_cfg:
            llm_cfg = {
                "provider": (os.getenv("LLM_PROVIDER") or "openai"),
                "base_url": os.getenv("LLM_BASE_URL"),
                "api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
                "models": {
                    "embeddings": os.getenv("LLM_EMBEDDING_MODEL")
                    or "text-embedding-3-small",
                },
                "tokenizer": os.getenv("LLM_TOKENIZER") or "none",
                "request": {},
                "rate_limits": {},
                "embeddings": {},
            }
        else:
            # Ensure sane defaults and environment overlays for partial file configs
            def _resolve_placeholder(
                value: object,
                fallback_env: str | None = None,
                default: object | None = None,
            ) -> object | None:
                if (
                    isinstance(value, str)
                    and value.startswith("${")
                    and value.endswith("}")
                ):
                    env_name = value[2:-1]
                    return (
                        os.getenv(env_name)
                        or (os.getenv(fallback_env) if fallback_env else None)
                        or default
                    )
                return (
                    value
                    if value not in (None, "")
                    else (os.getenv(fallback_env) if fallback_env else default)
                )

            # Provider and endpoints
            llm_cfg["provider"] = _resolve_placeholder(
                llm_cfg.get("provider"), fallback_env="LLM_PROVIDER", default="openai"
            )
            llm_cfg["base_url"] = _resolve_placeholder(
                llm_cfg.get("base_url"), fallback_env="LLM_BASE_URL", default=None
            )
            llm_cfg["api_key"] = _resolve_placeholder(
                llm_cfg.get("api_key"),
                fallback_env="LLM_API_KEY",
                default=os.getenv("OPENAI_API_KEY"),
            )

            # Models
            models = dict(llm_cfg.get("models") or {})
            models["embeddings"] = _resolve_placeholder(
                models.get("embeddings"),
                fallback_env="LLM_EMBEDDING_MODEL",
                default="text-embedding-3-small",
            )
            if models.get("chat") in (None, "") or (
                isinstance(models.get("chat"), str)
                and str(models.get("chat")).startswith("${")
                and str(models.get("chat")).endswith("}")
            ):
                env_chat = os.getenv("LLM_CHAT_MODEL")
                if env_chat:
                    models["chat"] = env_chat
            llm_cfg["models"] = models

            # Other optional blocks
            llm_cfg["tokenizer"] = _resolve_placeholder(
                llm_cfg.get("tokenizer"), fallback_env="LLM_TOKENIZER", default="none"
            )
            llm_cfg.setdefault("request", {})
            llm_cfg.setdefault("rate_limits", {})
            llm_cfg.setdefault("embeddings", {})

        llm_settings = LLMSettings.from_global_config({"llm": llm_cfg})
        return create_provider(llm_settings)
    except ImportError:
        # Attempt monorepo-relative import by adding sibling core package to sys.path
        try:
            import sys
            from pathlib import Path

            current_file = Path(__file__).resolve()
            for ancestor in current_file.parents:
                core_src = ancestor / "qdrant-loader-core" / "src"
                if core_src.exists():
                    sys.path.append(str(core_src))
                    break
            # Retry import after amending sys.path
            from importlib import import_module as _import_module  # type: ignore

            core_settings_mod = _import_module("qdrant_loader_core.llm.settings")
            core_factory_mod = _import_module("qdrant_loader_core.llm.factory")
            LLMSettings = core_settings_mod.LLMSettings
            create_provider = core_factory_mod.create_provider

            import os as _os

            llm_cfg = {
                "provider": (_os.getenv("LLM_PROVIDER") or "openai"),
                "base_url": _os.getenv("LLM_BASE_URL"),
                "api_key": _os.getenv("LLM_API_KEY") or _os.getenv("OPENAI_API_KEY"),
                "models": {
                    "embeddings": _os.getenv("LLM_EMBEDDING_MODEL")
                    or "text-embedding-3-small",
                },
                "tokenizer": _os.getenv("LLM_TOKENIZER") or "none",
                "request": {},
                "rate_limits": {},
                "embeddings": {},
            }
            llm_settings = LLMSettings.from_global_config({"llm": llm_cfg})
            return create_provider(llm_settings)
        except Exception:
            if logger is not None:
                try:
                    logger.debug(
                        "LLM provider import failed after path adjustment; falling back to None",
                        exc_info=True,
                    )
                except Exception:
                    pass
            return None
    except Exception as e:
        if logger is not None:
            try:
                # Log full stack for unexpected provider errors
                try:
                    logger.exception(
                        "Error creating LLM provider; falling back to None"
                    )
                except Exception:
                    logger.debug(
                        "Error creating LLM provider; falling back to None: %s",
                        e,
                        exc_info=True,
                    )
            except Exception:
                pass
        return None


def create_spacy_analyzer(spacy_model: str = "en_core_web_md") -> Any:
    """Create the SpaCyQueryAnalyzer instance."""
    from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer

    return SpaCyQueryAnalyzer(spacy_model=spacy_model)


def create_query_processor(spacy_analyzer: Any) -> Any:
    """Create the QueryProcessor bound to the given analyzer."""
    from ...components import QueryProcessor

    return QueryProcessor(spacy_analyzer)


def create_vector_search_service(
    *,
    qdrant_client: Any,
    collection_name: str,
    min_score: float,
    search_config: Any | None,
    embeddings_provider: Any | None,
    openai_client: Any,
) -> Any:
    """Create VectorSearchService with optional cache/search tuning from config."""
    from ...components import VectorSearchService

    if search_config:
        return VectorSearchService(
            qdrant_client=qdrant_client,
            collection_name=collection_name,
            min_score=min_score,
            cache_enabled=search_config.cache_enabled,
            cache_ttl=search_config.cache_ttl,
            cache_max_size=search_config.cache_max_size,
            hnsw_ef=search_config.hnsw_ef,
            use_exact_search=search_config.use_exact_search,
            embeddings_provider=embeddings_provider,
            openai_client=openai_client,
        )
    return VectorSearchService(
        qdrant_client=qdrant_client,
        collection_name=collection_name,
        min_score=min_score,
        embeddings_provider=embeddings_provider,
        openai_client=openai_client,
    )


def create_keyword_search_service(*, qdrant_client: Any, collection_name: str) -> Any:
    """Create KeywordSearchService."""
    from ...components import KeywordSearchService

    return KeywordSearchService(
        qdrant_client=qdrant_client, collection_name=collection_name
    )


def create_result_combiner(
    *,
    vector_weight: float,
    keyword_weight: float,
    metadata_weight: float,
    min_score: float,
    spacy_analyzer: Any,
) -> Any:
    """Create ResultCombiner with provided weights and analyzer."""
    from ...components import ResultCombiner

    return ResultCombiner(
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        metadata_weight=metadata_weight,
        min_score=min_score,
        spacy_analyzer=spacy_analyzer,
    )


def create_intent_components(spacy_analyzer: Any, knowledge_graph: Any, enable: bool):
    """Create intent classifier and adaptive strategy, or (None, None) if disabled."""
    if not enable:
        return None, None
    from ...enhanced.intent_classifier import AdaptiveSearchStrategy, IntentClassifier

    intent_classifier = IntentClassifier(spacy_analyzer)
    adaptive_strategy = AdaptiveSearchStrategy(knowledge_graph)
    return intent_classifier, adaptive_strategy


def create_topic_chain_generator(spacy_analyzer: Any, knowledge_graph: Any) -> Any:
    """Create TopicSearchChainGenerator."""
    from ...enhanced.topic_search_chain import TopicSearchChainGenerator

    return TopicSearchChainGenerator(spacy_analyzer, knowledge_graph)


def create_faceted_engine() -> Any:
    """Create FacetedSearchEngine."""
    from ...enhanced.faceted_search import FacetedSearchEngine

    return FacetedSearchEngine()


def create_cdi_engine(
    *,
    spacy_analyzer: Any,
    knowledge_graph: Any,
    qdrant_client: Any,
    openai_client: Any,
    collection_name: str,
    conflict_settings: dict | None,
) -> Any:
    """Create CrossDocumentIntelligenceEngine with provided settings."""
    from ...enhanced.cross_document_intelligence import CrossDocumentIntelligenceEngine

    return CrossDocumentIntelligenceEngine(
        spacy_analyzer,
        knowledge_graph,
        qdrant_client,
        openai_client,
        collection_name,
        conflict_settings=conflict_settings,
    )


def build_conflict_settings(search_config: Any | None) -> dict | None:
    """Construct conflict detection settings from ``search_config`` safely."""
    if search_config is None:
        return None
    try:
        return {
            "conflict_limit_default": getattr(
                search_config, "conflict_limit_default", 10
            ),
            "conflict_max_pairs_total": getattr(
                search_config, "conflict_max_pairs_total", 24
            ),
            "conflict_tier_caps": getattr(
                search_config,
                "conflict_tier_caps",
                {"primary": 12, "secondary": 8, "tertiary": 4, "fallback": 0},
            ),
            "conflict_use_llm": getattr(search_config, "conflict_use_llm", True),
            "conflict_max_llm_pairs": getattr(
                search_config, "conflict_max_llm_pairs", 2
            ),
            "conflict_llm_model": getattr(
                search_config, "conflict_llm_model", "gpt-4o-mini"
            ),
            "conflict_llm_timeout_s": getattr(
                search_config, "conflict_llm_timeout_s", 12.0
            ),
            "conflict_overall_timeout_s": getattr(
                search_config, "conflict_overall_timeout_s", 9.0
            ),
            "conflict_text_window_chars": getattr(
                search_config, "conflict_text_window_chars", 2000
            ),
            "conflict_embeddings_timeout_s": getattr(
                search_config, "conflict_embeddings_timeout_s", 2.0
            ),
            "conflict_embeddings_max_concurrency": getattr(
                search_config, "conflict_embeddings_max_concurrency", 5
            ),
        }
    except Exception:
        return None


def initialize_engine_components(
    engine_self: Any,
    *,
    qdrant_client: Any,
    openai_client: Any,
    collection_name: str,
    vector_weight: float,
    keyword_weight: float,
    metadata_weight: float,
    min_score: float,
    knowledge_graph: Any,
    enable_intent_adaptation: bool,
    search_config: Any | None,
    processing_config: Any | None,
) -> None:
    """Initialize all engine components and wire optional processing hooks."""
    # Analyzer and query processor
    spacy_analyzer = create_spacy_analyzer(spacy_model="en_core_web_md")
    query_processor = create_query_processor(spacy_analyzer)

    # Embeddings provider and search services
    # Create shared LLM provider if available from core settings
    llm_provider = _create_llm_provider_from_env(logger=engine_self.logger)
    embeddings_provider = llm_provider
    # If an explicit OpenAI client is provided, prefer it over any auto-created provider
    # so tests and engines that mock the client behave deterministically.
    if openai_client is not None:
        embeddings_provider = None
    vector_search_service = create_vector_search_service(
        qdrant_client=qdrant_client,
        collection_name=collection_name,
        min_score=min_score,
        search_config=search_config,
        embeddings_provider=embeddings_provider,
        openai_client=openai_client,
    )
    keyword_search_service = create_keyword_search_service(
        qdrant_client=qdrant_client, collection_name=collection_name
    )
    result_combiner = create_result_combiner(
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        metadata_weight=metadata_weight,
        min_score=min_score,
        spacy_analyzer=spacy_analyzer,
    )

    # Assign to engine
    engine_self.spacy_analyzer = spacy_analyzer
    engine_self.query_processor = query_processor
    engine_self.vector_search_service = vector_search_service
    engine_self.keyword_search_service = keyword_search_service
    engine_self.result_combiner = result_combiner

    # Metadata extractor
    from ...components import MetadataExtractor

    engine_self.metadata_extractor = MetadataExtractor()

    # Pipeline and adapters
    from ..adapters import (
        KeywordSearcherAdapter,
        ResultCombinerAdapter,
        VectorSearcherAdapter,
    )
    from ..pipeline import HybridPipeline

    engine_self.hybrid_pipeline = HybridPipeline(
        vector_searcher=VectorSearcherAdapter(vector_search_service),
        keyword_searcher=KeywordSearcherAdapter(keyword_search_service),
        result_combiner=ResultCombinerAdapter(result_combiner),
        reranker=None,
        booster=None,
        normalizer=None,
        deduplicator=None,
    )

    # Orchestration utilities
    from ..orchestration import HybridOrchestrator, QueryPlanner

    engine_self._planner = QueryPlanner()
    engine_self._orchestrator = HybridOrchestrator()

    # Optional processing toggles
    from ..components.reranking import HybridReranker

    engine_self.processing_config = processing_config
    if engine_self.hybrid_pipeline is not None and processing_config is not None:
        if getattr(processing_config, "enable_reranker", False):
            try:
                engine_self.hybrid_pipeline.reranker = HybridReranker()
            except Exception:
                engine_self.hybrid_pipeline.reranker = None
        if getattr(processing_config, "enable_booster", False):
            from ..components.boosting import ResultBooster

            engine_self.hybrid_pipeline.booster = ResultBooster()
        # Backward-compat: support both enable_normalizer and enable_normalization
        if getattr(processing_config, "enable_normalizer", False) or getattr(
            processing_config, "enable_normalization", False
        ):
            from ..components.normalization import ScoreNormalizer

            engine_self.hybrid_pipeline.normalizer = ScoreNormalizer()
        # Backward-compat: support both enable_deduplicator and enable_deduplication
        if getattr(processing_config, "enable_deduplicator", False) or getattr(
            processing_config, "enable_deduplication", False
        ):
            from ..components.deduplication import ResultDeduplicator

            engine_self.hybrid_pipeline.deduplicator = ResultDeduplicator()

    # Enhanced search components
    engine_self.enable_intent_adaptation = enable_intent_adaptation
    engine_self.knowledge_graph = knowledge_graph
    engine_self.intent_classifier, engine_self.adaptive_strategy = (
        create_intent_components(
            spacy_analyzer, knowledge_graph, enable_intent_adaptation
        )
    )
    if engine_self.enable_intent_adaptation:
        try:
            engine_self.logger.info("Intent-aware adaptive search ENABLED")
        except Exception:
            pass
    else:
        try:
            engine_self.logger.info("Intent-aware adaptive search DISABLED")
        except Exception:
            pass

    # Topic chain generator
    engine_self.topic_chain_generator = create_topic_chain_generator(
        spacy_analyzer, knowledge_graph
    )
    engine_self._topic_chains_initialized = False
    try:
        engine_self.logger.info("Topic-driven search chaining ENABLED")
    except Exception:
        pass

    # Faceted search
    engine_self.faceted_search_engine = create_faceted_engine()
    try:
        engine_self.logger.info("Dynamic faceted search interface ENABLED")
    except Exception:
        pass

    # Cross-document intelligence
    conflict_settings = build_conflict_settings(search_config)
    engine_self.cross_document_engine = create_cdi_engine(
        spacy_analyzer=spacy_analyzer,
        knowledge_graph=knowledge_graph,
        qdrant_client=qdrant_client,
        openai_client=openai_client,
        collection_name=collection_name,
        conflict_settings=conflict_settings,
    )
    # Attach provider for chat operations when available
    try:
        engine_self.cross_document_engine.llm_provider = llm_provider
        # Also link detector back to engine to let llm_validation access provider
        try:
            detector = engine_self.cross_document_engine.conflict_detector
            detector.engine = engine_self
        except Exception:
            pass
    except Exception:
        pass
    try:
        engine_self.logger.info("Cross-document intelligence ENABLED")
    except Exception:
        pass
