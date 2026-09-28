"""Run the fixed ask-mode test set and write one evidence card per test."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .catalog import slug
from .config import Config
from .modes import bold, dim, run_ask
from .runlog import environment
from .llm import LocalGemma


def _card(test: dict, res, env: dict) -> str:
    exp_sources = "\n".join(f"- {s}" for s in test.get("expected_sources", [])) or "- (none — unanswerable)"
    passages = []
    for i, h in enumerate(res.hits, 1):
        mark = " ← cited" if i in res.report.cited else ""
        text = h.doc.text.replace("\n", "\n> ")
        passages.append(f"**[{i}] {h.doc.location}**{mark}  \n`{h.doc.path}` · BM25 score {h.score} · "
                        f"matched: {', '.join(h.matched)}\n\n> {text}\n")
    stats = res.stats
    quotes = "\n".join(f"- [{q['passage']}] \"{q['quote']}\"" for q in res.quotes) or "- (none)"
    rejected = "\n".join(f"- [{q['passage']}] \"{q['quote']}\"" for q in res.rejected) or "- (none)"
    conflicts = "\n".join(f"- {c}" for c in stats.get("conflicts", [])) or "- (none detected)"
    calls = " · ".join(
        f"{k}: {stats[k]['wall_s']} s, {stats[k].get('prompt_tokens')} prompt → {stats[k].get('output_tokens')} output tokens"
        for k in ("extract", "answer") if k in stats) or "no model call"
    return f"""# Test {test['id']}: {test['name']}

| | |
|---|---|
| Mode | **ask** (standalone; no chat history, no persona) |
| Execution | **{env['execution']}** · internet: **{env['internet']}** |
| Model | `{env['model']}` = {env['model_identifier']} · {env['quantization']} |
| Runtime | {env.get('runtime')} |
| Run at | {env['timestamp']} on {env['platform']} |
| Test type | {test['kind']} |
| Saved run | `{res.saved}` |

## Question

> {test['question']}

## Expected (written before the run)

- Behavior: **{test['expected_behavior']}**
- Expected answer: {test['expected_answer']}
- Expected sources:
{exp_sources}
- Expected passage: {test['expected_passage'].strip()}

## Step 1: retrieved passages (top {len(res.hits)} by BM25, in the order given to Gemma)

{chr(10).join(passages) if passages else '_No passages retrieved._'}

## Step 2: evidence quotes extracted by Gemma and verified by the harness

Verified (found word-for-word in the cited passage):
{quotes}

Rejected (not found in the passage the model named):
{rejected}

Number conflicts between sources detected by the harness:
{conflicts}

## Actual Gemma answer

```text
{res.answer}
```

Timing: retrieval {stats.get('retrieval_ms')} ms · {calls} · total model time {stats.get('wall_s')} s

## Automatic citation check

{res.report.summary()}

## Assessment

_Pending human review: does retrieval contain the expected passage, and does each claim follow from the cited passage?_
"""


def run_eval(cfg: Config, tests_path: Path, out_dir: Path) -> list[dict]:
    tests = yaml.safe_load(tests_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    env = environment(cfg, LocalGemma(cfg))
    summary = []
    for t in tests:
        print(bold(f"\n=== Test {t['id']}: {t['name']} ==="))
        res = run_ask(cfg, t["question"], echo=True, save=True)
        expected_files = {re.split(r" › ", s)[0] for s in t.get("expected_sources", [])}
        retrieved_files = {h.doc.location.split(" › ")[0] for h in res.hits}
        row = {
            "id": t["id"], "name": t["name"], "question": t["question"],
            "expected_behavior": t["expected_behavior"],
            "actual_behavior": "insufficient_evidence" if res.report.insufficient else "answer",
            "expected_sources_retrieved": sorted(expected_files & retrieved_files),
            "expected_sources_missing": sorted(expected_files - retrieved_files),
            "citation_check": res.report.as_dict(), "answer": res.answer, "run": res.saved,
        }
        summary.append(row)
        card = out_dir / f"Test {t['id']} - {slug(t['name'])}.md"
        card.write_text(_card(t, res, env), encoding="utf-8")
        print(dim(f"Evidence card: {cfg.rel(card)}"))
    (out_dir / "summary.json").write_text(json.dumps({"env": env, "results": summary}, indent=2), encoding="utf-8")
    print(bold("\nSummary"))
    for r in summary:
        beh = "✓" if r["expected_behavior"] == r["actual_behavior"] else "✗"
        print(f"  Test {r['id']}: behavior {beh} ({r['actual_behavior']}) · "
              f"expected sources missing: {r['expected_sources_missing'] or 'none'} · {r['citation_check']['summary']}")
    return summary
