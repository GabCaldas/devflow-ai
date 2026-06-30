import asyncio
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.documenter import generate_docs
from app.agents.reviewer import review_code
from app.agents.testgen import generate_tests
from app.agents.triager import triage_pr
from app.config import settings
from app.observability import observe
from app.rag.index import format_context, retrieve_for_diff


class AnalysisState(TypedDict, total=False):
    diff: str
    language: Optional[str]
    plan: list[str]
    triage: dict
    review: dict
    tests: dict
    docs: dict
    rag_context: str
    retrieved_sources: list[dict]


async def retrieve_context_node(state: AnalysisState) -> dict:
    if not settings.rag_enabled:
        return {"rag_context": "", "retrieved_sources": []}
    chunks = await asyncio.to_thread(
        retrieve_for_diff,
        settings.codebase_path,
        state["diff"],
        top_k=settings.rag_top_k,
        max_files=settings.rag_max_files,
    )
    return {
        "rag_context": format_context(chunks, settings.rag_max_context_chars),
        "retrieved_sources": [chunk.as_dict() for chunk in chunks],
    }


async def orchestrator_node(state: AnalysisState) -> dict:
    triage = await triage_pr(state["diff"], state.get("language"))
    valid = {"reviewer", "testgen", "documenter"}
    plan = [a for a in triage.recommended_agents if a in valid] or ["reviewer"]
    return {"triage": triage.model_dump(), "plan": plan}


async def reviewer_node(state: AnalysisState) -> dict:
    result = await review_code(
        state["diff"], state.get("language"), state.get("rag_context", "")
    )
    return {"review": result.model_dump()}


async def testgen_node(state: AnalysisState) -> dict:
    result = await generate_tests(
        state["diff"], state.get("language"), state.get("rag_context", "")
    )
    return {"tests": result.model_dump()}


async def documenter_node(state: AnalysisState) -> dict:
    result = await generate_docs(
        state["diff"], state.get("language"), state.get("rag_context", "")
    )
    return {"docs": result.model_dump()}


def route_from_orchestrator(state: AnalysisState) -> list[str]:
    return state["plan"]


def build_graph():
    g = StateGraph(AnalysisState)

    g.add_node("retrieve_context", retrieve_context_node)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("reviewer", reviewer_node)
    g.add_node("testgen", testgen_node)
    g.add_node("documenter", documenter_node)

    g.add_edge(START, "retrieve_context")
    g.add_edge("retrieve_context", "orchestrator")
    g.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        ["reviewer", "testgen", "documenter"],
    )
    for agent in ("reviewer", "testgen", "documenter"):
        g.add_edge(agent, END)

    return g.compile()


graph = build_graph()


@observe(name="analyze")
async def analyze(diff: str, language: str | None = None) -> AnalysisState:
    return await graph.ainvoke({"diff": diff, "language": language})
