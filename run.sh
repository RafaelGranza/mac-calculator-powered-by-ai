#!/usr/bin/env bash
# One command to get the dumb LLM calculator running:
#   installs Ollama (if missing), builds the tiny Gemma model, opens the calculator.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="mac-calculator-gemma"
BASE="gemma3:1b"
API="http://localhost:11434/api/tags"

say() { printf "\033[1;33m==>\033[0m %s\n" "$*"; }

# 1. Ollama
if ! command -v ollama >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    say "Installing Ollama with Homebrew..."
    brew install ollama
  else
    echo "Ollama is not installed. Get it from https://ollama.com/download and run ./run.sh again."
    exit 1
  fi
fi

# 2. Ollama server
if ! curl -s -m 2 "$API" >/dev/null; then
  say "Starting the Ollama server..."
  nohup ollama serve >/tmp/llm-calculator-ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    curl -s -m 1 "$API" >/dev/null && break
    sleep 1
  done
  curl -s -m 2 "$API" >/dev/null || { echo "Ollama server didn't start (see /tmp/llm-calculator-ollama.log)."; exit 1; }
fi

# 3. The dumb model (first run downloads ~800 MB)
if ! ollama list | awk '{print $1}' | grep -qx "$BASE"; then
  say "Downloading $BASE (~800 MB, only the first time)..."
  ollama pull "$BASE"
fi
if ! ollama list | awk '{print $1}' | grep -Eqx "$MODEL(:latest)?"; then
  say "Building $MODEL..."
  ollama create "$MODEL" -f Modelfile
fi

# 4. Python with Tkinter
PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "Python 3 is not installed. Get it from https://www.python.org/downloads/ and run ./run.sh again."
  exit 1
fi
if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
  VER="$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  if command -v brew >/dev/null 2>&1; then
    say "Installing Tkinter for Python $VER..."
    brew install "python-tk@$VER"
  else
    echo "Your Python has no Tkinter. Install the python.org build of Python and run ./run.sh again."
    exit 1
  fi
fi

say "Opening the calculator. Good luck with the math."
exec "$PY" calculator.py
