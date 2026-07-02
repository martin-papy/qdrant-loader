"""The loader-config surface for the docling engine (pydantic) and its translation
into the engine-internal frozen :class:`~.config.ConversionConfig`.

The rest of qdrant-loader configures conversion through YAML, which is parsed into
pydantic models (validation, env interpolation, the existing settings tree). The
engine, by contrast, takes a *frozen* dataclass that knows nothing about pydantic.
This module is the one-way bridge between the two — the anti-corruption boundary that
keeps the engine swappable: pydantic stays in the config layer, the frozen config
stays in the engine, and ``to_config`` is the only crossing.

Only a curated subset of knobs is surfaced here; the rest come from the chosen
:class:`~.config.ConversionProfile`. Surfacing more is a mechanical extension the TDD
pass can drive as real configs demand it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .config import (
    ConversionConfig,
    ConversionProfile,
    PictureDescriptionConfig,
)


class DoclingPictureSettings(BaseModel):
    """YAML surface for API image-captioning, mapped to :class:`PictureDescriptionConfig`.

    Off by default. When enabled it drives docling's remote picture-description
    pipeline; ``api_key`` is typically supplied via ``${ENV_VAR}`` interpolation.
    """

    enabled: bool = Field(default=False)
    url: str = Field(default="https://api.openai.com/v1/chat/completions")
    model: str = Field(default="gpt-4o-mini")
    api_key: str | None = Field(default=None)
    prompt: str = Field(default="Describe this image in a few sentences.")
    timeout: float = Field(default=60.0, gt=0)
    concurrency: int = Field(default=1, gt=0)

    def to_config(self) -> PictureDescriptionConfig:
        """Project these settings into the engine's frozen picture config."""
        return PictureDescriptionConfig(
            enabled=self.enabled,
            url=self.url,
            model=self.model,
            api_key=self.api_key,
            prompt=self.prompt,
            timeout=self.timeout,
            concurrency=self.concurrency,
        )


class DoclingConversionSettings(BaseModel):
    """YAML surface for the docling conversion engine.

    A :class:`~.config.ConversionProfile` selects the baseline (cost vs. fidelity);
    the optional fields below override individual top-level knobs on top of it. Only
    fields the user *explicitly sets* override the profile — unset fields keep the
    profile's value, so ``profile: accurate`` is not silently reset to the schema
    defaults.
    """

    profile: ConversionProfile = Field(default=ConversionProfile.FAST)

    # Optional top-level overrides (unset => inherit from the profile baseline).
    max_file_size: int | None = Field(default=None, gt=0)
    document_timeout: float | None = Field(default=None)
    enabled_formats: tuple[str, ...] | None = Field(default=None)
    device: str | None = Field(default=None)
    num_threads: int | None = Field(default=None, gt=0)
    compile_models: bool | None = Field(default=None)
    artifacts_path: str | None = Field(default=None)

    picture: DoclingPictureSettings = Field(default_factory=DoclingPictureSettings)

    def to_config(self) -> ConversionConfig:
        """Translate into the frozen engine config: profile baseline + set overrides."""
        explicitly_set = self.model_fields_set
        overrides: dict[str, object] = {}

        for name in (
            "max_file_size",
            "document_timeout",
            "device",
            "num_threads",
            "compile_models",
            "artifacts_path",
        ):
            if name in explicitly_set:
                overrides[name] = getattr(self, name)

        if "enabled_formats" in explicitly_set and self.enabled_formats is not None:
            # The frozen config stores a tuple; pydantic may hand back a list.
            overrides["enabled_formats"] = tuple(self.enabled_formats)

        if "picture" in explicitly_set:
            overrides["picture"] = self.picture.to_config()

        return ConversionConfig.from_profile(self.profile, **overrides)
