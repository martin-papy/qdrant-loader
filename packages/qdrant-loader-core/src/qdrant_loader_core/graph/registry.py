from qdrant_loader_core.graph.extractor.base_extractor import EntityExtractor
from qdrant_loader_core.graph.extractor.confluence import ConfluenceEntityExtractor
from qdrant_loader_core.graph.extractor.git import GitEntityExtractor
from qdrant_loader_core.graph.extractor.jira import JiraEntityExtractor
from qdrant_loader_core.graph.extractor.localfile import LocalFileEntityExtractor
from qdrant_loader_core.graph.extractor.publicdocs import PublicDocsEntityExtractor

EntityExtractor.register_extractor("jira", JiraEntityExtractor)
EntityExtractor.register_extractor("confluence", ConfluenceEntityExtractor)
EntityExtractor.register_extractor("git", GitEntityExtractor)
EntityExtractor.register_extractor("localfile", LocalFileEntityExtractor)
EntityExtractor.register_extractor("publicdocs", PublicDocsEntityExtractor)
