"""CLI runner and helper for Primer commands in Antigravity."""

import json
import sys
from pathlib import Path


def load_board() -> dict:
    board_path = Path(".primer/board.json")
    if not board_path.exists():
        return {"epics": []}
    return json.loads(board_path.read_text(encoding="utf-8"))


def save_board(data: dict) -> None:
    board_path = Path(".primer/board.json")
    board_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cmd_status() -> None:
    board = load_board()
    print("=== Primer Project Status ===")
    active_path = Path(".primer/active.md")
    if active_path.exists():
        print(f"\n{active_path.read_text(encoding='utf-8')[:300]}...\n")
    print("Epics Overview:")
    for ep in board.get("epics", []):
        stories = ep.get("stories", [])
        done_count = sum(1 for s in stories if s.get("status") == "done")
        total = len(stories)
        status_str = ep.get("status", "todo").upper()
        title_str = ep.get("title")
        print(f"  [{status_str}] {ep.get('id')}: {title_str} ({done_count}/{total} stories)")


def cmd_story_start(story_id: str) -> None:
    board = load_board()
    found = False
    for ep in board.get("epics", []):
        for s in ep.get("stories", []):
            if s.get("id") == story_id or story_id in s.get("title", ""):
                s["status"] = "in_progress"
                ep["status"] = "in_progress"
                found = True
                print(f"[OK] Story '{s.get('id')}: {s.get('title')}' is now IN_PROGRESS.")
                break
    if not found:
        print(f"[FAIL] Story '{story_id}' not found in .primer/board.json")
        sys.exit(1)
    save_board(board)


def cmd_story_done(story_id: str) -> None:
    board = load_board()
    found = False
    for ep in board.get("epics", []):
        for s in ep.get("stories", []):
            if s.get("id") == story_id or story_id in s.get("title", ""):
                s["status"] = "done"
                found = True
                print(f"[OK] Story '{s.get('id')}: {s.get('title')}' is now DONE.")
                break
        # Check if all stories in epic are done
        stories = ep.get("stories", [])
        if stories and all(s.get("status") == "done" for s in stories):
            ep["status"] = "done"
            print(f"[OK] Epic '{ep.get('id')}: {ep.get('title')}' is now 100% DONE!")
    if not found:
        print(f"[FAIL] Story '{story_id}' not found in .primer/board.json")
        sys.exit(1)
    save_board(board)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: primer_runner.py [status|story-start|story-done|sync|init] [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        cmd_status()
    elif cmd in ("story-start", "story_start") and len(sys.argv) > 2:
        cmd_story_start(sys.argv[2])
    elif cmd in ("story-done", "story_done") and len(sys.argv) > 2:
        cmd_story_done(sys.argv[2])
    elif cmd == "sync":
        cmd_status()
    elif cmd == "init":
        Path(".primer").mkdir(exist_ok=True)
        print("[OK] Primer workspace initialized.")
    else:
        print(f"Unknown or incomplete command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
