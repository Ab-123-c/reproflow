import json
from types import SimpleNamespace

from reproflow.agent.openai_provider import OpenAIProvider
from reproflow.repo.context import RepositorySnapshot
from reproflow.repo.models import RepositoryProfile


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=next(self.outputs))


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


def test_openai_provider_uses_structured_responses_and_local_validation() -> None:
    bug_json = json.dumps(
        {
            "title": "unicode bug",
            "description": "fails",
            "expected_behavior": None,
            "actual_behavior": None,
            "reproduction_steps": [],
            "environment": {},
            "error_messages": ["UnicodeEncodeError"],
            "missing_information": [],
        }
    )
    client = FakeClient([bug_json])
    provider = OpenAIProvider(model="test-model", client=client)
    repo = RepositorySnapshot(
        profile=RepositoryProfile(root="/repo", language="Python"), files={}
    )
    bug = provider.parse_bug("fails on unicode", repo)
    assert bug.title == "unicode bug"
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["store"] is False
    assert call["text"]["format"]["type"] == "json_schema"
