"""Ingestion: original sources -> passages + Gemma-organized wiki notes + index.md + retrieval index.

Pipeline (see README "Architecture"):
  1. parse    each source in vault/raw/ into sections and passages (no model)
  2. assign   each new/changed section to a note: Gemma proposes a name, the catalog resolves it
              to an existing note when it is the same subject (prevents duplicates)
  3. write    each note whose inputs changed: Gemma summarizes ONLY that note's source excerpts
  4. render   Markdown notes with source references and links, index.md, Source Catalog.md
  5. index    rebuild the BM25 retrieval index over source passages + wiki notes
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml

from .catalog import Catalog, slug
from .config import Config
from .llm import LocalGemma
from .retrieval import Doc, Index, wiki_docs
from .sources import SUPPORTED, Source, load_source, passages_for

MAX_SECTION_WORDS_ASSIGN = 250
MAX_NOTE_INPUT_WORDS = 2000
SAME_SUBJECT_OVERLAP = 0.35


def _truncate(text: str, words: int) -> str:
    w = text.split()
    return text if len(w) <= words else " ".join(w[:words]) + " ..."


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
FOLDER_TYPE = {"Companies": "company", "Stories": "story", "Background": "background", "Concepts": "concept"}


def _short_q(heading: str, limit: int = 90) -> str:
    """Shorten a long interview-question heading for link lists: cut at the first '/' or ' ('."""
    h = re.split(r"/| \(", heading, maxsplit=1)[0].strip()
    h = h if len(h) <= limit else h[: limit - 3].rstrip() + "..."
    return h if h.endswith("?") or h == heading else h + "..."


def _short_label(filename: str) -> str:
    """'Amazon Interview.docx' -> 'Amazon prep' (display label for source links)."""
    first = Path(filename).stem.split()[0]
    return f"{first[:1].upper()}{first[1:]} prep"


class Ingestor:
    def __init__(self, cfg: Config, llm: LocalGemma | None, log=print, force: bool = False, reassign: bool = False):
        self.cfg = cfg
        self.llm = llm
        self.log = log
        self.force = force          # re-run Gemma on the targeted sources' notes (reviewed pages are still kept)
        self.reassign = reassign    # also redo the section -> note organization (pinned review choices are kept)
        self._targets: set[str] = set()
        self.data = cfg.path("data")
        self.catalog = Catalog(self.data / "catalog.json")
        self.calls: list[dict] = []
        self.stats = Counter()

    # ------------------------------------------------------------------ helpers
    def _call_json(self, step: str, messages: list[dict], schema: dict) -> dict:
        obj, res = self.llm.chat_json(messages, schema, purpose="ingest")
        self.calls.append({"step": step, **res.stats})
        return obj

    def _all_raw(self) -> list[Path]:
        raw = self.cfg.path("raw")
        return sorted(p for p in raw.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)

    def _load_sources(self) -> dict[str, Source]:
        return {s.source_id: s for s in (load_source(p) for p in self._all_raw())}

    # ------------------------------------------------------------------ step 2: assign
    @staticmethod
    def _shingles(text: str, n: int = 3) -> set[tuple]:
        w = re.findall(r"[a-z0-9$.%]+", text.lower())
        return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}

    def _same_subject(self, sec_text: str, sources: dict[str, Source], pending: list[tuple[str, str]]):
        """Find an already-assigned section telling the same thing (e.g. the same STAR story copied into
        another prep doc). Returns (note, overlap, where) or None. Overlap = shared 3-word shingles / the
        smaller section; repeated stories score 0.57-1.0 in this corpus, different subjects <= 0.23."""
        mine = self._shingles(sec_text)
        best = None
        candidates = list(pending)
        for sid, src in self.catalog.sources.items():
            if sid in sources:
                for rec in src["sections"]:
                    if rec["idx"] < len(sources[sid].sections):
                        candidates.append((rec["note"], sources[sid].sections[rec["idx"]].text, f"{src['filename']} › {rec['heading'][:40]}"))
        for cand in candidates:
            note, text, where = cand if len(cand) == 3 else (*cand, "this document")
            other = self._shingles(text)
            if not mine or not other:
                continue
            overlap = len(mine & other) / min(len(mine), len(other))
            if best is None or overlap > best[1]:
                best = (note, overlap, where)
        return best if best and best[1] >= SAME_SUBJECT_OVERLAP and best[0] in self.catalog.notes else None

    def _assign_source(self, src: Source, sources: dict[str, Source]) -> None:
        folders = self.cfg.folders
        schema = {
            "type": "object",
            "properties": {
                "about": {"type": "string"},
                "folder": {"type": "string", "enum": folders},
                "note_title": {"type": "string"},
            },
            "required": ["about", "folder", "note_title"],
        }
        old = {s.get("text_sha"): s for s in self.catalog.sources.get(src.source_id, {}).get("sections", [])}
        self.catalog.sources.pop(src.source_id, None)  # its sections are re-decided below
        sections, pending = [], []
        for sec in src.sections:
            text_sha = hashlib.sha256(f"{sec.heading}\n{sec.text}".encode()).hexdigest()[:16]
            prev = old.get(text_sha)
            pinned = prev if prev and prev.get("pinned") and prev.get("note") in self.catalog.notes else None
            same = None if (prev and not self.reassign) or pinned else self._same_subject(sec.text, sources, pending)
            if pinned:
                note = pinned["note"]
                self.log(f"  = {sec.label[:60]:60} -> {note} (pinned by review)")
            elif prev and prev.get("note") in self.catalog.notes and not self.reassign:
                note = prev["note"]
                self.log(f"  = {sec.label[:60]:60} -> {note} (unchanged)")
            elif same:
                note = same[0]
                self.log(f"  ≈ {sec.label[:60]:60} -> {note} (same text as {same[2]}, overlap {same[1]:.2f})")
                self.stats["sections_matched_by_text"] += 1
            else:
                # Stories are deduplicated by text overlap above, so only non-story notes are offered for reuse:
                # a small model shown story names tends to reuse them for unrelated stories.
                existing = "\n".join(
                    f"- {t} ({m['folder']}): {m.get('description', '')}"
                    for t, m in self.catalog.notes.items() if m["folder"] != "Stories"
                ) or "(none yet)"
                user = (
                    f"Existing Companies/Background/Concepts notes:\n{existing}\n\n"
                    f"Source document: {src.filename}\n"
                    f"Section heading: {sec.heading}\n"
                    + (f"Document part: {sec.group}\n" if sec.group else "")
                    + f"Section text:\n{_truncate(sec.text, MAX_SECTION_WORDS_ASSIGN)}\n\n"
                    "First write `about`: one line saying what this section is about (which company, which "
                    "experience, or which topic). Then choose the folder. Then the note_title:\n"
                    "- Companies: why this company/role, what the company does, questions for the interviewer -> "
                    "reuse that company's existing note name if listed, else '<Company> <Role or Team>'.\n"
                    "- Stories: a specific experience from the owner's past work told as an answer -> a NEW name "
                    "for what happened, e.g. 'Graton Casino Expansion', 'Supply Chain Delays'.\n"
                    "- Background: the owner's overall career summary or pitch.\n"
                    "- Concepts: industry or company knowledge not about the owner."
                )
                msgs = [{"role": "system", "content": self.cfg.prompt("ingest-instructions.md")},
                        {"role": "user", "content": user}]
                out = self._call_json(f"assign {src.source_id} s{sec.idx}", msgs, schema)
                folder = out.get("folder") if out.get("folder") in folders else folders[0]
                note, is_new = self.catalog.resolve(out.get("note_title", ""), folder)
                if is_new:
                    self.catalog.notes[note] = {
                        "folder": folder,
                        "note_id": f"{folder.lower()}/{slug(note)}",
                        "description": out.get("about", "").strip(),
                        "aliases": [],
                        "input_hash": None,
                    }
                    self.stats["notes_created"] += 1
                proposed = out.get("note_title", "").strip()
                if proposed and proposed != note and proposed not in self.catalog.notes[note]["aliases"]:
                    self.catalog.notes[note]["aliases"].append(proposed)
                self.log(f"  + {sec.label[:60]:60} -> {note}{' (new)' if is_new else ''}  [{out.get('about', '')[:70]}]")
                self.stats["sections_assigned_by_model"] += 1
            pending.append((note, sec.text))
            sections.append({
                "idx": sec.idx, "heading": sec.heading, "group": sec.group, "text_sha": text_sha,
                "paragraphs": f"¶{sec.para_nums[0]}-{sec.para_nums[-1]}", "words": sec.words, "note": note,
                **({"pinned": True} if pinned else {}),
            })
        self.catalog.sources[src.source_id] = {
            "file": self.cfg.rel(src.path),
            "filename": src.filename,
            "sha256": src.sha256,
            "ingested_at": datetime.now().isoformat(timespec="seconds"),
            "sections": sections,
        }

    # ------------------------------------------------------------------ step 3: write
    def _note_inputs(self, title: str, sources: dict[str, Source]) -> tuple[str, dict[str, str], str]:
        """Return (excerpt text, letter->source_id, input hash) for one note."""
        pairs = self.catalog.note_sections(title)
        letters: dict[str, str] = {}
        blocks = []
        budget = MAX_NOTE_INPUT_WORDS // max(len(pairs), 1)
        for sid, idx in pairs:
            if sid not in letters.values():
                letters["ABCDEFGHIJ"[len(letters)]] = sid
            letter = next(k for k, v in letters.items() if v == sid)
            sec = sources[sid].sections[idx]
            blocks.append(f"[{letter}] {sources[sid].filename} › {sec.heading}\n{_truncate(sec.text, max(budget, 150))}")
        text = "\n\n".join(blocks)
        h = hashlib.sha256((title + text).encode()).hexdigest()[:16]
        return text, letters, h

    def _write_note(self, title: str, sources: dict[str, Source]) -> None:
        meta = self.catalog.notes[title]
        excerpts, letters, h = self._note_inputs(title, sources)
        store = self.data / "notes" / f"{slug(meta['note_id'])}.json"
        if meta.get("input_hash") == h and store.exists() and not self.force:
            self.stats["notes_unchanged"] += 1
            return
        others = "\n".join(
            f"- {t}: {m.get('description', '')}" for t, m in self.catalog.notes.items() if t != title
        )
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "sources": {"type": "array", "items": {"type": "string", "enum": list(letters)}},
                        },
                        "required": ["text", "sources"],
                    },
                },
                "differences": {"type": "array", "items": {"type": "string"}},
                "related": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}, "why": {"type": "string"}},
                        "required": ["title", "why"],
                    },
                },
            },
            "required": ["summary", "key_points", "differences", "related"],
        }
        user = (
            f"Write the wiki note \"{title}\" (folder: {meta['folder']}).\n\n"
            f"Source excerpts (labeled by letter):\n\n{excerpts}\n\n"
            f"Other notes in the wiki:\n{others or '(none)'}\n\n"
            "Return JSON with:\n"
            "- summary: 2-3 sentences on what this note covers, using only the excerpts.\n"
            "- key_points: 4-8 specific facts from the excerpts (numbers, actions, results). Each lists the "
            "letters of the excerpts that state it.\n"
            "- differences: places where the excerpts disagree (e.g. different numbers for the same thing); "
            "empty list if none.\n"
            "- related: 0-3 notes from the 'Other notes' list that share the same project, client, company or "
            "a directly connected event, each with a one-sentence reason. An empty list is fine. Do not link "
            "notes just because both happened at the same employer, and do not invent note names."
        )
        msgs = [{"role": "system", "content": self.cfg.prompt("ingest-instructions.md")},
                {"role": "user", "content": user}]
        t0 = time.perf_counter()
        out = self._call_json(f"write {title}", msgs, schema)
        self.log(f"  ✎ {title} ({time.perf_counter() - t0:.0f}s)")
        known = {t.lower(): t for t in self.catalog.notes}
        related = []
        for r in out.get("related", [])[:3]:
            t = known.get(str(r.get("title", "")).strip().strip("[]").lower())
            if t and t != title and t not in {x["title"] for x in related}:
                related.append({"title": t, "why": r.get("why", "").strip()})
        points = []
        for p in out.get("key_points", [])[:8]:
            sids = list(dict.fromkeys(letters[l] for l in p.get("sources", []) if l in letters))
            points.append({"text": p.get("text", "").strip(), "sources": sids})
        # Gemma saw the sources as excerpts A/B/C; replace those letters with readable source names.
        names = {l: _short_label(sources[sid].filename).replace(" prep", "") + " prep" for l, sid in letters.items()}

        def readable(text: str) -> str:
            def sub(m: re.Match) -> str:
                ls = re.findall(r"\b[A-J]\b", m.group(0))
                return ("the " + " and ".join(names.get(l, l) for l in ls)) if ls else m.group(0)
            return re.sub(r"\bexcerpts?\s+[A-J](?:\s*(?:,|and)\s*[A-J])*\b", sub, text, flags=re.I)

        record = {
            "title": title,
            "summary": readable(out.get("summary", "").strip()),
            "key_points": points,
            "differences": [readable(d.strip()) for d in out.get("differences", []) if d.strip()],
            "related": related,
            "model": self.llm.model,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        meta["input_hash"] = h
        first = re.split(r"(?<=[.!?])\s", record["summary"], maxsplit=1)[0]
        meta["description"] = first[:160]
        self.stats["notes_written"] += 1

    # ------------------------------------------------------------------ step 4: render
    def _company_for_source(self) -> dict[str, str]:
        out = {}
        for sid, src in self.catalog.sources.items():
            c = Counter(s["note"] for s in src["sections"] if self.catalog.notes.get(s["note"], {}).get("folder") == "Companies")
            if c:
                out[sid] = c.most_common(1)[0][0]
        return out

    def _check_attribution(self, title: str, points: list[dict]) -> list[dict]:
        """A key point that states numbers keeps only the sources whose section text contains all of them
        (re-attributed to the sources that do, if the model named none correctly)."""
        src_text: dict[str, str] = defaultdict(str)
        for sid, idx in self.catalog.note_sections(title):
            if sid in self._sources:
                src_text[sid] += " " + self._sources[sid].sections[idx].text.replace(",", "")

        def has(sid: str, nums: list[str]) -> bool:
            return all(re.search(rf"(?<![\d.]){re.escape(n)}(?!\d)", src_text[sid]) for n in nums)

        out = []
        for p in points:
            sids = [s for s in p["sources"] if s in src_text]
            nums = [n.replace(",", "") for n in _NUM.findall(p["text"])]
            if nums:
                ok = [s for s in sids if has(s, nums)] or [s for s in src_text if has(s, nums)]
                if ok != sids:
                    self.stats["attributions_corrected"] += 1
                sids = ok
            out.append({**p, "sources": sids})
        return out

    def _render_note(self, title: str) -> str | None:
        meta = self.catalog.notes[title]
        store = self.data / "notes" / f"{slug(meta['note_id'])}.json"
        if not store.exists():
            return None
        rec = json.loads(store.read_text(encoding="utf-8"))
        srcs = self.catalog.sources
        pairs = self.catalog.note_sections(title)
        company_of = self._company_for_source()

        def src_link(sid: str) -> str:
            fn = srcs[sid]["filename"]
            return f"[[raw/{fn}|{_short_label(fn)}]]"

        fm_sources = []
        for sid, idx in pairs:
            sec = next(s for s in srcs[sid]["sections"] if s["idx"] == idx)
            fm_sources.append({"source_id": sid, "file": f"raw/{srcs[sid]['filename']}",
                               "section": sec["heading"], "paragraphs": sec["paragraphs"]})
        fm = {
            "title": title,
            "note_id": meta["note_id"],
            "type": FOLDER_TYPE.get(meta["folder"], meta["folder"].lower()),
            "aliases": meta.get("aliases", []),
            "sources": fm_sources,
            "generated_by": f"{rec['model']} (local Ollama)",
            "generated_at": rec["generated_at"],
            "reviewed": False,
        }
        lines = ["---", yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000).strip(), "---", "",
                 f"# {title}", "", rec["summary"], ""]
        if rec["key_points"]:
            lines += ["## Key points", ""]
            for p in self._check_attribution(title, rec["key_points"]):
                tag = ", ".join(src_link(s) for s in p["sources"]) or "unsourced — check"
                lines.append(f"- {p['text']} ({tag})")
            lines.append("")
        if rec["differences"]:
            lines += ["## Where the sources differ", ""] + [f"- {d}" for d in rec["differences"]] + [""]

        linked = set()
        if meta["folder"] == "Companies":
            prepared: dict[str, str] = {}
            for sid, comp in company_of.items():
                if comp != title:
                    continue
                for s in srcs[sid]["sections"]:
                    other = s["note"]
                    if other != title and other in self.catalog.notes and other not in prepared:
                        prepared[other] = f"- [[{other}]] — for \"{_short_q(s['heading'])}\""
                        linked.add(other)
            if prepared:
                lines += ["## Prepared answers", ""] + list(prepared.values()) + [""]
        else:
            used: dict[str, str] = {}
            for sid, idx in pairs:
                comp = company_of.get(sid)
                if comp and comp != title and comp not in used:
                    sec = next(s for s in srcs[sid]["sections"] if s["idx"] == idx)
                    used[comp] = f"- [[{comp}]] — answers \"{_short_q(sec['heading'])}\" ({_short_label(srcs[sid]['filename'])})"
                    linked.add(comp)
            if used:
                lines += ["## Used in interview prep", ""] + list(used.values()) + [""]
        rel = [r for r in rec["related"] if r["title"] in self.catalog.notes and r["title"] not in linked]
        if rel:
            lines += ["## Related notes", ""] + [f"- [[{r['title']}]] — {r['why']}" for r in rel] + [""]
        lines += ["## Sources", ""]
        for s in fm_sources:
            lines.append(f"- [[{s['file']}|{Path(s['file']).name}]] › \"{_short_q(s['section'])}\" ({s['paragraphs']})")
        lines += ["", "See also: [[index]] · [[Source Catalog]]", ""]
        return "\n".join(lines)

    def _note_path(self, title: str) -> Path:
        return self.cfg.path("wiki") / self.catalog.notes[title]["folder"] / f"{title}.md"

    def _is_reviewed(self, path: Path) -> bool:
        if not path.exists():
            return False
        m = re.match(r"^---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
        return bool(m and re.search(r"^reviewed:\s*true\s*$", m.group(1), re.M))

    def render_all(self) -> None:
        wiki = self.cfg.path("wiki")
        if not getattr(self, "_sources", None):
            self._sources = self._load_sources()
        expected = set()
        for title in sorted(self.catalog.notes):
            path = self._note_path(title)
            expected.add(path.resolve())
            if self._is_reviewed(path):
                self.stats["notes_kept_reviewed"] += 1
                continue
            text = self._render_note(title)
            if text is None:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
                self.stats["files_written"] += 1
        # Remove generated notes that no longer have any source section (e.g. after a merge).
        for f in wiki.rglob("*.md"):
            if f.resolve() not in expected and not self._is_reviewed(f):
                f.unlink()
                self.stats["files_removed"] += 1
        self._render_index()
        self._render_source_catalog()
        self._obsidian_defaults()

    def _index_description(self, title: str) -> str:
        """One-line description for index.md, taken from the note's own (possibly reviewed) summary."""
        text = self._note_path(title).read_text(encoding="utf-8")
        body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        m = re.search(r"^# .+\n\n(.+?)\n", body, re.M)
        desc = m.group(1) if m else self.catalog.notes[title].get("description", "")
        desc = re.split(r"(?<=[.!?])\s", desc, maxsplit=1)[0]
        desc = re.sub(r"^This note (?:covers|details|summarizes|describes)\s+(?:the\s+|an?\s+)?", "", desc).strip()
        desc = desc[:1].upper() + desc[1:]
        if len(desc) > 130:
            desc = desc[:130].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        return desc

    def _render_index(self) -> None:
        desc = {
            "Companies": "Target companies and roles: why this company, what it does, questions to ask.",
            "Stories": "Real experiences told as interview answers (STAR stories), merged across prep documents.",
            "Background": "Career summary and personal pitch.",
            "Concepts": "Company and industry knowledge to have ready.",
        }
        by = defaultdict(list)
        for t, m in self.catalog.notes.items():
            if self._note_path(t).exists():
                by[m["folder"]].append(t)
        lines = ["# Index", "",
                 "**Interview Prep Wiki** — personal wiki built from three internship interview-prep documents (Amazon Pathways, Tanium, "
                 "TikTok MSO). Notes were drafted by local Gemma from the originals in `raw/` and reviewed; every "
                 "note lists its sources. Start with a company, follow its stories, then open the source.", "",
                 "Source list and section-to-note mapping: [[Source Catalog]]", ""]
        for folder in self.cfg.folders:
            if not by.get(folder):
                continue
            lines += [f"## {folder}", "", f"_{desc.get(folder, '')}_", ""]
            for t in sorted(by[folder]):
                lines.append(f"- [[{t}]] — {self._index_description(t)}")
            lines.append("")
        (self.cfg.path("vault") / "index.md").write_text("\n".join(lines), encoding="utf-8")

    def _render_source_catalog(self) -> None:
        lines = ["# Source Catalog", "",
                 "Original documents in `raw/` are kept unchanged after import. The Tanium document is a copy in "
                 "which two third-party first names were replaced with `[former Tanium intern]` and `[interviewer]` "
                 "before ingestion; nothing else was edited.", ""]
        for sid, s in sorted(self.catalog.sources.items()):
            lines += [f"## {s['filename']}", "",
                      f"- File: [[raw/{s['filename']}|{s['filename']}]]",
                      f"- Source ID: `{sid}`",
                      f"- SHA-256: `{s['sha256'][:16]}…`",
                      f"- Ingested: {s['ingested_at']}", "",
                      "| Section | Paragraphs | Wiki note |", "|---|---|---|"]
            for sec in s["sections"]:
                h = sec["heading"].replace("|", "/")
                h = h if len(h) <= 80 else h[:77] + "..."
                lines.append(f"| {h} | {sec['paragraphs']} | [[{sec['note']}]] |")
            lines.append("")
        lines += ["Back to [[index]]", ""]
        (self.cfg.path("vault") / "Source Catalog.md").write_text("\n".join(lines), encoding="utf-8")

    def _obsidian_defaults(self) -> None:
        obs = self.cfg.path("vault") / ".obsidian"
        obs.mkdir(exist_ok=True)
        app = obs / "app.json"
        if not app.exists():
            app.write_text(json.dumps({"showUnsupportedFiles": True, "alwaysUpdateLinks": True,
                                       "newLinkFormat": "shortest"}, indent=2))
        graph = obs / "graph.json"
        if not graph.exists():
            colors = [(f"path:wiki/{f}", c) for f, c in zip(self.cfg.folders, [0x4E79A7, 0xF28E2B, 0x59A14F, 0xB07AA1])]
            graph.write_text(json.dumps({
                "search": "path:wiki/", "showAttachments": False, "hideUnresolved": True, "showOrphans": True,
                "showTags": False, "showArrow": False, "textFadeMultiplier": -1, "nodeSizeMultiplier": 1.2,
                "lineSizeMultiplier": 1, "colorGroups": [{"query": q, "color": {"a": 1, "rgb": c}} for q, c in colors],
            }, indent=2))

    # ------------------------------------------------------------------ step 5: index
    def build_index(self, sources: dict[str, Source]) -> Index:
        r = self.cfg.retrieval
        docs, passages = [], []
        for sid in sorted(self.catalog.sources):
            if sid not in sources:
                continue
            src = sources[sid]
            for p in passages_for(src, self.cfg.rel(src.path), r["passage_words"], r["max_passage_words"]):
                passages.append(p.__dict__)
                # heading field (weighted x2 by BM25) = document name + section, so "Tanium interview" finds that doc
                docs.append(Doc(p.passage_id, "source", p.path, p.location, f"{Path(p.filename).stem} {p.section}", p.text))
        docs += wiki_docs(self.cfg.path("wiki"), self.cfg.root)
        idx = Index(docs)
        idx.save(self.data / "index.json")
        with open(self.data / "passages.jsonl", "w", encoding="utf-8") as f:
            for p in passages:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        self.stats["passages"] = len(passages)
        self.stats["wiki_chunks"] = len(docs) - len(passages)
        return idx

    # ------------------------------------------------------------------ entry point
    def run(self, targets: list[Path]) -> dict:
        t0 = time.perf_counter()
        raw = self.cfg.path("raw").resolve()
        files: list[Path] = []
        for t in targets:
            t = t.resolve()
            if not t.exists():
                raise FileNotFoundError(f"No such file or folder: {t}")
            if raw not in [t, *t.parents]:
                raise ValueError(f"{t} is outside {self.cfg.rel(raw)}. Copy originals into vault/raw/ first "
                                 "(they are kept there unchanged as evidence).")
            files += [t] if t.is_file() else sorted(p for p in t.rglob("*") if p.suffix.lower() in SUPPORTED)
        if not files:
            raise FileNotFoundError(f"No supported sources ({', '.join(sorted(SUPPORTED))}) found in the given path.")
        sources = self._load_sources()
        for f in files:
            src = next(s for s in sources.values() if s.path.resolve() == f.resolve())
            prev = self.catalog.sources.get(src.source_id)
            status = "new" if not prev else ("changed" if prev["sha256"] != src.sha256 else "unchanged")
            self.log(f"\n[{status}] {src.filename}: {len(src.sections)} sections, {sum(s.words for s in src.sections)} words")
            self._targets.add(src.source_id)
            if status == "unchanged" and not (self.force or self.reassign):
                self.stats["sources_unchanged"] += 1
                continue
            if self.llm is None:
                raise RuntimeError("The local model is required to organize new or changed sources.")
            self._assign_source(src, sources)
            self.stats["sources_processed"] += 1
        self.refresh(sources)
        self.stats["seconds"] = round(time.perf_counter() - t0, 1)
        return {"stats": dict(self.stats), "calls": self.calls}

    def refresh(self, sources: dict[str, Source]) -> None:
        """Write notes whose inputs changed, re-render the vault, rebuild the retrieval index."""
        for t in [t for t in self.catalog.notes if not self.catalog.note_sections(t)]:
            del self.catalog.notes[t]
            self.stats["notes_dropped"] += 1
        pending = [t for t in sorted(self.catalog.notes)
                   if self._note_inputs(t, sources)[2] != self.catalog.notes[t].get("input_hash")
                   or (self.force and any(sid in self._targets for sid, _ in self.catalog.note_sections(t)))]
        if pending and self.llm is None:
            raise RuntimeError("The local model is required to write notes.")
        if pending:
            self.log(f"\nWriting {len(pending)} note(s) with {self.llm.model}:")
        for t in pending:
            self._write_note(t, sources)
            self.catalog.save()
        self.catalog.save()
        self.render_all()
        self.build_index(sources)

    # ------------------------------------------------------------------ cleanup: rename / merge
    def rename(self, old: str, new: str, folder: str | None = None) -> None:
        """Rename a note (or merge it into an existing one). Keeps the machine note_id, records the old
        name as an alias so re-ingestion maps back to the new name, and rewrites incoming links."""
        cat = self.catalog
        match = {t.lower(): t for t in cat.notes}
        if old.lower() not in match:
            raise ValueError(f"No note named '{old}'. Existing: {', '.join(sorted(cat.notes))}")
        old = match[old.lower()]
        new = new.strip()
        if re.search(r"[\\/:*?\"<>|#\[\]]", new) or not new:
            raise ValueError(f"'{new}' is not a valid note name (avoid / : * ? \" < > | # [ ]).")
        new = match.get(new.lower(), new)
        folder = folder or (cat.notes[new]["folder"] if new in cat.notes else cat.notes[old]["folder"])
        if folder not in self.cfg.folders:
            raise ValueError(f"Unknown folder '{folder}'. Choose from: {', '.join(self.cfg.folders)}")
        merge = new in cat.notes and new != old
        old_path = self._note_path(old)
        old_meta = cat.notes[old]

        for src in cat.sources.values():
            for sec in src["sections"]:
                if sec["note"] == old:
                    sec["note"] = new
        carried = [a for a in [old, *old_meta.get("aliases", [])] if a != new]
        for a in carried:
            cat.aliases[slug(a)] = new
        if merge:
            target = cat.notes[new]
            target["aliases"] = list(dict.fromkeys(target.get("aliases", []) + carried))
            target["input_hash"] = None  # inputs changed: regenerate the merged note
            del cat.notes[old]
            if old_path.exists():
                old_path.unlink()
            self.log(f"Merged '{old}' into '{new}'.")
        else:
            meta = cat.notes.pop(old)
            meta["folder"] = folder
            meta["aliases"] = list(dict.fromkeys(meta.get("aliases", []) + carried))
            cat.notes[new] = meta
            new_path = self._note_path(new)
            if old_path.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                text = old_path.read_text(encoding="utf-8").replace(f"# {old}\n", f"# {new}\n", 1)
                text = re.sub(rf"^title: {re.escape(old)}$", f"title: {new}", text, count=1, flags=re.M)
                old_path.unlink()
                new_path.write_text(text, encoding="utf-8")
            self.log(f"Renamed '{old}' -> '{new}' (folder {folder}, note_id {meta['note_id']} kept).")

        # rewrite incoming links in notes and in stored note records
        pat = re.compile(r"\[\[" + re.escape(old) + r"(\||\]\])")
        for f in list(self.cfg.path("wiki").rglob("*.md")) + list((self.data / "notes").glob("*.json")):
            text = f.read_text(encoding="utf-8")
            if f.suffix == ".json":
                rec = json.loads(text)
                for r in rec.get("related", []):
                    if r["title"] == old:
                        r["title"] = new
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            elif pat.search(text):
                f.write_text(pat.sub(lambda m: f"[[{new}{m.group(1)}", text), encoding="utf-8")
        cat.save()
        if merge and self.llm is None:
            self.log("Model not available: run `wiki ingest` later to regenerate the merged note.")
            self.render_all()
            self.build_index(self._load_sources())
        else:
            self.refresh(self._load_sources())
        self.log("Updated links, index.md, Source Catalog and retrieval index.")

    # ------------------------------------------------------------------ cleanup: reassign one section
    def assign(self, source: str, section: str, note: str, folder: str | None = None) -> None:
        """Review correction: move one source section to another (possibly new) note. The choice is
        pinned so later re-ingestion keeps it."""
        cat = self.catalog
        sid = next((k for k, v in cat.sources.items()
                    if source.lower() in (k, v["filename"].lower()) or v["filename"].lower().startswith(source.lower())), None)
        if sid is None:
            raise ValueError(f"Unknown source '{source}'. Known: {', '.join(v['filename'] for v in cat.sources.values())}")
        secs = cat.sources[sid]["sections"]
        hit = [s for s in secs if section.isdigit() and s["idx"] == int(section)] or \
              [s for s in secs if s["heading"].lower().startswith(section.lower())]
        if len(hit) != 1:
            raise ValueError(f"Section '{section}' matched {len(hit)} sections in {sid}. Use a longer prefix or the index:\n"
                             + "\n".join(f"  {s['idx']}: {s['heading'][:80]}" for s in secs))
        sec = hit[0]
        match = {t.lower(): t for t in cat.notes}
        title = match.get(note.lower(), note.strip())
        if title not in cat.notes:
            if not folder or folder not in self.cfg.folders:
                raise ValueError(f"'{title}' is a new note: pass --folder ({', '.join(self.cfg.folders)}).")
            cat.notes[title] = {"folder": folder, "note_id": f"{folder.lower()}/{slug(title)}", "description": "",
                                "aliases": [], "input_hash": None}
        elif folder and folder != cat.notes[title]["folder"]:
            raise ValueError(f"'{title}' already exists in {cat.notes[title]['folder']}; use `wiki rename --folder` to move it.")
        self.log(f"Section '{_short_q(sec['heading'])}' ({sid}) : {sec['note']} -> {title} (pinned)")
        sec["note"], sec["pinned"] = title, True
        cat.save()
        if self.llm is None:
            raise RuntimeError("The local model is required to rewrite the affected notes (start `ollama serve`).")
        self.refresh(self._load_sources())
