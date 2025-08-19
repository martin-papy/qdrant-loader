from __future__ import annotations

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
        all_sources.update(sources_config.publicdocs)
        all_sources.update(sources_config.git)
        all_sources.update(sources_config.confluence)
        all_sources.update(sources_config.jira)
        all_sources.update(sources_config.localfile)
        return all_sources

    if project_id:
        context = project_manager.get_project_context(project_id)
        contexts = {project_id: context} if context else {}
    else:
        contexts = project_manager.get_all_project_contexts()

    validation_results = []
    all_valid = True
    for context in contexts.values():
        if not context or not context.config:
            validation_results.append(
                {
                    "project_id": getattr(context, "project_id", project_id),
                    "valid": False,
                    "errors": ["Missing project configuration"],
                    "source_count": 0,
                }
            )
            all_valid = False
            continue

        source_errors: list[str] = []
        all_sources = _get_all_sources_from_config(context.config.sources)
        for source_name, source_config in all_sources.items():
            try:
                if not getattr(source_config, "source_type", None):
                    source_errors.append(f"Missing source_type for {source_name}")
                if not getattr(source_config, "source", None):
                    source_errors.append(f"Missing source for {source_name}")
            except Exception as e:
                source_errors.append(f"Error in {source_name}: {str(e)}")

        validation_results.append(
            {
                "project_id": context.project_id,
                "valid": len(source_errors) == 0,
                "errors": source_errors,
                "source_count": len(all_sources),
            }
        )
        if source_errors:
            all_valid = False

    return validation_results, all_valid


