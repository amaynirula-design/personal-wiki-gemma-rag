"""Save every run (mode, model, execution setting, retrieved passages, answer, checks) as JSON."""
from __future__ import annotations

import json
import platform
import socket
from datetime import datetime
from pathlib import Path

from .config import Config


def internet_status(timeout: float = 1.5) -> str:
    """'online' if a public host is reachable, else 'offline'. Used as proof in evidence files."""
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            socket.create_connection((host, port), timeout=timeout).close()
            return "online"
        except OSError:
            continue
    return "offline"


def environment(cfg: Config, llm=None) -> dict:
    env = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "execution": "local",
        "internet": internet_status(),
        "host": platform.node(),
        "platform": f"{platform.system()} {platform.mac_ver()[0] or platform.release()} ({platform.machine()})",
        "model": cfg.model["name"],
        "model_identifier": cfg.model.get("identifier"),
        "quantization": cfg.model.get("quantization"),
    }
    if llm is not None:
        env["runtime"] = f"ollama {llm.runtime_version() or 'unreachable'}"
    return env


def save_run(cfg: Config, mode: str, record: dict) -> Path:
    runs = cfg.path("runs")
    runs.mkdir(parents=True, exist_ok=True)
    path = runs / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{mode}.json"
    n = 1
    while path.exists():
        path = runs / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{mode}-{n}.json"
        n += 1
    path.write_text(json.dumps({"mode": mode, **record}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
