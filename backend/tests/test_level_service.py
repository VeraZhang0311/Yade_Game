"""Tests for the level service - loading and parsing YAML level data."""

from app.services.level_service import level_service


def test_load_chapter_01():
    level = level_service.load_level("chapter_01")
    assert level.id == "chapter_01"
    assert level.start_node == "intro"
    assert "intro" in level.nodes
    assert "yade_appears" in level.nodes


def test_list_levels():
    levels = level_service.list_levels()
    assert len(levels) >= 1
    assert levels[0]["id"] == "chapter_01"


def test_dialogue_options_have_affinity():
    level = level_service.load_level("chapter_01")
    node = level.nodes["yade_appears"]
    assert node.options is not None
    assert any(o.affinity_delta != 0 for o in node.options)
