#!/usr/bin/env bash
# Short offline re-run of the two checks that the first offline demo skipped (argument-quoting bug in
# offline_demo.sh): search with the model server stopped, and ask's error message when it is down.
set -u
cd "$(dirname "$0")/.."
OUT=evidence/offline
LOG="$OUT/terminal-transcript-search-check.txt"
export NO_COLOR=1 PYTHONUNBUFFERED=1
net() { .venv/bin/python -c "from wiki_cli.runlog import internet_status; print(internet_status())"; }
step() { printf '\n================================================================\n[%s] $ %s\n================================================================\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }

: > "$LOG"
echo "Offline re-run of search / model-down checks. Started $(date '+%Y-%m-%d %H:%M:%S'); waiting for the internet to be disconnected..." | tee -a "$LOG"
for i in $(seq 1 360); do [ "$(net)" = "offline" ] && break; sleep 5; done
[ "$(net)" = "offline" ] || { echo "ABORTED: internet still reachable after 30 minutes." | tee -a "$LOG"; exit 1; }

step "proof that the internet is disconnected"
{ echo "internet_status(): $(net)"; curl -sS -m 5 -o /dev/null https://huggingface.co 2>&1; ipconfig getifaddr en0 2>&1 || echo "en0: no IP address (Wi-Fi off)"; } | tee -a "$LOG"

step "stop the local model server"
pkill -f "ollama serve"; sleep 3
{ pgrep -fl "ollama serve" || echo "ollama serve: not running"; curl -s -m 2 http://127.0.0.1:11434/api/version || echo "127.0.0.1:11434: connection refused"; } 2>&1 | tee -a "$LOG"

step './wiki search "linear chain architecture" -k 3'
./wiki search "linear chain architecture" -k 3 2>&1 | tee -a "$LOG"
cp "$(ls -t runs/*-search.json | head -1)" "$OUT/mode-checks/search-linear-chain-model-stopped.json"

step './wiki ask "How quickly can Tanium query all endpoints?"   (model server stopped: expect a clear error)'
./wiki ask "How quickly can Tanium query all endpoints?" 2>&1 | tee -a "$LOG"
echo "exit code: ${PIPESTATUS[0]}" | tee -a "$LOG"

step "restart the local model server"
nohup env OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 /opt/homebrew/opt/ollama/bin/ollama serve > "$OUT/ollama-serve-2.log" 2>&1 &
for i in $(seq 1 30); do curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
./wiki status 2>&1 | tee -a "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] CHECK COMPLETE — you can turn Wi-Fi back on." | tee -a "$LOG"
