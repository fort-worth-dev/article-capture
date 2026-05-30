from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    ARTICLE = "article"
    YOUTUBE = "youtube"


class Content(BaseModel):
    """Normalized output of an extractor: source facts + clean text.

    Every extractor, whatever the source, returns this same shape. Think of it
    as the common DTO the rest of the pipeline depends on.
    """

    url: str
    source_type: SourceType
    title: str
    text: str
    author: str | None = None


class Summary(BaseModel):
    """The AI's analysis of a piece of content -- the schema models must fill.

    The field descriptions below are sent to the model verbatim as a tool schema,
    so they double as the prompt for each field. Tightening a description here is
    the cheapest way to improve output quality.
    """

    tldr: str = Field(description="A one or two sentence summary of the core point.")
    key_points: list[str] = Field(
        description="3-7 concise bullet points capturing the most important takeaways."
    )
    tags: list[str] = Field(
        description="3-6 lowercase topical tags, e.g. 'rag', 'multi-agent', 'evals', 'mcp'."
    )
