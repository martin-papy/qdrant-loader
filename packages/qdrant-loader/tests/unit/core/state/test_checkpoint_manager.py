"""Unit tests for CheckpointManager (WS-2 checkpointing)."""

import pytest
import pytest_asyncio

from qdrant_loader.core.state.checkpoint_manager import CheckpointManager, Checkpoint


@pytest.mark.asyncio
async def test_checkpoint_crud(state_manager):
    """Save, retrieve, and clear a checkpoint."""
    async with await state_manager.get_session() as session:
        cp_mgr = CheckpointManager(session)

        checkpoint = Checkpoint(
            project_id="project-1",
            source_type="Jira",
            source="jira-main",
            cursor_kind="page_token",
            cursor_value="tok-123",
            batch_index=2,
        )

        # Save checkpoint
        await cp_mgr.save_checkpoint(checkpoint)

        # Retrieve and validate
        got = await cp_mgr.get_checkpoint("project-1", "Jira", "jira-main")
        assert got is not None
        assert got.cursor_kind == "page_token"
        assert got.cursor_value == "tok-123"
        assert got.batch_index == 2

        # Clear and ensure it's gone
        await cp_mgr.clear_checkpoint("project-1", "Jira", "jira-main")
        got2 = await cp_mgr.get_checkpoint("project-1", "Jira", "jira-main")
        assert got2 is None


@pytest.mark.asyncio
async def test_get_all_and_clear_all(state_manager):
    async with await state_manager.get_session() as session:
        cp_mgr = CheckpointManager(session)

        # Create two checkpoints
        cp1 = Checkpoint(
            project_id="pA",
            source_type="Jira",
            source="a",
            cursor_kind="page_token",
            cursor_value="t1",
        )
        cp2 = Checkpoint(
            project_id="pB",
            source_type="Git",
            source="repo1",
            cursor_kind="git_commit",
            cursor_value="c1",
        )

        await cp_mgr.save_checkpoint(cp1)
        await cp_mgr.save_checkpoint(cp2)

        all_cps = await cp_mgr.get_all_checkpoints()
        assert any(c.project_id == "pA" for c in all_cps)
        assert any(c.project_id == "pB" for c in all_cps)

        # Clear all and verify
        await cp_mgr.clear_all_checkpoints()
        all_after = await cp_mgr.get_all_checkpoints()
        assert len(all_after) == 0
