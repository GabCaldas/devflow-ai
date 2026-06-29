import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from app.graph import analyze

console = Console()

SEVERITY_COLOR = {"high": "red", "medium": "yellow", "low": "cyan"}


def load_diff() -> tuple[str, str]:
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/sample_diff.diff"
    with open(path, encoding="utf-8") as f:
        return f.read(), path


async def main() -> None:
    diff, path = load_diff()

    console.print(
        Panel.fit(
            "[bold cyan]DevFlow AI[/bold cyan] - multi-agent code review",
            subtitle=f"analyzing [dim]{path}[/dim]",
        )
    )
    with console.status("[bold green]Agents working...", spinner="dots"):
        state = await analyze(diff, language="python")

    t = state["triage"]
    console.print(
        Panel(
            f"[bold]Risk:[/bold] {t['risk_level']}\n"
            f"[bold]Area:[/bold] {t['affected_area']}\n"
            f"[bold]Summary:[/bold] {t['summary']}\n"
            f"[bold]Plan:[/bold] {', '.join(t['recommended_agents'])}",
            title="Orchestrator / Triage",
            border_style="magenta",
        )
    )

    if review := state.get("review"):
        table = Table(title="Reviewer", show_lines=True, expand=True)
        table.add_column("Sev", style="bold", width=8)
        table.add_column("Category", width=12)
        table.add_column("Problem")
        for issue in review["issues"]:
            color = SEVERITY_COLOR.get(issue["severity"], "white")
            table.add_row(
                f"[{color}]{issue['severity']}[/{color}]",
                issue["category"],
                issue["message"],
            )
        console.print(table)

    if tests := state.get("tests"):
        console.print(
            Panel(
                Syntax(tests["tests_code"].strip(), "python", theme="monokai",
                       line_numbers=False),
                title=f"Test Generator ({tests['framework']})",
                border_style="green",
            )
        )

    if docs := state.get("docs"):
        console.print(
            Panel(docs["documentation"], title="Documenter", border_style="blue")
        )

    console.print("[dim]Done. All agents run on a free tier (Groq).[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
