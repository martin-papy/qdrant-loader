import pytest

from qdrant_loader_mcp_server.search.hybrid.components.combining import HybridCombiner


@pytest.mark.unit
def test_combiner_preserves_order():
    combiner = HybridCombiner()
    combined = combiner.combine([1, 2], [3, 4])
    assert combined == [1, 2, 3, 4]


@pytest.mark.unit
def test_combiner_two_empty_lists_returns_empty():
    combiner = HybridCombiner()
    assert combiner.combine([], []) == []


@pytest.mark.unit
def test_combiner_empty_and_non_empty_lists():
    combiner = HybridCombiner()
    assert combiner.combine([], [1, 2, 3]) == [1, 2, 3]
    assert combiner.combine([1, 2, 3], []) == [1, 2, 3]


@pytest.mark.unit
def test_combiner_none_inputs_raise_type_error():
    combiner = HybridCombiner()
    with pytest.raises(TypeError):
        combiner.combine(None, [1])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        combiner.combine([1], None)  # type: ignore[arg-type]


@pytest.mark.unit
def test_combiner_preserves_duplicates_and_order():
    combiner = HybridCombiner()
    combined = combiner.combine([1, 1, 2], [1])
    assert combined == [1, 1, 2, 1]


@pytest.mark.unit
def test_combiner_large_lists_length_and_integrity():
    combiner = HybridCombiner()
    left = list(range(10000))
    right = list(range(10000, 20000))
    combined = combiner.combine(left, right)
    assert len(combined) == len(left) + len(right)
    # Verify integrity and order
    assert combined[: len(left)] == left
    assert combined[len(left) :] == right


@pytest.mark.unit
def test_combiner_non_iterable_inputs_raise_type_error():
    combiner = HybridCombiner()
    with pytest.raises(TypeError):
        combiner.combine(123, [1, 2])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        combiner.combine([1, 2], 123)  # type: ignore[arg-type]

