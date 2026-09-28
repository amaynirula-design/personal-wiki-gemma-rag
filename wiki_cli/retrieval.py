"""Retrieval tool: a local BM25 keyword index over source passages and wiki notes.

Its only job is to find evidence. It never calls the language model, so `wiki search`
works with the Ollama server stopped.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

STOPWORDS = set(
    """a about above after again against all am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further had
    has have having he her here hers him his how i if in into is it its itself just me more most my
    myself no nor not now of off on once only or other our ours out over own same she should so some
    such than that the their theirs them then there these they this those through to too under until
    up very was we were what when where which while who whom why will with would you your yours
    tell time get got also like really much many""".split()
)

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")


def _stem(tok: str) -> str:
    """Tiny suffix stripper so 'monetize'/'monetization', 'shipments'/'shipment' match."""
    for suf, rep in (("ization", ""), ("isation", ""), ("ation", ""), ("ize", ""), ("ise", ""),
                     ("ies", "y"), ("ing", ""), ("ed", ""), ("s", "")):
        if tok.endswith(suf) and len(tok) - len(suf) >= 4 and not tok.endswith("ss"):
            return tok[: len(tok) - len(suf)] + rep
    return tok


def tokenize(text: str) -> list[str]:
    text = text.lower().replace("’", "'").replace("'s ", " ")
    out = []
    for t in _TOKEN.findall(text):
        t = t.strip(".-")
        if not t or t in STOPWORDS:
            continue
        out.append(_stem(t))
    return out


@dataclass
class Doc:
    doc_id: str
    kind: str  # "source" = original passage (evidence); "wiki" = generated note section
    path: str
    location: str
    heading: str
    text: str


@dataclass
class Hit:
    doc: Doc
    score: float
    matched: list[str]


class Index:
    K1, B = 1.5, 0.75

    def __init__(self, docs: list[Doc]):
        self.docs = docs
        self.tfs = [Counter(tokenize(d.heading) * 2 + tokenize(d.text)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg = sum(self.lens) / max(len(self.lens), 1)
        df = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int = 5, kinds: set[str] | None = None) -> list[Hit]:
        q = list(dict.fromkeys(tokenize(query)))
        hits = []
        for doc, tf, ln in zip(self.docs, self.tfs, self.lens):
            if kinds and doc.kind not in kinds:
                continue
            score, matched = 0.0, []
            for t in q:
                f = tf.get(t)
                if not f:
                    continue
                matched.append(t)
                score += self.idf[t] * f * (self.K1 + 1) / (f + self.K1 * (1 - self.B + self.B * ln / self.avg))
            if score > 0:
                hits.append(Hit(doc, round(score, 2), matched))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    # --- persistence -----------------------------------------------------------------
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(d) for d in self.docs], ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Index":
        if not path.exists():
            raise FileNotFoundError(
                f"No retrieval index at {path}. Run `wiki ingest` first to read sources and build it."
            )
        return cls([Doc(**d) for d in json.loads(path.read_text(encoding="utf-8"))])


def wiki_docs(wiki_dir: Path, root: Path) -> list[Doc]:
    """Split each wiki note into its '## ' sections (skipping pure navigation sections)."""
    docs = []
    skip = {"sources", "related notes", "used in interview prep", "stories prepared"}
    for f in sorted(wiki_dir.rglob("*.md")):
        body = f.read_text(encoding="utf-8")
        body = re.sub(r"^---\n.*?\n---\n", "", body, flags=re.S)
        title = f.stem
        parts = re.split(r"^## +", body, flags=re.M)
        intro = re.sub(r"^# .*\n", "", parts[0]).strip()
        rel = str(f.relative_to(root))
        if intro:
            docs.append(Doc(f"wiki:{title}#summary", "wiki", rel, f"{title} (wiki) › Summary", title, intro))
        for part in parts[1:]:
            head, _, text = part.partition("\n")
            if head.strip().lower() in skip or not text.strip():
                continue
            docs.append(Doc(f"wiki:{title}#{head.strip()}", "wiki", rel, f"{title} (wiki) › {head.strip()}",
                            f"{title} {head.strip()}", text.strip()))
    return docs
