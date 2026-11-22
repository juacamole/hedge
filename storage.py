import json
import os
from datetime import datetime

RUNS_DIR = "runs"


def default_path() -> str:
    name = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".json"
    return os.path.join(RUNS_DIR, name)


def save(run: dict, path: str) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=2)


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        run = json.load(f)
    if "meta" not in run or "records" not in run:
        raise ValueError(f"{path} is not a run file")
    return run


def saved_paths() -> list[str]:
    if not os.path.isdir(RUNS_DIR):
        return []
    names = sorted(n for n in os.listdir(RUNS_DIR) if n.endswith(".json"))
    return [os.path.join(RUNS_DIR, n) for n in names]
