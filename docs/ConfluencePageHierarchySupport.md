# Confluence Page Hierarchy Support

This document demonstrates how the enhanced Confluence connector now captures and stores page hierarchy information, making search results more meaningful and contextual.

## What's New

The Confluence connector now extracts and stores the following hierarchy information for each page:

- **Parent page ID and title**
- **Complete ancestor chain** (from root to immediate parent)
- **Child pages** (direct children only)
- **Depth level** in the hierarchy
- **Breadcrumb trail** for navigation context

## Metadata Structure

Each Confluence document now includes the following hierarchy metadata:

```python
{
    "hierarchy": {
        "ancestors": [
            {"id": "111111", "title": "Root Page", "type": "page"},
            {"id": "222222", "title": "Parent Page", "type": "page"}
        ],
        "parent_id": "222222",
        "parent_title": "Parent Page", 
        "children": [
            {"id": "333333", "title": "Child Page 1", "type": "page"},
            {"id": "444444", "title": "Child Page 2", "type": "page"}
        ],
        "depth": 2,
        "breadcrumb": ["Root Page", "Parent Page"]
    },
    "parent_id": "222222",
    "parent_title": "Parent Page",
    "ancestors": [...],
    "children": [...],
    "depth": 2,
    "breadcrumb": ["Root Page", "Parent Page"],
    "breadcrumb_text": "Root Page > Parent Page"
}
```

## Document Convenience Methods

The Document class now provides convenient methods to work with hierarchy:

```python
# Check hierarchy position
document.is_root_document()  # True if no parent
document.has_children()      # True if has child pages
document.get_depth()         # Depth level (0 = root)

# Get hierarchy information
document.get_parent_id()     # Parent page ID
document.get_parent_title()  # Parent page title
document.get_breadcrumb()    # List of ancestor titles
document.get_breadcrumb_text()  # "Root > Parent > Current"
document.get_ancestors()     # Full ancestor chain
document.get_children()      # Direct child pages

# Get formatted context
document.get_hierarchy_context()  # "Path: Root > Parent | Depth: 2 | Children: 3"
```

## Enhanced Search Capabilities

With hierarchy information, you can now perform more contextual searches:

### 1. Search with Context

When displaying search results, include the breadcrumb for better context:

```python
for result in search_results:
    print(f"📄 {result.title}")
    if result.get_breadcrumb_text():
        print(f"   📍 {result.get_breadcrumb_text()}")
    print(f"   {result.content[:200]}...")
```

### 2. Filter by Hierarchy Level

Find documents at specific hierarchy levels:

```python
# Find all root pages (documentation sections)
root_pages = [doc for doc in documents if doc.is_root_document()]

# Find all leaf pages (detailed content)
leaf_pages = [doc for doc in documents if not doc.has_children()]

# Find pages at specific depth
level_2_pages = [doc for doc in documents if doc.get_depth() == 2]
```

### 3. Related Content Discovery

Find related content based on hierarchy:

```python
def find_related_content(document, all_documents):
    related = []
    
    # Add parent page
    parent_id = document.get_parent_id()
    if parent_id:
        parent = next((d for d in all_documents if d.metadata.get("id") == parent_id), None)
        if parent:
            related.append(("parent", parent))
    
    # Add sibling pages (same parent)
    if parent_id:
        siblings = [d for d in all_documents 
                   if d.get_parent_id() == parent_id and d.id != document.id]
        related.extend([("sibling", s) for s in siblings])
    
    # Add child pages
    child_ids = [child["id"] for child in document.get_children()]
    children = [d for d in all_documents if d.metadata.get("id") in child_ids]
    related.extend([("child", c) for c in children])
    
    return related
```

### 4. Hierarchical Search Results

Group and organize search results by hierarchy:

```python
def organize_by_hierarchy(search_results):
    # Group by root ancestor
    hierarchy_groups = {}
    
    for result in search_results:
        ancestors = result.get_ancestors()
        root_title = ancestors[0]["title"] if ancestors else result.title
        
        if root_title not in hierarchy_groups:
            hierarchy_groups[root_title] = []
        hierarchy_groups[root_title].append(result)
    
    # Sort within each group by depth and title
    for group in hierarchy_groups.values():
        group.sort(key=lambda x: (x.get_depth(), x.title))
    
    return hierarchy_groups
```

### 5. Breadcrumb-Enhanced Search

Include breadcrumb information in search queries for better context matching:

```python
def enhanced_search_query(document):
    # Include breadcrumb context in search
    query_parts = [document.content]
    
    breadcrumb = document.get_breadcrumb_text()
    if breadcrumb:
        query_parts.append(f"Context: {breadcrumb}")
    
    return " ".join(query_parts)
```

## Example Use Cases

### Documentation Navigation

```python
# Find all pages under "API Documentation" section
api_docs = [doc for doc in documents 
           if any("API Documentation" in ancestor["title"] 
                  for ancestor in doc.get_ancestors())]

# Show hierarchical structure
for doc in api_docs:
    indent = "  " * doc.get_depth()
    print(f"{indent}📄 {doc.title}")
```

### Content Completeness Analysis

```python
# Find sections that might need more content (few or no children)
incomplete_sections = [doc for doc in documents 
                      if doc.get_depth() <= 2 and len(doc.get_children()) < 3]
```

### Search Result Ranking

```python
def calculate_relevance_score(document, query, base_score):
    score = base_score
    
    # Boost root pages (likely more important)
    if document.is_root_document():
        score *= 1.2
    
    # Boost pages with many children (comprehensive content)
    if len(document.get_children()) > 5:
        score *= 1.1
    
    # Boost if query matches breadcrumb (contextual relevance)
    if any(query.lower() in ancestor["title"].lower() 
           for ancestor in document.get_ancestors()):
        score *= 1.15
    
    return score
```

## Benefits

1. **Better Context**: Users understand where content fits in the overall documentation structure
2. **Improved Navigation**: Easy to find related content (parent, siblings, children)
3. **Smarter Search**: Results can be organized and ranked based on hierarchy
4. **Content Discovery**: Find gaps in documentation or related topics
5. **User Experience**: More intuitive browsing with breadcrumb navigation

The hierarchy information is automatically extracted from Confluence and stored in the document metadata, making all these enhanced search capabilities available without any additional configuration.
