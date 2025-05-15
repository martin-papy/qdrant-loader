# Semantic Search LDA Batching & Optimization Plan

## Background

Recent log analysis of the ingestion pipeline revealed severe performance and stability issues due to inefficient LDA topic modeling. The current approach retrains an LDA model for every document or tiny batch, causing major slowdowns and frequent failures (e.g., 'index out of bounds' errors). This plan outlines the steps to batch LDA topic modeling, fix model update bugs, and optimize the semantic analysis pipeline.

---

## Goals

- **Batch LDA topic modeling**: Train the LDA model on the entire corpus of Markdown documents at once, not per document or small batch.
- **Fix LDA model update logic**: Resolve dictionary/model size mismatches and ensure robust, consistent topic modeling.
- **Improve performance**: Reduce runtime and resource usage during ingestion.
- **Increase stability**: Eliminate model update errors and prevent resource exhaustion.

---

## Implementation Steps

### 1. Refactor LDA Topic Modeling Pipeline

- **Current State**: LDA is trained or updated for each document or very small batch, leading to inefficiency and errors.
- **Target State**: LDA is trained once on the full set of Markdown documents, and the resulting model is used for topic inference on each document.

#### Tasks

- [x] Refactor the chunking/semantic analysis logic to collect all Markdown documents before LDA training.
  - Created new `TopicModeler` class to handle batched LDA topic modeling
  - Updated `MarkdownChunkingStrategy` to utilize the new class
- [x] Train a single LDA model on the full corpus.
  - Implemented in `TopicModeler` class with proper corpus collection
- [x] For each document, infer topics using the trained model (do not retrain or update per document).
  - Added inference methods in `TopicModeler` class
- [x] Ensure the dictionary is built from the full corpus and reused for all inference steps.
  - Dictionary is now built once during model training and reused

### 2. Fix LDA Model Update Bug

- **Issue**: 'index X is out of bounds for axis 1 with size Y' error during model update.
- **Root Cause**: Dictionary/model size mismatch when updating or reusing the LDA model.

#### Tasks

- [x] Audit the code for all places where the LDA model is updated or reused.
- [x] Ensure the dictionary and corpus are consistent and not rebuilt per document.
- [x] Add robust error handling and logging for model update steps.
- [ ] Add unit tests for edge cases (e.g., empty documents, dictionary changes).

### 3. Optimize Logging and Resource Usage

- [x] Reduce verbosity of LDA training logs (especially in production mode).
- [ ] Monitor memory and CPU usage during batch LDA training.
- [ ] Add metrics for LDA training time and resource consumption.

### 4. Fallback for Small Batches

- [x] If the corpus is very small (e.g., <5 documents), skip LDA or use a simpler topic extraction method.
- [x] Log a warning if LDA is skipped due to insufficient data.

### 5. Testing & Validation

- [ ] Add/expand unit and integration tests for the new batching logic.
- [ ] Validate that all documents receive topic assignments after batching.
- [ ] Test with both small and large Markdown corpora.
- [ ] Ensure no 'index out of bounds' or similar errors occur.
- [ ] Measure and document performance improvements.

---

## Deliverables

- [x] Refactored ingestion pipeline with batched LDA topic modeling
- [x] Bugfix for LDA model update logic
- [ ] Improved logging and metrics for LDA steps
- [x] Documentation of new pipeline and fallback logic
- [ ] Test coverage for all new/changed code

---

## Timeline & Milestones

1. **Design & Planning**: 1 day ✅
2. **Refactor batching logic**: 2 days ✅
3. **Fix model update bug**: 1 day ✅
4. **Logging/metrics improvements**: 0.5 day (In Progress)
5. **Testing & validation**: 1 day (Pending)
6. **Documentation**: 0.5 day (In Progress)

**Total Estimate:** 6 days (3.5 days completed)

---

## Risks & Mitigations

- **Risk**: LDA batching may require significant refactoring of the ingestion pipeline.
  - *Mitigation*: ✅ Changes successfully isolated to semantic analysis/chunking modules
- **Risk**: Edge cases (e.g., very small or empty corpora) may cause failures.
  - *Mitigation*: ✅ Fallback logic implemented for small corpora
- **Risk**: Performance gains may not meet expectations if other bottlenecks exist.
  - *Mitigation*: Pending profiling after changes

---

## References

- [Semantic_Search_Enhancement_Roadmap.md](./Semantic_Search_Enhancement_Roadmap.md)
- [Performance_Improvement_Plan.md](./Performance_Improvement_Plan.md)
- [Log analysis, 2025-05-14]
