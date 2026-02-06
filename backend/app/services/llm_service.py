"""LLM service - integrates with DashScope (通义千问max) for free chat."""

from collections.abc import AsyncGenerator

import dashscope
from dashscope import Generation

from app.config import settings


class LLMService:
    def __init__(self):
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.LLM_MODEL

    def _build_system_prompt(self, character_prompt: str, affinity_score: int, memory_facts: dict) -> str:
        """Build system prompt with character personality, affinity context, and memory."""
        memory_section = ""
        if memory_facts:
            facts = "\n".join(f"- {k}: {v}" for k, v in memory_facts.items())
            memory_section = f"\n\n你记得关于玩家的以下信息:\n{facts}"

        affinity_hint = ""
        if affinity_score < 20:
            affinity_hint = "\n你对玩家还比较陌生，回复保持礼貌但有距离感。"
        elif affinity_score < 50:
            affinity_hint = "\n你对玩家有了一些好感，回复可以更加友善和自然。"
        elif affinity_score < 80:
            affinity_hint = "\n你和玩家已经是好朋友，回复亲切、愿意分享更多。"
        else:
            affinity_hint = "\n你和玩家关系非常亲密，回复可以展现深层情感。"

        return f"{character_prompt}{affinity_hint}{memory_section}"

    async def chat_stream(
        self,
        messages: list[dict],
        character_prompt: str,
        affinity_score: int = 0,
        memory_facts: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from the LLM."""
        system_prompt = self._build_system_prompt(
            character_prompt, affinity_score, memory_facts or {}
        )

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        responses = Generation.call(
            model=self.model,
            messages=full_messages,
            result_format="message",
            stream=True,
            incremental_output=True,
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
        """Use LLM to evaluate how much affinity delta a chat session deserves.

        Returns an integer affinity delta (can be negative).
        """
        eval_prompt = (
            "你是一个游戏系统的好感度评估模块。根据以下对话内容，评估玩家与角色之间的互动质量。\n"
            "考虑以下因素：对话轮次、内容深度、情感沟通质量。\n"
            "只返回一个整数（-5到+10之间），代表好感度变化值。正数表示好的互动，负数表示不好的互动。\n"
            "只返回数字，不要其他内容。"
        )

        response = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": eval_prompt},
                {"role": "user", "content": str(messages[-10:])},  # last 10 turns
            ],
            result_format="message",
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

        response = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": extract_prompt},
                {"role": "user", "content": str(messages[-10:])},
            ],
            result_format="message",
        )

        if response.status_code == 200:
            import json
            try:
                content = response.output.choices[0].message.content.strip()
                return json.loads(content)
            except (ValueError, json.JSONDecodeError):
                return {}
        return {}


llm_service = LLMService()
