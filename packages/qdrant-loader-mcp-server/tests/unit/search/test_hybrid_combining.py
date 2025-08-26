import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_combine_results(hybrid_search):
    vector_results = [
        {
            "score": 0.8,
            "text": "Test content 1",
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        }
    ]

    keyword_results = [
        {
            "score": 0.6,
            "text": "Test content 1",
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        },
        {
            "score": 0.4,
            "text": "Test content 2",
            "metadata": {"title": "Doc 2"},
            "source_type": "confluence",
        },
    ]

    query_context = {"is_question": False, "probable_intent": "informational"}

    results = await hybrid_search._combine_results(
        vector_results, keyword_results, query_context, 5
    )

    assert len(results) == 1
    assert results[0].vector_score == 0.8
    assert results[0].keyword_score == 0.6
    assert results[0].score == pytest.approx(0.66, abs=0.01)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_combine_results_with_source_filter(hybrid_search):
    vector_results = [
        {
            "score": 0.8,
            "text": "Git content",
            "metadata": {"title": "Git Doc"},
            "source_type": "git",
        }
    ]

    keyword_results = [
        {
            "score": 0.6,
            "text": "Confluence content",
            "metadata": {"title": "Confluence Doc"},
            "source_type": "confluence",
        }
    ]

    query_context = {"is_question": False}

    results = await hybrid_search._combine_results(
        vector_results, keyword_results, query_context, 5, source_types=["git"]
    )

    assert len(results) == 1
    assert results[0].source_type == "git"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_combine_results_with_low_min_score(hybrid_search):
    hybrid_search.min_score = 0.1

    vector_results = [
        {
            "score": 0.8,
            "text": "Test content 1",
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        }
    ]

    keyword_results = [
        {
            "score": 0.6,
            "text": "Test content 1",
            "metadata": {"title": "Doc 1"},
            "source_type": "git",
        },
        {
            "score": 0.4,
            "text": "Test content 2",
            "metadata": {"title": "Doc 2"},
            "source_type": "confluence",
        },
    ]

    query_context = {"is_question": False, "probable_intent": "informational"}

    results = await hybrid_search._combine_results(
        vector_results, keyword_results, query_context, 5
    )

    assert len(results) == 2
    assert results[0].vector_score == 0.8
    assert results[0].keyword_score == 0.6
    assert results[0].score == pytest.approx(0.66, abs=0.01)
    assert results[1].vector_score == 0.0
    assert results[1].keyword_score == 0.4
    assert results[1].score == pytest.approx(0.12, abs=0.01)
