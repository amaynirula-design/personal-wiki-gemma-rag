"""Read original sources from vault/raw/ and split them into sections and passages.

Sources are never modified. Supported: .docx (python-docx, fully local), .md, .txt.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED = {".docx", ".md", ".txt"}
_INVISIBLE = re.compile(r"[​‌‍⁠﻿]")
_BULLET = re.compile(r"^[•·\-\*–]\s*")
_PROMPT_START = re.compile(r"^(\d+\.\s+)?(tell me|why|what|how|who|describe|walk me)\b", re.I)
_QUESTION_LIST = re.compile(r"^questions\b", re.I)


@dataclass
class Section:
    idx: int
    heading: str
    group: str  # enclosing ALL-CAPS heading, e.g. "BEHAVIORAL QUESTIONS" ("" if none)
    paragraphs: list[str] = field(default_factory=list)
    para_nums: list[int] = field(default_factory=list)  # 1-based numbers among non-empty doc paragraphs

    @property
    def text(self) -> str:
        return "\n".join(self.paragraphs)

    @property
    def words(self) -> int:
        return len(self.text.split())

    @property
    def label(self) -> str:
        h = self.heading if len(self.heading) <= 90 else self.heading[:87].rstrip() + "..."
        return h


@dataclass
class Source:
    source_id: str
    path: Path
    sha256: str
    sections: list[Section]

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass
class Passage:
    passage_id: str
    source_id: str
    path: str  # project-relative path of the original file
    filename: str
    section: str
    group: str
    paragraphs: str  # e.g. "¶12-15"
    text: str

    @property
    def location(self) -> str:
        return f"{self.filename} › {self.section} ({self.paragraphs})"


def source_id_for(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean(text: str) -> str:
    text = _INVISIBLE.sub("", text).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def _heading_kind(text: str, bold: bool, in_question_list: bool) -> str | None:
    """Classify a paragraph as 'group', 'section' or None (body text). Heuristics tuned for
    interview-prep docs whose headings are inconsistently formatted (bold / caps / plain '?')."""
    words = len(text.split())
    if words == 0 or words > 40 or _BULLET.match(text):
        return None
    if text.lower().startswith("sample answer"):
        return None
    if _QUESTION_LIST.match(text):
        return "section"
    letters = [c for c in text if c.isalpha()]
    if letters and words <= 8 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        return "group"
    if bold:
        return "section"
    if in_question_list:
        return None
    if text.endswith("?"):
        return "section"
    if text.endswith(":") and _PROMPT_START.match(text):
        return "section"
    if _PROMPT_START.match(text) and (text.startswith("Tell me") or re.match(r"^\d+\.\s", text)):
        return "section"
    return None


def _docx_paragraphs(path: Path) -> list[tuple[str, bool]]:
    import docx  # local import so search mode still works if python-docx is missing

    out = []
    for p in docx.Document(str(path)).paragraphs:
        text = _clean(p.text)
        if not text:
            continue
        runs = [r for r in p.runs if r.text.strip()]
        bold = bool(runs) and all(r.bold for r in runs)
        style = (p.style.name or "").lower() if p.style is not None else ""
        if style.startswith("list") and not text.startswith(("•", "-")) and not bold:
            text = "- " + text
        out.append((text, bold))
    return out


def _text_paragraphs(path: Path) -> list[tuple[str, bool]]:
    out = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
        block = _clean(block)
        if not block:
            continue
        m = re.match(r"^#{1,6}\s+(.*)", block)
        if m and "\n" not in block:
            out.append((m.group(1), True))
        else:
            out.append((block, False))
    return out


def load_source(path: Path) -> Source:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {path.name} (supported: {', '.join(sorted(SUPPORTED))})")
    paras = _docx_paragraphs(path) if path.suffix.lower() == ".docx" else _text_paragraphs(path)

    sections: list[Section] = []
    group = ""
    current = Section(idx=0, heading="Introduction", group="")
    in_qlist = False
    for n, (text, bold) in enumerate(paras, start=1):
        kind = _heading_kind(text, bold, in_qlist)
        if kind == "group":
            group = text.rstrip(":").strip()
            in_qlist = bool(re.search(r"questions for", text, re.I))
            if in_qlist:  # "QUESTIONS FOR ..." is itself a section of interviewer questions
                kind = "section"
            else:
                continue
        if kind == "section":
            if current.paragraphs:
                sections.append(current)
            heading = re.sub(r"^\d+\.\s*", "", text).rstrip(":").strip()
            current = Section(idx=len(sections), heading=heading, group=group)
            in_qlist = bool(_QUESTION_LIST.match(text))
            continue
        current.paragraphs.append(text)
        current.para_nums.append(n)
    if current.paragraphs:
        sections.append(current)
    for i, s in enumerate(sections):
        s.idx = i
    return Source(source_id=source_id_for(path), path=path, sha256=sha256_file(path), sections=sections)


def passages_for(source: Source, rel_path: str, target_words: int = 180, max_words: int = 240) -> list[Passage]:
    """Split each section into passages of about `target_words`, on paragraph boundaries.
    Consecutive passages of one section overlap by one short paragraph for context."""
    out: list[Passage] = []
    for s in source.sections:
        chunks: list[tuple[int, int]] = []  # (start, end) paragraph indexes, end exclusive
        start, count = 0, 0
        for i, p in enumerate(s.paragraphs):
            w = len(p.split())
            if count and count + w > max_words:
                chunks.append((start, i))
                prev = s.paragraphs[i - 1]
                start = i - 1 if len(prev.split()) <= 60 and i - 1 > start else i
                count = sum(len(x.split()) for x in s.paragraphs[start:i])
            count += w
        chunks.append((start, len(s.paragraphs)))
        for n, (a, b) in enumerate(chunks, start=1):
            p0, p1 = s.para_nums[a], s.para_nums[b - 1]
            out.append(
                Passage(
                    passage_id=f"{source.source_id}:s{s.idx:02d}p{n}",
                    source_id=source.source_id,
                    path=rel_path,
                    filename=source.filename,
                    section=s.label,
                    group=s.group,
                    paragraphs=f"¶{p0}" if p0 == p1 else f"¶{p0}-{p1}",
                    text="\n".join(s.paragraphs[a:b]),
                )
            )
    return out
