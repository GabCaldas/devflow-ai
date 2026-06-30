from app.graph import AnalysisState


def to_markdown(state: AnalysisState) -> str:
    parts: list[str] = ["## DevFlow AI - automated review"]

    triage = state.get("triage", {})
    if triage:
        parts.append(
            f"**Risk:** {triage.get('risk_level', '?')} - "
            f"**Area:** {triage.get('affected_area', '?')}\n\n"
            f"{triage.get('summary', '')}"
        )

    sources = state.get("retrieved_sources", [])
    if sources:
        source_names = [
            f"`{source['path']}:{source['start_line']}-{source['end_line']}`"
            for source in sources
        ]
        parts.append("**Repository context:** " + ", ".join(source_names))

    review = state.get("review")
    if review:
        parts.append("### Code review")
        if review["issues"]:
            parts.append("| Severity | Category | Problem | Suggestion |")
            parts.append("|---|---|---|---|")
            for issue in review["issues"]:
                sugg = (issue.get("suggestion") or "").replace("\n", " ")
                msg = issue["message"].replace("\n", " ")
                parts.append(
                    f"| {issue['severity']} | {issue['category']} | {msg} | {sugg} |"
                )
        else:
            parts.append("No issues found.")

    tests = state.get("tests")
    if tests:
        parts.append(f"### Suggested tests ({tests['framework']})")
        parts.append(f"```\n{tests['tests_code']}\n```")

    docs = state.get("docs")
    if docs:
        parts.append("### Suggested documentation")
        parts.append(docs["documentation"])

    parts.append("\n---\n*Generated automatically - review before applying.*")
    return "\n\n".join(parts)
