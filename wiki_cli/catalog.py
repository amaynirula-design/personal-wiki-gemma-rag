"""Note catalog: maps source sections to readable wiki notes (machine IDs live here, not in filenames)."""
from __future__ import annotations

import json
import re
from pathlib import Path

SMALL = {"a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to", "vs"}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean_title(raw: str, max_words: int = 5) -> str:
    """Normalize a model-proposed note name into a short, Title Case, filename-safe subject name."""
    t = re.sub(r"[\"'“”‘’?!:;/\\|#\[\]{}<>*]", " ", raw)
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .-")
    t = re.sub(r"^(the|a|an)\s+", "", t, flags=re.I)
    words = t.split()[:max_words]
    out = []
    for i, w in enumerate(words):
        if any(c.isupper() for c in w[1:]) or w.isupper():  # keep TikTok, AR, MBA
            out.append(w)
        elif i > 0 and w.lower() in SMALL:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out) or "Untitled Note"


def _words(title: str) -> set[str]:
    return {w for w in slug(title).split("-") if w and w not in SMALL}


class Catalog:
    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.sources: dict = data.get("sources", {})
        self.notes: dict = data.get("notes", {})
        self.aliases: dict = data.get("aliases", {})  # slug of a proposed/old name -> canonical title

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"sources": self.sources, "notes": self.notes, "aliases": self.aliases}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def resolve(self, proposed: str, folder: str) -> tuple[str, bool]:
        """Map a proposed name to an existing note (exact, alias, or near-duplicate) -> (title, is_new)."""
        title = clean_title(proposed)
        s = slug(title)
        for existing in self.notes:
            if slug(existing) == s:
                return existing, False
        if s in self.aliases and self.aliases[s] in self.notes:
            return self.aliases[s], False
        w = _words(title)
        for existing, meta in self.notes.items():
            ew = _words(existing)
            if w and ew and len(w & ew) / len(w | ew) >= 0.6 and meta["folder"] == folder:
                self.aliases[s] = existing
                return existing, False
        return title, True

    def note_sections(self, title: str) -> list[tuple[str, int]]:
        return [
            (sid, sec["idx"])
            for sid, src in self.sources.items()
            for sec in src["sections"]
            if sec.get("note") == title
        ]
