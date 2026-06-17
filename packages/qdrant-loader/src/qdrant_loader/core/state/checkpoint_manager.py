"""Checkpoint manager for resumable ingestion (WS-2 feature)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qdrant_loader.core.state.models import IngestionCheckpoint
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class Checkpoint:
    """Represents a checkpoint for resumable ingestion."""

    project_id: str
    source_type: str
    source: str
    cursor_kind: str  # page_token | jql_window | git_commit | since_ts
    cursor_value: str
    batch_index: int = 0
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "project_id": self.project_id,
            "source_type": self.source_type,
            "source": self.source,
            "cursor_kind": self.cursor_kind,
            "cursor_value": self.cursor_value,
            "batch_index": self.batch_index,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_db(cls, db_record: IngestionCheckpoint) -> "Checkpoint":
        """Create a Checkpoint instance from database record."""
        return cls(
            project_id=db_record.project_id,
            source_type=db_record.source_type,
            source=db_record.source,
            cursor_kind=db_record.cursor_kind,
            cursor_value=db_record.cursor_value,
            batch_index=db_record.batch_index,
            updated_at=db_record.updated_at,
        )


class CheckpointManager:
    """Manages ingestion checkpoints for resumable runs."""

    def __init__(self, session: AsyncSession):
        """Initialize checkpoint manager.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def get_checkpoint(
        self, project_id: str, source_type: str, source: str
    ) -> Checkpoint | None:
        """Get the latest checkpoint for a source.

        Args:
            project_id: Project ID
            source_type: Type of source (jira, confluence, etc.)
            source: Source name/identifier

        Returns:
            Checkpoint if exists, None otherwise
        """
        try:
            stmt = select(IngestionCheckpoint).where(
                and_(
                    IngestionCheckpoint.project_id == project_id,
                    IngestionCheckpoint.source_type == source_type,
                    IngestionCheckpoint.source == source,
                )
            )
            result = await self.session.execute(stmt)
            db_record = result.scalar_one_or_none()

            if db_record:
                checkpoint = Checkpoint.from_db(db_record)
                logger.info(
                    "Found checkpoint for resumption",
                    project_id=project_id,
                    source_type=source_type,
                    source=source,
                    cursor_kind=checkpoint.cursor_kind,
                    batch_index=checkpoint.batch_index,
                )
                return checkpoint
            else:
                logger.debug(
                    "No checkpoint found for source",
                    project_id=project_id,
                    source_type=source_type,
                    source=source,
                )
                return None
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to retrieve checkpoint",
                project_id=project_id,
                source_type=source_type,
                source=source,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save or update a checkpoint after successful batch upsert.

        Args:
            checkpoint: Checkpoint to save

        Raises:
            Exception: If database operation fails
        """
        try:
            # Set updated_at to now if not provided
            if checkpoint.updated_at is None:
                checkpoint.updated_at = datetime.now(UTC)

            # Try to fetch existing checkpoint
            stmt = select(IngestionCheckpoint).where(
                and_(
                    IngestionCheckpoint.project_id == checkpoint.project_id,
                    IngestionCheckpoint.source_type == checkpoint.source_type,
                    IngestionCheckpoint.source == checkpoint.source,
                )
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing checkpoint
                existing.cursor_kind = checkpoint.cursor_kind
                existing.cursor_value = checkpoint.cursor_value
                existing.batch_index = checkpoint.batch_index
                existing.updated_at = checkpoint.updated_at
                await self.session.merge(existing)
                logger.debug(
                    "Updated checkpoint",
                    project_id=checkpoint.project_id,
                    source_type=checkpoint.source_type,
                    source=checkpoint.source,
                    cursor_value=checkpoint.cursor_value,
                    batch_index=checkpoint.batch_index,
                )
            else:
                # Create new checkpoint
                db_checkpoint = IngestionCheckpoint(
                    project_id=checkpoint.project_id,
                    source_type=checkpoint.source_type,
                    source=checkpoint.source,
                    cursor_kind=checkpoint.cursor_kind,
                    cursor_value=checkpoint.cursor_value,
                    batch_index=checkpoint.batch_index,
                    updated_at=checkpoint.updated_at,
                )
                self.session.add(db_checkpoint)
                logger.debug(
                    "Created new checkpoint",
                    project_id=checkpoint.project_id,
                    source_type=checkpoint.source_type,
                    source=checkpoint.source,
                    cursor_value=checkpoint.cursor_value,
                    batch_index=checkpoint.batch_index,
                )

            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to save checkpoint",
                project_id=checkpoint.project_id,
                source_type=checkpoint.source_type,
                source=checkpoint.source,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def clear_checkpoint(
        self, project_id: str, source_type: str, source: str
    ) -> None:
        """Clear checkpoint after successful clean run completion.

        Args:
            project_id: Project ID
            source_type: Type of source (jira, confluence, etc.)
            source: Source name/identifier

        Raises:
            Exception: If database operation fails
        """
        try:
            stmt = select(IngestionCheckpoint).where(
                and_(
                    IngestionCheckpoint.project_id == project_id,
                    IngestionCheckpoint.source_type == source_type,
                    IngestionCheckpoint.source == source,
                )
            )
            result = await self.session.execute(stmt)
            db_record = result.scalar_one_or_none()

            if db_record:
                await self.session.delete(db_record)
                await self.session.commit()
                logger.info(
                    "Cleared checkpoint on successful completion",
                    project_id=project_id,
                    source_type=source_type,
                    source=source,
                )
            else:
                logger.debug(
                    "No checkpoint to clear",
                    project_id=project_id,
                    source_type=source_type,
                    source=source,
                )
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to clear checkpoint",
                project_id=project_id,
                source_type=source_type,
                source=source,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_all_checkpoints(self) -> list[Checkpoint]:
        """Get all active checkpoints (useful for monitoring/debugging).

        Returns:
            List of all checkpoints in the database
        """
        try:
            stmt = select(IngestionCheckpoint)
            result = await self.session.execute(stmt)
            db_records = result.scalars().all()
            return [Checkpoint.from_db(record) for record in db_records]
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to retrieve all checkpoints",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def clear_all_checkpoints(self) -> None:
        """Clear all checkpoints (useful for admin/reset operations).

        Raises:
            Exception: If database operation fails
        """
        try:
            stmt = select(IngestionCheckpoint)
            result = await self.session.execute(stmt)
            records = result.scalars().all()
            for record in records:
                await self.session.delete(record)
            await self.session.commit()
            logger.info("Cleared all ingestion checkpoints", count=len(records))
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to clear all checkpoints",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
