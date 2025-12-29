import pytest
from pydantic import ValidationError

from src.models import (
    ChatMessage,
    ChatRequest,
    Dataset,
    SearchRequest,
    SearchResult,
)


def test_dataset_requires_identifier_and_title():
    with pytest.raises(ValidationError):
        Dataset(file_identifier="", title="x")

    with pytest.raises(ValidationError):
        Dataset(file_identifier="abc", title="")


def test_search_request_defaults():
    req = SearchRequest(query="rainfall")
    assert req.top_k == 10


def test_search_result_score_range():
    ds = Dataset(file_identifier="id-1", title="Title", abstract="A")

    SearchResult(dataset=ds, score=0.0)
    SearchResult(dataset=ds, score=1.0)

    with pytest.raises(ValidationError):
        SearchResult(dataset=ds, score=-0.1)

    with pytest.raises(ValidationError):
        SearchResult(dataset=ds, score=1.1)


def test_chat_request_requires_messages():
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])

    req = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])
    assert req.top_k == 5

def test_dataset_forbids_extra_fields():
    with pytest.raises(ValidationError):
        Dataset(file_identifier="id-1", title="t", extra_field="nope")  # type: ignore[arg-type]