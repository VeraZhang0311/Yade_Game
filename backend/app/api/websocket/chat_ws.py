"""WebSocket endpoint for streaming free-chat with Yade."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db.database import async_session
from app.db.redis import get_redis_client
from app.models.player import Player
from app.models.chat_history import ChatMessage
from app.services.chat_service import ChatService
from app.services.affinity_service import affinity_service
from app.services.llm_service import llm_service, load_character_prompt
from app.services.memory_service import memory_service

router = APIRouter()


@router.websocket("/ws/chat/{player_id}")
async def chat_websocket(websocket: WebSocket, player_id: int):
    """WebSocket endpoint for streaming free-chat.

    Protocol:
    - Client sends: {"type": "message", "content": "..."}
    - Server sends: {"type": "chunk", "content": "..."} (streaming)
    - Server sends: {"type": "end"} (stream complete)
    - Server sends: {"type": "error", "content": "..."} (on error)
    """
    await websocket.accept()

    redis = get_redis_client()
    chat_svc = ChatService(redis)
    character_prompt = load_character_prompt("yade")

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") != "message":
                continue

            user_content = data.get("content", "").strip()
            if not user_content:
                continue

            # Load player state for affinity-aware responses
            async with async_session() as db:
                result = await db.execute(select(Player).where(Player.id == player_id))
                player = result.scalar_one()
                affinity_score = player.affinity_score
                memory_facts = player.memory_facts or {}

            # Stream response
            full_response = ""
            async for chunk in chat_svc.stream_reply(
                player_id=player_id,
                user_message=user_content,
                character_prompt=character_prompt,
                affinity_score=affinity_score,
                memory_facts=memory_facts,
            ):
                full_response += chunk
                await websocket.send_text(
                    json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
                )

            await websocket.send_text(json.dumps({"type": "end"}))

            # Persist to DB (async, non-blocking to the user)
            async with async_session() as db:
                db.add(ChatMessage(
                    player_id=player_id, role="user", content=user_content
                ))
                db.add(ChatMessage(
                    player_id=player_id, role="assistant", content=full_response
                ))
                await db.commit()

    except WebSocketDisconnect:
        # On disconnect: evaluate affinity and extract memory from this session
        context = await chat_svc.get_context(player_id)
        if len(context) >= 2:  # at least one exchange
            async with async_session() as db:
                # Evaluate chat affinity
                delta = await llm_service.evaluate_chat_affinity(context, character_prompt)
                if delta != 0:
                    await affinity_service.add_affinity(
                        db, player_id, delta, "chat",
                        reason=f"Chat session ({len(context)} messages)",
                    )
                # Extract memory facts
                await memory_service.extract_and_save(db, player_id, context)
                await db.commit()
    except Exception as e:
        await websocket.send_text(
            json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
        )
