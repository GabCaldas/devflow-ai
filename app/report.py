"""Formata o resultado do pipeline como um comentario markdown para o PR."""
from app.graph import AnalysisState

SEV_LABEL = {"high": "alta", "medium": "media", "low": "baixa"}


def to_markdown(state: AnalysisState) -> str:
    """Monta o corpo do comentario a partir do estado final do grafo."""
    parts: list[str] = ["## DevFlow AI — revisao automatica"]

    triage = state.get("triage", {})
    if triage:
        parts.append(
            f"**Risco:** {triage.get('risk_level', '?')} · "
            f"**Area:** {triage.get('affected_area', '?')}\n\n"
            f"{triage.get('summary', '')}"
        )

    review = state.get("review")
    if review:
        parts.append("### Revisao de codigo")
        if review["issues"]:
            parts.append("| Severidade | Categoria | Problema | Sugestao |")
            parts.append("|---|---|---|---|")
            for issue in review["issues"]:
                sev = SEV_LABEL.get(issue["severity"], issue["severity"])
                sugg = (issue.get("suggestion") or "").replace("\n", " ")
                msg = issue["message"].replace("\n", " ")
                parts.append(f"| {sev} | {issue['category']} | {msg} | {sugg} |")
        else:
            parts.append("Nenhum problema encontrado.")

    tests = state.get("tests")
    if tests:
        parts.append(f"### Testes sugeridos ({tests['framework']})")
        parts.append(f"```\n{tests['tests_code']}\n```")

    docs = state.get("docs")
    if docs:
        parts.append("### Documentacao sugerida")
        parts.append(docs["documentation"])

    parts.append("\n---\n*Gerado automaticamente — revise antes de aplicar.*")
    return "\n\n".join(parts)
