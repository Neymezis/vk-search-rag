from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_n: int = Field(default=10, ge=1, le=100)


class SearchResultItem(BaseModel):
    score: float
    post_id: str
    url: str
    text: str
    date: int | None = None
    likes: int | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    context_docs: int = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[SearchResultItem]
