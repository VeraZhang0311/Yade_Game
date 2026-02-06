"""Tests for the player module - model, routes, and CRUD operations."""

import pytest
from sqlalchemy import select

from app.models.player import Player, DEFAULT_LEVEL


# ---------------------------------------------------------------------------
# Model unit tests (via direct DB session)
# ---------------------------------------------------------------------------


async def test_create_player_default(db):
    """Player created with defaults has expected initial state."""
    player = Player()
    db.add(player)
    await db.flush()
    await db.refresh(player)

    assert player.id is not None
    assert player.name == "Player"
    assert player.nickname is None
    assert player.current_level_id == DEFAULT_LEVEL
    assert player.max_unlocked_level == DEFAULT_LEVEL
    assert player.affinity_score == 0
    assert player.memory_facts == {}
    assert player.bio is None


async def test_create_player_custom_name(db):
    player = Player(name="Alice", nickname="小A")
    db.add(player)
    await db.flush()

    assert player.name == "Alice"
    assert player.nickname == "小A"


async def test_reset_progress(db):
    """reset_progress() should clear progress but keep profile fields."""
    player = Player(name="Alice", bio="Hello")
    db.add(player)
    await db.flush()

    # Simulate some progress
    player.current_level_id = "chapter_05"
    player.max_unlocked_level = "chapter_05"
    player.affinity_score = 75
    player.memory_facts = {"favorite_color": "blue"}
    await db.flush()

    player.reset_progress()
    await db.flush()

    assert player.current_level_id == DEFAULT_LEVEL
    assert player.max_unlocked_level == DEFAULT_LEVEL
    assert player.affinity_score == 0
    assert player.memory_facts == {}
    # Profile fields preserved
    assert player.name == "Alice"
    assert player.bio == "Hello"


# ---------------------------------------------------------------------------
# Route integration tests (via HTTP client)
# ---------------------------------------------------------------------------


async def test_create_player_route(client):
    """POST /api/player/ creates a player and returns state."""
    resp = await client.post("/api/player/", json={"name": "TestPlayer"})
    assert resp.status_code == 201

    data = resp.json()
    assert data["name"] == "TestPlayer"
    assert data["current_level_id"] == DEFAULT_LEVEL
    assert data["affinity_score"] == 0
    assert data["affinity_tier"] == "陌生人"
    assert "id" in data
    assert "created_at" in data


async def test_create_player_default_name(client):
    """POST with no name should use default 'Player'."""
    resp = await client.post("/api/player/", json={})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Player"


async def test_get_player_route(client):
    """GET /api/player/{id} returns the correct player."""
    create_resp = await client.post("/api/player/", json={"name": "GetMe"})
    player_id = create_resp.json()["id"]

    resp = await client.get(f"/api/player/{player_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"
    assert resp.json()["id"] == player_id


async def test_get_player_not_found(client):
    """GET /api/player/999 should return 404."""
    resp = await client.get("/api/player/999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_update_player_route(client):
    """PATCH /api/player/{id} updates only provided fields."""
    create_resp = await client.post("/api/player/", json={"name": "Original"})
    player_id = create_resp.json()["id"]

    # Update only nickname
    resp = await client.patch(
        f"/api/player/{player_id}", json={"nickname": "小O"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Original"  # unchanged
    assert data["nickname"] == "小O"

    # Update name and bio
    resp = await client.patch(
        f"/api/player/{player_id}", json={"name": "NewName", "bio": "Hi!"}
    )
    data = resp.json()
    assert data["name"] == "NewName"
    assert data["bio"] == "Hi!"
    assert data["nickname"] == "小O"  # still there


async def test_update_player_not_found(client):
    resp = await client.patch("/api/player/999", json={"name": "Nope"})
    assert resp.status_code == 404


async def test_delete_player_route(client):
    """DELETE /api/player/{id} removes the player."""
    create_resp = await client.post("/api/player/", json={"name": "DeleteMe"})
    player_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/player/{player_id}")
    assert resp.status_code == 204

    # Verify gone
    resp = await client.get(f"/api/player/{player_id}")
    assert resp.status_code == 404


async def test_delete_player_not_found(client):
    resp = await client.delete("/api/player/999")
    assert resp.status_code == 404


async def test_reset_player_route(client):
    """POST /api/player/{id}/reset clears progress but keeps profile."""
    create_resp = await client.post(
        "/api/player/", json={"name": "ResetMe", "nickname": "RR"}
    )
    player_id = create_resp.json()["id"]

    resp = await client.post(f"/api/player/{player_id}/reset")
    assert resp.status_code == 200

    data = resp.json()
    assert data["message"] == "Progress reset successfully"
    player = data["player"]
    assert player["name"] == "ResetMe"
    assert player["nickname"] == "RR"
    assert player["current_level_id"] == DEFAULT_LEVEL
    assert player["affinity_score"] == 0


async def test_reset_player_not_found(client):
    resp = await client.post("/api/player/999/reset")
    assert resp.status_code == 404


async def test_create_player_name_validation(client):
    """Name must be 1-100 chars."""
    resp = await client.post("/api/player/", json={"name": ""})
    assert resp.status_code == 422

    resp = await client.post("/api/player/", json={"name": "x" * 101})
    assert resp.status_code == 422
