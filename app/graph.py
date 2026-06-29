"""Grafo multi-agente (LangGraph) — o orquestrador do DevFlow AI.

Fluxo:
    START -> orquestrador (triagem + decisao do plano)
              -> [agentes recomendados, em PARALELO]
                   -> END

O orquestrador roda o Triador para classificar o PR e escolher quais agentes
executar. As arestas condicionais fazem o fan-out dinamico: so rodam os agentes
recomendados, e eles rodam concorrentemente. Cada agente escreve numa chave
propria do estado, entao nao ha conflito de escrita.
"""
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.documenter import generate_docs
from app.agents.reviewer import review_code
from app.agents.testgen import generate_tests
from app.agents.triager import triage_pr


class AnalysisState(TypedDict, total=False):
    """Estado compartilhado que flui pelo grafo."""
    diff: str
    language: Optional[str]
    plan: list[str]          # agentes a executar (decidido pelo orquestrador)
    triage: dict
    review: dict
    tests: dict
    docs: dict


# ----- Nos do grafo -----

async def orchestrator_node(state: AnalysisState) -> dict:
    """Tria o PR e define o plano de execucao."""
    triage = await triage_pr(state["diff"], state.get("language"))
    valid = {"reviewer", "testgen", "documenter"}
    plan = [a for a in triage.recommended_agents if a in valid] or ["reviewer"]
    return {"triage": triage.model_dump(), "plan": plan}


async def reviewer_node(state: AnalysisState) -> dict:
    result = await review_code(state["diff"], state.get("language"))
    return {"review": result.model_dump()}


async def testgen_node(state: AnalysisState) -> dict:
    result = await generate_tests(state["diff"], state.get("language"))
    return {"tests": result.model_dump()}


async def documenter_node(state: AnalysisState) -> dict:
    result = await generate_docs(state["diff"], state.get("language"))
    return {"docs": result.model_dump()}


def route_from_orchestrator(state: AnalysisState) -> list[str]:
    """Fan-out: dispara em paralelo apenas os agentes do plano."""
    return state["plan"]


def build_graph():
    """Monta e compila o grafo multi-agente."""
    g = StateGraph(AnalysisState)

    g.add_node("orchestrator", orchestrator_node)
    g.add_node("reviewer", reviewer_node)
    g.add_node("testgen", testgen_node)
    g.add_node("documenter", documenter_node)

    g.add_edge(START, "orchestrator")
    g.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        ["reviewer", "testgen", "documenter"],
    )
    for agent in ("reviewer", "testgen", "documenter"):
        g.add_edge(agent, END)

    return g.compile()


# Compilado uma vez na importacao (reutilizado a cada requisicao)
graph = build_graph()


async def analyze(diff: str, language: str | None = None) -> AnalysisState:
    """Executa o pipeline completo e retorna o estado final."""
    return await graph.ainvoke({"diff": diff, "language": language})
