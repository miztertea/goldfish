import json
import sys
from pathlib import Path

from goldfish.config import project_name
from goldfish.drain import handle_pre_compact, handle_session_start

try:
    from goldfish.enricher import enrich
except ImportError:
    def enrich(prompt: str, cwd: str, project: str) -> str:  # type: ignore[misc]
        return ""

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"

_ASYNC_EVENTS = {"Stop", "SessionEnd", "PostToolUse", "SubagentStop", "TaskCreated", "TaskCompleted"}
_SYNC_EVENTS = {"SessionStart", "UserPromptSubmit", "PreCompact"}


def handle(event: dict, queue: Path = QUEUE_PATH) -> None:
    """Append event to queue (for async events only)."""
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("a") as f:
        f.write(json.dumps(event) + "\n")


def main_with_event(event: dict, queue: Path = QUEUE_PATH) -> None:
    """Process one event. Exported for testing."""
    event_type = event.get("type", "")

    if event_type not in _SYNC_EVENTS:
        handle(event, queue=queue)
        return

    # Synchronous events: process inline, write to stdout
    if event_type == "SessionStart":
        result = handle_session_start(event)
        if result:
            sys.stdout.write(result)
    elif event_type == "UserPromptSubmit":
        prompt = event.get("prompt", "")
        cwd = event.get("cwd", ".")
        result = enrich(prompt, cwd, project_name(cwd))
        if result:
            sys.stdout.write(result)
    elif event_type == "PreCompact":
        handle_pre_compact(event)


def main() -> None:
    event = json.loads(sys.stdin.read())
    main_with_event(event)


if __name__ == "__main__":
    main()
