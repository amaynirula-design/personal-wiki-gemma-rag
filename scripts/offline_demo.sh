#!/usr/bin/env bash
# Offline demonstration for the assignment. Start it while online; it waits until the internet is
# unreachable, then restarts the local model server, runs every required step and records a
# timestamped transcript in evidence/offline/. Turn Wi-Fi back on when it prints "DEMO COMPLETE".
#
#   nohup scripts/offline_demo.sh > /dev/null 2>&1 &
#   tail -f evidence/offline/terminal-transcript.txt      # watch progress
set -u
cd "$(dirname "$0")/.."
OUT=evidence/offline
mkdir -p "$OUT/ask-tests" "$OUT/mode-checks"
LOG="$OUT/terminal-transcript.txt"
export NO_COLOR=1 PYTHONUNBUFFERED=1
PY=.venv/bin/python

log() { printf '%s\n' "$*" | tee -a "$LOG"; }
step() { log ""; log "================================================================"; log "[$(date '+%Y-%m-%d %H:%M:%S')] \$ $*"; log "================================================================"; }
run() { step "$(printf '%q ' "$@")"; "$@" 2>&1 | tee -a "$LOG"; }   # arguments passed through unchanged
net() { $PY -c "from wiki_cli.runlog import internet_status; print(internet_status())"; }

: > "$LOG"
log "Offline demonstration — Personal Interview-Prep Wiki (local Gemma + RAG)"
log "Started $(date '+%Y-%m-%d %H:%M:%S'). Waiting for the internet to be disconnected..."
for i in $(seq 1 360); do          # wait up to 30 minutes
  [ "$(net)" = "offline" ] && break
  sleep 5
done
if [ "$(net)" != "offline" ]; then log "ABORTED: internet still reachable after 30 minutes."; exit 1; fi

step "proof that the internet is disconnected"
log "internet_status(): $(net)   (TCP to 1.1.1.1:443 and 8.8.8.8:53 both failed)"
( curl -sS -m 5 -o /dev/null https://huggingface.co 2>&1 || true ) | tee -a "$LOG"
( ping -c 1 -t 3 8.8.8.8 2>&1 | tail -2 || true ) | tee -a "$LOG"
( ipconfig getifaddr en0 2>&1 || echo "en0: no IP address (Wi-Fi off)" ) | tee -a "$LOG"

step "device"
( system_profiler SPHardwareDataType | grep -E "Model Name|Chip|Total Number of Cores|Memory"; sw_vers -productVersion ) 2>&1 | tee -a "$LOG"

step "stop the model server, then show that search works with no model running"
pkill -f "ollama serve" ; sleep 3
( pgrep -fl "ollama serve" || echo "ollama serve: not running" ) | tee -a "$LOG"
run ./wiki search "linear chain architecture" -k 3
cp "$(ls -t runs/*-search.json | head -1)" "$OUT/mode-checks/search-linear-chain.json"
run ./wiki ask "How quickly can Tanium query all endpoints?"   # expected: clear error, model unavailable

step "restart the local model server (weights load from local disk)"
nohup env OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 /opt/homebrew/opt/ollama/bin/ollama serve > "$OUT/ollama-serve.log" 2>&1 &
for i in $(seq 1 30); do curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
run ./wiki status
run ./wiki --help

run /usr/bin/time -l ./wiki ingest "vault/raw/Tiktok Interview Prep.docx" --force
run ./wiki check
run ollama ps
step "model process physical memory footprint"
( footprint -p "$(pgrep -f llama-server | head -1)" 2>&1 | grep -E "phys_footprint" ) | tee -a "$LOG"

run ./wiki eval tests/ask_tests.yaml --out "$OUT/ask-tests"

step "mode checks: chat (capabilities, draft + follow-up, false claim) — script tests/chat_script.txt"
./wiki chat < tests/chat_script.txt 2>&1 | tee -a "$LOG" | tee "$OUT/mode-checks/chat-transcript.txt" > /dev/null
cp "$(ls -t runs/*-chat.json | head -1)" "$OUT/mode-checks/chat-run.json"

step "mode check: ask ignores the chat claim"
./wiki ask "How large was the Graton Casino Expansion project?" 2>&1 | tee -a "$LOG" | tee "$OUT/mode-checks/ask-after-chat-claim.txt" > /dev/null
cp "$(ls -t runs/*-ask.json | head -1)" "$OUT/mode-checks/ask-after-chat-claim.json"

step "peak memory during the run"
( footprint -p "$(pgrep -f llama-server | head -1)" 2>&1 | grep -E "phys_footprint"; memory_pressure | tail -1 ) | tee -a "$LOG"
log ""
log "internet_status() at end: $(net)"
log "[$(date '+%Y-%m-%d %H:%M:%S')] DEMO COMPLETE — you can turn Wi-Fi back on."
