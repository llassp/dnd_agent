import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class PatchOperation(BaseModel):
    op: str = Field(..., pattern="^(set|inc|append)$")
    path: str = Field(..., min_length=1)
    value: Any


class PatchValidationError(Exception):
    pass


class StatePatchValidator:
    KEY_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$"

    @classmethod
    def validate_patch(cls, patch: dict[str, Any]) -> PatchOperation:
        try:
            return PatchOperation.model_validate(patch)
        except ValidationError as e:
            errors = "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())
            raise PatchValidationError(f"Invalid patch: {errors}")

    @classmethod
    def validate_key(cls, key: str) -> bool:
        return bool(re.match(cls.KEY_PATTERN, key))

    @classmethod
    def validate_patches(cls, patches: list[dict[str, Any]]) -> list[PatchOperation]:
        validated = []
        for patch in patches:
            op = cls.validate_patch(patch)
            if not cls.validate_key(op.path):
                raise PatchValidationError(f"Invalid key format: {op.path}")
            validated.append(op)
        return validated


class WorldStateManager:
    def __init__(self, current_state: dict[str, Any] | None = None):
        self._state = current_state or {}

    def get(self, path: str) -> Any:
        keys = path.split(".")
        value = self._state
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def set(self, path: str, value: Any) -> None:
        keys = path.split(".")
        current = self._state
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def inc(self, path: str, amount: int | float) -> None:
        current = self.get(path)
        if current is None:
            self.set(path, amount)
        elif isinstance(current, (int, float)):
            self.set(path, current + amount)
        else:
            raise PatchValidationError(f"Cannot increment non-numeric value at {path}")

    def append(self, path: str, value: Any) -> None:
        current = self.get(path)
        if current is None:
            self.set(path, [value])
        elif isinstance(current, list):
            current.append(value)
        else:
            raise PatchValidationError(f"Cannot append to non-list value at {path}")

    def apply_patch(self, patch: PatchOperation) -> None:
        if patch.op == "set":
            self.set(patch.path, patch.value)
        elif patch.op == "inc":
            self.inc(patch.path, patch.value)
        elif patch.op == "append":
            self.append(patch.path, patch.value)

    def to_dict(self) -> dict[str, Any]:
        return self._state.copy()
