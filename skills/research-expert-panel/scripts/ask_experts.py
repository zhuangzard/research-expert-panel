#!/usr/bin/env python3
"""
ask_experts.py — query Codex and Kimi as independent third-party reviewers.

Both are external agentic CLIs reasoning over text (they do NOT read your repo
files), so the full artifact must be inlined in the prompt. This script runs the
requested experts in parallel, cleans up each CLI's noisy output, optionally
archives each opinion to docs/review_<ref>_<expert>_<aspect>.md, and prints the
clean text back to stdout so Claude can synthesize a verdict.

Usage:
    python ask_experts.py --prompt-file PROMPT.md --ref nozzle_v3 --aspect novelty
    python ask_experts.py --prompt "short question" --experts codex
    cat PROMPT.md | python ask_experts.py --ref draft_intro --aspect review

Design notes baked in from prior verification (2026-05-30):
  - Codex:  `codex exec --skip-git-repo-check "<PROMPT>"` -> clean text + minor
            log noise ("hook: Stop", a token count). We strip those lines.
  - Kimi:   `kimi --print -p "<PROMPT>"` run in a scratch dir -> the assistant
            text lives in `TextPart(type='text', text='...')` fragments inside a
            verbose Python-repr stream. We extract and decode those fragments.
            Never use `--yolo` (permission-bypass, classifier-blocked).
"""
import argparse
import ast
import concurrent.futures
import os
import re
import subprocess
import sys
import tempfile


def run_codex(prompt: str) -> tuple[str, str]:
    """Return (clean_text, error). error is '' on success."""
    try:
        p = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", prompt],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "", "codex CLI not found on PATH"
    out = p.stdout or ""
    noise = re.compile(r"^(hook:.*|tokens used|[\d,]+|-{3,}.*)$")
    lines = [ln for ln in out.splitlines() if not noise.match(ln.strip())]
    text = "\n".join(lines).strip()
    if not text and p.returncode != 0:
        return "", f"codex exited {p.returncode}: {(p.stderr or '').strip()[:400]}"
    return text or out.strip(), ""


def _decode_kimi_textparts(raw: str) -> str:
    """Extract every TextPart(...text=<py-string-literal>) by balanced scan.

    Kimi's repr stream is pretty-printed, so the marker may span newlines, e.g.
    `TextPart(\n    type='text',\n    text='...')`. The regex tolerates that and,
    by pinning type='text', skips ThinkPart (type='think') fragments.
    """
    marker = re.compile(r"TextPart\(\s*type='text',\s*text=")
    pieces, i = [], 0
    while True:
        m = marker.search(raw, i)
        if m is None:
            break
        k = m.end()
        if k >= len(raw) or raw[k] not in "'\"":
            i = k
            continue
        quote, buf, k = raw[k], [], k + 1
        while k < len(raw):
            c = raw[k]
            if c == "\\":          # keep escape sequence intact for literal_eval
                buf.append(raw[k:k + 2])
                k += 2
                continue
            if c == quote:
                break
            buf.append(c)
            k += 1
        body = "".join(buf)
        try:
            pieces.append(ast.literal_eval(quote + body + quote))
        except Exception:
            pieces.append(body)
        i = k + 1
    return "".join(pieces).strip()


def run_kimi(prompt: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="kimi_scratch_") as scratch:
        try:
            p = subprocess.run(
                ["kimi", "--print", "-p", prompt],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                cwd=scratch,
            )
        except FileNotFoundError:
            return "", "kimi CLI not found on PATH"
    out = p.stdout or ""
    text = _decode_kimi_textparts(out)
    if not text and p.returncode != 0:
        return "", f"kimi exited {p.returncode}: {(p.stderr or '').strip()[:400]}"
    return text or out.strip(), ""


RUNNERS = {"codex": run_codex, "kimi": run_kimi}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--prompt", help="inline prompt text")
    src.add_argument("--prompt-file", help="file containing the full prompt")
    ap.add_argument("--experts", default="codex,kimi",
                    help="comma-separated subset of: codex,kimi (default both)")
    ap.add_argument("--ref", help="short slug for the artifact, e.g. nozzle_v3")
    ap.add_argument("--aspect", default="review",
                    help="review|design|research|novelty|code (used in filename)")
    ap.add_argument("--out-dir", default="docs",
                    help="where review_*.md archives go (default: docs)")
    ap.add_argument("--no-save", action="store_true",
                    help="print only, do not archive to files")
    args = ap.parse_args()

    if args.prompt is not None:
        prompt = args.prompt
    elif args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("ERROR: empty prompt", file=sys.stderr)
        return 2

    experts = [e.strip() for e in args.experts.split(",") if e.strip() in RUNNERS]
    if not experts:
        print("ERROR: no valid experts (use codex,kimi)", file=sys.stderr)
        return 2

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(experts)) as ex:
        futures = {ex.submit(RUNNERS[name], prompt): name for name in experts}
        results = {futures[f]: f.result() for f in concurrent.futures.as_completed(futures)}

    saved = []
    if not args.no_save and args.ref:
        os.makedirs(args.out_dir, exist_ok=True)
    for name in experts:
        text, err = results[name]
        print(f"\n===== {name.upper()} =====")
        if err:
            print(f"[FAILED] {err}")
            continue
        print(text)
        if not args.no_save and args.ref:
            path = os.path.join(args.out_dir, f"review_{args.ref}_{name}_{args.aspect}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {name} review — {args.ref} ({args.aspect})\n\n")
                f.write("> Independent third-party opinion. Prompt was self-contained.\n\n")
                f.write(text + "\n")
            saved.append(path)

    if saved:
        print("\n===== ARCHIVED =====")
        for p in saved:
            print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
