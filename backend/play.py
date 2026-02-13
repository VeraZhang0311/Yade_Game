#!/usr/bin/env python3
"""Interactive CLI script to playtest a level's dialogue tree + chat with Yade.

Usage:
    python play.py                    # plays chapter_01 by default
    python play.py chapter_02         # plays a specific chapter

Features:
    - Walk through dialogue tree (from docs/ full reference YAML)
    - After completing a level, optionally enter free-chat with Yade (via DashScope API)

No server, database, or Docker needed.
"""

import json
import os
import sys
from pathlib import Path

import requests
import yaml

# --- Paths ---
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "app" / "data" / "docs"
LEVELS_DIR = BASE_DIR / "app" / "data" / "levels"
CHARACTER_DIR = BASE_DIR / "app" / "data" / "characters"

# --- ANSI Colors ---
SPEAKER_LABELS = {
    "narrator": "\033[90m[旁白]\033[0m",
    "yade": "\033[96m[亚德]\033[0m",
    "yade_inner": "\033[36m[亚德·内心]\033[0m",
    "girl": "\033[95m[小女孩]\033[0m",
    "action": "\033[33m[动作]\033[0m",
}

DIVIDER = "\033[90m" + "─" * 50 + "\033[0m"
YADE_COLOR = "\033[96m"
RESET = "\033[0m"
DIM = "\033[90m"
BOLD = "\033[1m"
YELLOW = "\033[93m"


# =============================================================
# Part 1: Level Dialogue Playthrough
# =============================================================

def load_full_level(level_id: str) -> dict:
    """Load the full dialogue YAML (from docs/ or levels/ fallback)."""
    # Try docs/ first (full reference version)
    docs_path = DOCS_DIR / f"{level_id}_full_reference.yaml"
    if docs_path.exists():
        with open(docs_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # Fallback to levels/ directory
    level_path = LEVELS_DIR / f"{level_id}.yaml"
    if level_path.exists():
        with open(level_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    raise FileNotFoundError(f"Level not found: {level_id}")


def display_node(node: dict):
    """Print a dialogue node to the terminal."""
    speaker = node.get("speaker", "narrator")
    label = SPEAKER_LABELS.get(speaker, f"\033[93m[{speaker}]\033[0m")
    print()
    print(DIVIDER)
    print(label)
    if node.get("action"):
        print(f"  \033[33m（{node['action']}）\033[0m")
    text = node.get("text", "")
    if text and text.strip():
        print(f"  {text.strip()}")


def display_choices(options: list[dict]) -> dict:
    """Print available options and return user's selection."""
    print()
    for opt in options:
        opt_id = opt["id"]
        major_tag = " \033[91m★\033[0m" if opt.get("is_major") else ""
        print(f"  \033[97m{opt_id}\033[0m. {opt['text']}{major_tag}")
    print()

    valid_ids = [o["id"] for o in options]
    while True:
        choice = input(f"  请选择 ({'/'.join(valid_ids)}): ").strip().upper()
        if choice in valid_ids:
            return next(o for o in options if o["id"] == choice)
        print(f"  \033[91m无效选择，请输入 {'/'.join(valid_ids)}\033[0m")


def wait_for_advance():
    """Wait for the player to press Enter to advance."""
    input(f"  {DIM}(按 Enter 继续...){RESET}")


def play_level(level_id: str = "chapter_01") -> int:
    """Play through a level's dialogue tree. Returns the final affinity score."""
    data = load_full_level(level_id)
    nodes = data.get("nodes", {})

    if not nodes:
        print(f"\n{YELLOW}此关卡没有完整对话树（仅有选项映射），跳过剧情演示。{RESET}")
        return 0

    print()
    print(f"{BOLD}" + "=" * 50 + f"{RESET}")
    print(f"{BOLD}  {data.get('title', level_id)}{RESET}")
    scene = data.get("scene")
    if scene:
        print(f"  {DIM}{scene}{RESET}")
    print(f"{BOLD}" + "=" * 50 + f"{RESET}")

    current_node_id = data.get("start_node")
    affinity = 0
    choices_made: dict[str, str] = {}

    while current_node_id:
        node = nodes.get(current_node_id)
        if node is None:
            print(f"\n\033[91m[错误] 找不到节点: {current_node_id}\033[0m")
            break

        node_id = current_node_id

        # --- Conditional branching ---
        condition = node.get("condition")
        if condition:
            jumped = False
            for ref_node_id, mapping in condition.items():
                prev_choice = choices_made.get(ref_node_id)
                if prev_choice and prev_choice in mapping:
                    current_node_id = mapping[prev_choice]
                    jumped = True
                    break
            if jumped:
                continue

        # --- Display the node ---
        display_node(node)

        # --- Handle options (player choice) ---
        options = node.get("options")
        if options:
            chosen = display_choices(options)
            choices_made[node_id] = chosen["id"]
            delta = chosen.get("affinity_delta", 0)
            affinity += delta

            if delta != 0:
                sign = "+" if delta > 0 else ""
                print(f"  {YELLOW}好感度 {sign}{delta} (总计: {affinity}){RESET}")

            current_node_id = chosen.get("next_node")

        # --- Ending ---
        elif node.get("is_ending"):
            print()
            print(DIVIDER)
            print(f"\n{BOLD}  ── 关卡结束 ──{RESET}")
            print(f"  {YELLOW}最终好感度: {affinity}{RESET}")
            print(f"  {DIM}选择记录: {choices_made}{RESET}")
            print()
            break

        # --- Auto-advance ---
        elif node.get("next_node"):
            wait_for_advance()
            current_node_id = node["next_node"]

        else:
            print(f"\n\033[91m[错误] 节点没有 next_node 也没有 options\033[0m")
            break

    return affinity


# =============================================================
# Part 2: Free Chat with Yade (DashScope HTTP API)
# =============================================================

def load_yade_config() -> dict:
    """Load the Yade character YAML config."""
    path = CHARACTER_DIR / "yade.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_affinity_tier(score: int) -> str:
    """Get the affinity tier name for a score."""
    tiers = [(0, "陌生人"), (20, "认识"), (40, "朋友"), (60, "好友"), (80, "挚友"), (100, "羁绊")]
    tier_name = tiers[0][1]
    for threshold, name in tiers:
        if score >= threshold:
            tier_name = name
    return tier_name


def build_system_prompt(base_prompt: str, affinity_score: int) -> str:
    """Build the full system prompt with affinity context."""
    tier = get_affinity_tier(affinity_score)
    hints = {
        "陌生人": "你对这个玩家还不熟悉，保持礼貌但有距离感。",
        "认识": "你对这个玩家有了一些印象，可以更自然地回应。",
        "朋友": "你们已经是朋友了，回复可以更加友善。",
        "好友": "你们关系已经很亲密，回复更温暖，愿意分享更多。",
        "挚友": "你非常信任这个玩家，可以展现更深层的情感。",
        "羁绊": "你和这个玩家之间有着最深的连结。",
    }
    hint = hints.get(tier, hints["陌生人"])
    return f"{base_prompt}\n\n【当前好感度：{tier}】{hint}"


def call_dashscope(
    api_key: str,
    model: str,
    messages: list[dict],
    params: dict,
) -> str | None:
    """Call DashScope HTTP API (OpenAI-compatible endpoint) and return the response text."""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": params.get("temperature", 0.7),
        "top_p": params.get("top_p", 0.8),
        "max_tokens": params.get("max_tokens", 1500),
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"\n  \033[91m[API 错误] {e}\033[0m")
        return None
    except (KeyError, IndexError):
        print(f"\n  \033[91m[API 响应异常]\033[0m")
        return None


def chat_with_yade(affinity_score: int = 0):
    """Interactive free-chat session with Yade via DashScope API."""
    # Load API key
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        # Try loading from .env file
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DASHSCOPE_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not api_key or api_key == "your_dashscope_api_key_here":
        print(f"\n  \033[91m[错误] 未设置 DASHSCOPE_API_KEY\033[0m")
        print(f"  {DIM}请在 .env 文件中设置，或通过环境变量设置：{RESET}")
        print(f"  {DIM}  export DASHSCOPE_API_KEY=sk-xxxxx{RESET}")
        return

    # Load character config
    config = load_yade_config()
    base_prompt = config.get("system_prompt", "你是亚德，一个沉默寡言的旅行者。")
    model_params = config.get("model_params", {})
    model = os.environ.get("LLM_MODEL", "qwen-plus")

    # Build system prompt with affinity
    system_prompt = build_system_prompt(base_prompt, affinity_score)

    # Chat state
    messages: list[dict] = []
    max_history = 20

    tier = get_affinity_tier(affinity_score)
    print()
    print(f"{BOLD}" + "=" * 50 + f"{RESET}")
    print(f"{BOLD}  闲聊模式 — 与亚德自由对话{RESET}")
    print(f"  {YELLOW}当前好感度: {affinity_score} ({tier}){RESET}")
    print(f"{BOLD}" + "=" * 50 + f"{RESET}")
    print()
    print(f"  {YADE_COLOR}亚德{RESET}: 你好。")
    print()
    print(f"  {DIM}[输入 'quit' 退出闲聊]{RESET}")
    print(f"  {DIM}[输入 'score' 查看好感度]{RESET}")
    print()

    while True:
        try:
            user_input = input(f"  {BOLD}你{RESET}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  {DIM}对话结束。{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "退出", "q"):
            print(f"\n  {YADE_COLOR}亚德{RESET}: 愿风雪记得你的名字。再见。\n")
            break

        if user_input.lower() in ("score", "好感度"):
            print(f"\n  {YELLOW}好感度: {affinity_score} ({tier}){RESET}\n")
            continue

        # Add user message
        messages.append({"role": "user", "content": user_input})

        # Trim history
        if len(messages) > max_history * 2:
            messages = messages[-max_history * 2:]

        # Build full message list with system prompt
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        # Call API
        print(f"\n  {DIM}(思考中...){RESET}", end="", flush=True)
        response = call_dashscope(api_key, model, full_messages, model_params)
        # Clear "thinking" line
        print("\r" + " " * 30 + "\r", end="")

        if response:
            messages.append({"role": "assistant", "content": response})
            print(f"  {YADE_COLOR}亚德{RESET}: {response}\n")
        else:
            fallback = "抱歉，我现在有些疲惫，无法回应...请稍后再试。"
            messages.append({"role": "assistant", "content": fallback})
            print(f"  {YADE_COLOR}亚德{RESET}: {fallback}\n")


# =============================================================
# Main
# =============================================================

def main():
    level_id = sys.argv[1] if len(sys.argv) > 1 else "chapter_01"

    # Play the level
    affinity = play_level(level_id)

    # Offer chat after level
    print(DIVIDER)
    print(f"\n  关卡结束后，你可以和亚德闲聊。")
    print(f"  {DIM}闲聊需要 DASHSCOPE_API_KEY（千问 API）{RESET}")
    print()

    try:
        choice = input("  是否要和亚德聊聊？(y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = "n"

    if choice in ("y", "yes", "是"):
        chat_with_yade(affinity_score=affinity)
    else:
        print(f"\n  {DIM}也好，亚德微微点了点头。{RESET}")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{DIM}游戏已退出。{RESET}")
    except FileNotFoundError as e:
        print(f"\033[91m{e}\033[0m")
