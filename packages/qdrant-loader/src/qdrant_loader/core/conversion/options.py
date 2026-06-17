"""Pure translation of a :class:`~.config.ConversionConfig` into docling options.

:class:`DoclingOptionsBuilder` is deterministic and side-effect free: it reads the
injected frozen config and constructs docling ``FormatOption`` / pipeline objects.
This replaces the doc's free ``build_format_options(cfg)`` functions with a single
cohesive class — same purity, but the config is injected once rather than threaded
through every call.

docling is imported lazily inside the methods so this module stays importable when
only the markitdown engine is present (the package must load without docling until
the engine is flipped). The numbered fixes neutralise docling's expensive defaults;
see ``docling/conversion/05-optimal-baseline-config.md`` §5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import ConversionConfig

if TYPE_CHECKING:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        PictureDescriptionApiOptions,
    )
    from docling.document_converter import FormatOption


class DoclingOptionsBuilder:
    """Builds docling format/pipeline options from our engine-agnostic config."""

    def __init__(self, config: ConversionConfig) -> None:
        self._config = config

    def build_format_options(self) -> dict[InputFormat, FormatOption]:
        """Map each configured input format to its docling ``FormatOption``.

        docx / pptx / html / csv / md are zero-config and omitted, so docling's
        defaults merge in. Only PDF, image and XLSX carry our overrides.
        """
        from docling.backend.docling_parse_backend import (
            DoclingParseDocumentBackend,
        )
        from docling.datamodel.backend_options import MsExcelBackendOptions
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import (
            ExcelFormatOption,
            ImageFormatOption,
            PdfFormatOption,
        )

        excel = self._config.excel
        pdf_pipeline_options = self._build_pdf_pipeline_options()
        return {
            # FIX 2: pin the docling-parse backend so it never auto-resolves.
            # docling 2.74.0 demoted ``DoclingParseV4DocumentBackend`` to a
            # deprecation shim that only emits a FutureWarning before delegating to
            # this same class; pin the parent directly to keep behaviour and silence
            # the warning (a hard error in a future docling release).
            InputFormat.PDF: PdfFormatOption(
                backend=DoclingParseDocumentBackend,
                pipeline_options=pdf_pipeline_options,
            ),
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=pdf_pipeline_options,  # images run the PDF pipeline
            ),
            InputFormat.XLSX: ExcelFormatOption(
                backend_options=MsExcelBackendOptions(
                    gap_tolerance=excel.gap_tolerance,
                    treat_singleton_as_text=excel.singleton_as_text,
                    sheet_names=list(excel.sheet_names) if excel.sheet_names else None,
                ),
            ),
        }

    def _build_pdf_pipeline_options(self) -> PdfPipelineOptions:
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            RapidOcrOptions,
            TableFormerMode,
        )

        config = self._config
        pipeline_options = PdfPipelineOptions()

        pipeline_options.do_ocr = config.ocr.enabled
        if config.ocr.enabled:  # FIX 1: pin the OCR engine, never let it auto-resolve
            pipeline_options.ocr_options = RapidOcrOptions(
                lang=list(config.ocr.languages),
                backend=config.ocr.backend,
                force_full_page_ocr=config.ocr.full_page,
            )

        pipeline_options.do_table_structure = config.table.enabled
        pipeline_options.table_structure_options.mode = TableFormerMode(  # FIX 3
            config.table.mode
        )
        pipeline_options.table_structure_options.do_cell_matching = (
            config.table.cell_matching
        )

        pipeline_options.do_code_enrichment = config.code_formula_enrichment
        pipeline_options.do_formula_enrichment = config.code_formula_enrichment
        pipeline_options.accelerator_options = AcceleratorOptions(
            device=config.device,
            num_threads=config.num_threads,
        )
        pipeline_options.document_timeout = config.document_timeout  # FIX 4: wall-clock
        pipeline_options.artifacts_path = config.artifacts_path

        if config.picture.enabled:  # FIX 5: declarative API captioning
            pipeline_options.enable_remote_services = True
            pipeline_options.do_picture_description = True
            # The enrichment stage only captions pictures whose crops were rendered;
            # generate_picture_images defaults to False, which silently disables
            # captioning. Scale 2 is docling's documented floor for legible crops.
            pipeline_options.generate_picture_images = True
            pipeline_options.images_scale = max(pipeline_options.images_scale, 2.0)
            pipeline_options.picture_description_options = self._build_picture_options()

        return pipeline_options

    def _build_picture_options(self) -> PictureDescriptionApiOptions:
        from docling.datamodel.pipeline_options import PictureDescriptionApiOptions

        picture = self._config.picture
        headers = (
            {"Authorization": f"Bearer {picture.api_key}"} if picture.api_key else {}
        )
        return PictureDescriptionApiOptions(
            url=picture.url,
            headers=headers,
            params={"model": picture.model},
            prompt=picture.prompt,
            timeout=picture.timeout,
            concurrency=picture.concurrency,
            scale=picture.scale,
        )
