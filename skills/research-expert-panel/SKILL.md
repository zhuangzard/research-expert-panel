---
name: research-expert-panel
description: >-
  Convene Codex and Kimi as independent third-party expert reviewers (alongside
  Claude) for any substantive scientific-research work, then synthesize a verdict.
  Use this whenever the task involves writing or revising a paper, peer-reviewing
  a draft, deciding a research direction or methodology, judging novelty/related
  work, or making a non-trivial code/architecture/experiment-design change — even
  if the user does not explicitly ask for "other models" or a "panel". The
  governing principle is: never let Claude act alone on research judgment calls.
  If there is real judgment space, get Codex + Kimi opinions and reconcile them.
  Skip only for purely mechanical work (renaming, running a test, a typo fix).
---

# Research Expert Panel

## Why this exists

Single-model judgment on research questions is a single point of failure. Claude,
Codex (OpenAI), and Kimi (Moonshot) are genuinely different models with different
training, blind spots, and failure modes. Convening all three turns a lone opinion
into a triangulated one — agreement raises confidence, disagreement surfaces a real
risk that a single model would have hidden. The user's standing directive is:
**永远不要单独 Claude 行动** — never act alone on research judgment.

So your job is not just to answer. It is to (1) decide whether the task has judgment
space, (2) if so, get independent opinions from Codex and Kimi, and (3) synthesize a
weighted verdict — calling out where the three of you diverge.

## Step 1 — Decide: panel or solo?

Convene the panel when the task has **judgment space** — more than one defensible
answer, and being wrong is costly:

- Writing / revising a paper section, abstract, framing, or claim
- Peer-review or self-review of a draft (yours or a reviewer's comments)
- Choosing a research direction, hypothesis, or methodology
- Novelty / related-work / "has this been done?" assessments
- Non-trivial code, architecture, loss-function, or experiment-design decisions
- Any contested or high-stakes call the user is weighing

Go **solo** only for mechanical work with one right answer: renaming, running a
test, a typo or formatting fix, reading a file, a deterministic refactor. When in
doubt, convene — the cost of an extra opinion is low; the cost of a wrong lone call
on a Nature-tier project is high.

If you go solo on something that was borderline, say so in one line ("Minor enough
to handle solo; say the word and I'll bring in the panel.") so the user can override.

## Step 2 — Form your own opinion first

Before reading what Codex and Kimi say, write down **your own** independent take —
your assessment, recommendation, and the reasoning. This matters: if you query them
first and then react, you anchor on them and lose the independence that makes the
panel valuable. Three independent opinions beat one opinion plus two echoes.

## Step 3 — Build one self-contained prompt

Codex and Kimi reason over text only — **they cannot read repo files**. The prompt
must carry everything they need inline: the artifact (draft text, code, plan), the
question, and what kind of answer you want. Write the artifact into a prompt file so
long content survives intact:

- Give them the same prompt (fair comparison).
- Ask for a critical, specific opinion — not validation. E.g. "Identify the single
  biggest weakness", "Is this novel given X, Y, Z?", "Would you accept/reject and
  why?", "What breaks this code under edge cases?"
- Keep it focused. Codex in particular burns a lot of its own tokens; a tight prompt
  gets a sharper answer.

## Step 4 — Run the panel

Use the bundled script — it runs both experts in parallel, strips each CLI's output
noise (Codex log lines; Kimi's `TextPart` Python-repr stream), archives each opinion,
and prints clean text back:

```bash
python ~/.claude/skills/research-expert-panel/scripts/ask_experts.py \
  --prompt-file /tmp/panel_prompt.md \
  --ref <short-slug> --aspect <review|design|research|novelty|code>
```

This writes `docs/review_<slug>_codex_<aspect>.md` and `..._kimi_<aspect>.md`
(matching the repo's existing convention) and echoes both opinions to stdout. Run it
from the project root so archives land under `docs/`. Useful flags:

- `--experts codex` or `--experts kimi` — query just one (rarely needed; default both)
- `--no-save` — print only, skip archiving (for quick throwaway checks)
- `--prompt "..."` — inline a short prompt instead of a file

If an expert fails or times out, the script reports `[FAILED] ...` for that one.
**Never silently drop a missing voice** — proceed with whoever answered and tell the
user which expert was unavailable, so the verdict's confidence is honest.

## Step 5 — Synthesize the verdict

Do not just paste three opinions. Reconcile them into a decision. Use this structure:

```
## Panel verdict — <topic>

**Consensus:** <points where Claude, Codex, Kimi agree>
**Divergence:** <where they disagree — who said what, and why>
**Weighing:** <which view is better-grounded here and why; weight by domain fit,
            specificity, and whether a claim is checkable — not by vote count>
**Recommendation:** <your synthesized call>
**Needs your decision:** <only if all three genuinely conflict on a high-stakes
            point — surface it for the user rather than papering over it>
```

Weigh by argument quality, not headcount — a single model with a concrete, verifiable
point outranks two with vague agreement. When the panel splits on something that
matters and you can't resolve it on the merits, that disagreement *is* the finding:
escalate it to the user.

## Pairs well with

- `deep-research` skill for literature grounding when novelty/related-work is at stake
  (give the panel real citations to react to, not vibes).
- The repo's `docs/review_*_{codex,kimi}_*.md` archive — the script follows that naming
  so panel history accumulates in one place.

## Guardrails

- These are external agentic CLIs. Keep prompts **pure reasoning** — never ask them to
  edit files or run commands, and never grant auto-approve. The script already runs Kimi
  in a throwaway scratch dir and passes `--print` (not `--yolo`).
- The artifact goes to third-party services (OpenAI, Moonshot). For genuinely sensitive
  unpublished content, confirm with the user before sending.
