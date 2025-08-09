"""Configuration for text chunking."""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class DefaultStrategyConfig(BaseModel):
    """Configuration for default text chunking strategy."""

    min_chunk_size: int = Field(
        default=100, description="Minimum chunk size in characters", gt=0
    )
    enable_semantic_analysis: bool = Field(
        default=True, description="Enable semantic analysis for text chunks"
    )
    enable_entity_extraction: bool = Field(
        default=True, description="Enable entity extraction from text"
    )


class HtmlStrategyConfig(BaseModel):
    """Configuration for HTML chunking strategy."""

    simple_parsing_threshold: int = Field(
        default=100000,
        description="Size threshold for simple vs complex HTML parsing",
        gt=0,
    )
    max_html_size_for_parsing: int = Field(
        default=500000,
        description="Maximum HTML size for complex parsing (bytes)",
        gt=0,
    )
    max_sections_to_process: int = Field(
        default=200, description="Maximum number of sections to process", gt=0
    )
    max_chunk_size_for_nlp: int = Field(
        default=20000,
        description="Maximum chunk size for NLP processing (characters)",
        gt=0,
    )
    preserve_semantic_structure: bool = Field(
        default=True, description="Preserve HTML semantic structure in chunks"
    )


class CodeStrategyConfig(BaseModel):
    """Configuration for code chunking strategy."""

    max_file_size_for_ast: int = Field(
        default=75000,
        description="Maximum file size for AST parsing (characters)",
        gt=0,
    )
    max_elements_to_process: int = Field(
        default=800, description="Maximum number of code elements to process", gt=0
    )
    max_recursion_depth: int = Field(
        default=8, description="Maximum AST recursion depth", gt=0
    )
    max_element_size: int = Field(
        default=20000,
        description="Maximum size for individual code elements (characters)",
        gt=0,
    )
    enable_ast_parsing: bool = Field(
        default=True, description="Enable AST parsing for code analysis"
    )
    enable_dependency_analysis: bool = Field(
        default=True, description="Enable dependency analysis for code"
    )


class JsonStrategyConfig(BaseModel):
    """Configuration for JSON chunking strategy."""

    max_json_size_for_parsing: int = Field(
        default=1000000, description="Maximum JSON size for parsing (bytes)", gt=0
    )
    max_objects_to_process: int = Field(
        default=200, description="Maximum number of JSON objects to process", gt=0
    )
    max_chunk_size_for_nlp: int = Field(
        default=20000,
        description="Maximum chunk size for NLP processing (characters)",
        gt=0,
    )
    max_recursion_depth: int = Field(
        default=5, description="Maximum recursion depth for nested structures", gt=0
    )
    max_array_items_per_chunk: int = Field(
        default=50, description="Maximum array items to include per chunk", gt=0
    )
    max_object_keys_to_process: int = Field(
        default=100, description="Maximum object keys to process", gt=0
    )
    enable_schema_inference: bool = Field(
        default=True, description="Enable JSON schema inference"
    )


class MarkdownStrategyConfig(BaseModel):
    """Configuration for Markdown chunking strategy."""

    min_content_length_for_nlp: int = Field(
        default=100,
        description="Minimum content length for NLP processing (characters)",
        gt=0,
    )
    min_word_count_for_nlp: int = Field(
        default=20, description="Minimum word count for NLP processing", gt=0
    )
    min_line_count_for_nlp: int = Field(
        default=3, description="Minimum line count for NLP processing", gt=0
    )
    min_section_size: int = Field(
        default=500, description="Minimum characters for a standalone section", gt=0
    )
    max_chunks_per_section: int = Field(
        default=1000,
        description="Maximum chunks per section (prevents runaway chunking)",
        gt=0,
    )
    max_overlap_percentage: float = Field(
        default=0.25,
        description="Maximum overlap between chunks as percentage (0.25 = 25%)",
        ge=0.0,
        le=1.0,
    )
    max_workers: int = Field(
        default=4, description="Maximum worker threads for parallel processing", gt=0
    )
    estimation_buffer: float = Field(
        default=0.2,
        description="Buffer factor for chunk count estimation (0.2 = 20%)",
        ge=0.0,
        le=1.0,
    )
    words_per_minute_reading: int = Field(
        default=200, description="Words per minute for reading time estimation", gt=0
    )
    header_analysis_threshold_h1: int = Field(
        default=3,
        description="H1 header count threshold for split level decisions",
        gt=0,
    )
    header_analysis_threshold_h3: int = Field(
        default=8,
        description="H3 header count threshold for split level decisions",
        gt=0,
    )
    enable_hierarchical_metadata: bool = Field(
        default=True, description="Enable extraction of hierarchical section metadata"
    )


class StrategySpecificConfig(BaseModel):
    """Strategy-specific configuration settings."""

    default: DefaultStrategyConfig = Field(
        default_factory=DefaultStrategyConfig,
        description="Configuration for default text chunking strategy",
    )
    html: HtmlStrategyConfig = Field(
        default_factory=HtmlStrategyConfig,
        description="Configuration for HTML chunking strategy",
    )
    code: CodeStrategyConfig = Field(
        default_factory=CodeStrategyConfig,
        description="Configuration for code chunking strategy",
    )
    json_strategy: JsonStrategyConfig = Field(
        default_factory=JsonStrategyConfig,
        description="Configuration for JSON chunking strategy",
        alias="json",
    )
    markdown: MarkdownStrategyConfig = Field(
        default_factory=MarkdownStrategyConfig,
        description="Configuration for Markdown chunking strategy",
    )


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""

    chunk_size: int = Field(
        default=1500,
        description="Size of text chunks in characters",
        gt=0,
        title="Chunk Size",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks in characters",
        ge=0,
        title="Chunk Overlap",
    )
    max_chunks_per_document: int = Field(
        default=500,
        description="Maximum number of chunks per document (safety limit)",
        gt=0,
        title="Max Chunks Per Document",
    )

    # Strategy-specific configurations
    strategies: StrategySpecificConfig = Field(
        default_factory=StrategySpecificConfig,
        description="Strategy-specific configuration settings",
    )

    @field_validator("chunk_overlap")
    def validate_chunk_overlap(cls, v: int, info: ValidationInfo) -> int:
        """Validate that chunk overlap is less than chunk size."""
        chunk_size = info.data.get("chunk_size", 1500)
        if v >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v
