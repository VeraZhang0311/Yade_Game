"""Level service - loads level data from YAML and manages level progression."""

from pathlib import Path

import yaml

from app.schemas.level import LevelData, DialogueNode, DialogueOption

DATA_DIR = Path(__file__).parent.parent / "data" / "levels"


class LevelService:
    def __init__(self):
        self._cache: dict[str, LevelData] = {}

    def load_level(self, level_id: str) -> LevelData:
        """Load a level definition from its YAML file."""
        if level_id in self._cache:
            return self._cache[level_id]

        file_path = DATA_DIR / f"{level_id}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Level file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        # Parse nodes
        nodes = {}
        for node_id, node_data in raw["nodes"].items():
            options = None
            if "options" in node_data:
                options = [
                    DialogueOption(**opt) for opt in node_data["options"]
                ]
            nodes[node_id] = DialogueNode(
                id=node_id,
                speaker=node_data.get("speaker", "yade"),
                text=node_data["text"],
                action=node_data.get("action"),
                options=options,
                next_node=node_data.get("next_node"),
                condition=node_data.get("condition"),
                is_ending=node_data.get("is_ending", False),
            )

        level = LevelData(
            id=raw["id"],
            title=raw["title"],
            order=raw["order"],
            scene=raw.get("scene", ""),
            start_node=raw["start_node"],
            nodes=nodes,
        )
        self._cache[level_id] = level
        return level

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


level_service = LevelService()
