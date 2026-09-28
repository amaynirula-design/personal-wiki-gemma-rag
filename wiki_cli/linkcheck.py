"""Vault checks: links resolve to exactly one file, headings match filenames, readable names, sources exist."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from .config import Config

_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
_MACHINE = re.compile(r"([0-9a-f]{8,}|\d{8}|\d{4}-\d{2}-\d{2}|--|_|\bchunk\b|\btask\b|\?)", re.I)


def check_vault(cfg: Config) -> tuple[list[str], dict]:
    vault = cfg.path("vault")
    files = [p for p in vault.rglob("*") if p.is_file() and ".obsidian" not in p.parts]
    by_name: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        by_name[(f.stem if f.suffix == ".md" else f.name).lower()].append(f)
        by_name[str(f.relative_to(vault)).lower()].append(f)
        if f.suffix == ".md":
            by_name[str(f.relative_to(vault).with_suffix("")).lower()].append(f)

    problems: list[str] = []
    stats = defaultdict(int)
    notes = sorted((cfg.path("wiki")).rglob("*.md"))
    incoming: dict[str, int] = defaultdict(int)
    for md in [vault / "index.md", vault / "Source Catalog.md", *notes]:
        if not md.exists():
            problems.append(f"missing {md.relative_to(vault)}")
            continue
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(vault)
        for target in _LINK.findall(text):
            stats["links"] += 1
            hits = set(by_name.get(target.strip().lower(), []))
            if not hits:
                problems.append(f"{rel}: broken link [[{target}]]")
            elif len(hits) > 1:
                problems.append(f"{rel}: ambiguous link [[{target}]] -> {sorted(str(h.relative_to(vault)) for h in hits)}")
            else:
                h = hits.pop()
                if h.suffix != ".md":
                    stats["source_links"] += 1
                if md != vault / "index.md" and h in notes:
                    incoming[h.stem] += 1
        if md in notes:
            stats["notes"] += 1
            m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            fm = yaml.safe_load(m.group(1)) if m else {}
            h1 = re.search(r"^# (.+)$", text, re.M)
            if not h1 or h1.group(1).strip() != md.stem:
                problems.append(f"{rel}: first heading does not match filename")
            words = md.stem.split()
            if not 1 <= len(words) <= 6 or _MACHINE.search(md.stem):
                problems.append(f"{rel}: filename is not a short readable subject name")
            srcs = fm.get("sources") or []
            if not srcs:
                problems.append(f"{rel}: no source references")
            for s in srcs:
                if not (vault / s["file"]).exists():
                    problems.append(f"{rel}: source file missing: {s['file']}")
            if fm.get("reviewed"):
                stats["reviewed"] += 1
    for n in notes:
        if incoming[n.stem] == 0:
            problems.append(f"{n.relative_to(vault)}: no incoming links from other notes (only the index)")
    stats["raw_sources"] = sum(1 for f in files if "raw" in f.relative_to(vault).parts)
    return problems, dict(stats)
