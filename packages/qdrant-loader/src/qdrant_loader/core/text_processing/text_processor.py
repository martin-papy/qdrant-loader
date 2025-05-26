"""Text processing module integrating LangChain, spaCy, and NLTK."""

import nltk
import spacy
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_loader.config import Settings
from qdrant_loader.utils.logging import LoggingConfig
from spacy.cli.download import download

logger = LoggingConfig.get_logger(__name__)

# Performance constants to prevent timeouts
MAX_TEXT_LENGTH_FOR_SPACY = 100_000  # 100KB limit for spaCy processing
MAX_ENTITIES_TO_EXTRACT = 50  # Limit number of entities
MAX_POS_TAGS_TO_EXTRACT = 200  # Limit number of POS tags


class TextProcessor:
    """Text processing service integrating multiple NLP libraries."""

    def __init__(self, settings: Settings):
        """Initialize the text processor with required models and configurations.

        Args:
            settings: Application settings containing configuration for text processing
        """
        self.settings = settings

        # Download required NLTK data
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt")
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            nltk.download("stopwords")

        # Load spaCy model with optimized settings
        try:
            self.nlp = spacy.load("en_core_web_sm")
            # Optimize spaCy pipeline for speed
            # Select only essential components for faster processing
            if "parser" in self.nlp.pipe_names:
                # Keep only essential components: tokenizer, tagger, ner (exclude parser)
                essential_pipes = [
                    pipe for pipe in self.nlp.pipe_names if pipe != "parser"
                ]
                self.nlp.select_pipes(enable=essential_pipes)
        except OSError:
            logger.info("Downloading spaCy model...")
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
            if "parser" in self.nlp.pipe_names:
                # Keep only essential components: tokenizer, tagger, ner (exclude parser)
                essential_pipes = [
                    pipe for pipe in self.nlp.pipe_names if pipe != "parser"
                ]
                self.nlp.select_pipes(enable=essential_pipes)

        # Initialize LangChain text splitter with configuration from settings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.global_config.chunking.chunk_size,
            chunk_overlap=settings.global_config.chunking.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n",
                "\n",
                ".",
                "!",
                "?",
                " ",
                "",
            ],  # Added sentence-ending punctuation
        )

    def process_text(self, text: str) -> dict:
        """Process text using multiple NLP libraries with performance optimizations.

        Args:
            text: Input text to process

        Returns:
            dict: Processed text features including:
                - tokens: List of tokens (limited)
                - entities: List of named entities (limited)
                - pos_tags: List of part-of-speech tags (limited)
                - chunks: List of text chunks
        """
        # Performance check: truncate very long text
        if len(text) > MAX_TEXT_LENGTH_FOR_SPACY:
            logger.debug(
                f"Text too long for spaCy processing ({len(text)} chars), truncating to {MAX_TEXT_LENGTH_FOR_SPACY}"
            )
            text = text[:MAX_TEXT_LENGTH_FOR_SPACY]

        try:
            # Process with spaCy (optimized)
            doc = self.nlp(text)

            # Extract features with limits to prevent timeouts
            tokens = [token.text for token in doc][
                :MAX_POS_TAGS_TO_EXTRACT
            ]  # Limit tokens
            entities = [(ent.text, ent.label_) for ent in doc.ents][
                :MAX_ENTITIES_TO_EXTRACT
            ]  # Limit entities
            pos_tags = [(token.text, token.pos_) for token in doc][
                :MAX_POS_TAGS_TO_EXTRACT
            ]  # Limit POS tags

            # Process with LangChain (fast)
            chunks = self.text_splitter.split_text(text)

            return {
                "tokens": tokens,
                "entities": entities,
                "pos_tags": pos_tags,
                "chunks": chunks,
            }
        except Exception as e:
            logger.warning(f"Text processing failed: {e}")
            # Return minimal results on error
            return {
                "tokens": [],
                "entities": [],
                "pos_tags": [],
                "chunks": [text] if text else [],
            }

    def get_entities(self, text: str) -> list[tuple]:
        """Extract named entities from text using spaCy with performance limits.

        Args:
            text: Input text

        Returns:
            List of (entity_text, entity_type) tuples
        """
        # Performance check: truncate very long text
        if len(text) > MAX_TEXT_LENGTH_FOR_SPACY:
            text = text[:MAX_TEXT_LENGTH_FOR_SPACY]

        try:
            doc = self.nlp(text)
            return [(ent.text, ent.label_) for ent in doc.ents][
                :MAX_ENTITIES_TO_EXTRACT
            ]
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return []

    def get_pos_tags(self, text: str) -> list[tuple]:
        """Get part-of-speech tags using spaCy with performance limits.

        Args:
            text: Input text

        Returns:
            List of (word, pos_tag) tuples
        """
        # Performance check: truncate very long text
        if len(text) > MAX_TEXT_LENGTH_FOR_SPACY:
            text = text[:MAX_TEXT_LENGTH_FOR_SPACY]

        try:
            doc = self.nlp(text)
            return [(token.text, token.pos_) for token in doc][:MAX_POS_TAGS_TO_EXTRACT]
        except Exception as e:
            logger.warning(f"POS tagging failed: {e}")
            return []

    def split_into_chunks(self, text: str, chunk_size: int | None = None) -> list[str]:
        """Split text into chunks using LangChain's text splitter.

        Args:
            text: Input text
            chunk_size: Optional custom chunk size

        Returns:
            List of text chunks
        """
        try:
            if chunk_size:
                # Create a new text splitter with the custom chunk size
                # Ensure chunk_overlap is smaller than chunk_size
                chunk_overlap = min(chunk_size // 4, 50)  # 25% of chunk size, max 50
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len,
                    separators=[
                        "\n\n",
                        "\n",
                        ".",
                        "!",
                        "?",
                        " ",
                        "",
                    ],  # Added sentence-ending punctuation
                )
                return text_splitter.split_text(text)
            return self.text_splitter.split_text(text)
        except Exception as e:
            logger.warning(f"Text splitting failed: {e}")
            # Return the original text as a single chunk on error
            return [text] if text else []
