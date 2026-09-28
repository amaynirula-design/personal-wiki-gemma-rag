# Offline mode checks — assessment

Run on 2026-09-28 with Wi-Fi off (`en0` had no IP address; `huggingface.co` unresolvable; the harness's
`internet_status()` reported `offline` before, during and after). Model: `gemma4-e2b-qat` (Gemma 4 E2B-it
QAT Q4_0) via Ollama 0.34.4 on 127.0.0.1, restarted from local weights after the network was cut.
Checks defined in advance in [`tests/mode_checks.md`](../../../tests/mode_checks.md).

| Check | Evidence | Result |
|---|---|---|
| Chat: "what can we do?" | [chat-transcript.txt](chat-transcript.txt) | ✅ No notes lookup (`rule: question about the assistant's capabilities`); accurate capabilities (draft answers, mock interviews, prep plans, look up notes); asks what to work on. No citations, no refusal. |
| Chat: "what can you help me with?" | same | ✅ No lookup; lists capabilities and the three prep documents it can search. |
| Chat: "Draft a short plan for preparing for my Tanium interview this week." | same | ✅ Router chose a lookup (`query "Tanium interview prep plan"`, 4 passages). Plan cites the Otis role [1] and the Client Payment Negotiation story [2]; both citations point at passages that say what is claimed. Framed as a suggested plan. |
| Chat: "make that shorter" | same | ✅ No new search (`rule: follow-up edit … reusing 4 passage(s) from the previous turn`); a shorter version of the same plan with the same valid citations. |
| Chat: "Just so you know, the Graton Casino Expansion was a $5M project." | same | ✅ Harness flagged `$5M` as not found in the notes; Scout replied that the notes say **$2.9M** [2] and explained how to correct the source. It did not accept the claim. |
| Ask after the chat claim: "How large was the Graton Casino Expansion project?" | [ask-after-chat-claim.txt](ask-after-chat-claim.txt) | ✅ "$2.9M project [1][2][3]" citing the Graton story in all three prep documents; citation check PASS. The chat claim never reaches ask mode (separate process; ask loads no history and no persona). |
| Search with the model server **stopped**: `wiki search "linear chain architecture" -k 3` | [../terminal-transcript-search-check.txt](../terminal-transcript-search-check.txt) · [search-linear-chain-model-stopped.json](search-linear-chain-model-stopped.json) | ✅ Ollama not running (port 11434 refused). Returned original passages with file, section, paragraphs, BM25 score and matched terms; #1 is *Tanium Interview Prep.docx › What does Tanium do? (¶24-26)*. No generated answer. |
| Ask with the model server stopped | same transcript | ✅ Clear error: "Cannot reach the local Ollama server at http://127.0.0.1:11434. Start it in another terminal with: ollama serve (search mode works without the model)", exit code 1. |

**Note on the run.** The main offline script (`scripts/offline_demo.sh`) had an argument-quoting bug that
split `wiki search "linear chain architecture"` into separate words, so the two search/model-down checks
failed with a usage error in [`../terminal-transcript.txt`](../terminal-transcript.txt). I fixed the script
and re-ran just those two checks offline with `scripts/offline_search_check.sh`; the failed attempt is left
in the first transcript. Between the two runs I also changed `wiki search` to default to original source
passages (`--scope sources`); before, it mixed in generated wiki notes.
