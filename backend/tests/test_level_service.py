"""Tests for the level service - loading simplified choice-only YAML data."""

from app.services.level_service import level_service


def test_load_chapter_01():
    """Level config loads basic metadata correctly."""
    level = level_service.load_level("chapter_01")
    assert level.id == "chapter_01"
    assert level.title == "初次相遇"
    assert level.order == 1


def test_load_level_has_choices():
    """Level config contains the expected choice nodes."""
    level = level_service.load_level("chapter_01")
    assert "choice_1" in level.choices
    assert "choice_2" in level.choices
    assert "choice_3" in level.choices
    assert "choice_4" in level.choices


def test_choice_options():
    """Each choice node has the expected option IDs (A, B, C)."""
    level = level_service.load_level("chapter_01")
    for node_id in ["choice_1", "choice_2", "choice_3", "choice_4"]:
        options = level.choices[node_id]
        assert "A" in options
        assert "B" in options
        assert "C" in options


def test_affinity_deltas():
    """Choice options have correct affinity_delta values."""
    level = level_service.load_level("chapter_01")
    assert level.choices["choice_1"]["A"].affinity_delta == 1
    assert level.choices["choice_1"]["B"].affinity_delta == 0
    assert level.choices["choice_1"]["C"].affinity_delta == -1


def test_major_choice_flag():
    """choice_3 and choice_4 options should be marked as is_major."""
    level = level_service.load_level("chapter_01")
    for opt in level.choices["choice_3"].values():
        assert opt.is_major is True
    for opt in level.choices["choice_4"].values():
        assert opt.is_major is True


def test_non_major_choices():
    """choice_1 and choice_2 options should NOT be is_major."""
    level = level_service.load_level("chapter_01")
    for opt in level.choices["choice_1"].values():
        assert opt.is_major is False
    for opt in level.choices["choice_2"].values():
        assert opt.is_major is False


def test_get_choice_affinity():
    """get_choice_affinity returns the correct ChoiceOption."""
    opt = level_service.get_choice_affinity("chapter_01", "choice_3", "A")
    assert opt is not None
    assert opt.affinity_delta == 3
    assert opt.is_major is True


def test_get_choice_affinity_missing():
    """get_choice_affinity returns None for nonexistent choice."""
    assert level_service.get_choice_affinity("chapter_01", "nonexistent", "A") is None
    assert level_service.get_choice_affinity("chapter_01", "choice_1", "Z") is None


def test_list_levels():
    """list_levels returns at least chapter_01 sorted by order."""
    levels = level_service.list_levels()
    assert len(levels) >= 1
    assert levels[0]["id"] == "chapter_01"
    assert levels[0]["order"] == 1


def test_get_next_level_none():
    """With only one level, get_next_level_id returns None."""
    result = level_service.get_next_level_id("chapter_01")
    # With only chapter_01, there's no next level
    assert result is None


def test_get_unlocked_levels():
    """get_unlocked_levels returns level IDs up to the given max."""
    unlocked = level_service.get_unlocked_levels("chapter_01")
    assert "chapter_01" in unlocked


def test_load_nonexistent_level():
    """Loading a nonexistent level raises FileNotFoundError."""
    import pytest
    with pytest.raises(FileNotFoundError):
        level_service.load_level("chapter_99")


def test_level_cache():
    """Second load should return cached config (same object)."""
    # Clear cache to test fresh
    level_service._cache.clear()
    config1 = level_service.load_level("chapter_01")
    config2 = level_service.load_level("chapter_01")
    assert config1 is config2
