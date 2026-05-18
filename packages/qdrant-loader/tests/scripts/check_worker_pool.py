from __future__ import annotations

import argparse
import asyncio
import logging
import time
from pathlib import Path

from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.session import (
    create_tables,
    dispose_engine,
    initialize_engine_and_session,
)
from qdrant_loader.core.worker.pool import QueueWorkerPool
from qdrant_loader.core.worker.queue import SQLiteJobQueue

LOG = logging.getLogger("qa.worker.pool")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="qa_worker_pool.db")
    parser.add_argument("--jobs", type=int, default=40)
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--lease-seconds", type=int, default=60)
    parser.add_argument("--same-source", action="store_true")
    parser.add_argument("--fail-every", type=int, default=0)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    db_path = Path(args.db).resolve()
    cfg = StateManagementConfig(database_path=str(db_path))
    engine, session_factory = initialize_engine_and_session(cfg)
    await create_tables(engine)
    queue = SQLiteJobQueue(session_factory)

    # 1) Prepare jobs
    for i in range(args.jobs):
        if args.same_source:
            source = "jira-main"
        else:
            source = f"source-{i % 10}"
        payload = {"source": source, "seq": i}
        await queue.enqueue("INCREMENTAL_PULL", payload)

    active_total = 0
    max_active_total = 0
    active_by_source: dict[str, int] = {}
    max_by_source: dict[str, int] = {}
    guard = asyncio.Lock()

    async def handler(job_type: str, payload: dict) -> None:
        nonlocal active_total, max_active_total
        source = str(payload.get("source", "unknown"))
        seq = int(payload.get("seq", -1))
        start = time.perf_counter()

        async with guard:
            active_total += 1
            max_active_total = max(max_active_total, active_total)
            now_active_src = active_by_source.get(source, 0) + 1
            active_by_source[source] = now_active_src
            max_by_source[source] = max(max_by_source.get(source, 0), now_active_src)

        LOG.info(
            "START job_type=%s source=%s seq=%s active_total=%s active_source=%s",
            job_type,
            source,
            seq,
            active_total,
            active_by_source[source],
        )

        try:
            await asyncio.sleep(0.05)

            if args.fail_every > 0 and seq % args.fail_every == 0:
                raise RuntimeError(f"forced failure for seq={seq}")

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            LOG.info("END   source=%s seq=%s elapsed_ms=%s", source, seq, elapsed_ms)
        finally:
            async with guard:
                active_total -= 1
                active_by_source[source] -= 1

    # 2) Configure worker_count here
    pool = QueueWorkerPool(
        queue=queue,
        handler=handler,
        worker_count=args.worker_count,
        lease_seconds=args.lease_seconds,
    )

    processed = await pool.run_until_empty()
    done = await queue.list(status=SQLiteJobQueue.DONE, limit=100000)
    failed = await queue.list(status=SQLiteJobQueue.FAILED, limit=100000)
    running = await queue.list(status=SQLiteJobQueue.RUNNING, limit=100000)

    LOG.info(
        "SUMMARY processed=%s done=%s failed=%s running=%s",
        processed,
        len(done),
        len(failed),
        len(running),
    )
    LOG.info("SUMMARY max_active_total=%s", max_active_total)

    # Print per-source max concurrency for QA evidence
    for src in sorted(max_by_source.keys()):
        LOG.info("SUMMARY source=%s max_active=%s", src, max_by_source[src])

    await dispose_engine(engine)


if __name__ == "__main__":
    asyncio.run(main())
