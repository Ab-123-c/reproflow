# ReproFlow v0.1.0-alpha.3 — GitHub Issue Ingestion

The third alpha connects ReproFlow's bounded reproduction loop to real maintainer input: a GitHub Issue URL.

## Highlights

- `reproflow reproduce --issue` now accepts either a local text/Markdown file or a GitHub Issue URL.
- Public GitHub Issues work without a token; `GH_TOKEN` or `GITHUB_TOKEN` can be used for private access and higher API limits.
- Issue title, body, labels, author, and up to 20 comments are converted into bounded untrusted planner input.
- `--github-max-comments` controls comment ingestion from 0 to 100.
- Only `https://github.com/<owner>/<repo>/issues/<number>` is accepted as a remote source; ReproFlow constructs `api.github.com` requests itself.
- Pull requests are rejected from this path even though GitHub's Issues API can represent them as issue-shaped objects.
- Remote issue runs get stable fallback evidence directories such as `.repro/github-owner-repo-123/`.
- New size limits reduce the risk of oversized issue bodies or comments overwhelming the planner context.

## Example

```bash
pip install -e ".[ai]"
export OPENAI_API_KEY="..."

reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --max-attempts 5
```

The GitHub network fetch happens before sandbox execution. Issue text and comments remain untrusted data; the model still cannot declare success. Docker execution and the deterministic Verifier remain the proof boundary.
