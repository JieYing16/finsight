#!/usr/bin/env python3
"""Apply the apply-review agent's response by writing updated file contents.

Parses ``=== FILE: <path> ===`` / ``=== END FILE ===`` blocks from the model
response and writes each one. Paths outside the repo, or inside ``.git``/
``.venv``, are refused.

Env vars:
    RESPONSE_FILE: path to the model response text.

Exit codes:
    0  one or more files written
    2  model returned NO_CHANGES, or no parseable blocks were found
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BLOCK = re.compile(
    r"=== FILE: (?P<path>.+?) ===\n(?P<body>.*?)\n=== END FILE ===",
    re.DOTALL,
)


def main() -> int:
    """Write files from the response; return an exit code (see module docs)."""
    response = Path(os.environ["RESPONSE_FILE"]).read_text(encoding="utf-8")
    if response.strip() == "NO_CHANGES":
        print("Model reported NO_CHANGES.")
        return 2

    repo = Path.cwd().resolve()
    written: list[str] = []
    for match in BLOCK.finditer(response):
        rel = match.group("path").strip()
        target = (repo / rel).resolve()
        if not str(target).startswith(str(repo) + os.sep):
            print(f"Refusing path outside repo: {rel}", file=sys.stderr)
            continue
        if {".git", ".venv"} & set(target.parts):
            print(f"Refusing protected path: {rel}", file=sys.stderr)
            continue

        body = match.group("body")
        if not body.endswith("\n"):
            body += "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        written.append(rel)

    if not written:
        print("No FILE blocks found in response.")
        return 2

    print("Wrote files:")
    for rel in written:
        print(f"  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
