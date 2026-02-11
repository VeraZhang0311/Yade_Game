"""Tests for the level service - loading and parsing YAML level data."""

from app.services.level_service import level_service


def test_load_chapter_01():
    level = level_service.load_level("chapter_01")
    assert level.id == "chapter_01"
    assert level.title == "初次相遇"
    assert level.scene == "情景1: 与小女孩的初遇"
    assert level.start_node == "prologue_1"
    assert "prologue_1" in level.nodes
    assert "choice_1" in level.nodes


def test_list_levels():
    levels = level_service.list_levels()
    assert len(levels) >= 1
    assert levels[0]["id"] == "chapter_01"


def test_dialogue_options_have_affinity():
    """choice_3 is the major story choice and should have affinity deltas."""
    level = level_service.load_level("chapter_01")
    node = level.nodes["choice_3"]
    assert node.options is not None
    assert any(o.affinity_delta != 0 for o in node.options)


def test_speaker_types():
    """Level should contain narrator, yade_inner, girl, and yade nodes."""
    level = level_service.load_level("chapter_01")
    speakers = {n.speaker for n in level.nodes.values()}
    assert "narrator" in speakers
    assert "yade_inner" in speakers
    assert "girl" in speakers


def test_action_field():
    """girl_greet node should have an action description."""
    level = level_service.load_level("chapter_01")
    node = level.nodes["girl_greet"]
    assert node.action is not None
    assert "泥土" in node.action


def test_major_choice_flag():
    """choice_3 options should be marked as is_major."""
    level = level_service.load_level("chapter_01")
    node = level.nodes["choice_3"]
    assert node.options is not None
    assert all(o.is_major for o in node.options)


def test_conditional_branching():
    """branch_check should have condition pointing to two branches."""
    level = level_service.load_level("chapter_01")
    node = level.nodes["branch_check"]
    assert node.condition is not None
    assert "choice_3" in node.condition
    mapping = node.condition["choice_3"]
    assert mapping["A"] == "branch_together"
    assert mapping["C"] == "branch_alone"


def test_multiple_endings():
    """Chapter 01 should have 3 different endings."""
    level = level_service.load_level("chapter_01")
    endings = [n for n in level.nodes.values() if n.is_ending]
    assert len(endings) == 3
