# Get logger for this module
from typing import Any

from qdrant_loader_core.logging import LoggingConfig

logger = LoggingConfig.get_logger("src.mcp.intelligence_handler")


async def handle_find_ticket_dependencies(
    self, request_id: str | int | None, params: dict[str, Any]
):
    """
    Traverse Jira blocking dependencies
    """

    if "ticket_key" not in params:
        logger.error("Missing required parameter: ticket_key")
        return self.protocol.create_response(
            request_id,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: ticket_key",
            },
        )

    if "depth" not in params:
        logger.error("Missing required parameter: depth")
        return self.protocol.create_response(
            request_id, error={"code": -32602, "message": "Invalid params"}
        )

    depth = params.get("depth")
    ticket_key = params.get("ticket_key")

    if not isinstance(depth, int):
        logger.error("Invalid depth parameter type")
        return self.protocol.create_response(
            request_id,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "depth must be an integer",
            },
        )

    query_params = {
        "ticket_key": ticket_key,
        "depth": depth,
    }
    try:
        depth = self._validate_depth(depth)

        query = f"""
            MATCH path =
                (start:Document {{id: $ticket_key}})
                -[:LINKS_TO*1..{depth}]->
                (target)
            RETURN
                nodes(path),
                relationships(path)
            """

        result = await self._run_graph_query(query, query_params)

        formatted = self.formatters.format_graph(result)

        return self.protocol.create_response(
            request_id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Found {len(formatted.get('nodes', []))} "
                            f"nodes and {len(formatted.get('edges', []))} edges"
                        ),
                    }
                ],
                "structuredContent": formatted,
                "isError": False,
            },
        )

    except ValueError as e:
        return self.protocol.create_response(
            request_id,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": str(e),
            },
        )

    except Exception:
        logger.exception("Error querying graph")
        return self.protocol.create_response(
            request_id,
            error={
                "code": -32603,
                "message": "Internal server error",
            },
        )
