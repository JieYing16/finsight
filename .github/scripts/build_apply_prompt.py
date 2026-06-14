#!/usr/bin/env python3
"""Build the prompt for the apply-review agent.

Reads the PR review recommendations and the full contents of the files changed
in the PR, then writes a single prompt file instructing the model to return
complete updated file contents that address those recommendations.

Env vars:
    RECS_FILE:    path to the review recommendations (default: recs.md)
    CHANGED_FILE: path to a newline list of changed files (default: changed.txt)
    PROMPT_FILE:  output prompt path (default: prompt.txt)
"""

from __future__ import annotations

import os
from pathlib import Path

# Character budget for included file contents — keeps within the GitHub Models
# free-tier context window.
MAX_TOTAL = 60_000


def _read(path: Path) -> str:
    """Return file text, or "" if it is missing/unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def main() -> None:
    """Assemble and write the prompt file."""
    recs = _read(Path(os.environ.get("RECS_FILE", "recs.md")))
    changed_file = Path(os.environ.get("CHANGED_FILE", "changed.txt"))
    out = Path(os.environ.get("PROMPT_FILE", "prompt.txt"))

    files = [ln.strip() for ln in _read(changed_file).splitlines() if ln.strip()]

    blocks: list[str] = []
    included: list[str] = []
    budget = MAX_TOTAL
    for rel in files:
        path = Path(rel)
        if not path.is_file():
            continue
        content = _read(path)
        if not content or len(content) > budget:
            continue  # skip empty/binary or oversized files to stay in budget
        budget -= len(content)
        included.append(rel)
        blocks.append(f"=== FILE: {rel} ===\n{content}\n=== END FILE ===")

    prompt = f"""You are the FinSight apply-review agent. Apply the pull request \
review recommendations below to the project's code.

Rules:
- Change ONLY what is needed to address the recommendations and clear blocking
  issues. Do not refactor or reformat unrelated code.
- Preserve required disclaimers, type hints, and Google-style docstrings.
- Never add real personal financial data, PII, secrets, or API keys.
- Keep lines <= 88 characters and Ruff-clean.

Output format (STRICT):
- For each file you change, output a block exactly like:
  === FILE: relative/path.py ===
  <the COMPLETE new contents of the file>
  === END FILE ===
- Output ONLY the files you change. Do not include unchanged files.
- Do NOT wrap blocks in Markdown code fences. No commentary outside the blocks.
- If no code change is warranted, output exactly: NO_CHANGES

## Review recommendations
{recs.strip() or "(no review comment found; infer fixes from the code and CLAUDE.md)"}

## Current contents of files changed in this PR
{chr(10).join(blocks) if blocks else "(no readable changed files)"}
"""

    out.write_text(prompt, encoding="utf-8")
    print(f"Included {len(included)} file(s): {included}")


if __name__ == "__main__":
    main()
