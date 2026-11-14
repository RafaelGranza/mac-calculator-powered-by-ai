# Mac Calculator - Powered by AI 🧮🤡

A faithful copy of the macOS Calculator with one small difference:

**the math is done by a tiny local LLM.**

<img width="640" height="360" alt="calculator-poweredbyAI-ezgif com-optimize" src="https://github.com/user-attachments/assets/087f2d76-8ed3-445c-8038-8bf92919eae5" />

It is very confident. It is often wrong.

```
12 × 3 + 4          = 16
banana + 2? = 2 banana
```

You can also type **any text** on the keyboard and press `=`. The calculator will answer anyway.

## Run it

macOS, one command:

```bash
git clone https://github.com/RafaelGranza/mac-calculator-powered-by-ai.git && cd mac-calculator-powered-by-ai && ./run.sh
```

`run.sh` takes care of everything:

1. Installs [Ollama](https://ollama.com) with Homebrew if you don't have it.
2. Starts the Ollama server.
3. Downloads `gemma3:1b` (~800 MB, only the first time) and builds the `mac-calculator-gemma` model from the [`Modelfile`](Modelfile).
4. Opens the calculator.

After the first run, `./run.sh` opens it in a couple of seconds.

## Using it

| | |
|---|---|
| Switch Basic / Scientific | calculator key (bottom left), **View** menu, or `⌘1` / `⌘2` |
| Calculate | `=` or `Enter` |
| Type anything | just type: `what is love?` then `Enter` |
| Delete / clear | `⌫` key or `Backspace`; `Esc` clears everything |
| Copy / paste | `⌘C` / `⌘V` |

## Make it smarter (or dumber)

At the top of [`calculator.py`](calculator.py):

- `OLLAMA_MODEL`: any Ollama model you have, e.g. `qwen3-vl:8b` (smarter, much heavier and slower).
- `THINK = True`: lets thinking models reason before answering.
- `TEMPERATURE`: higher means more creative and more wrong.
- `SYSTEM_PROMPT` and `EXAMPLES`: how the model is told to behave.

## Requirements

- macOS (uses the Mac menu bar and `⌘` shortcuts)
- Python 3 with Tkinter (installed by `run.sh` via Homebrew if missing)
- ~1.5 GB free RAM for the model

The model is Google's Gemma, used under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).

## License

[MIT](LICENSE). The Gemma model itself is covered by the Gemma Terms of Use above.
