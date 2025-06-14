# Template String Fixes Progress Tracker

This document tracks the progress of converting template strings to f-strings throughout the qdrant-loader codebase.

## Issue Summary
Template strings like `"Error: {variable}"` need to be converted to f-strings like `f"Error: {variable}"` to ensure proper string formatting. Without the `f` prefix, the template strings are treated as literal strings and variables are not interpolated.

## Progress Overview
- [ ] High Priority (Core functionality) - 5 files
- [ ] Medium Priority (Connectors) - 4 files  
- [ ] Medium Priority (Core modules) - 4 files
- [ ] Lower Priority (Utilities and schemas) - 6 files
- [ ] Special Cases (Need careful review) - 3 files

**Total: 22 files to fix**

---

## High Priority (Core functionality)

### 1. ✅ `packages/qdrant-loader/src/qdrant_loader/core/async_ingestion_pipeline.py`
**Status: PARTIALLY COMPLETED**
- [x] Line 123: `logger.info(f"Initializing metrics directory at {final_metrics_dir}")`
- [x] Line 212: `f"Document processing completed. Processed {len(documents)} documents"`
- [x] Line 217: `logger.error(f"Document processing failed: {e}", exc_info=True)`
- [ ] Line 238: `logger.warning("Error stopping metrics server: {e}")`
- [ ] Line 246: `logger.error("Error during pipeline cleanup: {e}")`
- [ ] Line 254: `logger.error("Error in destructor cleanup: {e}")`
- [ ] Line 269: `logger.error("Error saving metrics: {e}")`
- [ ] Line 275: `logger.error("Error stopping metrics server: {e}")`
- [ ] Line 282: `logger.error("Error in resource manager cleanup: {e}")`

### 2. ⏳ `packages/qdrant-loader/src/qdrant_loader/cli/cli.py`
**Status: PARTIALLY COMPLETED**
- [ ] Line 112: `raise ClickException("Failed to setup logging: {str(e)!s}") from e`
- [ ] Line 158: `raise ClickException("Failed to setup workspace: {str(e)!s}") from e`
- [ ] Line 194: `raise ClickException("Failed to load configuration: {str(e)!s}") from e`
- [ ] Line 212: `_get_logger().info("Created directory: {path.absolute()}")`
- [ ] Line 216: `raise ClickException("Failed to create directory: {str(e)!s}") from e`
- [ ] Line 239: `raise ClickException("Config file not found: {str(config_path)!s}")`
- [ ] Line 251: `"No config file found. Please specify a config file or create config.yaml in the current directory: {str(default_config)!s}"`
- [ ] Line 284: `raise ClickException("Failed to load configuration: {str(e)!s}") from e`
- [ ] Line 323: `raise ClickException("Failed to initialize collection: {str(e)!s}") from e`
- [ ] Line 408: `raise ClickException("Failed to initialize collection: {str(e)!s}") from e`
- [ ] Line 569: `logger.debug(" Awaiting {len(pending)} pending tasks before exit...")`
- [ ] Line 574: `logger.error(" Exception in ingest: {e}")`
- [ ] Line 587: `raise ClickException("Failed to run ingestion: {str(e)!s}") from e`
- [ ] Line 638: `raise ClickException("Failed to display configuration: {str(e)!s}") from e`

### 3. ⏳ `packages/qdrant-loader/src/qdrant_loader/cli/project_commands.py`
**Status: NOT STARTED**
- [ ] Line 125: `raise ClickException("Failed to list projects: {str(e)!s}") from e`
- [ ] Line 169: `raise ClickException("Project '{project_id}' not found")`
- [ ] Line 216: `Panel(project_info, title="Project: {context.project_id}")`
- [ ] Line 222: `raise ClickException("Failed to get project status: {str(e)!s}") from e`
- [ ] Line 259: `raise ClickException("Project '{project_id}' not found")`
- [ ] Line 294: `"Missing source_type for {source_name}"`
- [ ] Line 300: `source_errors.append("Missing source for {source_name}")`
- [ ] Line 302: `source_errors.append("Error in {source_name}: {str(e)}")`
- [ ] Line 331: `"[green]✓[/green] Project '{result['project_id']}' is valid ({result['source_count']} sources)"`
- [ ] Line 335: `"[red]✗[/red] Project '{result['project_id']}' has errors:"`
- [ ] Line 338: `console.print("  [red]•[/red] {error}")`
- [ ] Line 349: `raise ClickException("Failed to validate projects: {str(e)!s}") from e`
- [ ] Line 396: `logger.debug("Creating context for project: {project_id}")`
- [ ] Line 415: `logger.debug("Created context for project: {project_id}")`
- [ ] Line 418: `"Initialized {len(project_manager._project_contexts)} project contexts"`

### 4. ⏳ `packages/qdrant-loader/src/qdrant_loader/config/validator.py`
**Status: NOT STARTED**
- [ ] Line 81: `raise ValueError("Duplicate project ID: f'{project_id}'")`
- [ ] Line 92: `"Duplicate collection name f'{collection_name}' "`
- [ ] Line 93: `"found in project f'{project_id}'"`
- [ ] Line 109: `"Project f'{project_id}' configuration must be a dictionary"`
- [ ] Line 114: `raise ValueError("Project f'{project_id}' must have a 'display_name'")`
- [ ] Line 119: `"Project f'{project_id}' display_name must be a non-empty string"`
- [ ] Line 127: `"Project f'{project_id}' description must be a string or null"`
- [ ] Line 134: `"Project f'{project_id}' collection_name must be a non-empty string"`
- [ ] Line 147: `"Project f'{project_id}' overrides must be a dictionary"`
- [ ] Line 173: `raise ValueError("Source type f'{source_type}' must be a dictionary")`
- [ ] Line 176: `raise ValueError("Source type f'{source_type}' cannot be empty")`
- [ ] Line 182: `"Source f'{source_name}' in f'{source_type}' must be a dictionary"`
- [ ] Line 236: `"Invalid project ID f'{project_id}'. "`
- [ ] Line 245: `"Project ID f'{project_id}' is reserved and may cause conflicts"`
- [ ] Line 267: `"Invalid source name f'{source_name}'. "`
- [ ] Line 287: `"Source f'{source_name}' of type f'{source_type}' "`
- [ ] Line 295: `"Source f'{source_name}' of type f'{source_type}' "`
- [ ] Line 312: `"Collection name f'{collection_name}' is too long (max 255 characters)"`
- [ ] Line 319: `"Invalid collection name f'{collection_name}'. "`

### 5. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/qdrant_manager.py`
**Status: NOT STARTED**
- [ ] Line 107: `self.logger.info("Collection {self.collection_name} already exists")`
- [ ] Line 131: `self.logger.debug("Collection {self.collection_name} created successfully")`

---

## Medium Priority (Connectors)

### 6. ⏳ `packages/qdrant-loader/src/qdrant_loader/connectors/confluence/connector.py`
**Status: NOT STARTED**
- [ ] Line 901: `logger.debug("Failed to parse timestamp f'{timestamp_str}': {e}")`
- [ ] Line 984: `"Processed {len(attachment_docs)} attachments for {content['type']} f'{content['title']}'"`
- [ ] Line 988: `"Failed to process attachments for {content['type']} f'{content['title']}' "`
- [ ] Line 993: `"Processed {content['type']} f'{content['title']}' "`
- [ ] Line 998: `"Failed to process {content['type']} f'{content['title']}' "`
- [ ] Line 1083: `"Processed {len(attachment_docs)} attachments for {content['type']} f'{content['title']}'"`
- [ ] Line 1087: `"Failed to process attachments for {content['type']} f'{content['title']}' "`
- [ ] Line 1092: `"Processed {content['type']} f'{content['title']}' "`
- [ ] Line 1097: `"Failed to process {content['type']} f'{content['title']}' "`

### 7. ⏳ `packages/qdrant-loader/src/qdrant_loader/connectors/jira/connector.py`
**Status: NOT STARTED**
- [ ] Line 270: `jql = jql.replace("{{{key}}}", "f'{formatted_date}'f")`
- [ ] Line 309: `jql += " AND updated >= f'{updated_after.strftime('%Y-%m-%d %H:%M')}'f"`
- [ ] Line 589: `"\nComment by {comment.author.display_name} on {comment.created.strftime('%Y-%m-%d %H:%M')}:"`

### 8. ⏳ `packages/qdrant-loader/src/qdrant_loader/connectors/git/metadata_extractor.py`
**Status: NOT STARTED**
- [ ] Line 210: `self.logger.debug("Content to process:\n{content!s}")`

### 9. ⏳ `packages/qdrant-loader/src/qdrant_loader/connectors/localfile/metadata_extractor.py`
**Status: NOT STARTED**
- [ ] Line 23: `self.logger.debug("Completed metadata extraction for {file_path!s}.")`

---

## Medium Priority (Core modules)

### 10. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/graphiti_manager.py`
**Status: NOT STARTED**
- [ ] Line 84: `"Creating OpenAI LLM client with model: {self.graphiti_config.llm.model}"`
- [ ] Line 114: `"Creating OpenAI embedder with model: {self.graphiti_config.embedder.model}"`
- [ ] Line 151: `"LLM model: {self.graphiti_config.llm.model}, "`
- [ ] Line 152: `"Embedder model: {self.graphiti_config.embedder.model}"`
- [ ] Line 156: `logger.error("Failed to initialize Graphiti client: {e}")`
- [ ] Line 166: `logger.error("Error closing Graphiti client: {e}")`
- [ ] Line 228: `logger.debug("Adding episode: {name} (type: {episode_type.value})")`
- [ ] Line 246: `logger.info("Successfully added episode: {name} with UUID: {episode_uuid}")`
- [ ] Line 250: `logger.error("Failed to add episode {name}: {e}")`
- [ ] Line 281: `logger.debug("Searching knowledge graph: {query}")`
- [ ] Line 290: `logger.info("Search returned {len(results)} results for query: {query}")`
- [ ] Line 294: `logger.error("Search failed for query f'{query}': {e}")`
- [ ] Line 318: `logger.debug("Retrieving {len(node_uuids)} specific nodes")`
- [ ] Line 325: `query="uuid:{uuid}",`
- [ ] Line 331: `logger.warning("Failed to retrieve node {uuid}: {e}")`
- [ ] Line 335: `logger.debug("Retrieving up to {limit} nodes via search")`
- [ ] Line 347: `logger.error("Failed to retrieve nodes: {e}")`
- [ ] Line 371: `logger.debug("Retrieving {len(edge_uuids)} specific edges")`
- [ ] Line 388: `logger.error("Failed to retrieve edges: {e}")`
- [ ] Line 410: `logger.debug("Retrieving entities from episode: {episode_id}")`
- [ ] Line 414: `search_query = "episode:{episode_id}"`
- [ ] Line 417: `type_filter = " OR ".join(["type:{et}" for et in entity_types])`
- [ ] Line 418: `search_query = "({search_query}) AND ({type_filter})"`
- [ ] Line 425: `logger.info("Found {len(results)} entities for episode {episode_id}")`
- [ ] Line 429: `logger.error("Failed to retrieve entities from episode {episode_id}: {e}")`
- [ ] Line 455: `type_filter = " OR ".join(["type:{et}" for et in entity_types])`
- [ ] Line 456: `search_query = "({query}) AND ({type_filter})"`
- [ ] Line 458: `logger.debug("Searching entities with query: {search_query}")`
- [ ] Line 467: `logger.info("Entity search returned {len(results)} results")`
- [ ] Line 471: `logger.error("Entity search failed for query f'{query}': {e}")`

### 11. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/attachment_downloader.py`
**Status: NOT STARTED**
- [ ] Line 215: `delete=False, suffix=file_ext, prefix="attachment_{attachment.id}_"`
- [ ] Line 340: `content = "# {attachment.filename}\n\nFile type: {attachment.mime_type}\nSize: {attachment.size} bytes\n\nThis attachment could not be converted to text."`
- [ ] Line 370: `title="Attachment: {attachment.filename}",`

### 12. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/temporal_manager.py`
**Status: NOT STARTED**
- [ ] Line 94: `"TemporalManager initialized with strategy: {default_strategy.value}"`
- [ ] Line 141: `logger.debug("Added entity {entity.name} with UUID {entity.entity_uuid}")`
- [ ] Line 191: `"Added relationship {relationship.relationship_type.value} with UUID {relationship.relationship_uuid}"`
- [ ] Line 229: `conflict_description="Temporal overlap for entity f'{new_entity.name}' between versionsf",`
- [ ] Line 250: `conflict_description="Attribute conflict for entity f'{new_entity.name}'f",`
- [ ] Line 301: `conflict_description="Temporal overlap for relationship {new_relationship.relationship_type.value}",`
- [ ] Line 347: `"Resolving conflict {conflict.conflict_id} using strategy {conflict.resolution_strategy.value}"`
- [ ] Line 377: `logger.error("Failed to resolve conflict {conflict.conflict_id}: {e}")`
- [ ] Line 378: `conflict.resolution_notes = "Resolution failed: {e}"`
- [ ] Line 403: `"Invalidated conflicting items at {invalidation_time.isoformat()}"`
- [ ] Line 441: `"Latest wins: {winner.temporal_info.transaction_time.isoformat()}"`
- [ ] Line 470: `conflict.resolution_notes = "Highest confidence wins: {highest_confidence}"`
- [ ] Line 699: `errors["entity_{entity_uuid}"] = chain_errors`
- [ ] Line 705: `errors["relationship_{rel_uuid}"] = chain_errors`
- [ ] Line 728: `"Version sequence broken: expected {expected_version}, got {version.temporal_info.version}"`
- [ ] Line 736: `"Supersession chain broken at version {version.temporal_info.version}"`
- [ ] Line 740: `"Reverse supersession chain broken at version {version.temporal_info.version}"`
- [ ] Line 764: `"Version sequence broken: expected {expected_version}, got {version.temporal_info.version}"`
- [ ] Line 775: `"Supersession chain broken at version {version.temporal_info.version}"`
- [ ] Line 779: `"Reverse supersession chain broken at version {version.temporal_info.version}"`
- [ ] Line 803: `"Repaired {repairs['entities']} entity chains and {repairs['relationships']} relationship chains"`
- [ ] Line 917: `logger.warning("Entity {entity_uuid} not found for rollback")`
- [ ] Line 931: `"Version {target_version} not found for entity {entity_uuid}"`
- [ ] Line 963: `logger.info("Rolled back entity {entity_uuid} to version {target_version}")`
- [ ] Line 979: `logger.warning("Relationship {relationship_uuid} not found for rollback")`
- [ ] Line 993: `"Version {target_version} not found for relationship {relationship_uuid}"`
- [ ] Line 1030: `"Rolled back relationship {relationship_uuid} to version {target_version}"`
- [ ] Line 1233: `"Bulk rollback completed: {len(results['successful'])} successful, {len(results['failed'])} failed"`
- [ ] Line 1273: `"Pruned {pruned['entities']} entity versions and {pruned['relationships']} relationship versions"`

### 13. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/monitoring/ingestion_metrics.py`
**Status: NOT STARTED**
- [ ] Line 111: `logger.debug("Started tracking operation {operation_id}")`
- [ ] Line 124: `logger.warning("Attempted to end untracked operation {operation_id}")`
- [ ] Line 137: `logger.debug("Ended tracking operation {operation_id}")`
- [ ] Line 156: `logger.debug("Started tracking batch {batch_id}")`
- [ ] Line 180: `logger.warning("Attempted to end untracked batch {batch_id}")`
- [ ] Line 235: `logger.debug("Ended tracking batch {batch_id}")`
- [ ] Line 267: `logger.debug("Started tracking conversion for {operation_id}: {file_path}")`
- [ ] Line 285: `logger.warning("Attempted to end untracked conversion {operation_id}")`
- [ ] Line 336: `logger.debug("Ended tracking conversion for {operation_id}: success={success}")`
- [ ] Line 361: `"Attempted to update conversion metrics for untracked batch {batch_id}"`
- [ ] Line 371: `logger.debug("Updated conversion metrics for batch {batch_id}")`
- [ ] Line 395: `metrics_file = self.metrics_dir / "ingestion_metrics_{timestamp}.json"`
- [ ] Line 465: `logger.info("Metrics saved to {metrics_file}")`
- [ ] Line 467: `logger.error("Failed to save metrics: {str(e)}")`

---

## Lower Priority (Utilities and schemas)

### 14. ⏳ `packages/qdrant-loader/src/qdrant_loader/schemas/registry.py`
**Status: NOT STARTED**
- [ ] Line 367: `raise ValueError("Invalid schema type: {schema_type}. Must be 'node' or 'edge'")`

### 15. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/document.py`
**Status: NOT STARTED**
- [ ] Line 212: `logger.debug("Normalized string f'{s}' to f'{normalized}'")`

### 16. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/prompts/entity_prompts.py`
**Status: NOT STARTED**
- [ ] Line 381: `logger.warning("No prompt found for domain {domain}, using default")`

### 17. ⏳ `packages/qdrant-loader/src/qdrant_loader/config/models.py`
**Status: NOT STARTED**
- [ ] Line 97: `raise ValueError("Project f'{project_config.project_id}' already exists")`

### 18. ⏳ `packages/qdrant-loader/src/qdrant_loader/connectors/publicdocs/connector.py`
**Status: NOT STARTED**
- [ ] Line 438: `new_code = BeautifulSoup("\n```\n{code_text}\n```\n", "html.parser")`

### 19. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/state/document_state_manager.py`
**Status: NOT STARTED**
- [ ] Line 67: `"Error updating document state: {str(e)}",`
- [ ] Line 77: `"Unexpected error updating document state: {str(e)}",`
- [ ] Line 139: `"Error getting document state: {str(e)}",`
- [ ] Line 149: `"Unexpected error getting document state: {str(e)}",`

### 20. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/neo4j_manager.py`
**Status: NOT STARTED**
- [ ] Line 100: `"Non-retryable exception in {func.__name__}",`
- [ ] Line 109: `"Retry time budget exceeded for {func.__name__}",`
- [ ] Line 133: `"Transient failure in {func.__name__}, retrying",`
- [ ] Line 149: `"Unexpected error: no exception recorded in {func.__name__}"`
- [ ] Line 153: `"All retry attempts exhausted for {func.__name__}",`

### 21. ⏳ `packages/qdrant-loader/src/qdrant_loader/core/state/state_change_detector.py`
**Status: NOT STARTED**
- [ ] Line 38: `"qdrant_loader.{self.__class__.__name__}"`
- [ ] Line 123: `raise InvalidDocumentStateError("Failed to get document state: {e}") from e`
- [ ] Line 203: `return "{source_type}:{source}:{self._normalize_url(url)}"`

---

## Special Cases (Need careful review)

### 22. ⏳ `packages/qdrant-loader/src/qdrant_loader/__init__.py`
**Status: NOT STARTED**
- [ ] Line 45: `raise AttributeError("module f'{__name__}' has no attribute f'{name}'")`
  - **Note**: This uses nested f-strings and needs careful handling

### 23. ⏳ `packages/qdrant-loader/src/qdrant_loader/cli/__init__.py`
**Status: NOT STARTED**
- [ ] Line 25: `raise AttributeError("module f'{__name__}' has no attribute f'{name}'")`
  - **Note**: This uses nested f-strings and needs careful handling

### 24. ⏳ `packages/qdrant-loader/src/qdrant_loader/config/parser.py`
**Status: NOT STARTED**
- [ ] Line 203: `"Invalid project ID f'{project_id}'. "`
  - **Note**: This uses nested f-strings and needs careful handling

### 25. ⏳ `packages/qdrant-loader/src/qdrant_loader/config/__init__.py`
**Status: NOT STARTED**
- [ ] Line 100: `raise AttributeError("module f'{__name__}' has no attribute f'{name}'")`
- [ ] Line 348: `pattern = r"\${([^}]+)}"` (This is a regex pattern, may not need fixing)
- [ ] Line 365: `result = result.replace("${{{var_name}}}", env_value)` (Environment variable substitution)
  - **Note**: Lines 348 and 365 are for environment variable substitution and may be intentional

---

## Completed Files

### ✅ `packages/qdrant-loader/src/qdrant_loader/config/state.py`
**Status: COMPLETED**
- [x] Line 20: `super().__init__(f"Database directory does not exist: {path}")`

### ✅ `packages/qdrant-loader/src/qdrant_loader/connectors/localfile/connector.py`
**Status: COMPLETED**
- [x] Line 132: `self.logger.debug(f"Processed local file: {rel_path}")`
- [x] Line 141: `url=f"file://{os.path.realpath(file_path)}",`

### ✅ `packages/qdrant-loader/tests/unit/connectors/localfile/test_localfile_id_consistency.py`
**Status: COMPLETED**
- [x] All template strings converted to f-strings (34+ lines fixed)

### ✅ `packages/qdrant-loader/src/qdrant_loader/config/graphiti.py`
**Status: COMPLETED**
- [x] Migrated from Pydantic V1 `@validator` to V2 `@field_validator`

---

## Notes

- **Regex patterns**: Some strings with `{}` are regex patterns and should NOT be converted to f-strings
- **Environment variables**: Some `${}` patterns are for environment variable substitution and may be intentional
- **Nested f-strings**: Special cases with nested f-strings need careful review to avoid syntax errors
- **Test priority**: Focus on core functionality first, then connectors, then utilities

## Next Steps

1. Start with high-priority core functionality files
2. Test each file after fixing to ensure no regressions
3. Pay special attention to the "Special Cases" section
4. Update this tracker as progress is made 