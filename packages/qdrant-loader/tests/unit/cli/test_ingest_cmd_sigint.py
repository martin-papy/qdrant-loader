from __future__ import annotations

import asyncio
import signal
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_sigint_handler_schedules_cancellation_unix_path(mocker):
    from qdrant_loader.cli.commands import ingest_cmd as ingest_module

    # Patch environment dependencies to keep the command lightweight
    mocker.patch.object(ingest_module, "_load_config_with_workspace", return_value=None)
    mocker.patch.object(ingest_module, "validate_workspace_flags", return_value=None)
    mocker.patch("qdrant_loader.config.get_settings", return_value=SimpleNamespace())
    mocker.patch("qdrant_loader.core.qdrant_manager.QdrantManager", return_value=object())

    # Make the pipeline run short and non-blocking
    async def _fake_run_pipeline(*_args, **_kwargs):
        await asyncio.sleep(0.05)

    mocker.patch.object(ingest_module, "_run_ingest_pipeline", side_effect=_fake_run_pipeline)

    # Track that the cancellation helper was scheduled and executed
    cancellation_called = asyncio.Event()

    async def _fake_cancel_all_tasks():
        cancellation_called.set()

    mocker.patch.object(ingest_module, "_cancel_all_tasks_helper", side_effect=_fake_cancel_all_tasks)

    loop = asyncio.get_running_loop()

    captured = {"callback": None, "sig": None}

    def _fake_add_signal_handler(sig, callback):
        captured["sig"] = sig
        captured["callback"] = callback

    # Intercept signal handler registration (Unix path)
    mocker.patch.object(loop, "add_signal_handler", side_effect=_fake_add_signal_handler)

    # Prevent awaiting unrelated framework tasks that can cause hangs in tests
    mocker.patch.object(ingest_module.asyncio, "all_tasks", return_value=[])

    # Start the command
    task = asyncio.create_task(
        ingest_module.run_ingest_command(
            workspace=None,
            config=None,
            env=None,
            project=None,
            source_type=None,
            source=None,
            log_level="INFO",
            profile=False,
            force=False,
        )
    )

    # Wait for handler to be registered
    for _ in range(100):
        if captured["callback"] is not None:
            break
        await asyncio.sleep(0)

    assert captured["sig"] == signal.SIGINT
    assert callable(captured["callback"])  # type: ignore

    # Simulate SIGINT and allow loop to schedule the cancellation helper
    captured["callback"]()  # type: ignore
    await asyncio.wait_for(cancellation_called.wait(), timeout=1.0)

    # Ensure command completes cleanly
    await asyncio.wait_for(task, timeout=2.0)


@pytest.mark.asyncio
async def test_sigint_handler_schedules_cancellation_windows_fallback(mocker):
    from qdrant_loader.cli.commands import ingest_cmd as ingest_module

    # Patch environment dependencies to keep the command lightweight
    mocker.patch.object(ingest_module, "_load_config_with_workspace", return_value=None)
    mocker.patch.object(ingest_module, "validate_workspace_flags", return_value=None)
    mocker.patch("qdrant_loader.config.get_settings", return_value=SimpleNamespace())
    mocker.patch("qdrant_loader.core.qdrant_manager.QdrantManager", return_value=object())

    async def _fake_run_pipeline(*_args, **_kwargs):
        await asyncio.sleep(0.05)

    mocker.patch.object(ingest_module, "_run_ingest_pipeline", side_effect=_fake_run_pipeline)

    cancellation_called = asyncio.Event()

    async def _fake_cancel_all_tasks():
        cancellation_called.set()

    mocker.patch.object(ingest_module, "_cancel_all_tasks_helper", side_effect=_fake_cancel_all_tasks)

    loop = asyncio.get_running_loop()

    # Force Windows fallback path by raising NotImplementedError on add_signal_handler
    mocker.patch.object(loop, "add_signal_handler", side_effect=NotImplementedError)

    captured = {"handler": None}

    def _fake_signal(sig, handler):
        if sig == signal.SIGINT:
            captured["handler"] = handler
        return None

    mocker.patch.object(signal, "signal", side_effect=_fake_signal)

    # Prevent awaiting unrelated framework tasks that can cause hangs in tests
    mocker.patch.object(ingest_module.asyncio, "all_tasks", return_value=[])

    task = asyncio.create_task(
        ingest_module.run_ingest_command(
            workspace=None,
            config=None,
            env=None,
            project=None,
            source_type=None,
            source=None,
            log_level="INFO",
            profile=False,
            force=False,
        )
    )

    # Wait for fallback handler to be registered
    for _ in range(100):
        if captured["handler"] is not None:
            break
        await asyncio.sleep(0)

    assert callable(captured["handler"])  # type: ignore

    # Simulate SIGINT via fallback handler and ensure cancellation helper runs
    captured["handler"](signal.SIGINT, None)  # type: ignore
    await asyncio.wait_for(cancellation_called.wait(), timeout=1.0)

    # Ensure command completes cleanly
    await asyncio.wait_for(task, timeout=2.0)


