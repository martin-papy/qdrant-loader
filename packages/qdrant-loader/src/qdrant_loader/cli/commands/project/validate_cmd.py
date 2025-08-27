from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def run_project_validate(
    settings: Any,
    project_manager: Any,
    *,
    project_id: str | None,
) -> tuple[list[dict[str, object]], bool]:
    """Validate projects and return (results, all_valid)."""

    def _get_all_sources_from_config(sources_config):
        all_sources = {}
        if not sources_config:
            return all_sources
        for name in ("publicdocs", "git", "confluence", "jira", "localfile"):
            value = getattr(sources_config, name, None)
            if isinstance(value, dict):
                all_sources.update(value)
        return all_sources

    if project_id:
        context = project_manager.get_project_context(project_id)
        contexts = {project_id: context} if context else {}
    else:
        contexts = project_manager.get_all_project_contexts()

    validation_results = []
    all_valid = True
    for key, context in contexts.items():
        if not context or not getattr(context, "config", None):
            validation_results.append(
                {
                    "project_id": (
                        context.project_id
                        if context and hasattr(context, "project_id")
                        else key
                    ),
                    "valid": False,
                    "errors": ["Missing project configuration"],
                    "source_count": 0,
                }
            )
            all_valid = False
            continue

        source_errors: list[str] = []
        sources_cfg = context.config.sources if context and context.config else None
        all_sources = _get_all_sources_from_config(sources_cfg)
        for source_name, source_config in all_sources.items():
            try:
                if isinstance(source_config, Mapping):
                    source_type = source_config.get("source_type")
                    source_val = source_config.get("source")
                else:
                    source_type = getattr(source_config, "source_type", None)
                    source_val = getattr(source_config, "source", None)

                if not source_type:
                    source_errors.append(f"Missing source_type for {source_name}")
                if not source_val:
                    source_errors.append(f"Missing source for {source_name}")
            except Exception as e:
                source_errors.append(f"Error in {source_name}: {str(e)}")

        validation_results.append(
            {
                "project_id": (
                    context.project_id
                    if context and hasattr(context, "project_id")
                    else key
                ),
                "valid": len(source_errors) == 0,
                "errors": source_errors,
                "source_count": len(all_sources),
            }
        )
        if source_errors:
            all_valid = False

    return validation_results, all_valid
