"""Load config.yaml and resolve project paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


def find_root(start: Path | None = None) -> Path:
    """Project root = WIKI_HOME, else the nearest parent of cwd with config.yaml, else the repo."""
    if os.environ.get("WIKI_HOME"):
        return Path(os.environ["WIKI_HOME"]).expanduser().resolve()
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        if (d / "config.yaml").exists():
            return d
    repo = Path(__file__).resolve().parent.parent
    if (repo / "config.yaml").exists():
        return repo
    raise ConfigError("config.yaml not found. Run wiki from the project folder or set WIKI_HOME.")


@dataclass
class Config:
    root: Path
    raw: dict

    def path(self, key: str) -> Path:
        return self.root / self.raw["paths"][key]

    @property
    def model(self) -> dict:
        return self.raw["model"]

    @property
    def retrieval(self) -> dict:
        return self.raw["retrieval"]

    @property
    def chat(self) -> dict:
        return self.raw["chat"]

    @property
    def folders(self) -> list[str]:
        return self.raw["wiki"]["folders"]

    def rel(self, p: Path) -> str:
        """Path relative to the project root, for display and logs."""
        try:
            return str(Path(p).resolve().relative_to(self.root))
        except ValueError:
            return str(p)

    def prompt(self, name: str) -> str:
        p = self.path("prompts") / name
        if not p.exists():
            raise ConfigError(f"Missing prompt file: {self.rel(p)}")
        return p.read_text(encoding="utf-8").strip()


def load_config(start: Path | None = None) -> Config:
    root = find_root(start)
    with open(root / "config.yaml", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config(root=root, raw=raw)
