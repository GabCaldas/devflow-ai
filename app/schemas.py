from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    diff: str = Field(..., description="Diff or code to review", min_length=1)
    language: str | None = Field(None, description="Language hint, e.g. python")


class ReviewIssue(BaseModel):
    severity: str = Field(..., description="low | medium | high")
    category: str = Field(..., description="bug | security | style | performance")
    message: str
    suggestion: str | None = None


class ReviewResponse(BaseModel):
    summary: str
    issues: list[ReviewIssue]
    provider_used: str


class TriageResponse(BaseModel):
    risk_level: str = Field(..., description="low | medium | high")
    affected_area: str
    summary: str
    recommended_agents: list[str]
    provider_used: str = ""


class TestGenResponse(BaseModel):
    framework: str
    tests_code: str
    notes: str | None = None
    provider_used: str = ""


class DocResponse(BaseModel):
    documentation: str
    provider_used: str = ""


class RetrievedSource(BaseModel):
    path: str
    start_line: int
    end_line: int
    score: float


class AnalysisRequest(BaseModel):
    diff: str = Field(..., min_length=1)
    language: str | None = None


class AnalysisResponse(BaseModel):
    triage: TriageResponse
    review: ReviewResponse | None = None
    tests: TestGenResponse | None = None
    docs: DocResponse | None = None
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)


class PRRequest(BaseModel):
    url: str | None = None
    owner: str | None = None
    repo: str | None = None
    number: int | None = None
    language: str | None = None
    post_comment: bool = False


class PRAnalysisResponse(AnalysisResponse):
    pr: str
    comment_url: str | None = None
