from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from reproflow.issue import source
from reproflow.issue.source import IssueSourceError, load_issue_source, parse_github_issue_url


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _response(payload):
    return FakeResponse(json.dumps(payload).encode("utf-8"))


def test_parse_github_issue_url_accepts_issue_and_strips_query_fragment():
    ref = parse_github_issue_url("https://github.com/Ab-123-c/reproflow/issues/42?x=1#top")
    assert ref is not None
    assert ref.owner == "Ab-123-c"
    assert ref.repo == "reproflow"
    assert ref.number == 42
    assert ref.html_url == "https://github.com/Ab-123-c/reproflow/issues/42"


@pytest.mark.parametrize(
    "value",
    [
        "http://github.com/owner/repo/issues/1",
        "https://example.com/owner/repo/issues/1",
        "https://github.com/owner/repo/pull/1",
        "https://github.com/owner/repo/issues/not-a-number",
        "https://github.com/owner/repo/issues/0",
    ],
)
def test_parse_github_issue_url_rejects_unsupported_urls(value):
    assert parse_github_issue_url(value) is None


def test_load_local_issue(tmp_path: Path):
    path = tmp_path / "issue.md"
    path.write_text("Unicode input crashes", encoding="utf-8")
    loaded = load_issue_source(str(path))
    assert loaded.source == "local"
    assert loaded.slug == "issue"
    assert loaded.text == "Unicode input crashes"


def test_load_unsupported_url_is_not_treated_as_a_file():
    with pytest.raises(IssueSourceError, match="Unsupported issue URL"):
        load_issue_source("https://example.com/issues/1")


def test_fetch_github_issue_loads_bounded_comments_and_auth_header(monkeypatch):
    calls = []
    responses = iter(
        [
            _response(
                {
                    "title": "Unicode parser crash",
                    "body": "Calling parse('你') raises UnicodeEncodeError.",
                    "state": "open",
                    "user": {"login": "reporter"},
                    "labels": [{"name": "bug"}, {"name": "needs-repro"}],
                    "comments": 2,
                }
            ),
            _response(
                [
                    {
                        "user": {"login": "maintainer"},
                        "created_at": "2026-08-19T00:00:00Z",
                        "body": "Seen on Python 3.12.",
                    },
                    {
                        "user": {"login": "reporter"},
                        "created_at": "2026-08-19T01:00:00Z",
                        "body": "Minimal input appears to be 你.",
                    },
                ]
            ),
        ]
    )

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return next(responses)

    monkeypatch.setattr(source, "urlopen", fake_urlopen)
    loaded = load_issue_source(
        "https://github.com/Ab-123-c/reproflow/issues/12",
        token="top-secret",
        max_comments=2,
    )

    assert loaded.source == "github"
    assert loaded.slug == "github-Ab-123-c-reproflow-12"
    assert loaded.display_name == "Ab-123-c/reproflow#12"
    assert "Unicode parser crash" in loaded.text
    assert "Seen on Python 3.12." in loaded.text
    assert "needs-repro" in loaded.text
    assert "top-secret" not in loaded.text
    assert len(calls) == 2
    assert calls[0][0].get_header("Authorization") == "Bearer top-secret"
    assert calls[0][0].get_header("X-github-api-version") == "2026-03-10"
    assert "per_page=2" in calls[1][0].full_url


def test_fetch_github_issue_rejects_pull_request_payload(monkeypatch):
    monkeypatch.setattr(
        source,
        "urlopen",
        lambda request, timeout: _response(
            {
                "title": "This is a PR",
                "body": "body",
                "comments": 0,
                "pull_request": {"url": "https://api.github.com/example"},
            }
        ),
    )
    with pytest.raises(IssueSourceError, match="pull request"):
        load_issue_source("https://github.com/owner/repo/issues/3")


def test_github_404_has_clear_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(source, "urlopen", fake_urlopen)
    with pytest.raises(IssueSourceError, match="not found"):
        load_issue_source("https://github.com/owner/repo/issues/404")
