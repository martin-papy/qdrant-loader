# Conversion test fixtures

Real sample documents used to test `qdrant_loader.core.conversion`. We use real
files (not mocks) so the tests exercise docling's actual backends through *our*
engine, the way production will.

## Provenance

Lifted verbatim from the docling project's own test corpus
(<https://github.com/docling-project/docling/tree/main/tests/data>), MIT licensed:

| File | Source path | Why this file |
|------|-------------|---------------|
| `xlsx_05_table_with_title.xlsx` | `tests/data/xlsx/` | Small workbook with a titled table — exercises the structured-table path (the A1 round-trip we are removing). |
| `csv-comma.csv` | `tests/data/csv/` | Minimal comma-separated table — a SimplePipeline format we enable. |
| `lorem_ipsum.docx` | `tests/data/docx/` | Prose document — the export-to-markdown path. |

All three are model-free (SimplePipeline) formats: converting them downloads no
model weights, so the tests are fast, offline, and deterministic. PDF/image
pipeline behaviour (OCR, TableFormer, confidence) is covered by builder unit
tests, which assert the *options we hand docling* without running a conversion.
