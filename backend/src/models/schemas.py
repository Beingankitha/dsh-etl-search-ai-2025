from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Dataset(BaseModel):
    """
    Canonical dataset metadata shape used across ETL, search indexing, and API responses.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    file_identifier: str = Field(..., min_length=1, description="Dataset file identifier")
    title: str = Field(..., min_length=1, description="Dataset title")
    abstract: str = Field("", description="Dataset abstract/summary")

    topic_category: list[str] = Field(default_factory=list, description="ISO topic categories")
    keywords: list[str] = Field(default_factory=list, description="Free-text keywords/tags")

    lineage: str | None = Field(default=None, description="Provenance / lineage description")
    supplemental_info: str | None = Field(
        default=None, description="Supplemental information / notes"
    )


class SearchResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    dataset: Dataset
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized relevance score 0..1")


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    query: str = Field(..., min_length=1, description="User search query")
    top_k: int = Field(10, ge=1, le=100, description="Max number of results")


class SearchResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    query: str
    results: list[SearchResult] = Field(default_factory=list)


class ChatMessage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    messages: list[ChatMessage] = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50, description="How many sources to retrieve for grounding")


class ChatResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    message: ChatMessage
    sources: list[SearchResult] = Field(default_factory=list)