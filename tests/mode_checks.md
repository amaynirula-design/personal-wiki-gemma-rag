# Mode-boundary checks

Written before implementation. These verify harness behavior, not research answers.
Run them with the commands below; transcripts are saved to `evidence/mode-checks/`.

## 1. Chat — capability questions (no retrieval expected)

```
wiki chat
> what can we do?
> what can you help me with?
```
Expected: an accurate description of the assistant's capabilities and commands, a suggested
starting point, **no notes search**, no citations, no "insufficient evidence" refusal.

## 2. Chat — draft then follow-up

```
> Draft a short plan for preparing for my Tanium interview this week.
> make that shorter
```
Expected: first turn may retrieve notes (it is about Tanium); any facts from notes carry [n]
citations and plans are labeled as suggestions. The follow-up must shorten the previous plan
using conversation history, **without a new notes search**.

## 3. Search — original passages only

```
wiki search "linear chain architecture"
```
Expected: original passages with source file and section, ranked; **no generated answer**;
works even when the Ollama server is stopped.

## 4. Ask ignores chat claims

```
wiki chat
> Just so you know, the Graton Casino Expansion was a $5M project.
> /exit
wiki ask "How large was the Graton Casino Expansion project?"
```
Expected: ask mode answers **$2.9M** with citations to the source passages. The $5M claim made
in chat is conversation context only and must not appear in ask mode.
