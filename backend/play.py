#!/usr/bin/env python3
"""Interactive CLI script to playtest a level's dialogue tree.

Usage:
    python play.py                    # plays chapter_01 by default
    python play.py chapter_02         # plays a specific chapter

No server, database, or Docker needed — reads directly from YAML.
"""

import sys

from app.services.level_service import level_service

# --- Display helpers ---

SPEAKER_LABELS = {
    "narrator": "\033[90m[旁白]\033[0m",
    "yade": "\033[96m[亚德]\033[0m",
    "yade_inner": "\033[36m[亚德·内心]\033[0m",
    "girl": "\033[95m[小女孩]\033[0m",
    "action": "\033[33m[动作]\033[0m",
}

DIVIDER = "\033[90m" + "─" * 50 + "\033[0m"


def display_node(node):
    """Print a dialogue node to the terminal."""
    label = SPEAKER_LABELS.get(node.speaker, f"\033[93m[{node.speaker}]\033[0m")
    print()
    print(DIVIDER)
    print(label)
    if node.action:
        print(f"  \033[33m（{node.action}）\033[0m")
    if node.text:
        print(f"  {node.text.strip()}")


def display_choices(options):
    """Print available options and return user's selection."""
    print()
    for i, opt in enumerate(options):
        major_tag = " \033[91m★\033[0m" if opt.is_major else ""
        print(f"  \033[97m{opt.id}\033[0m. {opt.text}{major_tag}")
    print()

    valid_ids = [o.id for o in options]
    while True:
        choice = input(f"  请选择 ({'/'.join(valid_ids)}): ").strip().upper()
        if choice in valid_ids:
            return next(o for o in options if o.id == choice)
        print(f"  \033[91m无效选择，请输入 {'/'.join(valid_ids)}\033[0m")


def wait_for_advance():
    """Wait for the player to press Enter to advance."""
    input("  \033[90m(按 Enter 继续...)\033[0m")


# --- Main game loop ---

def play(level_id: str = "chapter_01"):
    level = level_service.load_level(level_id)

    print()
    print("\033[1m" + "=" * 50 + "\033[0m")
    print(f"\033[1m  {level.title}\033[0m")
    if level.scene:
        print(f"  \033[90m{level.scene}\033[0m")
    print("\033[1m" + "=" * 50 + "\033[0m")

    current_node_id = level.start_node
    affinity = 0
    choices_made: dict[str, str] = {}  # node_id -> chosen option id

    while current_node_id:
        node = level.nodes.get(current_node_id)
        if node is None:
            print(f"\n\033[91m[错误] 找不到节点: {current_node_id}\033[0m")
            break

        # --- Conditional branching ---
        if node.condition:
            for ref_node_id, mapping in node.condition.items():
                prev_choice = choices_made.get(ref_node_id)
                if prev_choice and prev_choice in mapping:
                    current_node_id = mapping[prev_choice]
                    continue
            # If we set current_node_id via condition, loop again
            if current_node_id != node.id:
                continue

        # --- Display the node ---
        display_node(node)

        # --- Handle options (player choice) ---
        if node.options:
            chosen = display_choices(node.options)
            choices_made[node.id] = chosen.id
            affinity += chosen.affinity_delta

            if chosen.affinity_delta != 0:
                sign = "+" if chosen.affinity_delta > 0 else ""
                print(f"  \033[93m好感度 {sign}{chosen.affinity_delta} (总计: {affinity})\033[0m")

            current_node_id = chosen.next_node

        # --- Ending ---
        elif node.is_ending:
            print()
            print(DIVIDER)
            print(f"\n\033[1m  ── 关卡结束 ──\033[0m")
            print(f"  \033[93m最终好感度: {affinity}\033[0m")
            print(f"  \033[90m选择记录: {choices_made}\033[0m")
            print()
            break

        # --- Auto-advance ---
        elif node.next_node:
            wait_for_advance()
            current_node_id = node.next_node

        else:
            print("\n\033[91m[错误] 节点没有 next_node 也没有 options\033[0m")
            break


if __name__ == "__main__":
    level_id = sys.argv[1] if len(sys.argv) > 1 else "chapter_01"
    try:
        play(level_id)
    except KeyboardInterrupt:
        print("\n\n\033[90m游戏已退出。\033[0m")
    except FileNotFoundError as e:
        print(f"\033[91m{e}\033[0m")
