import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Module, SourceDoc, Chunk, RuleEntity, LoreEntity
from app.ingestion.manifest_validator import ManifestValidator, ManifestValidationError, ModuleManifestSchema
from app.ingestion.chunker import Chunker, compute_checksum
from app.ingestion.embedder import get_embedder
from app.ingestion.entity_extractor import EntityExtractor, ExtractedEntity
from app.schemas.module import IngestionReport, SourceDocResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModuleAlreadyExistsError(Exception):
    pass


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunker = Chunker()
        self.entity_extractor = EntityExtractor()
        self.embedder = get_embedder()

    async def ingest_module(
        self, package_path: str, force: bool = False
    ) -> tuple[Module, IngestionReport]:
        package_path = Path(package_path)

        if not package_path.exists():
            raise FileNotFoundError(f"Module package not found: {package_path}")

        manifest = ManifestValidator.validate_file(package_path / "module.yaml")

        existing = await self._check_existing_version(manifest.name, manifest.version)
        if existing and not force:
            raise ModuleAlreadyExistsError(
                f"Module {manifest.name} v{manifest.version} already exists"
            )

        if existing and force:
            logger.info("reingesting_module", name=manifest.name, version=manifest.version)

        module = Module(
            id=existing.id if existing else uuid.uuid4(),
            name=manifest.name,
            version=manifest.version,
            edition=manifest.edition,
            manifest_json=manifest.model_dump(),
        )
        self.db.add(module)

        report = IngestionReport()

        await self._process_sources(package_path, manifest, module, report)

        await self._process_entities(package_path, manifest, module, report)

        await self.db.commit()
        await self.db.refresh(module)

        logger.info(
            "module_ingested",
            module_id=str(module.id),
            name=module.name,
            version=module.version,
            report=report.model_dump(),
        )

        return module, report

    async def _check_existing_version(
        self, name: str, version: str
    ) -> Module | None:
        stmt = select(Module).where(Module.name == name, Module.version == version)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _process_sources(
        self,
        package_path: Path,
        manifest: ModuleManifestSchema,
        module: Module,
        report: IngestionReport,
    ) -> None:
        for source_def in manifest.sources:
            source_path = package_path / source_def.path

            if not source_path.exists():
                report.warnings.append(f"Source not found: {source_def.path}")
                continue

            try:
                source_doc = await self._process_source_file(
                    source_path, source_def.type, module
                )
                await self.db.flush()

                await self._chunk_and_embed_source(source_doc, module, report)
            except Exception as e:
                report.errors.append(f"Error processing {source_def.path}: {str(e)}")
                logger.error("source_processing_error", path=source_def.path, error=str(e))

    async def _process_source_file(
        self, file_path: Path, source_type: str, module: Module
    ) -> SourceDoc:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        checksum = compute_checksum(content)

        source_doc = SourceDoc(
            module_id=module.id,
            title=file_path.stem,
            source_type=source_type,
            uri=str(file_path),
            checksum=checksum,
            version=module.version,
            metadata_json={"module_name": module.name},
        )
        self.db.add(source_doc)

        return source_doc

    async def _chunk_and_embed_source(
        self, source_doc: SourceDoc, module: Module, report: IngestionReport
    ) -> None:
        file_path = Path(source_doc.uri or "")
        if not file_path.exists():
            return

        chunks = list(
            self.chunker.process_file(
                file_path=file_path,
                source_doc_id=str(source_doc.id),
                metadata={
                    "campaign_id": None,
                    "module_id": str(module.id),
                    "source_type": source_doc.source_type,
                    "canon_level": "official" if source_doc.source_type != "homebrew" else "homebrew",
                    "entity_refs": [],
                    "version": module.version,
                },
            )
        )

        if not chunks:
            report.warnings.append(f"No chunks generated for {file_path.name}")
            return

        texts = [c.text for c in chunks]
        embeddings = await self.embedder.embed(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk_model = Chunk(
                source_doc_id=source_doc.id,
                chunk_text=chunk.text,
                token_count=chunk.token_count,
                embedding=embedding.embedding,
                metadata_json=chunk.metadata,
            )
            self.db.add(chunk_model)
            report.chunks_created += 1

    async def _process_entities(
        self,
        package_path: Path,
        manifest: ModuleManifestSchema,
        module: Module,
        report: IngestionReport,
    ) -> None:
        for entity_def in manifest.entities:
            entity_path = package_path / entity_def.path

            if not entity_path.exists():
                report.warnings.append(f"Entity file not found: {entity_def.path}")
                continue

            try:
                entities = self.entity_extractor.extract_from_file(
                    entity_path, entity_def.type, str(module.id)
                )

                for entity in entities:
                    await self._store_entity(entity, module, report)
            except Exception as e:
                report.errors.append(f"Error processing {entity_def.path}: {str(e)}")
                logger.error(
                    "entity_processing_error",
                    path=entity_def.path,
                    error=str(e),
                )

    async def _store_entity(
        self, entity: ExtractedEntity, module: Module, report: IngestionReport
    ) -> None:
        from app.ingestion.entity_extractor import EntityExtractor

        normalized = EntityExtractor._normalize_name(entity.name)

        is_lore = entity.entity_type in ["npc", "location", "faction", "item"]

        if is_lore:
            lore = LoreEntity(
                module_id=module.id,
                entity_type=entity.entity_type,
                name=entity.name,
                aliases=entity.aliases,
                data_json=entity.data,
            )
            self.db.add(lore)
        else:
            rule = RuleEntity(
                module_id=module.id,
                entity_type=entity.entity_type,
                name=entity.name,
                normalized_name=normalized,
                data_json=entity.data,
            )
            self.db.add(rule)

        report.entities_created += 1
