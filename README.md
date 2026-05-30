# research-expert-panel

A [Claude Code](https://claude.com/claude-code) skill that stops Claude from making research
judgment calls alone. Whenever you do substantive scientific work — writing or reviewing a
paper, choosing a research direction, judging novelty, or making a non-trivial code/architecture
decision — this skill automatically convenes **Codex** (OpenAI) and **Kimi** (Moonshot) as
independent third-party reviewers, then synthesizes a triangulated verdict.

> Governing principle: **never let one model decide a research judgment call alone.**
> Three genuinely different models with different blind spots beat one confident opinion.
> Agreement raises confidence; disagreement surfaces a real risk a single model would hide.

## What it does

When a task has real judgment space, the skill:

1. Has Claude form its **own** opinion first (so it doesn't just echo the others).
2. Sends the same self-contained prompt to **Codex** and **Kimi** in parallel.
3. Archives each opinion to `docs/review_<ref>_<expert>_<aspect>.md`.
4. Synthesizes a verdict: **consensus → divergence → weighing → recommendation**, and
   escalates to you whenever all three genuinely conflict on a high-stakes point.

It stays out of the way for purely mechanical work (renames, running a test, typo fixes).

## Requirements

Two external CLIs must be installed and authenticated on your PATH:

| Expert | CLI | Install |
|--------|-----|---------|
| Codex  | `codex` | OpenAI Codex CLI |
| Kimi   | `kimi`  | Moonshot Kimi CLI |

The skill calls them in pure read-only reasoning mode (`codex exec`, `kimi --print`). It never
grants them write access or auto-approve, and runs Kimi in a throwaway scratch dir.

## Install

### Option A — copy the skill (simplest)

```bash
git clone https://github.com/zhuangzard/research-expert-panel.git
cp -r research-expert-panel/skills/research-expert-panel ~/.claude/skills/
```

The skill is now available in every Claude Code session. It triggers on its own when you do
research work; you can also nudge it ("get the panel's opinion on this draft").

### Option B — as a plugin

This repo is a valid Claude Code plugin (`.claude-plugin/plugin.json`). Add it through your
plugin marketplace flow and enable `research-expert-panel`.

## The helper script

`skills/research-expert-panel/scripts/ask_experts.py` does the heavy lifting — runs both experts
in parallel, strips each CLI's output noise (Codex log lines; Kimi's verbose `TextPart` repr
stream), and archives the clean opinions. You can also run it directly:

```bash
python ask_experts.py --prompt-file PROMPT.md --ref nozzle_v3 --aspect novelty
python ask_experts.py --prompt "short question" --experts codex --no-save
```

| Flag | Meaning |
|------|---------|
| `--prompt-file` / `--prompt` / stdin | the full, self-contained prompt (experts can't read your files) |
| `--experts codex,kimi` | which experts to query (default both) |
| `--ref` / `--aspect` | name the archive `docs/review_<ref>_<expert>_<aspect>.md` |
| `--no-save` | print only, don't archive |

If an expert is missing or fails, the script reports it instead of silently dropping the voice —
so the verdict's confidence stays honest.

## Why Codex + Kimi

They're trained differently from Claude and from each other, so their failure modes don't
correlate. That's the whole point: a real second and third opinion, not a rubber stamp.

## License

MIT
