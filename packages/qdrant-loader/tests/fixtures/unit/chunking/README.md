# Chunking test fixtures

Real documents lifted from the [Docling](https://github.com/docling-project/docling)
test corpus (`tests/data/`, MIT licensed) — never mocks. They exercise the
Docling-native chunking layer (`core/chunking/docling/`) on the model-free
SimplePipeline formats, so the suite runs offline with no model downloads.

| File | Source | Why it's here |
|------|--------|---------------|
| `unit_test_headers.docx` | `tests/data/docx/unit_test_headers.docx` | Nested headings (`Test Document > Section 1 > Section 1.1`) — the only way to exercise `heading_path` / heading-depth projection, which the flat `lorem_ipsum.docx` cannot. |
| `xlsx_05_table_with_title.xlsx` | `tests/data/xlsx/xlsx_05.xlsx` | `TABLE` doc-items carrying real `prov` (page number + bounding box) — exercises `is_table` / `page_start` / `bbox` projection. Same file used by the conversion fixtures. |

These drive the `StructureProjector` and `DoclingChunker` tests against the actual
shape Docling emits, not an assumed one.
