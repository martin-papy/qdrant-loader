from dataclasses import dataclass

from qdrant_loader_mcp_server.search.enhanced.cdi.models import DocumentSimilarity
from qdrant_loader_mcp_server.search.enhanced.cdi.pipeline import CrossDocumentPipeline


@dataclass
class DummySimilarityComputer:
    def compute(self, a, b):
        return DocumentSimilarity(doc1_id="a", doc2_id="b", similarity_score=1.0)


def test_pipeline_similarity_route():
    pipe = CrossDocumentPipeline(similarity_computer=DummySimilarityComputer())
    result = pipe.compute_similarity(object(), object())
    assert result.similarity_score == 1.0
