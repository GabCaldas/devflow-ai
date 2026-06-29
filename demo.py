"""Demo de linha de comando do DevFlow AI.

Roda o pipeline multi-agente sobre um diff e imprime um relatorio formatado.
Ideal para gravar um GIF de demonstracao para o portfolio.

Uso:
    python demo.py                      # usa samples/sample_diff.diff
    python demo.py caminho/arquivo.diff # usa um diff proprio
"""
import asyncio
import sys

# garante UTF-8 na saida (consoles legados do Windows usam cp1252 e quebram
# com acentos). Faz o demo rodar em qualquer terminal.
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
            "[bold cyan]DevFlow AI[/bold cyan] — revisao multi-agente de codigo",
            subtitle=f"analisando [dim]{path}[/dim]",
        )
    )
    with console.status("[bold green]Agentes trabalhando...", spinner="dots"):
        state = await analyze(diff, language="python")

    # ----- Triagem -----
    t = state["triage"]
    console.print(
        Panel(
            f"[bold]Risco:[/bold] {t['risk_level']}\n"
            f"[bold]Area:[/bold] {t['affected_area']}\n"
            f"[bold]Resumo:[/bold] {t['summary']}\n"
            f"[bold]Plano:[/bold] {', '.join(t['recommended_agents'])}",
            title="Orquestrador / Triagem",
            border_style="magenta",
        )
    )

    # ----- Revisor -----
    if review := state.get("review"):
        table = Table(title="Revisor", show_lines=True, expand=True)
        table.add_column("Sev", style="bold", width=8)
        table.add_column("Categoria", width=12)
        table.add_column("Problema")
        for issue in review["issues"]:
            color = SEVERITY_COLOR.get(issue["severity"], "white")
            table.add_row(
                f"[{color}]{issue['severity']}[/{color}]",
                issue["category"],
                issue["message"],
            )
        console.print(table)

    # ----- Testes -----
    if tests := state.get("tests"):
        console.print(
            Panel(
                Syntax(tests["tests_code"].strip(), "python", theme="monokai",
                       line_numbers=False),
                title=f"Gerador de Testes ({tests['framework']})",
                border_style="green",
            )
        )

    # ----- Documentacao -----
    if docs := state.get("docs"):
        console.print(
            Panel(
                docs["documentation"],
                title="Documentador",
                border_style="blue",
            )
        )

    console.print("[dim]Concluido. Todos os agentes via free tier (Groq).[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
