import asyncio

from qdrant_loader.webhooks.queue_backend import SINGLE_DELETE, SINGLE_UPSERT
from qdrant_loader.webhooks.single_event_handler import parse_webhook_event


def test_parse_jira_issue_updated():
    event = asyncio.run(
        parse_webhook_event(
            "jira",
            "my-jira",
            {
                "webhookEvent": "jira:issue_updated",
                "issue": {"key": "TEST-1"},
            },
        )
    )
    assert event is not None
    assert event.operation == SINGLE_UPSERT
    assert event.entity_id == "TEST-1"
    assert event.source == "my-jira"


def test_parse_jira_issue_deleted():
    event = asyncio.run(
        parse_webhook_event(
            "jira",
            "my-jira",
            {
                "webhookEvent": "jira:issue_deleted",
                "issue": {"key": "TEST-2"},
            },
        )
    )
    assert event is not None
    assert event.operation == SINGLE_DELETE


def test_parse_returns_none_for_unknown_event():
    event = asyncio.run(
        parse_webhook_event(
            "jira",
            "my-jira",
            {"webhookEvent": "jira:comment_created", "issue": {"key": "X-1"}},
        )
    )
    assert event is None
