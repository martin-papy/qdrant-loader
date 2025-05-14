"""Text processing module integrating LangChain, spaCy, and NLTK."""

import nltk
import spacy
from spacy.cli.download import download
from typing import List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document as LangChainDocument
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class TextProcessor:
    """Text processing service integrating multiple NLP libraries."""

    def __init__(self):
        """Initialize the text processor with required models and configurations."""
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')

        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.info("Downloading spaCy model...")
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

        # Initialize LangChain text splitter with smaller default chunk size
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Reduced from 1000
            chunk_overlap=50,  # Reduced from 200
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", " ", ""]  # Added sentence-ending punctuation
        )

    def process_text(self, text: str) -> dict:
        """Process text using multiple NLP libraries.

        Args:
            text: Input text to process

        Returns:
            dict: Processed text features including:
                - tokens: List of tokens
                - entities: List of named entities
                - pos_tags: List of part-of-speech tags
                - chunks: List of text chunks
        """
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract features
        tokens = [token.text for token in doc]
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        pos_tags = [(token.text, token.pos_) for token in doc]

        # Process with LangChain
        chunks = self.text_splitter.split_text(text)

        return {
            "tokens": tokens,
            "entities": entities,
            "pos_tags": pos_tags,
            "chunks": chunks
        }

    def get_entities(self, text: str) -> List[tuple]:
        """Extract named entities from text using spaCy.

        Args:
            text: Input text

        Returns:
            List of (entity_text, entity_type) tuples
        """
        doc = self.nlp(text)
        return [(ent.text, ent.label_) for ent in doc.ents]

    def get_pos_tags(self, text: str) -> List[tuple]:
        """Get part-of-speech tags using spaCy.

        Args:
            text: Input text

        Returns:
            List of (word, pos_tag) tuples
        """
        doc = self.nlp(text)
        return [(token.text, token.pos_) for token in doc]

    def split_into_chunks(self, text: str, chunk_size: Optional[int] = None) -> List[str]:
        """Split text into chunks using LangChain's text splitter.

        Args:
            text: Input text
            chunk_size: Optional custom chunk size

        Returns:
            List of text chunks
        """
        if chunk_size:
            # Create a new text splitter with the custom chunk size
            # Ensure chunk_overlap is smaller than chunk_size
            chunk_overlap = min(chunk_size // 4, 50)  # 25% of chunk size, max 50
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", " ", ""]  # Added sentence-ending punctuation
            )
            return text_splitter.split_text(text)
        return self.text_splitter.split_text(text) 