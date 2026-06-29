from fastapi import FastAPI, HTTPException

from app.agents.reviewer import review_code
from app.config import settings
from app.graph import AnalysisState, analyze
from app.llm.client import LLMError
from app.report import to_markdown
from app.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    PRAnalysisResponse,
    PRRequest,
    ReviewRequest,
    ReviewResponse,
)
from app.sources.github import (
    GitHubError,
    fetch_pr_diff,
    parse_pr_url,
    post_pr_comment,
)

app = FastAPI(
    title="DevFlow AI",
    description="Agentic platform that supports the software development lifecycle.",
    version="0.2.0",
)


def _build_response(state: AnalysisState) -> AnalysisResponse:
    return AnalysisResponse(
        triage=state["triage"],
        review=state.get("review"),
        tests=state.get("tests"),
        docs=state.get("docs"),
    )


@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok"}


@app.post("/review", response_model=ReviewResponse, tags=["agents"])
async def review(req: ReviewRequest) -> ReviewResponse:
    try:
        return await review_code(req.diff, req.language)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")


@app.post("/analyze", response_model=AnalysisResponse, tags=["agents"])
async def analyze_diff(req: AnalysisRequest) -> AnalysisResponse:
    try:
        state = await analyze(req.diff, req.language)
        return _build_response(state)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")


@app.post("/analyze/pr", response_model=PRAnalysisResponse, tags=["github"])
async def analyze_pull_request(req: PRRequest) -> PRAnalysisResponse:
    try:
        if req.url:
            owner, repo, number = parse_pr_url(req.url)
        elif req.owner and req.repo and req.number:
            owner, repo, number = req.owner, req.repo, req.number
        else:
            raise HTTPException(400, "Provide 'url' OR 'owner'+'repo'+'number'.")

        diff = await fetch_pr_diff(owner, repo, number)
        diff = diff[: settings.max_diff_chars]

        state = await analyze(diff, req.language)

        comment_url = None
        if req.post_comment:
            comment_url = await post_pr_comment(
                owner, repo, number, to_markdown(state)
            )

        base = _build_response(state)
        return PRAnalysisResponse(
            **base.model_dump(),
            pr=f"{owner}/{repo}#{number}",
            comment_url=comment_url,
        )
    except GitHubError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub: {exc}")
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")
