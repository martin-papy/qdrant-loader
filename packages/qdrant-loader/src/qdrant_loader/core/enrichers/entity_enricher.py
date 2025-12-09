"""Entity extraction enricher using spaCy NER.

POC2-003: Entity enricher following Haystack's EntityExtractor pattern.

This enricher extracts named entities from document content using spaCy's
named entity recognition (NER) capabilities. It adds structured entity
metadata that can be used for:

1. Faceted search (filter by person, organization, location)
2. Knowledge graph construction
3. Document clustering by entities
4. Semantic understanding enhancement
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import spacy
from spacy.cli.download import download

from .base_enricher import BaseEnricher, EnricherConfig, EnricherPriority, EnricherResult

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.core.document import Document

logger = LoggingConfig.get_logger(__name__)


# Entity type categories for grouping
ENTITY_CATEGORIES = {
    "PERSON": "people",
    "ORG": "organizations",
    "GPE": "locations",
    "LOC": "locations",
    "FAC": "locations",
    "PRODUCT": "products",
    "EVENT": "events",
    "WORK_OF_ART": "works",
    "LAW": "legal",
    "LANGUAGE": "languages",
    "DATE": "dates",
    "TIME": "times",
    "PERCENT": "percentages",
    "MONEY": "monetary",
    "QUANTITY": "quantities",
    "ORDINAL": "ordinals",
    "CARDINAL": "numbers",
    "NORP": "groups",  # Nationalities, religious/political groups
}


@dataclass
class EntityEnricherConfig(EnricherConfig):
    """Configuration specific to the entity enricher.

    Attributes:
        spacy_model: spaCy model to use for NER
        max_entities: Maximum number of entities to extract per category
        min_entity_length: Minimum character length for entity text
        include_categories: Entity categories to include (None = all)
        exclude_categories: Entity categories to exclude
        deduplicate: Whether to remove duplicate entities
        include_positions: Whether to include character positions
    """

    spacy_model: str = "en_core_web_sm"
    max_entities: int = 50
    min_entity_length: int = 2
    include_categories: list[str] | None = None
    exclude_categories: list[str] = field(default_factory=list)
    deduplicate: bool = True
    include_positions: bool = False


class EntityEnricher(BaseEnricher):
    """Extracts named entities from document content.

    This enricher uses spaCy's NER to identify entities like people,
    organizations, locations, dates, etc. Entities are structured
    for efficient filtering and search.

    Output metadata keys:
        - entities: List of {text, type, category} dicts
        - entity_types: Dict mapping type -> list of entity texts
        - entity_count: Total number of unique entities
        - has_people: Boolean if document mentions people
        - has_organizations: Boolean if document mentions orgs
        - has_locations: Boolean if document mentions places

    Example output:
        {
            "entities": [
                {"text": "Microsoft", "type": "ORG", "category": "organizations"},
                {"text": "Bill Gates", "type": "PERSON", "category": "people"},
            ],
            "entity_types": {
                "ORG": ["Microsoft"],
                "PERSON": ["Bill Gates"],
            },
            "entity_count": 2,
            "has_people": True,
            "has_organizations": True,
            "has_locations": False,
        }
    """

    def __init__(
        self,
        settings: "Settings",
        config: EntityEnricherConfig | None = None,
    ):
        """Initialize the entity enricher.

        Args:
            settings: Application settings
            config: Entity enricher configuration
        """
        config = config or EntityEnricherConfig()
        config.priority = EnricherPriority.HIGH
        super().__init__(settings, config)

        self.entity_config: EntityEnricherConfig = config
        self._nlp: spacy.Language | None = None

    @property
    def name(self) -> str:
        return "entity_enricher"

    @property
    def nlp(self) -> spacy.Language:
        """Lazy-load the spaCy model."""
        if self._nlp is None:
            model_name = self.entity_config.spacy_model
            try:
                self._nlp = spacy.load(model_name)
                self.logger.debug(f"Loaded spaCy model: {model_name}")
            except OSError:
                self.logger.info(f"Downloading spaCy model: {model_name}")
                download(model_name)
                self._nlp = spacy.load(model_name)

            # Optimize: disable components we don't need
            # Keep only NER for entity extraction
            disable = [p for p in self._nlp.pipe_names if p not in ["ner", "tok2vec"]]
            if disable:
                self._nlp.disable_pipes(*disable)
                self.logger.debug(f"Disabled spaCy pipes: {disable}")

        return self._nlp

    def should_process(self, document: "Document") -> tuple[bool, str | None]:
        """Check if document should be processed for entities.

        Override to add entity-specific filtering.
        """
        should, reason = super().should_process(document)
        if not should:
            return should, reason

        # Skip very short documents
        if len(document.content) < 50:
            return False, "content_too_short"

        # Skip code files (entities in code aren't usually useful)
        file_name = document.metadata.get("file_name", "")
        code_extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"}
        if any(file_name.endswith(ext) for ext in code_extensions):
            return False, "code_file"

        return True, None

    async def enrich(self, document: "Document") -> EnricherResult:
        """Extract named entities from the document.

        Args:
            document: Document to process

        Returns:
            EnricherResult with entity metadata
        """
        try:
            content = document.content

            # Process with spaCy
            doc = self.nlp(content)

            # Extract entities
            entities: list[dict[str, str]] = []
            entity_types: dict[str, list[str]] = {}
            seen: set[tuple[str, str]] = set()

            for ent in doc.ents:
                # Apply filters
                if len(ent.text) < self.entity_config.min_entity_length:
                    continue

                if self.entity_config.include_categories:
                    if ent.label_ not in self.entity_config.include_categories:
                        continue

                if ent.label_ in self.entity_config.exclude_categories:
                    continue

                # Deduplicate
                key = (ent.text.lower(), ent.label_)
                if self.entity_config.deduplicate and key in seen:
                    continue
                seen.add(key)

                # Check max entities per type
                if ent.label_ not in entity_types:
                    entity_types[ent.label_] = []

                if len(entity_types[ent.label_]) >= self.entity_config.max_entities:
                    continue

                # Build entity dict
                entity_dict: dict[str, Any] = {
                    "text": ent.text,
                    "type": ent.label_,
                    "category": ENTITY_CATEGORIES.get(ent.label_, "other"),
                }

                if self.entity_config.include_positions:
                    entity_dict["start"] = ent.start_char
                    entity_dict["end"] = ent.end_char

                entities.append(entity_dict)
                entity_types[ent.label_].append(ent.text)

            # Build metadata
            metadata = {
                "entities": entities,
                "entity_types": entity_types,
                "entity_count": len(entities),
                "has_people": bool(entity_types.get("PERSON")),
                "has_organizations": bool(entity_types.get("ORG")),
                "has_locations": bool(
                    entity_types.get("GPE") or
                    entity_types.get("LOC") or
                    entity_types.get("FAC")
                ),
            }

            return EnricherResult(metadata=metadata)

        except Exception as e:
            self.logger.warning(f"Entity extraction failed: {e}")
            return EnricherResult.error_result(str(e))

    def get_metadata_keys(self) -> list[str]:
        """Return metadata keys produced by this enricher."""
        return [
            "entities",
            "entity_types",
            "entity_count",
            "has_people",
            "has_organizations",
            "has_locations",
        ]

    async def shutdown(self) -> None:
        """Clean up spaCy resources."""
        self._nlp = None
