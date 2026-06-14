# PR Review Agent

FinSight runs an automated review agent on every pull request. It builds the PR
diff, asks an LLM to review it against a rubric, and posts a structured review
report as a single (sticky) comment on the PR. Focus areas: **code quality &
standards** and **privacy / data safety**, per [`CLAUDE.md`](../CLAUDE.md).

It is powered by [**GitHub Models**](https://github.com/marketplace/models),
which is **free** for personal and open-source accounts — no paid API key and
no extra account. The workflow authenticates with the built-in `GITHUB_TOKEN`.

## Files

- `.github/workflows/pr-review.yml` — the GitHub Actions workflow.
- `.github/pr-review-rubric.md` — the system prompt: what the agent checks and
  the exact report format it produces.

## Setup

Nothing to configure — there is **no secret to add**. The workflow uses the
runner's `GITHUB_TOKEN` (granted `models: read` in the workflow) and triggers
automatically on every PR (opened, updated, reopened, or marked ready for
review). Drafts are skipped.

> If GitHub Models isn't already enabled for your account/org, enable it once at
> <https://github.com/settings/features> (or your org's settings). It's free.

## How it works

1. Checks out the PR and computes the diff against the base branch (excluding
   `.venv/`, lockfiles, and binaries).
2. Caps the diff (~45k chars) to fit the free-tier context window.
3. Calls `actions/ai-inference@v1` (model `openai/gpt-4o-mini`) with the rubric
   as the system prompt.
4. Posts/updates one sticky comment via `actions/github-script` (matched by a
   hidden `<!-- finsight-pr-review -->` marker).

The agent **only reports** — it never approves, merges, or pushes commits.
Merging to `main` still requires explicit owner confirmation (see `CLAUDE.md`).

## Tuning

- **Model:** change `model:` in the workflow to any model in the
  [GitHub Models catalog](https://github.com/marketplace?type=models)
  (e.g. `openai/gpt-4o` for stronger reviews).
- **Large PRs:** raise the diff cap (`MAX`) or `max-completion-tokens`, but mind
  the free-tier rate/context limits.
- **Cost:** free tier is rate-limited per minute/day. If you hit limits on busy
  days, gate the job behind a `pr-review` label instead of every PR.
