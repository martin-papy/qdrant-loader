"""CLI commands package — lazy imports for fast startup."""


def __getattr__(name: str):
    if name == "run_init":
        from .init import run_init

        return run_init
    if name == "run_pipeline_ingestion":
        from .ingest import run_pipeline_ingestion

        return run_pipeline_ingestion
    if name == "run_webhook_command":
        from .webhook_cmd import run_webhook_command

        return run_webhook_command
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "run_init",
    "run_pipeline_ingestion",
    "run_webhook_command",
]
