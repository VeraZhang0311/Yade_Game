"""LLM service - integrates with DashScope (通义千问) for free chat.

Supports two modes:
- Async streaming via DashScope SDK (used by WebSocket server)
- Sync HTTP call (used by CLI play.py)
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import yaml

from app.config import settings

CHARACTER_DIR = Path(__file__).parent.parent / "data" / "characters"


def _get_generation():
    """Lazy import of dashscope.Generation to avoid import-time crashes in test."""
    import dashscope
    from dashscope import Generation

    dashscope.api_key = settings.DASHSCOPE_API_KEY
    return Generation


def load_character(character: str = "yade") -> dict:
    """Load character YAML and return the full config dict."""
    path = CHARACTER_DIR / f"{character}.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_character_prompt(character: str = "yade") -> str:
    """Load only the system_prompt string from the character YAML."""
    data = load_character(character)
    return data.get("system_prompt", "")


def load_model_params(character: str = "yade") -> dict:
    """Load model params (temperature, top_p, max_tokens) from character YAML."""
    data = load_character(character)
    return data.get("model_params", {})


# Affinity tier hints injected into system prompt
AFFINITY_HINTS = {
    "陌生人": "\n\n【当前好感度：陌生人】你对这个玩家还不熟悉，保持礼貌但有距离感，像对待刚认识的旅人。",
    "认识": "\n\n【当前好感度：认识】你对这个玩家有了一些印象，可以更自然地回应，但依然保持克制。",
    "朋友": "\n\n【当前好感度：朋友】你们已经是朋友了，回复可以更加友善，偶尔主动关心。",
    "好友": "\n\n【当前好感度：好友】你们关系已经很亲密，回复更温暖，愿意分享更多个人故事。",
    "挚友": "\n\n【当前好感度：挚友】你非常信任这个玩家，可以展现更深层的情感和脆弱面。",
    "羁绊": "\n\n【当前好感度：羁绊】你和这个玩家之间有着最深的连结，可以表达最真实的自我。",
}


class LLMService:
    def __init__(self):
        self.model = settings.LLM_MODEL
        self._model_params = load_model_params()

    def _build_system_prompt(
        self, character_prompt: str, affinity_score: int, memory_facts: dict
    ) -> str:
        """Build system prompt with character personality, affinity context, and memory."""
        # Determine affinity tier
        from app.services.affinity_service import affinity_service

        tier = affinity_service.get_tier(affinity_score)
        affinity_hint = AFFINITY_HINTS.get(tier, AFFINITY_HINTS["陌生人"])

        memory_section = ""
        if memory_facts:
            facts = "\n".join(f"- {k}: {v}" for k, v in memory_facts.items())
            memory_section = f"\n\n【你记得关于这位玩家的信息】\n{facts}"

        return f"{character_prompt}{affinity_hint}{memory_section}"

    async def chat_stream(
        self,
        messages: list[dict],
        character_prompt: str,
        affinity_score: int = 0,
        memory_facts: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from the LLM (async, for WebSocket)."""
        system_prompt = self._build_system_prompt(
            character_prompt, affinity_score, memory_facts or {}
        )

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        Generation = _get_generation()
        responses = Generation.call(
            model=self.model,
            messages=full_messages,
            result_format="message",
            stream=True,
            incremental_output=True,
            temperature=self._model_params.get("temperature", 0.7),
            top_p=self._model_params.get("top_p", 0.8),
            max_tokens=self._model_params.get("max_tokens", 1500),
        )

        for response in responses:
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if content:
                    yield content
            else:
                raise RuntimeError(
                    f"LLM API error: {response.status_code} - {response.message}"
                )

    async def evaluate_chat_affinity(
        self, messages: list[dict], character_prompt: str
    ) -> int:
        """Use LLM to evaluate how much affinity delta a chat session deserves."""
        eval_prompt = (
            "你是一个游戏系统的好感度评估模块。根据以下对话内容，评估玩家与角色之间的互动质量。\n"
            "考虑以下因素：对话轮次、内容深度、情感沟通质量。\n"
            "只返回一个整数（-5到+10之间），代表好感度变化值。正数表示好的互动，负数表示不好的互动。\n"
            "只返回数字，不要其他内容。"
        )

        Generation = _get_generation()
        response = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": eval_prompt},
                {"role": "user", "content": str(messages[-10:])},
            ],
            result_format="message",
            temperature=0.3,
        )

        if response.status_code == 200:
            try:
                return int(response.output.choices[0].message.content.strip())
            except ValueError:
                return 0
        return 0

    async def extract_memory_facts(
        self, messages: list[dict], existing_facts: dict
    ) -> dict:
        """Use LLM to extract key facts from a chat session for long-term memory."""
        extract_prompt = (
            "你是一个记忆提取模块。从以下对话中提取玩家提到的关键个人信息。\n"
            f"已知信息: {existing_facts}\n"
            "返回JSON格式的新增或更新的信息，例如: "
            '{"favorite_color": "蓝色", "pet_name": "小白"}\n'
            "如果没有新信息，返回空的 {}"
        )

        Generation = _get_generation()
        response = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": extract_prompt},
                {"role": "user", "content": str(messages[-10:])},
            ],
            result_format="message",
            temperature=0.3,
        )

        if response.status_code == 200:
            try:
                content = response.output.choices[0].message.content.strip()
                return json.loads(content)
            except (ValueError, json.JSONDecodeError):
                return {}
        return {}


llm_service = LLMService()
