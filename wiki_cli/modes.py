"""The three interaction modes. The harness, not the model, enforces their differences:

  search : retrieval tool only -> original passages. No model call.
  ask    : RAG. retrieve -> research rules + numbered evidence -> Gemma -> citation check.
           Standalone: never sees chat history or the persona.
  chat   : persona + conversation history; a router decides per turn whether to retrieve notes.
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field

from . import citations
from .config import Config
from .llm import LLMError, LocalGemma
from .retrieval import Hit, Index
from .runlog import environment, save_run

# ------------------------------------------------------------------ terminal styling
import os

_TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")  # NO_COLOR=1 for clean transcripts


def style(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def dim(t): return style(t, "2")
def bold(t): return style(t, "1")
def cyan(t): return style(t, "36")
def yellow(t): return style(t, "33")
def green(t): return style(t, "32")
def red(t): return style(t, "31")


def header(cfg: Config, mode: str, llm: LocalGemma | None) -> str:
    if llm is None:
        return dim(f"[{mode} mode · retrieval only, no model call · local BM25 index]")
    return dim(f"[{mode} mode · model {cfg.model['name']} ({cfg.model.get('quantization', '')}) · local via Ollama {llm.runtime_version() or '?'}]")


def load_index(cfg: Config) -> Index:
    return Index.load(cfg.path("data") / "index.json")


def hit_record(i: int, h: Hit) -> dict:
    return {"n": i, "id": h.doc.doc_id, "kind": h.doc.kind, "path": h.doc.path, "location": h.doc.location,
            "score": h.score, "matched_terms": h.matched, "text": h.doc.text}


def print_passages(hits: list[Hit], full: bool = True) -> None:
    for i, h in enumerate(hits, 1):
        kind = "source" if h.doc.kind == "source" else "wiki note (generated)"
        print(f"\n{bold(f'[{i}]')} {cyan(h.doc.location)}")
        print(dim(f"    {kind} · {h.doc.path} · BM25 {h.score} · matched: {', '.join(h.matched)}"))
        text = h.doc.text if full else (h.doc.text[:300] + ("..." if len(h.doc.text) > 300 else ""))
        for line in text.splitlines():
            print(f"    {line}")


# ------------------------------------------------------------------ search
def run_search(cfg: Config, query: str, k: int, scope: str = "sources", save: bool = True) -> list[Hit]:
    idx = load_index(cfg)
    kinds = {"all": None, "sources": {"source"}, "wiki": {"wiki"}}[scope]
    t0 = time.perf_counter()
    hits = idx.search(query, k=k, kinds=kinds)
    ms = (time.perf_counter() - t0) * 1000
    print(header(cfg, "search", None))
    print(f"Query: {bold(query)}  ·  scope: {scope}  ·  {len(hits)} passage(s) in {ms:.0f} ms")
    if not hits:
        print(yellow("No matching passages."))
    print_passages(hits)
    if save:
        p = save_run(cfg, "search", {"env": environment(cfg), "query": query, "scope": scope,
                                     "passages": [hit_record(i, h) for i, h in enumerate(hits, 1)]})
        print(dim(f"\nSaved: {cfg.rel(p)}"))
    return hits


# ------------------------------------------------------------------ ask
@dataclass
class AskResult:
    question: str
    hits: list[Hit]
    answer: str
    report: citations.CitationReport
    stats: dict = field(default_factory=dict)
    skipped_model: bool = False
    saved: str = ""
    quotes: list = field(default_factory=list)
    rejected: list = field(default_factory=list)


EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"passage": {"type": "integer"}, "quote": {"type": "string"}},
                "required": ["passage", "quote"],
            },
        }
    },
    "required": ["quotes"],
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?", text.lower().replace("’", "'"))


def verify_quote(quote: str, passage: str) -> bool:
    """True if the quote really comes from the passage: >= 85% of its words appear, in order, in the passage."""
    q, p = _words(quote), _words(passage)
    if len(q) < 3:
        return False
    if " ".join(q) in " ".join(p):
        return True
    import difflib
    sm = difflib.SequenceMatcher(None, q, p, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(q) >= 0.85


def extract_messages(cfg: Config, question: str, hits: list[Hit]) -> list[dict]:
    passages = "\n\n".join(f"[{i}] {h.doc.location}\n{h.doc.text}" for i, h in enumerate(hits, 1))
    user = f"Passages:\n\n{passages}\n\nQuestion: {question}\n\nReturn the evidence quotes as JSON."
    return [{"role": "system", "content": cfg.prompt("ask-extract.md")}, {"role": "user", "content": user}]


_QNUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?")


def find_conflicts(quotes: list[dict]) -> list[str]:
    """Deterministic conflict check: quotes from different passages that say nearly the same thing but with
    different numbers (e.g. the same story copied into two prep docs with '10 to 16 weeks' vs '12 to 16 weeks')."""
    out = []
    groups: list[list[dict]] = []
    for q in quotes:
        words = set(re.sub(r"\d[\d,.%]*", " ", q["quote"].lower()).split())
        for g in groups:
            gw = g[0]["_w"]
            if words and gw and len(words & gw) / len(words | gw) >= 0.6:
                g.append({**q, "_w": words})
                break
        else:
            groups.append([{**q, "_w": words}])
    for g in groups:
        versions: dict[tuple, list[int]] = {}
        for q in g:
            versions.setdefault(tuple(_QNUM.findall(q["quote"])), []).append(q["passage"])
        if len(versions) > 1 and len({n for ps in versions.values() for n in ps}) > 1:
            parts = [f"passage(s) {', '.join(f'[{n}]' for n in sorted(set(ps)))} say {' / '.join(nums)}"
                     for nums, ps in versions.items()]
            out.append("; ".join(parts))
    return out


def answer_messages(cfg: Config, question: str, hits: list[Hit], quotes: list[dict],
                    conflicts: list[str] | None = None) -> list[dict]:
    by_passage: dict[int, list[str]] = {}
    for q in quotes:
        by_passage.setdefault(q["passage"], []).append(q["quote"])
    evidence = "\n\n".join(
        f"[{n}] {hits[n - 1].doc.location}\n" + "\n".join(f"- \"{t}\"" for t in qs)
        for n, qs in sorted(by_passage.items())
    )
    note = ""
    if conflicts:
        note = ("\n\nThe harness found that the sources DISAGREE on numbers:\n" + "\n".join(f"- {c}" for c in conflicts)
                + "\nYour answer must state each version with only its own citations and say the sources disagree.")
    user = (f"Evidence quotes (verified word-for-word from the owner's documents):\n\n{evidence}{note}\n\n"
            f"Question: {question}\n\nAnswer from these quotes only, citing passage numbers as [n].")
    return [{"role": "system", "content": cfg.prompt("wiki-instructions.md")}, {"role": "user", "content": user}]


def run_ask(cfg: Config, question: str, *, mode: str = "local", k: int | None = None,
            echo: bool = True, save: bool = True) -> AskResult:
    """RAG workflow: retrieve -> Gemma extracts quotes -> harness verifies quotes -> Gemma answers from
    verified quotes -> harness checks citations. The harness (not the model) returns INSUFFICIENT EVIDENCE
    when retrieval or quote verification finds nothing."""
    llm = LocalGemma(cfg, mode)
    llm.check()
    k = k or cfg.retrieval["ask_top_k"]
    idx = load_index(cfg)
    t0 = time.perf_counter()
    hits = idx.search(question, k=k, kinds={"source"})  # evidence = original source passages only
    retrieval_ms = round((time.perf_counter() - t0) * 1000, 1)
    if echo:
        print(header(cfg, "ask", llm))
        print(f"Question: {bold(question)}")
        print(dim(f"1. Retrieved {len(hits)} source passage(s) in {retrieval_ms} ms: "
                  + "; ".join(f"[{i}] {h.doc.location} ({h.score})" for i, h in enumerate(hits, 1))))
    stats: dict = {"retrieval_ms": retrieval_ms}
    quotes: list[dict] = []
    rejected: list[dict] = []
    skipped = not hits or hits[0].score < cfg.retrieval["min_score"]
    if skipped:
        answer = (f"{citations.INSUFFICIENT}: no source passage matched this question well enough "
                  f"(best score {hits[0].score if hits else 0} < {cfg.retrieval['min_score']}).")
    else:
        out, res = llm.chat_json(extract_messages(cfg, question, hits), EXTRACT_SCHEMA, purpose="ask")
        stats["extract"] = res.stats
        for q in out.get("quotes", [])[:8]:
            n, text = q.get("passage"), str(q.get("quote", "")).strip()
            ok = isinstance(n, int) and 1 <= n <= len(hits) and verify_quote(text, hits[n - 1].doc.text)
            (quotes if ok else rejected).append({"passage": n, "quote": text})
        if echo:
            print(dim(f"2. Gemma extracted {len(quotes) + len(rejected)} quote(s); harness verified {len(quotes)}"
                      + (f", rejected {len(rejected)} not found in the cited passage" if rejected else "")))
            for q in quotes:
                print(dim(f"     [{q['passage']}] \"{q['quote'][:110]}{'...' if len(q['quote']) > 110 else ''}\""))
        if not quotes:
            answer = (f"{citations.INSUFFICIENT}: none of the {len(hits)} retrieved passages contains a statement "
                      "that answers this question.")
            skipped = True
        else:
            if echo:
                print(dim("3. Answer from verified quotes:") + "\n")
            conflicts = find_conflicts(quotes)
            stats["conflicts"] = conflicts
            if echo and conflicts:
                print(yellow("   Sources disagree: " + " | ".join(conflicts)))
            res = llm.chat(answer_messages(cfg, question, hits, quotes, conflicts), purpose="ask",
                           on_token=(lambda t: print(t, end="", flush=True)) if echo else None)
            answer = res.text
            stats["answer"] = res.stats
            if echo:
                print()
    if skipped and echo:
        print("\n" + yellow(answer))
    stats["wall_s"] = round(sum(stats.get(k2, {}).get("wall_s", 0) for k2 in ("extract", "answer")), 2)
    report = citations.check(answer, [h.doc.text for h in hits])
    if echo:
        if report.cited:
            print(bold("\nSources cited:"))
            for c in report.cited:
                h = hits[c - 1]
                print(f"  [{c}] {cyan(h.doc.location)}  {dim(h.doc.path)}")
        color = green if report.ok else yellow
        print(color(f"\nCitation check: {report.summary()}"))
        if stats["wall_s"]:
            parts = [f"{k2} {stats[k2]['wall_s']}s ({stats[k2].get('prompt_tokens')}→{stats[k2].get('output_tokens')} tok)"
                     for k2 in ("extract", "answer") if k2 in stats]
            print(dim(f"Model time {stats['wall_s']}s · " + " · ".join(parts)))
    result = AskResult(question, hits, answer, report, stats, skipped)
    result.quotes, result.rejected = quotes, rejected
    if save:
        p = save_run(cfg, "ask", {
            "env": environment(cfg, llm), "question": question, "chat_history_used": False, "persona_used": False,
            "passages": [hit_record(i, h) for i, h in enumerate(hits, 1)], "verified_quotes": quotes,
            "rejected_quotes": rejected, "model_skipped_answer": skipped,
            "answer": answer, "citation_check": report.as_dict(), "stats": stats,
        })
        result.saved = cfg.rel(p)
        if echo:
            print(dim(f"Saved: {result.saved}"))
    return result


# ------------------------------------------------------------------ chat
_CAPABILITY = re.compile(r"\b(what can (you|we|u)|help me with|who are you|what do you do|how do you work|what are you)\b", re.I)
_FOLLOWUP = re.compile(r"^(make (that|it|this)|shorten|shorter|longer|expand|rewrite|rephrase|turn (that|it|this)|"
                       r"summari[sz]e (that|it|this)|more concise|less formal|more formal|again|try again|redo)", re.I)
_SMALLTALK = re.compile(r"^(hi|hey|hello|thanks|thank you|ok|okay|cool|great|bye)\b[\s!.?]*$", re.I)

ROUTER_SCHEMA = {
    "type": "object",
    "properties": {"use_notes": {"type": "boolean"}, "search_query": {"type": "string"}},
    "required": ["use_notes", "search_query"],
}


class ChatSession:
    def __init__(self, cfg: Config, mode: str = "local"):
        self.cfg = cfg
        self.llm = LocalGemma(cfg, mode)
        self.llm.check()
        self.persona = cfg.prompt("persona.md")
        self.history: list[dict] = []
        self.last_hits: list[Hit] = []
        self.turns: list[dict] = []
        self._index: Index | None = None

    @property
    def index(self) -> Index:
        if self._index is None:
            self._index = load_index(self.cfg)
        return self._index

    def route(self, message: str) -> tuple[bool, str, str]:
        """Decide whether this turn needs the notes. Returns (retrieve, query, reason)."""
        if _SMALLTALK.match(message.strip()):
            return False, "", "rule: small talk"
        if _CAPABILITY.search(message):
            return False, "", "rule: question about the assistant's capabilities"
        if self.history and _FOLLOWUP.match(message.strip()):
            return False, "", "rule: follow-up edit of the previous reply (uses conversation)"
        recent = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in self.history[-2:])
        user = (f"Recent conversation:\n{recent or '(none)'}\n\nNew user message: {message}\n\n"
                "Decide use_notes and search_query.")
        try:
            out, _ = self.llm.chat_json([{"role": "system", "content": self.cfg.prompt("chat-router.md")},
                                         {"role": "user", "content": user}], ROUTER_SCHEMA, purpose="router")
        except LLMError:
            return False, "", "router failed; answered without notes"
        q = (out.get("search_query") or message).strip()
        return bool(out.get("use_notes")), q, "model router"

    @staticmethod
    def _unverified_figures(message: str, hits: list[Hit]) -> list[str]:
        """Quantities ($5M, 34%, 16 weeks...) stated by the user that no retrieved passage contains."""
        evidence = re.sub(r"[\s,$]", "", " ".join(h.doc.text for h in hits).lower())
        out = []
        for m in re.finditer(r"\$\s?\d[\d,.]*\s?[mk]?\b|\d[\d,.]*\s?(?:%|m\b|k\b|million|weeks?|days?|years?)|\b\d{2,}\b",
                             message, re.I):
            core = re.sub(r"[\s,$]", "", m.group(0).lower()).replace("million", "m")
            core = re.sub(r"(weeks?|days?|years?)$", "", core)
            if core and core not in evidence:
                out.append(m.group(0).strip())
        return out

    def _trimmed_history(self) -> list[dict]:
        keep = self.history[-2 * self.cfg.chat["history_turns"]:]
        while keep and sum(len(m["content"]) for m in keep) > self.cfg.chat["history_chars"]:
            keep = keep[2:]
        return keep

    def reply(self, message: str, force_query: str | None = None) -> dict:
        if force_query:
            retrieve, query, reason = True, force_query, "user command /notes"
        else:
            retrieve, query, reason = self.route(message)
        hits: list[Hit] = []
        reused = False
        if not retrieve and reason.startswith("rule: follow-up") and self.last_hits:
            hits, reused = self.last_hits, True  # no new search: keep the passages the previous reply cited
        if retrieve:
            # chat may use reviewed wiki notes as well as original passages; ask uses original passages only
            hits = [h for h in self.index.search(query, k=self.cfg.retrieval["chat_top_k"])
                    if h.score >= self.cfg.retrieval["min_score"]]
        self.last_hits = hits
        print(dim(f"  ↳ notes lookup: {'yes' if retrieve else 'no'} ({reason})"
                  + (f" · query \"{query}\" · {len(hits)} passage(s)" if retrieve else "")
                  + (f" · reusing {len(hits)} passage(s) from the previous turn" if reused else "")))
        msgs = [{"role": "system", "content": self.persona}] + self._trimmed_history()
        if hits:
            notes = "\n\n".join(f"[{i}] {h.doc.location}\n{h.doc.text}" for i, h in enumerate(hits, 1))
            msgs.append({"role": "system", "content":
                         "Note passages retrieved for this turn (Amay's prep documents and reviewed wiki notes):\n\n" + notes +
                         "\n\nCite [n] after any fact taken from these passages. Label your own ideas as suggestions. "
                         "Earlier chat messages are not sources."})
        elif retrieve:
            msgs.append({"role": "system", "content":
                         "A notes lookup found nothing relevant for this turn. Do not invent personal facts; "
                         "say what is missing or use placeholders."})
        claims = self._unverified_figures(message, hits) if retrieve else []
        if claims:
            print(dim(f"  ↳ figures in your message not found in the notes: {', '.join(claims)}"))
            msgs.append({"role": "system", "content":
                         f"Amay's message states {', '.join(claims)}, which does not appear in the retrieved notes. Chat "
                         "messages are not verified sources. Do not accept, repeat or 'note' this figure as fact. Tell Amay "
                         "what the notes say on this point, citing [n], and that you cannot change the notes; they can edit "
                         "the source document and re-run `wiki ingest` if the notes are wrong."})
        msgs.append({"role": "user", "content": message})
        print(style("Scout: ", "1;35"), end="", flush=True)
        res = self.llm.chat(msgs, purpose="chat", on_token=lambda t: print(t, end="", flush=True))
        print()
        check = None
        if hits:
            cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", res.text) if 1 <= int(n) <= len(hits)})
            if cited:
                print(dim("  Sources: " + "; ".join(f"[{c}] {hits[c - 1].doc.location}" for c in cited)))
            check = citations.check(res.text, [h.doc.text for h in hits])
            qty = re.compile(r"\$|%|\d{2,}|\d[mk]$", re.I)  # ignore list numbering like "Day 1"
            problems = ([n for n in check.unsupported_numbers if qty.search(n)]
                        + [c for c in check.unsupported_citations if qty.search(c.split(" lacks ")[-1])]
                        + [f"[{n}] not retrieved" for n in check.invalid])
            if problems:
                print(yellow("  ⚠ citation check: " + "; ".join(problems) + " — verify against the notes (wiki search)"))
        elif re.search(r"\[\d+\]", res.text):
            print(yellow("  ⚠ citation check: reply shows [n] markers but no notes were retrieved this turn"))
        print(dim(f"  ({res.stats.get('wall_s')}s)"))
        self.history += [{"role": "user", "content": message}, {"role": "assistant", "content": res.text}]
        turn = {"user": message, "retrieve": retrieve, "route_reason": reason, "reused_previous_passages": reused, "query": query if retrieve else "",
                "passages": [hit_record(i, h) for i, h in enumerate(hits, 1)], "reply": res.text, "stats": res.stats,
                "citation_check": check.as_dict() if check else None}
        self.turns.append(turn)
        return turn

    def save_transcript(self) -> str:
        if not self.turns:
            return ""
        p = save_run(self.cfg, "chat", {"env": environment(self.cfg, self.llm), "persona": "prompts/persona.md",
                                        "turns": self.turns})
        return self.cfg.rel(p)


CHAT_HELP = """Commands:
  /notes <query>   look up your notes and answer using them
  /sources         show the passages used for the last reply
  /save <name>     save the last reply to drafts/<name>.md (a draft, never used as evidence)
  /reset           clear the conversation
  /help            show this help
  /exit            end the chat (transcript saved to runs/)"""


def run_chat(cfg: Config, mode: str = "local") -> None:
    session = ChatSession(cfg, mode)
    print(header(cfg, "chat", session.llm))
    print("Scout — your interview-prep assistant. Type /help for commands, /exit to quit.\n")
    interactive = sys.stdin.isatty()
    while True:
        try:
            msg = input(style("you: ", "1;34")) if interactive else input()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        msg = msg.strip()
        if not msg:
            continue
        if not interactive:
            print(style("you: ", "1;34") + msg)
        if msg.startswith("/"):
            cmd, _, arg = msg.partition(" ")
            cmd = cmd.lower()
            if cmd in ("/exit", "/quit"):
                break
            if cmd == "/help":
                print(CHAT_HELP)
            elif cmd == "/reset":
                session.history.clear()
                print(dim("Conversation cleared."))
            elif cmd == "/sources":
                if session.last_hits:
                    print_passages(session.last_hits, full=False)
                else:
                    print(dim("The last reply did not use any notes."))
            elif cmd == "/save":
                last = next((m["content"] for m in reversed(session.history) if m["role"] == "assistant"), None)
                if not last:
                    print(dim("Nothing to save yet."))
                    continue
                name = re.sub(r"[^\w\- ]", "", arg).strip() or time.strftime("draft-%Y%m%d-%H%M%S")
                d = cfg.path("drafts")
                d.mkdir(parents=True, exist_ok=True)
                path = d / f"{name}.md"
                path.write_text(f"<!-- Generated chat draft by {cfg.model['name']} on {time.strftime('%Y-%m-%d %H:%M')}. "
                                f"Not source evidence. -->\n\n{last}\n", encoding="utf-8")
                print(green(f"Saved draft: {cfg.rel(path)}"))
            elif cmd == "/notes":
                if not arg:
                    print(dim("Usage: /notes <query>"))
                    continue
                session.reply(arg, force_query=arg)
            else:
                print(dim(f"Unknown command {cmd}. Type /help."))
            continue
        try:
            session.reply(msg)
        except LLMError as e:
            print(red(f"\nModel error: {e}"))
    saved = session.save_transcript()
    if saved:
        print(dim(f"Chat transcript saved: {saved}"))
