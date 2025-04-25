# Chunking Strategy Refactoring Plan

## Overview

This document outlines the plan to refactor the chunking system to support different strategies based on document types. The goal is to improve search relevance by using appropriate chunking methods for different content types.

## Current Architecture

Currently, the system uses a single `ChunkingStrategy` class that implements token-based chunking for all document types. This approach doesn't take into account the specific structure and semantics of different file types.

## Proposed Changes

### 1. Create Base Abstract Class

Create a new abstract base class `BaseChunkingStrategy` that defines the interface for all chunking strategies:

```python
class BaseChunkingStrategy(ABC):
    @abstractmethod
    def chunk_document(self, document: Document) -> list[Document]:
        pass

    @abstractmethod
    def _split_text(self, text: str) -> list[str]:
        pass
```

### 2. Rename Current Implementation

- Rename current `ChunkingStrategy` to `DefaultChunkingStrategy`
- Move it to a new file `default_strategy.py`
- Make it inherit from `BaseChunkingStrategy`

### 3. Create Markdown Strategy

Create a new `MarkdownChunkingStrategy` that:

- Inherits from `BaseChunkingStrategy`
- Splits content based on markdown headers (##)
- Preserves header hierarchy
- Includes section metadata in chunks

### 4. Update ChunkingService

Modify `ChunkingService` to:

- Maintain a registry of strategies
- Select appropriate strategy based on document type
- Fall back to `DefaultChunkingStrategy` when no specific strategy exists

## Implementation Steps

1. **Create Base Strategy**
   - Create new file `base_strategy.py`
   - Implement abstract base class
   - Add documentation and type hints

2. **Refactor Default Strategy**
   - Create new file `default_strategy.py`
   - Move current implementation
   - Update inheritance
   - Add tests

3. **Implement Markdown Strategy**
   - Create new file `markdown_strategy.py`
   - Implement section-based chunking
   - Add tests
   - Document strategy

4. **Update ChunkingService**
   - Add strategy registry
   - Implement strategy selection
   - Add fallback mechanism
   - Update tests

## Testing Strategy

1. **Unit Tests**
   - Test each strategy independently
   - Verify chunking behavior
   - Check metadata preservation

2. **Integration Tests**
   - Test strategy selection
   - Verify fallback behavior
   - Check end-to-end chunking

3. **Search Quality Tests**
   - Compare search scores before/after
   - Verify improvement in markdown search
   - Check other document types

## Migration Plan

1. **Phase 1: Preparation**
   - Create new files
   - Implement base class
   - Add tests

2. **Phase 2: Implementation**
   - Implement strategies
   - Update service
   - Add tests

3. **Phase 3: Testing**
   - Run full test suite
   - Verify search quality
   - Check performance

4. **Phase 4: Deployment**
   - Deploy changes
   - Monitor search quality
   - Gather feedback

## Future Considerations

1. **Additional Strategies**
   - Code-specific strategy
   - JSON/YAML strategy
   - HTML strategy

2. **Performance Optimization**
   - Caching strategies
   - Parallel processing
   - Batch processing

3. **Configuration**
   - Strategy-specific settings
   - Dynamic strategy selection
   - Custom strategy registration

## Success Criteria

1. **Search Quality**
   - Improved search scores for markdown files
   - No degradation for other file types
   - Better semantic understanding

2. **Performance**
   - No significant increase in processing time
   - Efficient strategy selection
   - Minimal memory overhead

3. **Maintainability**
   - Clear separation of concerns
   - Easy to add new strategies
   - Well-documented code
