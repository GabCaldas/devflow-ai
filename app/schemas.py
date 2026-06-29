"""Contratos da API (entrada/saida). Pydantic valida tudo automaticamente
e gera a documentacao OpenAPI — parte do bom design de REST API.
"""
from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """O que o cliente envia para revisao."""
    diff: str = Field(..., description="Diff/codigo a ser revisado", min_length=1)
    language: str | None = Field(None, description="Linguagem (opcional, ex: python)")


class ReviewIssue(BaseModel):
    """Um achado individual da revisao."""
    severity: str = Field(..., description="low | medium | high")
    category: str = Field(..., description="bug | security | style | performance")
    message: str
    suggestion: str | None = None


class ReviewResponse(BaseModel):
    """Resposta estruturada do agente revisor."""
    summary: str
    issues: list[ReviewIssue]
    provider_used: str


# ===== Fase 2: agentes adicionais e orquestracao =====

class TriageResponse(BaseModel):
    """Saida do Orquestrador/Triador: classifica o PR e define o plano."""
    risk_level: str = Field(..., description="low | medium | high")
    affected_area: str = Field(..., description="area/tema afetado pela mudanca")
    summary: str
    recommended_agents: list[str] = Field(
        ..., description="quais agentes rodar: reviewer | testgen | documenter"
    )
    provider_used: str = ""


class TestGenResponse(BaseModel):
    """Saida do agente Gerador de Testes."""
    framework: str = Field(..., description="ex: pytest, unittest, jest")
    tests_code: str = Field(..., description="codigo dos testes gerados")
    notes: str | None = None
    provider_used: str = ""


class DocResponse(BaseModel):
    """Saida do agente Documentador."""
    documentation: str = Field(..., description="docstrings/markdown gerados")
    provider_used: str = ""


class AnalysisRequest(BaseModel):
    """Entrada do pipeline multi-agente completo."""
    diff: str = Field(..., description="Diff/codigo a analisar", min_length=1)
    language: str | None = None


class AnalysisResponse(BaseModel):
    """Relatorio agregado de todos os agentes que rodaram."""
    triage: TriageResponse
    review: ReviewResponse | None = None
    tests: TestGenResponse | None = None
    docs: DocResponse | None = None


# ===== Fase 5: trigger via Pull Request do GitHub =====

class PRRequest(BaseModel):
    """Entrada do trigger de PR. Aceita a URL OU owner/repo/number."""
    url: str | None = Field(None, description="URL do PR, ex: https://github.com/o/r/pull/1")
    owner: str | None = None
    repo: str | None = None
    number: int | None = None
    language: str | None = None
    post_comment: bool = Field(False, description="se True, posta a revisao no PR")


class PRAnalysisResponse(AnalysisResponse):
    """Analise do PR + link do comentario postado (se houver)."""
    pr: str
    comment_url: str | None = None
