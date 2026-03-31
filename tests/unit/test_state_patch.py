import pytest
from app.state.manager import StatePatchValidator, PatchValidationError, WorldStateManager


class TestStatePatchValidator:
    def test_validate_valid_patch(self):
        patch = {"op": "set", "path": "quests.main.status", "value": "completed"}
        result = StatePatchValidator.validate_patch(patch)
        assert result.op == "set"
        assert result.path == "quests.main.status"
        assert result.value == "completed"

    def test_validate_invalid_op(self):
        patch = {"op": "delete", "path": "test", "value": 1}
        with pytest.raises(PatchValidationError):
            StatePatchValidator.validate_patch(patch)

    def test_validate_invalid_key_format(self):
        patch = {"op": "set", "path": "invalid key", "value": 1}
        with pytest.raises(PatchValidationError):
            StatePatchValidator.validate_patches([patch])

    def test_validate_multiple_patches(self):
        patches = [
            {"op": "set", "path": "test.value", "value": 1},
            {"op": "inc", "path": "counter", "value": 1},
        ]
        results = StatePatchValidator.validate_patches(patches)
        assert len(results) == 2


class TestWorldStateManager:
    def test_set_value(self):
        manager = WorldStateManager()
        manager.set("player.hp", 10)
        assert manager.get("player.hp") == 10

    def test_get_nonexistent(self):
        manager = WorldStateManager()
        assert manager.get("nonexistent") is None

    def test_inc_value(self):
        manager = WorldStateManager()
        manager.set("counter", 5)
        manager.inc("counter", 3)
        assert manager.get("counter") == 8

    def test_append_to_list(self):
        manager = WorldStateManager()
        manager.set("inventory", [])
        manager.append("inventory", "sword")
        assert "sword" in manager.get("inventory")

    def test_apply_patch_set(self):
        manager = WorldStateManager()
        patch = StatePatchValidator.validate_patch({"op": "set", "path": "test", "value": 42})
        manager.apply_patch(patch)
        assert manager.get("test") == 42
