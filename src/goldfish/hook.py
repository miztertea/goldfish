import json
import sys
from pathlib import Path

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def handle(event: dict, queue: Path = QUEUE_PATH) -> None:
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("a") as f:
        f.write(json.dumps(event) + "\n")


def main() -> None:
    event = json.loads(sys.stdin.read())
    handle(event)


if __name__ == "__main__":
    main()
