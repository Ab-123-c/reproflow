# GitHub Issue input

`v0.1.3` lets `reproflow reproduce` accept either a local Markdown/text file or a GitHub Issue URL.

```bash
reproflow reproduce \
  --repo . \
  --issue https://github.com/OWNER/REPO/issues/123
```

## What is fetched

ReproFlow accepts only `https://github.com/<owner>/<repo>/issues/<number>` URLs. It constructs requests to `api.github.com` itself rather than following an arbitrary user-supplied API URL.

The default GitHub input contains:

- issue title and body
- state and labels
- author login
- up to 20 issue comments

Use `--github-max-comments 0` to load only the issue body, or choose a value up to 100.

## Authentication

Public issues can be fetched without authentication. For private repositories, or to avoid the lower unauthenticated GitHub API rate limit, set a token in the environment:

```bash
export GH_TOKEN="..."
# or
export GITHUB_TOKEN="..."
```

Do not put tokens in the Issue URL or bug-report file. ReproFlow uses the token only in the GitHub API request header and does not place it into the issue text passed to the planner.

## Trust boundary

GitHub issue bodies and comments are untrusted data. ReproFlow prefixes fetched text with an explicit untrusted-data marker, caps input size, and still requires Docker execution plus the deterministic Verifier before a reproduction can become `VERIFIED`.

The network request used to retrieve the Issue happens in the CLI process before reproduction. The reproduction container remains network-disabled under the existing sandbox policy.
