import json
import subprocess
from pathlib import Path

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def drain(queue: Path = QUEUE_PATH) -> int:
    if not queue.exists():
        return 0
    lines = queue.read_text().splitlines()
    queue.write_text("")
    processed = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        _route(event)
        processed += 1
    return processed


def _route(event: dict) -> None:
    cwd = event.get("cwd", ".")
    subprocess.run(
        ["semble", "search", ".", cwd],
        capture_output=True,
        check=False,
    )


def main() -> None:
    count = drain()
    print(f"Drained {count} events")


if __name__ == "__main__":
    main()
