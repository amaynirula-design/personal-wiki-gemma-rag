"""`wiki` command-line interface: parses the command and hands it to the harness."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import ConfigError, load_config
from .llm import LLMError, LocalGemma
from .modes import bold, dim, green, red, yellow

DESCRIPTION = """Personal interview-prep wiki: local Gemma + RAG over your own notes (runs offline).

Modes:
  chat    personal assistant (Scout) with conversation memory; looks up notes only when needed
  ask     standalone factual answer from retrieved source passages, with citations
          (or an explicit INSUFFICIENT EVIDENCE response)
  search  show matching original passages and their source locations; no model, no answer"""

EPILOG = """examples:
  wiki ingest vault/raw                     read sources, write/update wiki notes, rebuild the index
  wiki search "linear chain architecture"   original passages only (works with the model stopped)
  wiki ask "How quickly can Tanium query all endpoints?"
  wiki chat                                 start Scout; /help inside chat lists commands
  wiki eval tests/ask_tests.yaml            run the four ask-mode tests, write evidence cards
  wiki status                               model, runtime, index and internet status
  wiki check                                verify wiki links, headings, names and source references
  wiki rename "Old Name" "New Name" [--folder Background]    cleanup: rename/merge, links updated
  wiki assign Tanium "Why Cybersecurity" "Tanium Product Management"   cleanup: move one section

configuration: config.yaml (model name, context size, retrieval settings, paths)
instructions:  prompts/persona.md (chat personality), prompts/wiki-instructions.md (ask research rules),
               prompts/ask-extract.md (ask evidence step), prompts/chat-router.md, prompts/ingest-instructions.md
requires:      Ollama running locally (`ollama serve`) with the model in config.yaml,
               except for `wiki search`, which needs only the index built by `wiki ingest`."""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wiki", description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("ingest", help="read sources in vault/raw, write linked wiki notes, update index")
    s.add_argument("paths", nargs="*", default=["vault/raw"], help="files or folders inside vault/raw (default: vault/raw)")
    s.add_argument("--force", action="store_true",
                   help="re-run Gemma on the notes of these sources even if unchanged (reviewed pages are kept; "
                        "fresh drafts go to data/notes/)")
    s.add_argument("--reassign", action="store_true",
                   help="also redo the section-to-note organization (review choices made with `wiki assign` are kept)")

    s = sub.add_parser("search", help="show original matching passages (no model)")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=None, help="number of passages (default from config)")
    s.add_argument("--scope", choices=["sources", "wiki", "all"], default="sources",
                   help="original source passages (default), generated wiki notes, or both")

    s = sub.add_parser("ask", help="standalone factual answer with citations")
    s.add_argument("question")
    s.add_argument("--mode", choices=["local", "online"], default="local", help="execution setting (default: local)")
    s.add_argument("-k", type=int, default=None, help="passages given to the model (default from config)")

    s = sub.add_parser("chat", help="interactive personal assistant")
    s.add_argument("--mode", choices=["local", "online"], default="local", help="execution setting (default: local)")

    s = sub.add_parser("eval", help="run the ask-mode test set and write evidence cards")
    s.add_argument("tests", nargs="?", default="tests/ask_tests.yaml")
    s.add_argument("--out", default="evidence/ask-tests")

    sub.add_parser("status", help="show model, runtime, index and internet status")
    sub.add_parser("check", help="check wiki links, headings, note names and source references")

    s = sub.add_parser("rename", help="rename or merge a wiki note and update links, catalog and index")
    s.add_argument("old")
    s.add_argument("new")
    s.add_argument("--folder", default=None, help="also move the note to this topic folder")

    s = sub.add_parser("assign", help="review correction: move one source section to another note (pinned)")
    s.add_argument("source", help="source id or filename prefix, e.g. Tanium")
    s.add_argument("section", help="section heading prefix or section index (see Source Catalog)")
    s.add_argument("note", help="target note title (existing or new)")
    s.add_argument("--folder", default=None, help="folder for a new note")

    sub.add_parser("help", help="show this help")
    return p


def cmd_status(cfg) -> None:
    from .runlog import internet_status
    llm = LocalGemma(cfg)
    print(bold("Personal Wiki status"))
    print(f"  project:   {cfg.root}")
    print(f"  model:     {cfg.model['name']}  ({cfg.model.get('identifier')}, {cfg.model.get('quantization')})")
    ver = llm.runtime_version()
    print(f"  runtime:   {'ollama ' + ver if ver else red('Ollama server not reachable (start: ollama serve)')}")
    if ver:
        try:
            llm.check()
            print(f"  model ok:  {green('installed')}")
        except LLMError as e:
            print(f"  model ok:  {red(str(e).splitlines()[0])}")
        for m in llm.loaded_models():
            print(f"  loaded:    {m['name']} · {m.get('size', 0) / 1e9:.2f} GB total · {m.get('size_vram', 0) / 1e9:.2f} GB on GPU · ctx {m.get('context_length', '?')}")
    idx = cfg.path("data") / "index.json"
    if idx.exists():
        docs = json.loads(idx.read_text())
        n_src = sum(d["kind"] == "source" for d in docs)
        print(f"  index:     {n_src} source passages + {len(docs) - n_src} wiki sections ({cfg.rel(idx)})")
    else:
        print(f"  index:     {yellow('not built — run wiki ingest')}")
    notes = list(cfg.path("wiki").rglob("*.md"))
    print(f"  wiki:      {len(notes)} notes in {cfg.rel(cfg.path('wiki'))}")
    print(f"  internet:  {internet_status()}  (execution is local either way)")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        parser.print_help()
        return 0
    try:
        cfg = load_config()
        if args.command == "search":
            from .modes import run_search
            run_search(cfg, args.query, args.k or cfg.retrieval["search_top_k"], args.scope)
        elif args.command == "ask":
            from .modes import run_ask
            run_ask(cfg, args.question, mode=args.mode, k=args.k)
        elif args.command == "chat":
            from .modes import run_chat
            run_chat(cfg, args.mode)
        elif args.command == "ingest":
            from .ingest import Ingestor
            from .runlog import environment, save_run
            llm = LocalGemma(cfg)
            llm.check()
            print(dim(f"[ingest · model {cfg.model['name']} · local via Ollama {llm.runtime_version()}]"))
            ing = Ingestor(cfg, llm, force=args.force, reassign=args.reassign)
            out = ing.run([Path(p) for p in args.paths])
            st = out["stats"]
            print(bold("\nIngest complete") + f" in {st.get('seconds')}s")
            for k in ("sources_processed", "sources_unchanged", "sections_assigned", "notes_created", "notes_written",
                      "notes_unchanged", "notes_kept_reviewed", "files_written", "files_removed", "passages", "wiki_chunks"):
                if st.get(k):
                    print(f"  {k.replace('_', ' ')}: {st[k]}")
            loaded = llm.loaded_models()
            path = save_run(cfg, "ingest", {"env": environment(cfg, llm), "paths": args.paths, "force": args.force, "reassign": args.reassign,
                                            "stats": st, "model_calls": out["calls"], "ollama_ps": loaded})
            print(dim(f"Saved: {cfg.rel(path)}"))
        elif args.command == "eval":
            from .evaluate import run_eval
            run_eval(cfg, cfg.root / args.tests, cfg.root / args.out)
        elif args.command == "status":
            cmd_status(cfg)
        elif args.command == "check":
            from .linkcheck import check_vault
            problems, st = check_vault(cfg)
            print(bold("Vault check") + f": {st.get('notes', 0)} notes ({st.get('reviewed', 0)} reviewed), "
                  f"{st.get('links', 0)} links ({st.get('source_links', 0)} to original sources), "
                  f"{st.get('raw_sources', 0)} files in raw/")
            for p in problems:
                print(red(f"  ✗ {p}"))
            print(green("  ✓ all links resolve to exactly one file; headings match filenames; every note has sources")
                  if not problems else yellow(f"  {len(problems)} problem(s)"))
            return 1 if problems else 0
        elif args.command == "rename":
            from .ingest import Ingestor
            llm = LocalGemma(cfg)
            try:
                llm.check()
            except LLMError:
                llm = None
            Ingestor(cfg, llm).rename(args.old, args.new, args.folder)
        elif args.command == "assign":
            from .ingest import Ingestor
            llm = LocalGemma(cfg)
            llm.check()
            Ingestor(cfg, llm).assign(args.source, args.section, args.note, args.folder)
        return 0
    except (ConfigError, LLMError, FileNotFoundError, ValueError, RuntimeError) as e:
        print(red(f"error: {e}"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())
