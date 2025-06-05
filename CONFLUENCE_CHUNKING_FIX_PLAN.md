# Confluence Chunking Fix Plan - Issue #27

## Problem Summary

**Issue**: Confluence documents always result in single chunk regardless of the chunking size specified in configuration.

**Reporter**: mikecirioli  
**GitHub Issue**: #27  
**Branch**: `fix/confluence-chunking-issue-27`

## Problem Analysis

### Root Cause

1. **Content Type**: Confluence documents have `content_type="html"` (set in `confluence/connector.py` line 803)
2. **Strategy Selection**: This triggers the `HTMLChunkingStrategy` in the chunking service
3. **Semantic vs Size-based**: HTML strategy chunks based on semantic HTML elements, not character count
4. **Single Element Issue**: Confluence pages often have a single large semantic element containing all content

### Current Behavior vs Expected

- **Current**: Single chunk of 1190-3456 characters regardless of `chunk_size: 100`
- **Expected**: Multiple chunks of ~100 characters each with `chunk_overlap: 20`

### Key Code Locations

1. **Strategy Selection**: `chunking_service.py` lines 95-130
2. **HTML Strategy**: `html_strategy.py` - semantic-based chunking implementation
3. **Confluence Connector**: `confluence/connector.py` line 803 - sets content_type
4. **Configuration**: Global config chunking settings

## Technical Deep Dive

### HTML Strategy Current Logic

```python
# In _parse_html_structure method
if (
    tag_name in self.section_elements
    or tag_name in self.heading_elements
    or tag_name in self.block_elements
):
    text_content = element.get_text(strip=True)
```

### Constants and Thresholds

- `MAX_HTML_SIZE_FOR_PARSING = 500_000` (500KB)
- `SIMPLE_PARSING_THRESHOLD = 100_000` (100KB)
- `MAX_SECTIONS_TO_PROCESS = 200`

### Strategy Selection Logic

```python
# In chunking_service.py
file_type = document.content_type.lower()  # "html" for Confluence
strategy_class = self.strategies.get(file_type)  # HTMLChunkingStrategy
```

## Implementation Plan

### Phase 1: Analysis and Preparation ✅ **COMPLETED**

**🔍 CRITICAL DISCOVERY: The reported issue does NOT exist in the current codebase!**

1. ✅ **Created comprehensive test cases** to reproduce the issue with Confluence-like HTML content
2. ✅ **Analyzed typical Confluence HTML structure** to understand common patterns  
3. ✅ **Reviewed existing fallback mechanisms** in the HTML strategy

**Test Results:**

- Original content: 2,334 characters
- Configured chunk_size: 100 characters  
- **Actual result: 35 chunks** (not 1 as reported!)
- Average chunk size: 78.0 characters
- All chunk sizes properly respect the 100-character limit

**Additional Testing:**

- ✅ Large paragraphs (1910+ chars) split into 22+ sections
- ✅ Edge cases (empty, nested divs, tables) work correctly
- ✅ Multiple chunk sizes (50, 100, 200, 500, 1000) all work properly

**Possible Explanations for User's Report:**

1. Issue was fixed in a recent update
2. User has different configuration/environment
3. User's specific HTML structure differs from our tests
4. Version-specific behavior

**Recommendation:** Contact the user to verify their current version and configuration before proceeding with implementation.

### Phase 2: Core Solution Implementation

#### Option A: Enhanced HTML Strategy (Recommended)

- Modify `HTMLChunkingStrategy` to respect `chunk_size` when semantic elements are too large
- Add hybrid approach: semantic chunking + size-based splitting for large sections
- Implement Confluence-specific HTML parsing logic

#### Option B: Confluence-Specific Strategy

- Create new `ConfluenceChunkingStrategy` extending `HTMLChunkingStrategy`
- Add Confluence-specific logic for handling their HTML structure
- Modify strategy selection to use this for Confluence documents

#### Option C: Configuration-Based Approach

- Add configuration option to force size-based chunking over semantic chunking
- Allow users to choose between semantic and size-based chunking per source

### Phase 3: Implementation Details

#### Enhanced HTML Strategy (Option A - Recommended)

**1. Modify `_split_text` method** in `html_strategy.py`:

```python
def _split_text(self, html: str) -> list[dict[str, Any]]:
    """Split HTML text into chunks based on semantic structure with size limits."""
    # ... existing semantic parsing ...
    
    # After getting merged_sections, apply size-based splitting if needed
    final_sections = []
    for section in merged_sections:
        content_size = len(section.get("text_content", ""))
        
        # If section exceeds chunk_size, split it while preserving semantic info
        if content_size > self.chunk_size:
            split_parts = self._split_large_semantic_section(section, self.chunk_size)
            final_sections.extend(split_parts)
        else:
            final_sections.append(section)
    
    return final_sections
```

**2. Enhance `_split_large_section` method**:

- Improve current implementation to better handle HTML content
- Preserve HTML structure while splitting by size
- Add overlap support for better context preservation

**3. Add new method `_split_large_semantic_section`**:

```python
def _split_large_semantic_section(self, section: dict, max_size: int) -> list[dict]:
    """Split a large semantic section while preserving metadata."""
    # Extract text content
    text_content = section.get("text_content", "")
    
    # Split by size with overlap
    chunks = self._split_text_with_overlap(text_content, max_size, self.chunk_overlap)
    
    # Create section dictionaries for each chunk
    split_sections = []
    for i, chunk in enumerate(chunks):
        split_section = section.copy()
        split_section.update({
            "content": chunk,
            "text_content": chunk,
            "title": f"{section.get('title', 'Section')} (Part {i+1})",
            "is_split_section": True,
            "original_section_size": len(text_content),
            "split_index": i,
            "total_splits": len(chunks)
        })
        split_sections.append(split_section)
    
    return split_sections
```

**4. Add configuration options**:

```python
class ChunkingConfig:
    chunk_size: int = 1500
    chunk_overlap: int = 200
    prefer_semantic_chunking: bool = True
    max_semantic_chunk_size: int = 3000  # 2x chunk_size
    force_size_based_chunking: bool = False
    confluence_specific_handling: bool = True
```

**5. Improve strategy selection logic**:

```python
def _get_strategy(self, document: Document) -> BaseChunkingStrategy:
    # Special handling for Confluence documents if configured
    if (document.source_type == SourceType.CONFLUENCE and 
        self.config.chunking.force_size_based_chunking):
        self.logger.info("Using size-based chunking for Confluence document")
        return DefaultChunkingStrategy(self.settings)
    
    # ... existing logic ...
```

### Phase 4: Testing Strategy

#### Unit Tests

1. **Test with typical Confluence HTML structures**:
   - Single large div with all content
   - Nested semantic elements
   - Mixed content types (text, lists, tables)

2. **Test with various chunk sizes**:
   - Small chunks (100 characters)
   - Medium chunks (500 characters)
   - Large chunks (1500 characters)

3. **Test edge cases**:
   - Very large pages (>100KB)
   - Empty or minimal content
   - Malformed HTML

#### Integration Tests

1. **Test with real Confluence documents**
2. **Verify chunk count and sizes match expectations**
3. **Test with different configuration options**

#### Performance Tests

1. **Ensure no significant performance impact**
2. **Test with large Confluence pages**
3. **Memory usage validation**

### Phase 5: Documentation and Configuration

1. **Update documentation** explaining new chunking behavior
2. **Add configuration examples** for different use cases
3. **Create migration guide** for existing users
4. **Update README with Confluence-specific notes**

## Specific Code Changes Required

### 1. New Configuration Options

```yaml
global_config:
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
    # New options
    prefer_semantic_chunking: true
    max_semantic_chunk_size: 3000
    force_size_based_chunking: false
    confluence_specific_handling: true
```

### 2. Enhanced HTML Strategy Methods

- `_split_large_semantic_section()` - New method
- `_split_text_with_overlap()` - Enhanced text splitting
- `_should_split_semantic_section()` - Decision logic
- Enhanced `_split_text()` method

### 3. Strategy Selection Updates

- Add Confluence-specific logic in `_get_strategy()`
- Configuration-based strategy override
- Logging improvements for debugging

### 4. Test Files

- `test_confluence_chunking.py` - Specific test cases
- Enhanced `test_html_strategy.py` - Additional test scenarios
- Integration tests for end-to-end validation

## Implementation Priority

### High Priority

1. **Fix core issue** with size-based splitting in HTML strategy
2. **Add basic configuration** for enabling/disabling new behavior
3. **Create comprehensive tests** to validate the fix

### Medium Priority

1. **Add advanced configuration options** for fine-tuning
2. **Optimize performance** for large documents
3. **Improve error handling** and logging

### Low Priority

1. **Create Confluence-specific optimizations**
2. **Add metrics and monitoring** for chunking performance
3. **Documentation and examples**

## Success Criteria

### Functional Requirements

1. **Confluence documents** with `chunk_size: 100` should produce multiple chunks of ~100 characters
2. **Chunk overlap** should work correctly with the new splitting logic
3. **Semantic information** should be preserved in chunk metadata
4. **Backward compatibility** maintained for existing configurations

### Performance Requirements

1. **No significant performance degradation** (< 10% increase in processing time)
2. **Memory usage** should remain reasonable for large documents
3. **Scalability** maintained for high-volume processing

### Quality Requirements

1. **Test coverage** > 90% for new code
2. **Documentation** updated and comprehensive
3. **Configuration validation** and error handling

## Risk Mitigation

### Technical Risks

1. **Feature Flags**: Use configuration to enable/disable new behavior
2. **Gradual Rollout**: Implement as opt-in first, then make default
3. **Fallback Mechanisms**: Robust fallback to existing behavior if new logic fails

### Performance Risks

1. **Benchmarking**: Measure performance impact before and after
2. **Optimization**: Profile and optimize critical paths
3. **Monitoring**: Add metrics to track performance in production

### Compatibility Risks

1. **Versioning**: Proper semantic versioning for breaking changes
2. **Migration Path**: Clear upgrade instructions for users
3. **Testing**: Extensive testing with various HTML structures

## Timeline Estimate

- **Phase 1 (Analysis)**: 1-2 days
- **Phase 2 (Core Implementation)**: 3-4 days
- **Phase 3 (Testing)**: 2-3 days
- **Phase 4 (Documentation)**: 1-2 days
- **Total**: 7-11 days

## Next Steps

1. **Start with Phase 1**: Create test cases to reproduce the issue
2. **Implement Option A**: Enhanced HTML Strategy approach
3. **Validate with real Confluence content**: Test with actual documents
4. **Iterate based on results**: Refine implementation as needed
5. **Create PR**: Submit for review once testing is complete

---

**Created**: 2025-01-06  
**Last Updated**: 2025-01-06  
**Status**: Planning Phase  
**Assignee**: Development Team
