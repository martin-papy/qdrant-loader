"""CLI commands package — lazy imports for fast startup."""


def __getattr__(name: str):
    if name == "run_init":
        from .init import run_init

        return run_init
    if name == "run_pipeline_ingestion":
        from .ingest import run_pipeline_ingestion

        return run_pipeline_ingestion
    if name == "serve_cmd":
        from .serve_cmd import serve_cmd

        return serve_cmd
    if name == "jobs_cmd":
        from .jobs_cmd import jobs_cmd

        return jobs_cmd
    if name == "run_webhook_command":
        from .webhook_cmd import run_webhook_command

        return run_webhook_command
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "run_init",
    "run_pipeline_ingestion",
    "serve_cmd",
    "jobs_cmd",
    "run_webhook_command",
]
