import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_expand_query_with_expansions(hybrid_search):
    expanded = await hybrid_search._expand_query("product requirements")
    assert "product requirements" in expanded
    assert len(expanded) > len("product requirements")

    expanded = await hybrid_search._expand_query("API documentation")
    assert "API documentation" in expanded
    assert len(expanded) > len("API documentation")

    expanded = await hybrid_search._expand_query("unknown term")
    assert "unknown term" in expanded


@pytest.mark.unit
@pytest.mark.asyncio
async def test_expand_query_case_insensitive(hybrid_search):
    expanded = await hybrid_search._expand_query("PRODUCT REQUIREMENTS")
    expanded_lower = expanded.lower()
    assert any(tok.startswith("product") for tok in expanded_lower.split())
    assert "PRODUCT REQUIREMENTS" in expanded
    assert len(expanded.split()) > len("PRODUCT REQUIREMENTS".split())
