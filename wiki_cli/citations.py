"""Citation checks on generated answers.

A citation is not proof by itself, so the harness checks mechanically what it can:
  - every [n] points to a passage that was actually retrieved and shown to the model
  - factual sentences carry at least one citation
  - numbers in a cited sentence appear in EACH passage it cites (a citation to a passage that
    does not contain the number is flagged, even if another cited passage does)
Human review is still needed to confirm the passage supports the claim's meaning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

INSUFFICIENT = "INSUFFICIENT EVIDENCE"
_CITE = re.compile(r"\[(\d+)\]")
_NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*(?:%|[mk]\b)?", re.I)


def _norm_num(s: str) -> str:
    return re.sub(r"[\s,$]", "", s.lower())


def _sentences(text: str) -> list[str]:
    parts = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        if not line:
            continue
        parts += [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line) if p.strip()]
    return parts


@dataclass
class CitationReport:
    insufficient: bool
    cited: list[int] = field(default_factory=list)
    invalid: list[int] = field(default_factory=list)
    uncited_sentences: list[str] = field(default_factory=list)
    unsupported_numbers: list[str] = field(default_factory=list)
    unsupported_citations: list[str] = field(default_factory=list)  # "[2] lacks 12"

    @property
    def ok(self) -> bool:
        if self.insufficient:
            return not self.cited and not self.invalid
        return (bool(self.cited) and not self.invalid and not self.unsupported_numbers
                and not self.unsupported_citations and not self.uncited_sentences)

    def summary(self) -> str:
        if self.insufficient:
            return "insufficient-evidence response" + ("" if self.ok else " (but it also cites passages — check)")
        bits = [f"{len(self.cited)} passage(s) cited: {', '.join(f'[{c}]' for c in self.cited) or 'none'}"]
        if self.invalid:
            bits.append(f"INVALID citation numbers {self.invalid}")
        if self.uncited_sentences:
            bits.append(f"{len(self.uncited_sentences)} sentence(s) without a citation")
        if self.unsupported_numbers:
            bits.append(f"numbers not found in any cited passage: {', '.join(self.unsupported_numbers)}")
        if self.unsupported_citations:
            bits.append(f"citations that do not contain the stated number: {', '.join(self.unsupported_citations)}")
        return ("PASS — " if self.ok else "CHECK — ") + "; ".join(bits)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "insufficient": self.insufficient, "cited": self.cited, "invalid": self.invalid,
                "uncited_sentences": self.uncited_sentences, "unsupported_numbers": self.unsupported_numbers,
                "unsupported_citations": self.unsupported_citations,
                "summary": self.summary()}


def check(answer: str, passages: list[str]) -> CitationReport:
    """`passages` are the texts numbered [1..n] in the prompt."""
    insufficient = answer.strip().upper().startswith(INSUFFICIENT)
    nums = [int(n) for n in _CITE.findall(answer)]
    rep = CitationReport(insufficient=insufficient)
    rep.cited = sorted({n for n in nums if 1 <= n <= len(passages)})
    rep.invalid = sorted({n for n in nums if not 1 <= n <= len(passages)})
    if insufficient:
        return rep
    for sent in _sentences(answer):
        cites = [int(n) for n in _CITE.findall(sent) if 1 <= int(n) <= len(passages)]
        bare = _CITE.sub("", sent).strip()
        if not cites:
            if len(bare.split()) >= 5 and not bare.endswith(":"):
                rep.uncited_sentences.append(bare)
            continue
        # Check each clause against the citation group that follows it:
        # "from 12 to 16 weeks [1][3], but ... from 10 to 16 weeks [2]." -> ("...12 to 16...", [1,3]), ("...10...", [2])
        parts = _GROUP.split(sent)
        for clause, group in zip(parts[0::2], parts[1::2]):
            _check_numbers(rep, clause, [int(n) for n in _CITE.findall(group) if 1 <= int(n) <= len(passages)], passages)
    return rep


_GROUP = re.compile(r"((?:\s*\[\d+\])+)")


def _check_numbers(rep: CitationReport, bare: str, cites: list[int], passages: list[str]) -> None:
    if not cites:
        return
    per = {c: _norm_num(passages[c - 1]) for c in cites}
    for m in _NUM.findall(bare):
        core = re.sub(r"[%mk]$", "", _norm_num(m))
        if not core:
            continue
        present = [c for c in per if re.search(rf"(?<![\d.]){re.escape(core)}(?!\d)", per[c])]
        if not present:
            rep.unsupported_numbers.append(m.strip())
        else:
            rep.unsupported_citations += [f"[{c}] lacks {m.strip()}" for c in per if c not in present]
