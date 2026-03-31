import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class SourceDefinition(BaseModel):
    type: str = Field(..., pattern="^(adventure|rule|homebrew)$")
    path: str


class EntityDefinition(BaseModel):
    type: str
    path: str


class HooksDefinition(BaseModel):
    on_session_start: list[str] = Field(default_factory=list)
    on_long_rest: list[str] = Field(default_factory=list)


class CompatibilityDefinition(BaseModel):
    min_platform_version: str | None = None


class ModuleManifestSchema(BaseModel):
    name: str = Field(..., min_length=1)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    edition: str = Field(..., min_length=1)
    priority: int = Field(default=50, ge=1, le=100)
    sources: list[SourceDefinition] = Field(default_factory=list)
    entities: list[EntityDefinition] = Field(default_factory=list)
    hooks: HooksDefinition = Field(default_factory=HooksDefinition)
    compatibility: CompatibilityDefinition = Field(default_factory=CompatibilityDefinition)


class ManifestValidationError(Exception):
    pass


class ManifestValidator:
    VALID_UNKNOWN_FIELDS = False

    @classmethod
    def validate_file(cls, manifest_path: Path | str) -> ModuleManifestSchema:
        manifest_path = Path(manifest_path)

        if not manifest_path.exists():
            raise ManifestValidationError(f"Manifest file not found: {manifest_path}")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ManifestValidationError(f"Invalid YAML: {e}")

        if not isinstance(raw_data, dict):
            raise ManifestValidationError("Manifest must be a YAML object")

        try:
            manifest = ModuleManifestSchema.model_validate(raw_data)
        except ValidationError as e:
            errors = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
            raise ManifestValidationError(f"Schema validation failed: {errors}")

        if not cls._validate_semver(manifest.version):
            raise ManifestValidationError(f"Invalid semver format: {manifest.version}")

        cls._validate_source_paths(manifest, manifest_path.parent)

        logger.info("manifest_validated", name=manifest.name, version=manifest.version)

        return manifest

    @staticmethod
    def _validate_semver(version: str) -> bool:
        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    @staticmethod
    def _validate_source_paths(manifest: ModuleManifestSchema, base_dir: Path) -> None:
        for source in manifest.sources:
            source_path = base_dir / source.path
            if not source_path.exists():
                logger.warning("source_path_not_found", path=str(source_path))
