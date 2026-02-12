"""Level service - loads level configs from YAML and manages level progression.

Simplified: YAML only contains choice→affinity mappings and level metadata.
Dialogue content is managed by the frontend (YarnSpinner).
"""

from pathlib import Path

import yaml

from app.schemas.level import LevelConfig, ChoiceOption

DATA_DIR = Path(__file__).parent.parent / "data" / "levels"


class LevelService:
    def __init__(self):
        self._cache: dict[str, LevelConfig] = {}

    def load_level(self, level_id: str) -> LevelConfig:
        """Load a level config from its YAML file."""
        if level_id in self._cache:
            return self._cache[level_id]

        file_path = DATA_DIR / f"{level_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Level file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        # Parse choices: node_id -> {option_id -> ChoiceOption}
        choices = {}
        for node_id, options in raw.get("choices", {}).items():
            choices[node_id] = {
                opt_id: ChoiceOption(**opt_data)
                for opt_id, opt_data in options.items()
            }

        config = LevelConfig(
            id=raw["id"],
            title=raw["title"],
            order=raw["order"],
            choices=choices,
        )
        self._cache[level_id] = config
        return config

    def get_choice_affinity(self, level_id: str, node_id: str, choice_id: str) -> ChoiceOption | None:
        """Look up affinity config for a specific choice. Returns None if not found."""
        config = self.load_level(level_id)
        node_choices = config.choices.get(node_id)
        if not node_choices:
            return None
        return node_choices.get(choice_id)

    def list_levels(self) -> list[dict]:
        """List all available levels with basic info."""
        levels = []
        for file_path in sorted(DATA_DIR.glob("*.yaml")):
            with open(file_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            levels.append({
                "id": raw["id"],
                "title": raw["title"],
                "order": raw["order"],
            })
        return sorted(levels, key=lambda x: x["order"])

    def get_next_level_id(self, current_level_id: str) -> str | None:
        """Get the next level ID after the given one, or None if it's the last."""
        all_levels = self.list_levels()
        for i, level in enumerate(all_levels):
            if level["id"] == current_level_id and i + 1 < len(all_levels):
                return all_levels[i + 1]["id"]
        return None

    def get_unlocked_levels(self, max_unlocked: str) -> list[str]:
        """Get list of all level IDs that are unlocked."""
        all_levels = self.list_levels()
        max_order = 0
        for lvl in all_levels:
            if lvl["id"] == max_unlocked:
                max_order = lvl["order"]
                break
        return [lvl["id"] for lvl in all_levels if lvl["order"] <= max_order]


level_service = LevelService()
