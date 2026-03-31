import json
import re
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class EntityType(str):
    SPELL = "spell"
    CONDITION = "condition"
    FEAT = "feat"
    MONSTER = "monster"
    NPC = "npc"
    LOCATION = "location"
    FACTION = "faction"
    ITEM = "item"
    CLASS_FEATURE = "class_feature"
    BACKGROUND = "background"
    OTHER = "other"


class ExtractedEntity:
    def __init__(
        self,
        entity_type: str,
        name: str,
        data: dict[str, Any],
        aliases: list[str] | None = None,
    ):
        self.entity_type = entity_type
        self.name = name
        self.data = data
        self.aliases = aliases or []


class EntityExtractor:
    def __init__(self):
        self.entity_type_mapping = {
            "spell": EntityType.SPELL,
            "condition": EntityType.CONDITION,
            "feat": EntityType.FEAT,
            "monster": EntityType.MONSTER,
            "npc": EntityType.NPC,
            "location": EntityType.LOCATION,
            "faction": EntityType.FACTION,
            "item": EntityType.ITEM,
            "class_feature": EntityType.CLASS_FEATURE,
            "background": EntityType.BACKGROUND,
        }

    def extract_from_file(
        self, file_path: Path, entity_type: str, module_id: str
    ) -> list[ExtractedEntity]:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning("entity_file_not_found", path=str(file_path))
            return []

        suffix = file_path.suffix.lower()

        if suffix == ".json":
            return self._extract_from_json(file_path, entity_type, module_id)
        elif suffix == ".txt" or suffix == ".md":
            return self._extract_from_text(file_path, entity_type, module_id)
        else:
            logger.warning("unsupported_entity_file_type", suffix=suffix)
            return []

    def _extract_from_json(
        self, file_path: Path, entity_type: str, module_id: str
    ) -> list[ExtractedEntity]:
        entities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("invalid_json", path=str(file_path), error=str(e))
            return []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]
        else:
            return []

        for item in items:
            name = self._extract_name(item, entity_type)
            if name:
                normalized = self._normalize_name(name)
                aliases = self._extract_aliases(item)
                entities.append(
                    ExtractedEntity(
                        entity_type=entity_type,
                        name=name,
                        data=item,
                        aliases=aliases,
                    )
                )

        logger.info("entities_extracted", type=entity_type, count=len(entities))
        return entities

    def _extract_from_text(
        self, file_path: Path, entity_type: str, module_id: str
    ) -> list[ExtractedEntity]:
        entities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error("file_read_error", path=str(file_path), error=str(e))
            return []

        name_pattern = r"^#\s+(.+)$|^([A-Z][a-zA-Z\s]+):"

        for line in content.split("\n"):
            match = re.match(name_pattern, line.strip())
            if match:
                name = match.group(1) or match.group(2)
                if name:
                    entities.append(
                        ExtractedEntity(
                            entity_type=entity_type,
                            name=name.strip(),
                            data={"raw_text": line},
                            aliases=[],
                        )
                    )

        return entities

    @staticmethod
    def _extract_name(item: dict[str, Any], entity_type: str) -> str | None:
        name_fields = ["name", "Name", "title", "Title"]

        for field in name_fields:
            if field in item and isinstance(item[field], str):
                return item[field]

        return None

    @staticmethod
    def _extract_aliases(item: dict[str, Any]) -> list[str]:
        alias_fields = ["aliases", "alias", "also_known_as", "synonyms"]

        for field in alias_fields:
            if field in item and isinstance(item[field], list):
                return [str(a) for a in item[field]]

        return []

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.lower().strip()
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized
