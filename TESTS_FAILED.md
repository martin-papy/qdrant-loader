================================================================================================================== warnings summary ==================================================================================================================
packages/qdrant-loader/tests/unit/cli/test_validation_commands.py::TestValidationCommands::test_validate_graph_error_handling
  /Users/martin.papy/.pyenv/versions/3.12.2/lib/python3.12/unittest/mock.py:767: RuntimeWarning: coroutine '_run_validation' was never awaited
    def __setattr__(self, name, value):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

packages/qdrant-loader/tests/unit/core/validation_repair/test_event_integration.py::TestEventHandling::test_on_entity_extracted_success
  /Users/martin.papy/.pyenv/versions/3.12.2/lib/python3.12/unittest/mock.py:2185: RuntimeWarning: coroutine 'ValidationEventIntegrator._handle_pending_validation' was never awaited
    def __init__(self, name, parent):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

packages/qdrant-loader/tests/unit/core/validation_repair/test_event_integration.py::TestBatchValidationLogic::test_handle_pending_validation_threshold_reached
  /Users/martin.papy/.pyenv/versions/3.12.2/lib/python3.12/unittest/mock.py:478: RuntimeWarning: coroutine 'ValidationEventIntegrator._handle_pending_validation' was never awaited
    _safe_super(NonCallableMock, self).__init__(
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

packages/qdrant-loader/tests/unit/core/validation_repair/test_event_integration.py::TestValidationEventHandlers::test_on_validation_completed
  /Users/martin.papy/.pyenv/versions/3.12.2/lib/python3.12/unittest/mock.py:1020: RuntimeWarning: coroutine 'ValidationEventIntegrator._delayed_validation_trigger' was never awaited
    def _get_child_mock(self, /, **kw):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

packages/qdrant-loader/tests/unit/core/validation_repair/test_scheduler.py::TestValidationScheduler::test_context_manager
  /Users/martin.papy/.pyenv/versions/3.12.2/lib/python3.12/selectors.py:192: RuntimeWarning: coroutine 'ValidationScheduler._wait_for_jobs_completion' was never awaited
    raise KeyError("{!r} is not registered".format(fileobj)) from None
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html